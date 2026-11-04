"""HTTP client for TopTex catalog API (v3)."""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

TOPTEX_USAGE_RIGHTS = ("b2b_b2c", "b2b_uniquement", "b2c_uniquement")


class TopTexConfigError(Exception):
    pass


class TopTexAPIError(Exception):
    def __init__(self, message: str, status: int | None = None, body: str = ""):
        super().__init__(message)
        self.status = status
        self.body = body


class TopTexClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ):
        self.base_url = (base_url or getattr(settings, "TOPTEX_BASE_URL", "") or "").rstrip("/")
        self.api_key = api_key or getattr(settings, "TOPTEX_API_KEY", "") or ""
        self.username = username or getattr(settings, "TOPTEX_USERNAME", "") or ""
        self.password = password or getattr(settings, "TOPTEX_PASSWORD", "") or ""
        self._token: str = ""

    def ensure_configured(self) -> None:
        missing = []
        if not self.base_url:
            missing.append("TOPTEX_BASE_URL")
        if not self.api_key:
            missing.append("TOPTEX_API_KEY")
        if not self.username:
            missing.append("TOPTEX_USERNAME")
        if not self.password:
            missing.append("TOPTEX_PASSWORD")
        if missing:
            raise TopTexConfigError(
                "TopTex non configurato. Imposta in .env: " + ", ".join(missing),
            )

    def authenticate(self) -> str:
        self.ensure_configured()
        payload = json.dumps({"username": self.username, "password": self.password}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/v3/authenticate",
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "x-api-key": self.api_key,
            },
        )
        data = self._read_json(req)
        token = (data.get("token") or "").strip()
        if not token:
            raise TopTexAPIError("Authenticate TopTex: risposta senza token.", body=json.dumps(data))
        self._token = token
        return token

    def get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        if not self._token:
            self.authenticate()
        query = urllib.parse.urlencode(params or {})
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{query}"
        req = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Accept": "application/json",
                "x-api-key": self.api_key,
                "x-toptex-authorization": self._token,
            },
        )
        return self._read_json(req)

    def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        if not self._token:
            self.authenticate()
        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "x-api-key": self.api_key,
                "x-toptex-authorization": self._token,
            },
        )
        return self._read_json(req)

    def download_url(self, url: str) -> tuple[bytes, str]:
        """GET a URL with TopTex auth (packshots often require the same headers as the API)."""
        if not self._token:
            self.authenticate()
        req = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                "x-api-key": self.api_key,
                "x-toptex-authorization": self._token,
            },
        )
        try:
            with urllib.request.urlopen(
                req,
                timeout=int(getattr(settings, "TOPTEX_HTTP_TIMEOUT", 120)),
            ) as resp:
                data = resp.read()
                content_type = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
                return data, content_type
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise TopTexAPIError(
                f"TopTex download HTTP {exc.code}",
                status=exc.code,
                body=body,
            ) from exc
        except urllib.error.URLError as exc:
            raise TopTexAPIError(f"TopTex download rete: {exc.reason}") from exc

    def fetch_inventory_by_catalog_ref(self, catalog_ref: str) -> list[dict[str, Any]]:
        """Stock by Codice Padre — GET /v3/products/inventory, then POST search fallbacks."""
        catalog_ref = (catalog_ref or "").strip()
        if not catalog_ref:
            return []
        items = self._fetch_paginated_by_catalog_reference(
            "/v3/products/inventory",
            catalog_ref,
        )
        if items:
            return items
        items = self._fetch_paginated_by_catalog_reference(
            "/v3/products/stocks",
            catalog_ref,
        )
        if items:
            return items
        return self._post_inventory_catalog_search(catalog_ref)

    def _post_inventory_catalog_search(self, catalog_ref: str) -> list[dict[str, Any]]:
        paths = (
            "/v3/products/inventory/search",
            "/v3/inventory/search",
            "/v3/products/stocks/search",
        )
        bodies = (
            {"catalogReferences": [catalog_ref]},
            {"catalog_references": [catalog_ref]},
            {"catalogReference": catalog_ref},
            {"references": [catalog_ref]},
        )
        for path in paths:
            for body in bodies:
                try:
                    data = self.post(path, body)
                except TopTexAPIError as exc:
                    if exc.status in (404, 405, 400, 422):
                        continue
                    raise
                batch = _list_records_from_toptex_response(data)
                if batch:
                    return batch
        return []

    def fetch_prices_by_catalog_ref(self, catalog_ref: str) -> list[dict[str, Any]]:
        """GET /v3/products/price — fallback when catalog/all omits publicUnitPrice."""
        return self._fetch_paginated_by_catalog_reference(
            "/v3/products/price",
            catalog_ref,
        )

    def _fetch_paginated_by_catalog_reference(
        self,
        path: str,
        catalog_ref: str,
    ) -> list[dict[str, Any]]:
        catalog_ref = (catalog_ref or "").strip()
        if not catalog_ref:
            return []
        page_size = str(max(1, int(getattr(settings, "TOPTEX_API_PAGE_SIZE", 100))))
        max_pages = int(getattr(settings, "TOPTEX_MAX_CATALOG_PAGES", 500))
        items: list[dict[str, Any]] = []
        page_number = 1
        lang = getattr(settings, "TOPTEX_LANG", "it") or "it"
        while page_number <= max_pages:
            params = {
                "catalog_reference": catalog_ref,
                "page_size": page_size,
                "page_number": str(page_number),
                "lang": lang,
            }
            try:
                data = self.get(path, params)
            except TopTexAPIError as exc:
                if page_number == 1 and exc.status in (400, 404):
                    return []
                raise
            batch = _list_records_from_toptex_response(data)
            if not batch:
                break
            items.extend(batch)
            if len(batch) < int(page_size):
                break
            page_number += 1
        return items

    def fetch_products_all_for_usage_right(
        self,
        usage_right: str,
        *,
        lang: str = "it",
        display_prices: bool = True,
    ) -> list[dict[str, Any]]:
        if usage_right not in TOPTEX_USAGE_RIGHTS:
            raise ValueError(
                f"usage_right must be one of: {', '.join(TOPTEX_USAGE_RIGHTS)}",
            )
        base_params = {
            "usage_right": usage_right,
            "lang": lang,
            "display_prices": "1" if display_prices else "0",
        }
        max_pages = int(getattr(settings, "TOPTEX_MAX_CATALOG_PAGES", 500))
        items: list[dict[str, Any]] = []

        data = self.get("/v3/products/all", base_params)
        batch = _catalog_batch_items(data)
        items.extend(batch)

        total_pages = _catalog_total_pages(data)
        page_size_hint = _catalog_page_size(data)
        seen_refs = _catalog_refs(batch)

        if total_pages is not None:
            try:
                pages = min(int(total_pages), max_pages)
            except (TypeError, ValueError):
                pages = 1
            for page in range(2, pages + 1):
                page_data = self.get(
                    "/v3/products/all",
                    {**base_params, "page": str(page)},
                )
                page_batch = _catalog_batch_items(page_data)
                if not page_batch:
                    break
                items.extend(page_batch)
            return items

        full_page_threshold = page_size_hint or 50
        if len(batch) < full_page_threshold:
            return items

        page = 2
        while page <= max_pages:
            page_data = self.get(
                "/v3/products/all",
                {**base_params, "page": str(page)},
            )
            page_batch = _catalog_batch_items(page_data)
            if not page_batch:
                break
            new_items = [
                item for item in page_batch
                if _catalog_item_ref(item) not in seen_refs
            ]
            if not new_items:
                break
            for item in new_items:
                ref = _catalog_item_ref(item)
                if ref:
                    seen_refs.add(ref)
            items.extend(new_items)
            if len(page_batch) < full_page_threshold:
                break
            page += 1

        return items

    def fetch_products_all_usage_rights(
        self,
        usage_rights: tuple[str, ...] | None = None,
        *,
        lang: str = "it",
        display_prices: bool = True,
    ) -> dict[str, list[dict[str, Any]]]:
        rights = usage_rights or _configured_usage_rights()
        result: dict[str, list[dict[str, Any]]] = {}
        for usage_right in rights:
            logger.info("TopTex fetch catalog usage_right=%s", usage_right)
            result[usage_right] = self.fetch_products_all_for_usage_right(
                usage_right,
                lang=lang,
                display_prices=display_prices,
            )
        return result

    def _read_json(self, req: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(req, timeout=int(getattr(settings, "TOPTEX_HTTP_TIMEOUT", 120))) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            message = body
            try:
                parsed = json.loads(body)
                message = parsed.get("message") or parsed.get("errorMessage") or body
            except json.JSONDecodeError:
                pass
            raise TopTexAPIError(
                f"TopTex HTTP {exc.code}: {message}",
                status=exc.code,
                body=body,
            ) from exc
        except urllib.error.URLError as exc:
            raise TopTexAPIError(f"TopTex rete: {exc.reason}") from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TopTexAPIError("Risposta TopTex non JSON.") from exc
        if isinstance(data, list):
            return {"items": data}
        if not isinstance(data, dict):
            raise TopTexAPIError("Risposta TopTex non valida.")
        return data


def _catalog_item_ref(item: dict[str, Any]) -> str:
    return (item.get("catalogReference") or item.get("productReference") or "").strip().lower()


def _catalog_refs(items: list[dict[str, Any]]) -> set[str]:
    refs: set[str] = set()
    for item in items:
        ref = _catalog_item_ref(item)
        if ref:
            refs.add(ref)
    return refs


def _catalog_batch_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [i for i in extract_toptex_list_payload(data) if isinstance(i, dict)]


def _catalog_total_pages(data: dict[str, Any]) -> Any:
    return (
        data.get("totalPages")
        or data.get("total_pages")
        or data.get("nbPages")
        or data.get("pageCount")
    )


def _catalog_page_size(data: dict[str, Any]) -> int | None:
    for key in ("pageSize", "page_size", "limit", "perPage"):
        raw = data.get(key)
        if raw is not None:
            try:
                return int(raw)
            except (TypeError, ValueError):
                continue
    return None


def extract_toptex_list_payload(data: Any) -> list[Any]:
    """Normalize TopTex list responses (items, inventoryItems, …)."""
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in (
        "items",
        "inventoryItems",
        "inventory",
        "stockItems",
        "stocks",
        "variants",
        "skus",
        "prices",
        "priceItems",
        "data",
        "results",
        "content",
    ):
        value = data.get(key)
        if isinstance(value, list):
            return value
    return []


def _list_records_from_toptex_response(data: Any) -> list[dict[str, Any]]:
    """Price/inventory rows: array, wrapped list, or single SKU record."""
    if isinstance(data, list):
        return [i for i in data if isinstance(i, dict)]
    if isinstance(data, dict) and (data.get("sku") or data.get("SKU")):
        return [data]
    batch = extract_toptex_list_payload(data)
    return [i for i in batch if isinstance(i, dict)]


def _configured_usage_rights() -> tuple[str, ...]:
    raw = getattr(settings, "TOPTEX_USAGE_RIGHTS", "") or ""
    if raw.strip():
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        for part in parts:
            if part not in TOPTEX_USAGE_RIGHTS:
                raise TopTexConfigError(
                    f"TOPTEX_USAGE_RIGHTS invalido: {part}. "
                    f"Usa: {', '.join(TOPTEX_USAGE_RIGHTS)}",
                )
        return tuple(parts)
    return TOPTEX_USAGE_RIGHTS
