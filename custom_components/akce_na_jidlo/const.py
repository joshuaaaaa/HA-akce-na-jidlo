"""Constants for the Akce na jídlo integration."""

from __future__ import annotations

DOMAIN = "akce_na_jidlo"
NAME = "Akce na jídlo"

PLATFORMS = ["sensor"]

# Config / options keys
CONF_COUNTRY = "country"
CONF_LANGUAGE = "language"
CONF_LOCATION_ENTITY = "location_entity"
CONF_MAX_DISTANCE_KM = "max_distance_km"
CONF_NEARBY_ONLY = "nearby_only"
CONF_SHOW_MAP = "show_map"
CONF_RESULTS_PER_ITEM = "results_per_item"
CONF_SORT_BY = "sort_by"
CONF_SHOP_TYPE = "shop_type"
CONF_EXCLUDE_LOYALTY = "exclude_loyalty"
CONF_INCLUDE_UPCOMING = "include_upcoming"
CONF_SOURCES = "sources"
CONF_CUSTOM_URLS = "custom_urls"

# Typ obchodu: kamenné i online / jen kamenné / jen online
SHOP_TYPE_ALL = "all"
SHOP_TYPE_PHYSICAL = "physical"
SHOP_TYPE_ONLINE = "online"
SHOP_TYPE_OPTIONS = [SHOP_TYPE_ALL, SHOP_TYPE_PHYSICAL, SHOP_TYPE_ONLINE]

SORT_PRICE = "price"  # cena za balení
SORT_UNIT = "unit"  # cena za kg / l / ks
SORT_DISTANCE = "distance"  # nejbližší obchod, pak cena
SORT_OPTIONS = [SORT_PRICE, SORT_UNIT, SORT_DISTANCE]

DEFAULT_MAX_DISTANCE_KM = 10
DEFAULT_NEARBY_ONLY = True
DEFAULT_SHOW_MAP = False
DEFAULT_RESULTS_PER_ITEM = 5
DEFAULT_SORT_BY = SORT_PRICE
DEFAULT_SHOP_TYPE = SHOP_TYPE_PHYSICAL
DEFAULT_EXCLUDE_LOYALTY = False
DEFAULT_INCLUDE_UPCOMING = False

MAX_RESULTS_PER_ITEM = 10
MAX_ITEMS = 15  # víc potravin najednou nehledáme – weby by se zbytečně zatěžovaly
MAX_QUERY_LENGTH = 60

# Názvy obchodních řetězců, jak je uvádějí letákové weby -> aliasy pro OpenStreetMap
CHAIN_ALIASES: dict[str, tuple[str, ...]] = {
    "albert": ("albert",),
    "billa": ("billa",),
    "globus": ("globus",),
    "kaufland": ("kaufland",),
    "lidl": ("lidl",),
    "penny": ("penny",),
    "tesco": ("tesco",),
    "makro": ("makro",),
    "norma": ("norma",),
    "coop": ("coop", "jednota", "tempo", "terno"),
    "tamda": ("tamda",),
    "flop": ("flop",),
    "hruska": ("hruska",),
    "terno": ("terno",),
    "trefa": ("trefa",),
    "ratio": ("ratio",),
    "brnenka": ("brnenka",),
    "cba": ("cba",),
    "zabka": ("zabka",),
    "tesco express": ("tesco",),
    "potraviny cz": ("potraviny cz",),
    "enapo": ("enapo",),
    "rohlik": ("rohlik",),
    "kosik": ("kosik",),
    "jip": ("jip",),
    "travel free": ("travel free",),
    "tuty": ("tuty",),
    "dm": ("dm drogerie", "dm-drogerie"),
    "rossmann": ("rossmann",),
    "teta": ("teta",),
    # slovenské řetězce
    "fresh": ("fresh",),
    "kraj": ("kraj",),
    "koruna": ("koruna",),
    "metro": ("metro",),
    "klas": ("klas",),
    "moja samoska": ("moja samoska", "samoska"),
    "milk agro": ("milk agro", "milk-agro"),
    "kon rad": ("kon rad", "kon-rad"),
    "yeme": ("yeme",),
}

# Zobrazované názvy řetězců – podle nich obecný parser pozná obchod v textu stránky
CHAIN_NAMES: dict[str, str] = {
    "albert": "Albert",
    "billa": "Billa",
    "globus": "Globus",
    "kaufland": "Kaufland",
    "lidl": "Lidl",
    "penny": "Penny",
    "tesco": "Tesco",
    "makro": "Makro",
    "norma": "Norma",
    "coop": "COOP",
    "tamda": "Tamda",
    "flop": "Flop",
    "hruska": "Hruška",
    "terno": "Terno",
    "trefa": "Trefa",
    "ratio": "Ratio",
    "brnenka": "Brněnka",
    "cba": "CBA",
    "zabka": "Žabka",
    "jip": "JIP",
    "travel free": "Travel Free",
    "tuty": "COOP Tuty",
    "rohlik": "Rohlik.cz",
    "kosik": "Košík.cz",
    "dm": "dm drogerie",
    "rossmann": "Rossmann",
    "teta": "Teta",
    "fresh": "Fresh",
    "kraj": "Kraj",
    "koruna": "Koruna",
    "metro": "Metro",
    "klas": "Klas",
    "moja samoska": "Moja Samoška",
    "milk agro": "Milk-Agro",
    "kon rad": "KON-RAD",
    "yeme": "Yeme",
}

