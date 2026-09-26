"""Vyhodnocení hledání: které akce odpovídají zadané potravině a kam pro ni jít.

Modul nezávisí na Home Assistantu, aby šel snadno testovat.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any
from urllib.parse import quote_plus

from .const import (
    MAX_ITEMS,
    MAX_QUERY_LENGTH,
    SHOP_TYPE_ONLINE,
    SHOP_TYPE_PHYSICAL,
    SORT_DISTANCE,
    SORT_UNIT,
)
from .kupi import clean_text, normalize

# slova, která při porovnání názvů nic neznamenají
STOP_WORDS = {"a", "i", "s", "se", "v", "na", "do", "z", "ze", "k", "o", "pro", "bez", "the"}


def split_items(raw: Any) -> list[str]:
    """ "mléko, chleba\\nmáslo" nebo ["mléko", "chleba"] -> seznam potravin (bez duplicit)."""
    if raw is None:
        return []
    parts = raw if isinstance(raw, (list, tuple)) else [raw]
    items: list[str] = []
    seen: set[str] = set()
    for part in parts:
        for item in re.split(r"[,;\n\r]+", str(part)):
            item = clean_text(item).strip(" .-–")[:MAX_QUERY_LENGTH]
            key = normalize(item)
            if item and key not in seen:
                seen.add(key)
                items.append(item)
    return items[:MAX_ITEMS]


def query_slug(item: str) -> str:
    """'Mléko polotučné' -> 'mleko-polotucne'."""
    return re.sub(r"[^a-z0-9]+", "-", normalize(item)).strip("-")


def query_param(item: str) -> str:
    """'Mléko polotučné' -> 'ml%C3%A9ko+polotu%C4%8Dn%C3%A9' (pro ?q=)."""
    return quote_plus(clean_text(item).lower())


def _words(text: str) -> list[str]:
    return [w for w in re.split(r"[^a-z0-9]+", normalize(text)) if w]


def _stem(token: str) -> str:
    """Zkrácení kvůli skloňování: mléko/mléka, rohlík/rohlíky, kuřecí prsa/prsní."""
    if token.isdigit():
        return token
    if len(token) >= 7:
        return token[:-2]
    if len(token) >= 4:
        return token[:-1]
    return token


def query_tokens(item: str) -> list[str]:
    tokens = [t for t in _words(item) if t not in STOP_WORDS]
    return [_stem(t) for t in tokens] or [_stem(t) for t in _words(item)]


def matches(item: str, product: str) -> bool:
    """Obsahuje název produktu všechna slova hledané potraviny (i v jiném tvaru)?"""
    tokens = query_tokens(item)
    if not tokens:
        return False
    words = _words(product)
    return all(any(word.startswith(token) for word in words) for token in tokens)


def _relevance(item: str, product: str) -> int:
    """Menší = lepší: hledané slovo je na začátku názvu („Mléko polotučné“ před „Mléčná čokoláda s mlékem“)."""
    tokens = query_tokens(item)
    words = _words(product)
    for index, word in enumerate(words[:6]):
        if tokens and word.startswith(tokens[0]):
            return index
    return 6


def sort_key(sort_by: str):
    def key(offer: dict[str, Any]) -> tuple:
        price = offer.get("price") or 0
        unit = offer.get("unit_price")
        if sort_by == SORT_UNIT:
            return (unit is None, unit if unit is not None else price, price)
        if sort_by == SORT_DISTANCE:
            distance = offer.get("distance_km")
            return (distance is None, distance if distance is not None else 0, price)
        return (price, unit if unit is not None else price)

    return key


def filter_offers(
    item: str,
    offers: list[dict[str, Any]],
    today: date,
    *,
    shop_type: str,
    exclude_loyalty: bool,
    include_upcoming: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Vrátí (platné akce, připravované akce) odpovídající potravině."""
    today_iso = today.isoformat()
    current: list[dict[str, Any]] = []
    upcoming: list[dict[str, Any]] = []
    seen: set[tuple] = set()
    for offer in offers:
        if not matches(item, offer.get("product", "")):
            continue
        if offer.get("valid_to") and offer["valid_to"] < today_iso:
            continue
        if shop_type == SHOP_TYPE_PHYSICAL and offer.get("online"):
            continue
        if shop_type == SHOP_TYPE_ONLINE and not offer.get("online"):
            continue
        if exclude_loyalty and offer.get("loyalty"):
            continue
        key = (offer.get("chain"), normalize(offer.get("product")), round(offer["price"], 1))
        if key in seen:
            continue
        seen.add(key)
        if offer.get("valid_from") and offer["valid_from"] > today_iso:
            if include_upcoming:
                upcoming.append({**offer, "upcoming": True})
            continue
        current.append({**offer, "upcoming": False})
    return current, upcoming


