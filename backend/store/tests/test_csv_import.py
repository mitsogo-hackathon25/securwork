from decimal import Decimal

from django.test import override_settings
from django.test import TestCase

from store.csv_import import import_parsed_rows, parse_and_validate_csv
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

    def test_supplier_tab_separated_ace_mesh_sample(self):
        rows, errors = parse_and_validate_csv(ACE_MESH_TAB_CSV.encode("utf-8"))
        self.assertEqual(errors, [], errors)
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(r["product_sku"] == "ACE MESH" for r in rows))
        self.assertEqual(rows[0]["price"], Decimal("18.780"))
        self.assertEqual(rows[0]["stock"], 242)
        self.assertEqual(rows[1]["size"], "M")