# Online obchody – nemají kamennou pobočku
ONLINE_SHOPS = (
    "rohlik",
    "kosik",
    "tesco online",
    "albert online",
    "online",
    "e-shop",
    "eshop",
    "kosik.sk",
    "potravinydomov",
    "freshbox",
    "mall.cz",
    "alza",
)

# Zdroje akcí. URL šablony: {query} = hledaný text ("mleko+polotucne"),
# {slug} = hledaný text ve tvaru "mleko-polotucne". Zkouší se postupně, první funkční vyhrává.
SOURCE_KUPI = "kupi"
SOURCE_KOMPASSLEV = "kompasslev"
SOURCE_AKCNICENY = "akcniceny"
SOURCE_CUSTOM = "custom"
SOURCE_KIMBINO = "kimbino"
SOURCE_LETAKOMAT = "letakomat"
SOURCE_KDEJEAKCIA = "kdejeakcia"
SOURCE_KOMPASZLIAV = "kompaszliav"
SOURCE_KUPINO = "kupino"
SOURCE_AKCNELETAKY = "akcneletaky"
SOURCE_PROMOTHEUS = "promotheus"

SOURCES: dict[str, dict] = {
    SOURCE_KUPI: {
        "country": "CZ",
        "name": "Kupi.cz",
        "search": (
            "https://www.kupi.cz/hledej?f={query}",
            "https://www.kupi.cz/slevy/{slug}",
        ),
    },
    SOURCE_KOMPASSLEV: {
        "country": "CZ",
        "name": "Kompas Slev",
        "search": ("https://kompasslev.cz/produkty/{slug}",),
    },
    SOURCE_AKCNICENY: {
        "country": "CZ",
        "name": "AkcniCeny.cz",
        "search": (
            "https://www.akcniceny.cz/hledat/?q={query}",
            "https://www.akcniceny.cz/vyhledavani/?q={query}",
        ),
    },
    SOURCE_KIMBINO: {
        "country": "SK",
        "name": "Kimbino.sk",
        "search": ("https://www.kimbino.sk/produkty/{slug}/",),
    },
    SOURCE_LETAKOMAT: {
        "country": "SK",
        "name": "Letakomat.sk",
        "search": ("https://www.letakomat.sk/hladat/?q={query}",),
    },
    SOURCE_KDEJEAKCIA: {
        "country": "SK",
        "name": "KdeJeAkcia.sk",
        "search": ("https://kdejeakcia.sk/kde-je-{slug}-v-akcii",),
    },
    SOURCE_KOMPASZLIAV: {
        "country": "SK",
        "name": "Kompas Zliav",
        "search": ("https://kompaszliav.sk/produkty/{slug}",),
    },
    SOURCE_KUPINO: {
        "country": "SK",
        "name": "Kupino.sk",
        "search": ("https://www.kupino.sk/akcia/{slug}",),
    },
    SOURCE_AKCNELETAKY: {
        "country": "SK",
        "name": "AkčnéLetáky.sk",
        "search": ("https://www.akcneletaky.sk/akcie/{query}",),
    },
    SOURCE_PROMOTHEUS: {
        "country": "SK",
        "name": "Promotheus.sk",
        "search": ("https://promotheus.sk/{slug}",),
    },
}

COUNTRY_CZ = "CZ"
COUNTRY_SK = "SK"
DEFAULT_COUNTRY = COUNTRY_CZ

# Nastavení podle země. bbox = hrubý obdélník (lat_min, lat_max, lon_min, lon_max),
# přesnou hranici řeší Overpass area.
COUNTRIES: dict[str, dict] = {
    COUNTRY_CZ: {
        "name": "Česká republika",
        "currency": "CZK",
        "symbol": "Kč",
        "currency_aliases": ("czk", "kc", ",-"),
        "bbox": (48.55, 51.06, 12.09, 18.86),
    },
    COUNTRY_SK: {
        "name": "Slovensko",
        "currency": "EUR",
        "symbol": "€",
        "currency_aliases": ("eur", "€"),
        "bbox": (47.73, 49.61, 16.83, 22.57),
    },
}


def country_sources(country: str) -> list[str]:
    return [key for key, spec in SOURCES.items() if spec["country"] == country]


KUPI_BASE_URL = "https://www.kupi.cz"

OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
)
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
OSM_USER_AGENT = "HomeAssistant-AkceNaJidlo/1.0 (+https://github.com/joshuaaaaa/HA-akce-na-jidlo)"

STORE_CACHE_DAYS = 7
RELOCATE_DISTANCE_KM = 2.0
SEARCH_CACHE_HOURS = 3  # stejné hledání se do 3 hodin bere z mezipaměti

EVENT_SEARCH_DONE = f"{DOMAIN}_vysledky"
SERVICE_SEARCH = "search"
ATTR_ITEMS = "items"
ATTR_CONFIG_ENTRY_ID = "config_entry_id"

DEFAULT_SOURCES = country_sources(COUNTRY_CZ)