def rank_offers(
    item: str, offers: list[dict[str, Any]], sort_by: str, nearby_only: bool, stores_known: bool
) -> list[dict[str, Any]]:
    """Seřadí akce; když chceme jen obchody v okolí, vyřadí řetězce bez pobočky poblíž.

    Když se pobočky nepodařilo zjistit (OpenStreetMap nedostupné), nic se nevyřazuje.
    """
    if nearby_only and stores_known:
        offers = [o for o in offers if o.get("online") or o.get("latitude") is not None]
    base = sort_key(sort_by)
    # u stejné ceny dáme přednost produktu, jehož název potravinou začíná
    return sorted(offers, key=lambda o: (*base(o), _relevance(item, o.get("product", ""))))


SHOP_FIELDS = (
    "chain",
    "shop",
    "online",
    "store_name",
    "address",
    "opening_hours",
    "latitude",
    "longitude",
    "distance_km",
    "map_url",
    "navigate_url",
)
ITEM_OFFER_FIELDS = (
    "product",
    "price",
    "currency",
    "old_price",
    "discount_percent",
    "amount",
    "unit",
    "unit_price",
    "validity",
    "valid_from",
    "valid_to",
    "loyalty",
    "url",
    "image",
    "sources",
)


def build_shops(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Seznam obchodů: co v kterém obchodě koupit v akci.

    `all_offers` položky = všechny vyhovující akce (ne jen zobrazených TOP N).
    Pro každý obchod (nejbližší pobočku řetězce) se u každé hledané potraviny vezme
    nejlevnější akce v tomto obchodě. `best` = obchod je pro potravinu nejlevnější ze všech.
    """
    shops: dict[str, dict[str, Any]] = {}
    for item in items:
        offers = item.get("all_offers", item["offers"])
        best_price = min((o["price"] for o in offers), default=None)
        # v každém obchodě bereme nejlevnější akci (i když karta řadí podle vzdálenosti)
        for offer in sorted(offers, key=lambda o: o["price"]):
            key = offer.get("osm_id") or offer.get("chain") or normalize(offer.get("shop"))
            shop = shops.get(key)
            if shop is None:
                shop = {field: offer.get(field) for field in SHOP_FIELDS}
                shop.update(items=[], best_count=0, total=0.0)
                shops[key] = shop
            if any(entry["query"] == item["query"] for entry in shop["items"]):
                continue  # první (nejlevnější) akce v obchodě stačí
            is_best = offer["price"] == best_price
            shop["items"].append(
                {"query": item["query"], "best": is_best}
                | {field: offer.get(field) for field in ITEM_OFFER_FIELDS}
            )
            shop["best_count"] += int(is_best)
            shop["total"] = round(shop["total"] + offer["price"], 2)
    order = {item["query"]: index for index, item in enumerate(items)}
    for shop in shops.values():
        shop["items"].sort(key=lambda entry: order.get(entry["query"], 99))
        shop["item_count"] = len(shop["items"])
    # nejdřív obchody, kde je nejvíc potravin nejlevněji, pak kde jich je nejvíc, pak nejbližší
    return sorted(
        shops.values(),
        key=lambda s: (
            -s["best_count"],
            -s["item_count"],
            s["distance_km"] if s["distance_km"] is not None else 9999,
            s["total"],
        ),
    )


def cheapest_total(items: list[dict[str, Any]]) -> float | None:
    """Kolik stojí celý nákup, když se každá potravina koupí tam, kde je nejlevnější."""
    prices = [min(o["price"] for o in item["offers"]) for item in items if item["offers"]]
    return round(sum(prices), 2) if prices else None
