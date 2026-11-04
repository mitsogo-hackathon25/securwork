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
        data = self.get("/v3/products/all", base_params)
        items: list[dict[str, Any]] = list(data.get("items") or [])
        total_pages = data.get("totalPages") or data.get("total_pages")
        if total_pages is not None:
            try:
                pages = int(total_pages)
            except (TypeError, ValueError):
                pages = 1
            for page in range(2, pages + 1):
                params = {**base_params, "page": str(page)}
                page_data = self.get("/v3/products/all", params)
                items.extend(page_data.get("items") or [])
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
        if not isinstance(data, dict):
            raise TopTexAPIError("Risposta TopTex non valida.")
        return data


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
