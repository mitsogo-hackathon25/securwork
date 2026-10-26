from decimal import Decimal

from django.test import override_settings
from django.test import TestCase

from store.csv_import import (
    BRAND_FILTER_NONE,
    brand_filter_key,
    canonical_brand_key,
    canonical_filter_key,
    import_parsed_rows,
    normalize_column_key,
    parse_and_validate_csv,
    scan_csv_brands,
    scan_csv_column_values,
    scan_csv_columns,
)
from store.models import Category, Product, ProductVariant


NATIVE_CSV = """sku_prodotto,marca,categoria,nome_it,nome_en,descrizione_it,descrizione_en,taglia,colore,prezzo,scorte,sku_variante
SW-POLO-01,ExampleBrand,polo,Polo da lavoro,Work polo,Polo IT,Polo EN,M,Blu,29.90,10,SW-POLO-01-M-BLU
"""

SUPPLIER_CSV = """Codice Padre;Merceologica;Categoria;SCategoria;SKU;EAN;In Arrivo;Colore;Taglia;Descrizione;Foto;Unico;Confezione;Imballo;Prezzo Unico;Prezzo Confezione;Prezzo Imballo
PAD-01;Abbigliamento da lavoro;Pantaloni;Cargo;PAD-01-M-NE;123;5;Nero;M;Pantalone cargo;https://example.com/p.jpg;1;6;24;19,90;110;400
PAD-01;Abbigliamento da lavoro;Pantaloni;Cargo;PAD-01-L-NE;124;3;Nero;L;Pantalone cargo;https://example.com/p.jpg;1;6;24;19,90;110;400
"""

SUPPLIER_CSV_DIFFERENT_PHOTOS = """Codice Padre;Merceologica;Categoria;SCategoria;SKU;EAN;In Arrivo;Colore;Taglia;Descrizione;Foto;Unico;Confezione;Imballo;Prezzo Unico;Prezzo Confezione;Prezzo Imballo
ACE-1;Abbigliamento;Giacche;Softshell;ACE-1-S-BL;1;1;Blu;S;ACE MESH;https://example.com/ace-blue.jpg;1;1;1;10,00;10;10
ACE-1;Abbigliamento;Giacche;Softshell;ACE-1-M-NE;2;1;Nero;M;ACE MESH;https://example.com/ace-black.jpg;1;1;1;10,00;10;10
"""

SUPPLIER_CSV_SAME_DESCRIPTION_DIFFERENT_PARENT = """Codice Padre;Merceologica;Categoria;SCategoria;SKU;EAN;In Arrivo;Colore;Taglia;Descrizione;Foto;Unico;Confezione;Imballo;Prezzo Unico;Prezzo Confezione;Prezzo Imballo
p20 box;Payper;Accessori;Box;P20-S;1;1;Nero;S;CUSTOM PAYPER BOX;;1;1;1;5,00;5;5
P40 box;Payper;Accessori;Box;P40-M;2;1;Nero;M;CUSTOM PAYPER BOX;;1;1;1;8,00;8;8
"""

SUPPLIER_CSV_DUPLICATE_VARIANT_ROWS = """Codice Padre;Merceologica;Categoria;SCategoria;SKU;EAN;In Arrivo;Colore;Taglia;Descrizione;Foto;Unico;Confezione;Imballo;Prezzo Unico;Prezzo Confezione;Prezzo Imballo
AG 2086;Payper;Abbigliamento;Alta visibilità;AG 2086-UN-UNIQUE;1;10;UNIQUE;UN;Gilet test;;1;1;1;12,00;12;12
AG 2086;Payper;Abbigliamento;Alta visibilità;AG 2086-UN-UNIQUE;1;99;UNIQUE;UN;Gilet test;;1;1;1;12,00;12;12
"""

WHOLESALE_NATIVE_CSV = """sku_prodotto,marca,nome_it,nome_en,descrizione_it,descrizione_en,taglia,colore,prezzo,scorte,sku_variante,scategoria,ricamo_petto,ricamo_grande,dtf_petto,dtf_grande,url_immagini,url_mockup
k223_a,Brand,Polo uomo manica corta,Polo short,Polo IT,Polo EN,M,Blue,19.90,5,k223_a-M-BLU,Polo,Max formato 10x10 cm,Max formato 15x15 cm,Max formato 10x10 cm,Max formato A4,cdn.example.com/a.jpg,cdn.example.com/mock.jpg
k223_b,Brand,Polo uomo manica corta,Polo short,Polo IT,Polo EN,L,Blue,19.90,3,k223_b-L-BLU,Polo,no,no,no,no,cdn.example.com/b.jpg,
"""

