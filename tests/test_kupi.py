from datetime import date

from akce_na_jidlo.generic import parse_generic
from akce_na_jidlo.kupi import (
    chain_key,
    parse_offers,
    parse_quantity,
    parse_unit_price,
    parse_validity,
)

TODAY = date(2026, 9, 26)

HTML = """
<h1>Výsledky hledání: mléko</h1>
<div class="product--wrap" data-product-id="11">
  <div class="product_image"><a href="/sleva/mleko-polotucne"><img data-src="/img/mleko.jpg" src="data:image/gif;base64,xx"></a></div>
  <div class="product_name"><h2><a title="Mléko polotučné trvanlivé" href="/sleva/mleko-polotucne">Mléko</a>
     <span class="nowrap">1&nbsp;l</span></h2></div>
  <div class="discount_row" data-product="11" data-discount="100">
    <div class="discounts_shop_name"><a href="/obchod/albert">Albert Hypermarket</a></div>
    <span class="discount_price_value">16,90&nbsp;Kč</span>
    <span class="discount_amount">/ 1 l</span>
    <span class="discount_percentage">–30 %</span>
    <span class="price_per_unit">16,90 Kč / 1 l</span>
    <span class="discounts_validity">st 23. 9. – út 29. 9.</span>
    <a class="btn_link_leaflet" href="/letak/albert">leták</a>
  </div>
  <div class="discount_row" data-product="11" data-discount="101">
    <div class="discounts_shop_name"><a>Lidl</a></div>
    <span class="discount_price_value">14,90 Kč</span>
    <span class="discount_amount">/ 1 l</span>
    <span class="discounts_validity">čt 24. 9. – ne 27. 9.</span>
    Platí pro členy klubu Lidl Plus
  </div>
</div>
<div class="product--wrap" data-product-id="12">
  <div class="product_name"><h2><a title="Máslo 82 %" href="/sleva/maslo">Máslo</a></h2></div>
  <div class="discount_row" data-product="12" data-discount="200">
    <div class="discounts_shop_name"><a>Penny Market</a></div>
    <span class="discount_price_value">39,90 Kč</span>
    <span class="discount_amount">/ 250 g</span>
    <span class="discounts_validity">dnes končí</span>
  </div>
</div>
"""


def test_parse_offers():
    offers = parse_offers(HTML, "https://www.kupi.cz/hledej?f=mleko", TODAY)
    assert len(offers) == 3
    albert, lidl, penny = offers
    assert albert["product"] == "Mléko polotučné trvanlivé 1 l"
    assert albert["chain"] == "albert"
    assert albert["price"] == 16.9
    assert albert["unit_price"] == 16.9 and albert["unit"] == "l"
    assert albert["discount_percent"] == 30
    assert albert["old_price"] == 24.14
    assert albert["valid_from"] == "2026-09-23" and albert["valid_to"] == "2026-09-29"
    assert albert["url"] == "https://www.kupi.cz/letak/albert"
    assert albert["image"] == "https://www.kupi.cz/img/mleko.jpg"
    assert not albert["loyalty"]
    assert lidl["loyalty"]
    assert penny["chain"] == "penny"
    assert penny["unit_price"] == 159.6 and penny["unit"] == "kg"
    assert penny["valid_to"] == "2026-09-26"


def test_quantity_and_unit_price():
    assert parse_quantity("4 x 125 g") == (0.5, "kg")
    assert parse_quantity("1,5 l") == (1.5, "l")
    assert parse_quantity("500 ml") == (0.5, "l")
    assert parse_quantity("10 ks") == (10.0, "ks")
    assert parse_quantity("") == (None, None)
    assert parse_unit_price("5,90 Kč / 100 g") == (59.0, "kg")
    assert parse_unit_price("19,90 Kč / 1 kg") == (19.9, "kg")
    assert parse_unit_price("2,50 Kč / 1 ks") == (2.5, "ks")
    assert parse_unit_price("1,18 € / l") == (1.18, "l")


def test_validity_and_chain():
    assert parse_validity("zítra končí", TODAY) == (TODAY, date(2026, 9, 27))
    assert parse_validity("od 1. 10.", TODAY) == (date(2026, 10, 1), None)
    assert chain_key("Tesco Express") == "tesco express"
    assert chain_key("Penny Market") == "penny"
    assert chain_key("COOP Jednota") == "coop"


def test_generic_jsonld():
    html = """<script type="application/ld+json">{"@type":"Product","name":"Chléb konzumní 1 kg",
      "offers":{"@type":"Offer","price":"29.90","priceCurrency":"CZK",
      "seller":{"name":"Kaufland"},"priceValidUntil":"2026-09-30"}}</script>"""
    offers = parse_generic(html, "https://example.cz/hledat?q=chleb", TODAY, "custom")
    assert len(offers) == 1
    assert offers[0]["shop"] == "Kaufland"
    assert offers[0]["price"] == 29.9
    assert offers[0]["unit_price"] == 29.9 and offers[0]["unit"] == "kg"
    # nabídka v eurech se v Česku zahodí
    assert parse_generic(html.replace("CZK", "EUR"), "https://x.cz", TODAY, "custom") == []


def test_generic_html_cards_sk():
    html = """<ul>
      <li class="card"><h3>Mlieko polotučné 1 l</h3><img alt="Tesco" src="/tesco.png">
        <span class="price">0,79 €</span><del>1,09 €</del><span>1,18 €/l</span></li>
    </ul>"""
    offers = parse_generic(html, "https://www.kimbino.sk/produkty/mlieko/", TODAY, "kimbino", "SK")
    assert len(offers) == 1
    offer = offers[0]
    assert offer["shop"] == "Tesco"
    assert offer["price"] == 0.79 and offer["old_price"] == 1.09
    assert offer["currency"] == "EUR"
