import html
import json
import unittest
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]

class MarketplaceIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "data/mercadolivre-curado.json").read_text(encoding="utf-8"))
        self.page = (ROOT / "mercado-livre/index.html").read_text(encoding="utf-8")

    def test_marketplace_has_distinct_curated_products(self):
        products = self.data["products"]
        self.assertGreaterEqual(len(products), 2)
        self.assertEqual(len({p["id"] for p in products}), len(products))
        self.assertEqual(len({p["source_listing"] for p in products}), len(products))

    def test_affiliate_links_are_product_specific_and_preserved(self):
        for product in self.data["products"]:
            url = product["affiliate_url"]
            parsed = urlparse(url)
            self.assertIn(parsed.netloc, {"meli.la", "www.mercadolivre.com.br"})
            if parsed.netloc == "www.mercadolivre.com.br":
                self.assertIn("/p/MLB", parsed.path)
                full = parsed.query + "#" + parsed.fragment
                self.assertIn("matt_tool_id=48778863", full)
                self.assertIn("source=affiliate-profile", full)
            self.assertIn(html.escape(url, quote=True), self.page)

    def test_page_discloses_affiliation_and_does_not_store_price(self):
        self.assertIn("Publicidade · link de afiliado do Mercado Livre", self.page)
        self.assertNotIn("R$", self.page)
        self.assertGreaterEqual(self.page.count('rel="sponsored nofollow noopener"'), len(self.data["products"]))

    def test_product_images_and_sources_are_present(self):
        for product in self.data["products"]:
            self.assertTrue(product["image"].startswith("https://http2.mlstatic.com/"))
            self.assertIn(product["image"], self.page.replace("&amp;", "&"))
            self.assertTrue(product["manufacturer_source"].startswith("https://"))

if __name__ == "__main__":
    unittest.main()