ACE_MESH_TAB_CSV = """Codice Padre\tMerceologica\tCategoria\tSCategoria\tSKU\tEAN\tIn Arrivo\tColore\tTaglia\tDescrizione\tFoto\tUnico\tConfezione\tImballo\tPrezzo Unico\tPrezzo Confezione\tPrezzo Imballo
ACE MESH\tPAYPER\tABBIGLIAMENTO\tALTA VISIBILITÀ\tACE MESH-S-ARANCIO FLUO\t\t242\tARANCIO FLUO\tS\tACE MESH GILET A/V IN RETE TRASPIRANTE PAYPER\thttps://store.imacosrl.com/upload/immagini_prodotto/285/863940B65CE8000000000000810417000000000000000000.bmp\t1\t10\t50\t18.780\t18.780\t18.780
ACE MESH\tPAYPER\tABBIGLIAMENTO\tALTA VISIBILITÀ\tACE MESH-M-ARANCIO FLUO\t\t475\tARANCIO FLUO\tM\tACE MESH GILET A/V IN RETE TRASPIRANTE PAYPER\thttps://store.imacosrl.com/upload/immagini_prodotto/285/863940B65CE8000000000000810417000000000000000000.bmp\t1\t10\t50\t18.780\t18.780\t18.780
ACE MESH\tPAYPER\tABBIGLIAMENTO\tALTA VISIBILITÀ\tACE MESH-L-ARANCIO FLUO\t\t665\tARANCIO FLUO\tL\tACE MESH GILET A/V IN RETE TRASPIRANTE PAYPER\thttps://store.imacosrl.com/upload/immagini_prodotto/285/863940B65CE8000000000000810417000000000000000000.bmp\t1\t10\t50\t18.780\t18.780\t18.780
"""


