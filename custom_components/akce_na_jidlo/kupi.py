"""Parser akčních nabídek z kupi.cz a společné pomocné funkce.

Modul nezávisí na Home Assistantu, aby šel snadno testovat.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

try:  # lxml je řádově rychlejší než vestavěný html.parser
    import lxml  # noqa: F401

    _LXML = True
except ImportError:  # pragma: no cover - závisí na instalaci HA
    _LXML = False

from .const import CHAIN_ALIASES, KUPI_BASE_URL, ONLINE_SHOPS

MONTHS = {
    "ledna": 1,
    "leden": 1,
    "unora": 2,
    "unor": 2,
    "brezna": 3,
    "brezen": 3,
    "dubna": 4,
    "duben": 4,
    "kvetna": 5,
    "kveten": 5,
    "cervna": 6,
    "cerven": 6,
    "cervence": 7,
    "cervenec": 7,
    "srpna": 8,
    "srpen": 8,
    "zari": 9,
    "rijna": 10,
    "rijen": 10,
    "listopadu": 11,
    "listopad": 11,
    "prosince": 12,
    "prosinec": 12,
    # slovensky
    "januara": 1,
    "januar": 1,
    "februara": 2,
    "februar": 2,
    "marca": 3,
    "marec": 3,
    "aprila": 4,
    "april": 4,
    "maja": 5,
    "maj": 5,
    "juna": 6,
    "jun": 6,
    "jula": 7,
    "jul": 7,
    "augusta": 8,
    "august": 8,
    "septembra": 9,
    "september": 9,
    "oktobra": 10,
    "oktober": 10,
    "novembra": 11,
    "november": 11,
    "decembra": 12,
    "december": 12,
}

_NUM = r"\d+(?:[,.]\d+)?"

LOYALTY_WORDS = (
    "cleny klubu",
    "s kartou",
    "s aplikaci",
    "s aplikaciou",
    "lidl plus",
    "clubcard",
    "moje billa",
    "moja billa",
    "billa club",
    "muj albert",
    "penny karta",
    "vernostni",
    "kartou coop",
)


def clean_text(text: str | None) -> str:
    """Sjednotí mezery (včetně nezlomitelných)."""
    if not text:
        return ""
    return " ".join(str(text).replace("\xa0", " ").split())


def normalize(text: str | None) -> str:
    """Malá písmena bez diakritiky."""
    text = unicodedata.normalize("NFKD", clean_text(text).lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def to_float(value: str) -> float:
    return float(value.replace(" ", "").replace(",", "."))


def parse_price(text: str | None) -> float | None:
    match = re.search(rf"({_NUM})\s*(?:Kč|,-|€)", clean_text(text))
    if not match:
        match = re.search(rf"({_NUM})", clean_text(text))
    return to_float(match.group(1)) if match else None


def parse_percentage(text: str | None) -> float | None:
    match = re.search(rf"({_NUM})\s*%", clean_text(text))
    return to_float(match.group(1)) if match else None


# množství -> (násobek základní jednotky, základní jednotka)
_UNITS = {
    "kg": (1.0, "kg"),
    "g": (0.001, "kg"),
    "dkg": (0.01, "kg"),
    "l": (1.0, "l"),
    "ml": (0.001, "l"),
    "cl": (0.01, "l"),
    "dl": (0.1, "l"),
}
_UNIT_RE = r"(kg|dkg|g|ml|cl|dl|l)\b"
_PIECES_RE = re.compile(r"(\d+)\s*(?:ks|kusu|kusy|kus|kusov|pack|-pack|x)\b")


def parse_quantity(*texts: str | None) -> tuple[float | None, str | None]:
    """Celkové množství balení: "4 x 125 g" -> (0.5, "kg"), "1 l" -> (1.0, "l"), "10 ks" -> (10, "ks")."""
    for raw in texts:
        text = normalize(raw).replace("×", "x")
        if not text:
            continue
        multi = re.search(rf"(\d+)\s*x\s*({_NUM})\s*{_UNIT_RE}", text)
        if multi:
            factor, unit = _UNITS[multi.group(3)]
            return round(int(multi.group(1)) * to_float(multi.group(2)) * factor, 4), unit
        single = re.search(rf"({_NUM})\s*{_UNIT_RE}", text)
        if single:
            factor, unit = _UNITS[single.group(2)]
            return round(to_float(single.group(1)) * factor, 4), unit
        pieces = _PIECES_RE.search(text)
        if pieces and int(pieces.group(1)) > 0:
            return float(pieces.group(1)), "ks"
    return None, None


def parse_unit_price(text: str | None) -> tuple[float | None, str | None]:
    """'39,80 Kč / 1 kg' -> (39.8, "kg"); '5,90 Kč / 100 g' -> (59.0, "kg")."""
    norm = normalize(text)
    match = re.search(
        rf"({_NUM})\s*(?:kc|€|eur)\s*/\s*({_NUM})?\s*(kg|dkg|g|ml|cl|dl|l|ks)\b", norm
    )
    if not match:
        return None, None
    price = to_float(match.group(1))
    qty = to_float(match.group(2)) if match.group(2) else 1.0
    if match.group(3) == "ks":
        return (round(price / qty, 2) if qty else None), "ks"
    factor, unit = _UNITS[match.group(3)]
    qty *= factor
    return (round(price / qty, 2) if qty else None), unit


def _partial_date(text: str, today: date) -> date | None:
    match = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.(?:\s*(\d{4}))?", text)
    if match:
        day, month = int(match.group(1)), int(match.group(2))
        year = int(match.group(3)) if match.group(3) else None
    else:
        match = re.search(r"(\d{1,2})\.\s*([a-z]+)", text)
        if not match or match.group(2) not in MONTHS:
            return None
        day, month, year = int(match.group(1)), MONTHS[match.group(2)], None
    try:
        parsed = date(year or today.year, month, day)
    except ValueError:
        return None
    if year is None and parsed < today - timedelta(days=180):
        parsed = date(today.year + 1, month, day)
    elif year is None and parsed > today + timedelta(days=180):
        parsed = date(today.year - 1, month, day)
    return parsed


def parse_validity(text: str | None, today: date) -> tuple[date | None, date | None]:
    """Převede text platnosti ("st 23. 9. – út 29. 9.", "dnes končí"…) na (od, do)."""
    norm = normalize(text)
    if not norm:
        return None, None
    if "dnes konci" in norm:
        return today, today
    if "zitra konci" in norm or "zajtra konci" in norm:
        return today, today + timedelta(days=1)
    if "plati do" in norm or "platnost do" in norm or norm.startswith("do "):
        return today, _partial_date(norm, today)
    both = re.search(r"\bod\s+(.+?)\s+do\s+(.+)", norm)
    if both:
        return _partial_date(both.group(1), today), _partial_date(both.group(2), today)
    if norm.startswith("od ") or "plati od" in norm or "platnost od" in norm:
        return _partial_date(norm, today), None
    parts = re.split(r"\s+[–-]\s+|\s*[–-]\s*(?=[a-z]{2}\s*\d|\d)", norm, maxsplit=1)
    if len(parts) == 2:
        return _partial_date(parts[0], today), _partial_date(parts[1], today)
    single = _partial_date(norm, today)
    return today, single


def chain_key(shop: str | None) -> str:
    """'Albert Hypermarket' -> 'albert'."""
    norm = normalize(shop)
    for key in sorted(CHAIN_ALIASES, key=len, reverse=True):
        if re.search(rf"(?<![a-z]){re.escape(key)}(?![a-z])", norm):
            return key
    return norm.split(" ")[0] if norm else ""


def is_online_shop(shop: str | None) -> bool:
    norm = normalize(shop)
    return any(word in norm for word in ONLINE_SHOPS)


def has_loyalty(text: str | None) -> bool:
    norm = normalize(text)
    return any(word in norm for word in LOYALTY_WORDS)


def _text(node: Any, selector: str) -> str:
    found = node.select_one(selector) if node is not None else None
    return clean_text(found.get_text(" ", strip=True)) if found else ""


def _wrap_info(wrap: Any) -> dict[str, str]:
    title = wrap.select_one(".product_name h2 a[title], .product_name a[title], h2 a[title]")
    name = clean_text(title["title"]) if title else _text(wrap, ".product_name h2, .product_name")
    amount = _text(wrap, ".product_name .nowrap, .product_name .amount")
    if name and amount and normalize(amount) not in normalize(name):
        name = f"{name} {amount}".strip()
    link = wrap.select_one(".product_name a[href], .product_image a[href], a[href*='/sleva/']")
    img = wrap.select_one(".product_image img, img")
    image = ""
    if img is not None:
        image = str(img.get("data-src") or img.get("src") or "")
        if image.startswith("data:"):
            image = ""
    return {
        "name": name,
        "url": urljoin(KUPI_BASE_URL, link["href"]) if link else "",
        "image": urljoin(KUPI_BASE_URL, image) if image else "",
    }


def _product_lookup(soup: BeautifulSoup) -> dict[str, dict[str, str]]:
    """Názvy produktů podle data-product-id.

    Atribut data-product-id mají i drobné prvky uvnitř bloku produktu (tlačítka
    „hlídat“, oblíbené…). Ty nesmí přepsat název nalezený v hlavním bloku.
    """
    products: dict[str, dict[str, str]] = {}
    wraps = soup.select(".product--wrap[data-product-id]") + soup.select("[data-product-id]")
    for wrap in wraps:
        product_id = str(wrap.get("data-product-id"))
        if products.get(product_id, {}).get("name"):
            continue
        info = _wrap_info(wrap)
        if info["name"] or product_id not in products:
            products[product_id] = info
    return products


def name_from_url(href: str | None) -> str:
    """'/sleva/mleko-polotucne-trvanlive' -> 'mleko polotucne trvanlive'."""
    if not href or "/sleva/" not in href:
        return ""
    slug = href.split("/sleva/", 1)[1].split("?")[0].split("#")[0].strip("/").split("/")[0]
    return clean_text(slug.replace("-", " "))


def _ancestor_name(row: Any) -> str:
    """Název z nejbližšího bloku produktu nad řádkem slevy."""
    node = row
    for _ in range(4):
        node = node.parent
        if node is None or node.name in ("body", "html", "main"):
            return ""
        classes = " ".join(node.get("class") or [])
        if not node.has_attr("data-product-id") and "product" not in classes:
            continue
        info = _wrap_info(node)
        if info["name"]:
            return info["name"]
        link = node.select_one("a[href*='/sleva/']")
        if link and (name := name_from_url(link["href"])):
            return name
    return ""


def _cls_text(node: Any, css_class: str, inner: str | None = None) -> str:
    """Text prvku s danou třídou – rychlejší než CSS selektor (find místo select)."""
    found = node.find(class_=css_class)
    if found is None:
        return ""
    if inner:
        found = found.find(inner) or found
    return clean_text(found.get_text(" ", strip=True))


def make_soup(html: str | BeautifulSoup) -> BeautifulSoup:
    """HTML -> BeautifulSoup; rychlejší lxml, pokud je v Home Assistantu k dispozici."""
    if isinstance(html, BeautifulSoup):
        return html
    if _LXML:
        try:
            return BeautifulSoup(html, "lxml")
        except Exception:  # noqa: BLE001 - poškozené HTML zkusíme vestavěným parserem
            pass
    return BeautifulSoup(html, "html.parser")


def parse_offers(html: str | BeautifulSoup, source_url: str, today: date) -> list[dict[str, Any]]:
    """Najde všechny akční nabídky (řádky slev) na stránce kupi.cz."""
    soup = make_soup(html)
    products = _product_lookup(soup)
    page_title = _text(soup, "h1")
    # nadpis stránky je název produktu jen na detailu (/sleva/...), ne na výpisu
    is_detail = "/sleva/" in source_url
    # nadpisy sekcí stránky ("Akce dle ceny", "Výsledky hledání"…) nejsou názvy produktů
    headings = {
        normalize(h.get_text(" ", strip=True))
        for h in soup.select("h1, h2, h3, h4")
        if not h.find_parent(attrs={"data-product-id": True})
        and not h.find_parent(class_=re.compile("product"))
    }
    if is_detail:
        headings.discard(normalize(page_title))
    offers: list[dict[str, Any]] = []

    for row in soup.select(".discount_row"):
        product_id = str(row.get("data-product") or "")
        if not product_id:
            parent = row.find_parent(attrs={"data-product-id": True})
            product_id = str(parent.get("data-product-id")) if parent else ""
        product = products.get(product_id, {})

        def row_link_href(row=row) -> str:
            link = row.find("a", class_="product_link_history", href=True) or row.find(
                "a", href=re.compile("/sleva/")
            )
            return link["href"] if link else ""

        # záložní zdroje názvu počítáme až když jsou potřeba (CSS selektory jsou drahé)
        candidates = (
            lambda p=product: p.get("name"),
            lambda r=row: _ancestor_name(r),
            lambda f=row_link_href: name_from_url(f()),
            lambda p=product: name_from_url(p.get("url")),
        )
        name = next((c for get in candidates if (c := get()) and normalize(c) not in headings), "")
        if not name and is_detail:
            name = page_title
        shop = _cls_text(row, "discounts_shop_name", inner="a")
        price = parse_price(
            _cls_text(row, "discount_price_value") or _cls_text(row, "discount_price")
        )
        if not name or not shop or price is None:
            continue

        amount = _cls_text(row, "discount_amount").lstrip("/ ").strip()
        validity = _cls_text(row, "discounts_validity")
        valid_from, valid_to = parse_validity(validity, today)
        link = next(
            (
                found
                for css_class in ("btn_link_leaflet", "product_link_history")
                if (found := row.find("a", class_=css_class, href=True)) is not None
            ),
            None,
        )
        offers.append(
            build_offer(
                product_id=product_id or normalize(name),
                discount_id=str(row.get("data-discount") or ""),
                name=name,
                shop=shop,
                price=price,
                amount=amount,
                unit_text=_cls_text(row, "price_per_unit"),
                discount=parse_percentage(_cls_text(row, "discount_percentage")),
                validity=validity,
                valid_from=valid_from,
                valid_to=valid_to,
                loyalty=has_loyalty(row.get_text(" ", strip=True)),
                url=urljoin(KUPI_BASE_URL, link["href"])
                if link
                else (product.get("url") or source_url),
                image=product.get("image", ""),
            )
        )
    if not is_detail:
        # stejný "název" u mnoha různých produktů = nadpis stránky/sekce, ne jméno produktu
        ids_by_name: dict[str, set[str]] = {}
        for offer in offers:
            ids_by_name.setdefault(normalize(offer["product"]), set()).add(offer["product_id"])
        generic = {name for name, ids in ids_by_name.items() if len(ids) > 3}
        offers = [o for o in offers if normalize(o["product"]) not in generic]
    return offers


def build_offer(
    *,
    product_id: str,
    discount_id: str,
    name: str,
    shop: str,
    price: float,
    amount: str,
    unit_text: str,
    discount: float | None,
    validity: str,
    valid_from: date | None,
    valid_to: date | None,
    loyalty: bool,
    url: str,
    image: str,
    source: str = "kupi",
    old_price: float | None = None,
    currency: str = "CZK",
) -> dict[str, Any]:
    unit_price, unit = parse_unit_price(unit_text)
    quantity, qty_unit = parse_quantity(amount, name)
    if unit_price is None and quantity:
        unit_price, unit = round(price / quantity, 2), qty_unit
    if old_price is not None and old_price <= price:
        old_price = None
    if old_price is None and discount and 0 < discount < 100:
        old_price = round(price / (1 - discount / 100), 2)
    if discount is None and old_price:
        discount = round((1 - price / old_price) * 100)
    return {
        "id": f"{source}|{normalize(shop)}|{product_id}|{discount_id or price}",
        "source": source,
        "sources": [source],
        "currency": currency,
        "product_id": product_id,
        "product": name,
        "shop": shop,
        "chain": chain_key(shop),
        "online": is_online_shop(shop),
        "price": round(price, 2),
        "old_price": old_price,
        "discount_percent": discount,
        "amount": amount,
        "quantity": quantity,
        "unit": unit,
        "unit_price": unit_price,
        "validity": validity,
        "valid_from": valid_from.isoformat() if valid_from else None,
        "valid_to": valid_to.isoformat() if valid_to else None,
        "loyalty": loyalty,
        "url": url,
        "image": image,
    }