@override_settings(USE_SQLITE=True)
class CsvImportTests(TestCase):
    def setUp(self):
        polo = Category.objects.create(slug="polo", section=Category.Section.WORKWEAR)
        polo.set_current_language("it")
        polo.name = "Polo"
        polo.save()
        polo.set_current_language("en")
        polo.name = "Polo"
        polo.save()

    def test_wholesale_csv_imports_with_column_value_filter(self):
        col = normalize_column_key("colore")
        rows, errors = parse_and_validate_csv(
            WHOLESALE_NATIVE_CSV.encode("utf-8"),
            column_value_filter=(col, {canonical_filter_key("Blue"), "blue"}),
        )
        self.assertEqual(errors, [], errors)
        self.assertEqual(len(rows), 2)

    def test_wholesale_native_csv_tolerates_customization_and_urls(self):
        rows, errors = parse_and_validate_csv(WHOLESALE_NATIVE_CSV.encode("utf-8"))
        self.assertEqual(errors, [], errors)
        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[0]["image_urls"][0].startswith("https://"))
        self.assertTrue(rows[0]["embroidery_chest_enabled"])

    def test_native_csv_still_imports(self):
        rows, errors = parse_and_validate_csv(NATIVE_CSV.encode("utf-8"))
        self.assertEqual(errors, [])
        result = import_parsed_rows(rows)
        self.assertEqual(result["created_products"], 1)
        self.assertEqual(result["created_variants"], 1)
        product = Product.objects.get(sku="SW-POLO-01")
        self.assertEqual(product.brand, "ExampleBrand")
        self.assertEqual(product.variants.get().price, Decimal("29.90"))

    def test_supplier_csv_imports_parent_variants_and_categories(self):
        rows, errors = parse_and_validate_csv(SUPPLIER_CSV.encode("utf-8"))
        self.assertEqual(errors, [], errors)
        result = import_parsed_rows(rows)
        self.assertEqual(result["created_products"], 1)
        self.assertEqual(result["created_variants"], 2)
        product = Product.objects.get(sku="PAD-01")
        self.assertEqual(product.safe_translation_getter("name", language_code="it"), "Pantalone cargo")
        self.assertEqual(product.safe_translation_getter("name", language_code="en"), "Pantalone cargo")
        self.assertTrue(product.categories.filter(slug="pantaloni").exists())
        self.assertTrue(product.categories.filter(slug="cargo").exists())
        variants = list(ProductVariant.objects.filter(product=product).order_by("size"))
        self.assertEqual(variants[0].size, "L")
        self.assertEqual(variants[1].size, "M")
        self.assertEqual(variants[1].price, Decimal("19.90"))
        self.assertEqual(variants[1].stock_quantity, 5)
        self.assertEqual(variants[1].sku, "PAD-01-M-NE")

    def test_supplier_csv_allows_different_foto_per_variant(self):
        rows, errors = parse_and_validate_csv(SUPPLIER_CSV_DIFFERENT_PHOTOS.encode("utf-8"))
        self.assertEqual(errors, [], errors)
        self.assertEqual(
            rows[0]["image_urls"],
            [
                "https://example.com/ace-blue.jpg",
                "https://example.com/ace-black.jpg",
            ],
        )

    def test_supplier_csv_allows_same_description_different_parent_code(self):
        rows, errors = parse_and_validate_csv(
            SUPPLIER_CSV_SAME_DESCRIPTION_DIFFERENT_PARENT.encode("utf-8"),
        )
        self.assertEqual(errors, [], errors)
        self.assertEqual(len({r["product_sku"].lower() for r in rows}), 2)
        self.assertEqual(len(rows), 2)

    def test_supplier_csv_skips_row_without_price(self):
        csv_text = """Codice Padre;Merceologica;Categoria;SCategoria;SKU;EAN;In Arrivo;Colore;Taglia;Descrizione;Foto;Unico;Confezione;Imballo;Prezzo Unico;Prezzo Confezione;Prezzo Imballo
OK-1;Payper;Cat;Sub;OK-1-M;1;5;Nero;M;Prodotto ok;;1;1;1;10,00;;
SKIP-1;Payper;Cat;Sub;SKIP-1-M;2;1;Nero;M;Senza prezzo;;1;1;1;;;
"""
        rows, errors = parse_and_validate_csv(csv_text.encode("utf-8"))
        self.assertEqual(errors, [], errors)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["variant_sku"], "OK-1-M")

    def test_supplier_csv_dedupes_duplicate_variant_sku_last_wins(self):
        rows, errors = parse_and_validate_csv(
            SUPPLIER_CSV_DUPLICATE_VARIANT_ROWS.encode("utf-8"),
        )
        self.assertEqual(errors, [], errors)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["variant_sku"], "AG 2086-UN-UNIQUE")
        self.assertEqual(rows[0]["stock"], 99)

    def test_scan_csv_brands_groups_by_marca(self):
        csv_text = """sku_prodotto,marca,categoria,nome_it,nome_en,descrizione_it,descrizione_en,taglia,colore,prezzo,scorte,sku_variante
A-1,Alpha,polo,Polo A,Polo A,D,D,M,Blu,10,1,A-1-M
A-2,Alpha,polo,Polo A2,Polo A2,D,D,L,Blu,10,1,A-2-L
B-1,Beta,polo,Polo B,Polo B,D,D,M,Rosso,12,2,B-1-M
"""
        brands, errors = scan_csv_brands(csv_text.encode("utf-8"))
        self.assertEqual(errors, [])
        by_name = {b["name"]: b for b in brands}
        self.assertEqual(by_name["Alpha"]["product_count"], 2)
        self.assertEqual(by_name["Alpha"]["row_count"], 2)
        self.assertEqual(by_name["Beta"]["product_count"], 1)

    def test_parse_and_validate_csv_filters_by_brand(self):
        csv_text = """sku_prodotto,marca,categoria,nome_it,nome_en,descrizione_it,descrizione_en,taglia,colore,prezzo,scorte,sku_variante
A-1,Alpha,polo,Polo A,Polo A,D,D,M,Blu,10,1,A-1-M
B-1,Beta,polo,Polo B,Polo B,D,D,M,Rosso,12,2,B-1-M
"""
        rows, errors = parse_and_validate_csv(
            csv_text.encode("utf-8"),
            brand_keys_filter={"alpha"},
        )
        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["product_sku"], "A-1")

    def test_brand_filter_none_key_for_empty_marca(self):
        row = {"marca": ""}
        self.assertEqual(brand_filter_key(row), BRAND_FILTER_NONE)

    def test_native_csv_empty_categoria_uses_default_category(self):
        csv_text = """sku_prodotto,marca,categoria,nome_it,nome_en,descrizione_it,descrizione_en,taglia,colore,prezzo,scorte,sku_variante
IMP-1,Brand,,Prodotto test,Test product,Desc IT,Desc EN,M,Nero,9.90,1,IMP-1-M-N
"""
        rows, errors = parse_and_validate_csv(csv_text.encode("utf-8"))
        self.assertEqual(errors, [], errors)
        result = import_parsed_rows(rows)
        self.assertEqual(result["created_products"], 1)
        product = Product.objects.get(sku="IMP-1")
        self.assertTrue(product.categories.filter(slug="generale").exists())

    def test_supplier_minimal_columns_without_scategoria_header(self):
        csv_text = """Codice Padre;SKU;Descrizione;Colore;Taglia;Categoria;Prezzo Unico
P1;P1-M;Pantalone;Nero;M;Pantaloni;19,90
"""
        rows, errors = parse_and_validate_csv(csv_text.encode("utf-8"))
        self.assertEqual(errors, [], errors)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["supplier_category"], "Pantaloni")

    def test_supplier_parent_sku_keeps_one_brand_across_variants(self):
        csv_text = """Codice Padre;Merceologica;Categoria;SCategoria;SKU;Colore;Taglia;Descrizione;Prezzo Unico
AY 7438;PAYPER;PROMOSOLUTION;Polo;AY7438-S;Nero;S;Polo test;10,00
AY 7438;Abbigliamento;PROMOSOLUTION;Polo;AY7438-M;Nero;M;Polo test;10,00
"""
        rows, errors = parse_and_validate_csv(csv_text.encode("utf-8"))
        self.assertEqual(errors, [], errors)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["brand"], "PAYPER")
        self.assertEqual(rows[1]["brand"], "PAYPER")

    def test_variant_rows_inherit_parent_price(self):
        csv_text = """Codice Padre;SKU;Descrizione;Colore;Taglia;Prezzo Unico
P1;P1-S;Polo test;Nero;S;19,90
P1;P1-M;Polo test;Nero;M;
P1;P1-L;Polo test;Nero;L;
"""
        rows, errors = parse_and_validate_csv(csv_text.encode("utf-8"))
        self.assertEqual(errors, [], errors)
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(r["price"] == Decimal("19.90") for r in rows))

    def test_import_without_category_columns_defaults_generale(self):
        csv_text = """Codice Padre;SKU;Descrizione;Colore;Taglia;Prezzo Unico
P1;P1-M;Polo test;Nero;M;19,90
"""
        rows, errors = parse_and_validate_csv(csv_text.encode("utf-8"))
        self.assertEqual(errors, [], errors)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["supplier_category"], "Generale")

    def test_duplicate_price_headers_prefers_numeric_value(self):
        csv_text = """Codice Padre;Merceologica;Categoria;SCategoria;SKU;Descrizione;Colore;Taglia;price;Prezzo;Prezzo Unico
P1;Abbigliamento;Generale;Polo;PS_BO5O;Polo test;Nero;M;19,90;PS_BO5O-FS_BLACK;21,00
"""
        rows, errors = parse_and_validate_csv(csv_text.encode("utf-8"))
        self.assertEqual(errors, [], errors)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["price"], Decimal("19.90"))

    def test_import_ignores_sku_misplaced_in_prezzo_column(self):
        csv_text = """Codice Padre;Merceologica;Categoria;SCategoria;SKU;Descrizione;Colore;Taglia;Prezzo;Prezzo Unico
P1;Abbigliamento;Generale;Polo;PS_BO5O-FS_BLACK;Polo test;Nero;M;PS_BO5O-FS_BLACK;19,90
"""
        rows, errors = parse_and_validate_csv(csv_text.encode("utf-8"))
        self.assertEqual(errors, [], errors)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["price"], Decimal("19.90"))

    def test_scan_column_values_minimal_supplier_without_merceologica(self):
        csv_text = """Codice Padre;SKU;Descrizione;Colore;Taglia;Prezzo Unico
P1;P1-M;Polo test;Blu;M;10,00 EUR
P2;P2-L;Polo 2;Nero;L;12,50
"""
        values, errors = scan_csv_column_values(csv_text.encode("utf-8"), "colore")
        self.assertEqual(errors, [], errors)
        self.assertGreaterEqual(len(values), 2)

    def test_scan_csv_columns_lists_headers(self):
        csv_text = """Codice Padre;Merceologica;Categoria;SKU;Colore;Taglia;Descrizione;Prezzo Unico
P1;Payper;Polo;P1-M;Blu;M;Polo;10,00
"""
        columns, errors = scan_csv_columns(csv_text.encode("utf-8"))
        self.assertEqual(errors, [])
        keys = {c["key"] for c in columns}
        self.assertIn("merceologica", keys)
        self.assertIn("categoria", keys)

    def test_column_filter_marca_uses_inferred_brand(self):
        csv_text = """Codice Padre;Merceologica;Categoria;SCategoria;SKU;Colore;Taglia;Descrizione;Prezzo Unico
P1;;Kariban;Polo;P1-M;Blu;M;Polo;10,00
"""
        col = "marca"
        values, errors = scan_csv_column_values(csv_text.encode("utf-8"), col)
        self.assertEqual(errors, [])
        self.assertEqual(len(values), 1)
        rows, parse_errors = parse_and_validate_csv(
            csv_text.encode("utf-8"),
            column_value_filter=(col, {values[0]["key"], values[0]["name"]}),
        )
        self.assertEqual(parse_errors, [], parse_errors)
        self.assertEqual(len(rows), 1)

    def test_scan_csv_column_values_and_filter_import(self):
        csv_text = """Codice Padre;Merceologica;Categoria;SCategoria;SKU;Colore;Taglia;Descrizione;Prezzo Unico
P1;Abbigliamento;Kariban;Polo;P1-M;Blu;M;Polo;10,00
P2;Abbigliamento;Dickies;Polo;P2-M;Nero;L;Polo 2;12,00
"""
        col = normalize_column_key("Categoria")
        values, errors = scan_csv_column_values(csv_text.encode("utf-8"), col)
        self.assertEqual(errors, [])
        self.assertEqual(len(values), 2)
        rows, parse_errors = parse_and_validate_csv(
            csv_text.encode("utf-8"),
            column_value_filter=(col, {canonical_brand_key("Kariban"), "kariban"}),
        )
        self.assertEqual(parse_errors, [], parse_errors)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["product_sku"], "P1")

    def test_scan_csv_brands_uses_categoria_when_merceologica_is_section(self):
        csv_text = """Codice Padre;Merceologica;Categoria;SCategoria;SKU;Colore;Taglia;Descrizione;Prezzo Unico
P1;Abbigliamento da lavoro;Kariban;Polo;P1-M;Blu;M;Polo test;10,00
P2;Abbigliamento da lavoro;Dickies;Pantaloni;P2-M;Nero;L;Pant test;12,00
"""
        brands, errors = scan_csv_brands(csv_text.encode("utf-8"))
        self.assertEqual(errors, [])
        keys = {b["key"] for b in brands}
        self.assertIn(canonical_brand_key("Kariban"), keys)
        self.assertIn(canonical_brand_key("Dickies"), keys)

    def test_parse_filters_by_brand_with_categoria_brand(self):
        csv_text = """Codice Padre;Merceologica;Categoria;SCategoria;SKU;Colore;Taglia;Descrizione;Prezzo Unico
P1;Abbigliamento da lavoro;Kariban;Polo;P1-M;Blu;M;Polo test;10,00
P2;Abbigliamento da lavoro;Dickies;Polo;P2-M;Nero;L;Polo 2;12,00
"""
        rows, errors = parse_and_validate_csv(
            csv_text.encode("utf-8"),
            brand_keys_filter={canonical_brand_key("Kariban"), "kariban"},
        )
        self.assertEqual(errors, [], errors)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["product_sku"], "P1")

    def test_scan_csv_brands_uses_supplier_merceologica_as_brand(self):
        brands, errors = scan_csv_brands(ACE_MESH_TAB_CSV.encode("utf-8"))
        self.assertEqual(errors, [])
        names = {b["name"].lower() for b in brands}
        self.assertIn("payper", names)
        self.assertNotIn("senza marca", names)

    def test_supplier_tab_separated_ace_mesh_sample(self):
        rows, errors = parse_and_validate_csv(ACE_MESH_TAB_CSV.encode("utf-8"))
        self.assertEqual(errors, [], errors)
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(r["product_sku"] == "ACE MESH" for r in rows))
        self.assertEqual(rows[0]["price"], Decimal("18.780"))
        self.assertEqual(rows[0]["stock"], 242)
        self.assertEqual(rows[1]["size"], "M")
