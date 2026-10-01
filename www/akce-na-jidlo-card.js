/*
 * Akce na jídlo – Lovelace karta (custom:akce-na-jidlo-card)
 * Nákupní košík: napište jednu nebo víc potravin, zmáčkněte Hledat a karta ukáže,
 * ve kterých okolních obchodech jsou v akci nejlevněji (název, adresa, vzdálenost),
 * volitelně i s mapou.
 *
 * Instalace:
 *   1. zkopírujte soubor do /config/www/akce-na-jidlo-card.js
 *   2. Nastavení → Ovládací panely → ⋮ → Zdroje → Přidat zdroj
 *        URL: /local/akce-na-jidlo-card.js      Typ: JavaScript modul
 *   3. do dashboardu přidejte kartu "Akce na jídlo" (type: custom:akce-na-jidlo-card)
 *
 * Mapa se kreslí přímo z dlaždic (CARTO / OpenStreetMap) – bez externích knihoven.
 */

const CARD_VERSION = "1.0.1";
const DOMAIN = "akce_na_jidlo";
const FLAGS = { CZ: "🇨🇿", SK: "🇸🇰" };
const I18N = {
  cs: {
    title: "Nákupní košík v akci", placeholder: "Napište potraviny, např. mléko, chleba, máslo",
    search: "Hledat", searching: "Hledám v letácích…", shops: "Obchody", items: "Potraviny",
    found: "Nalezeno", of: "z", total: "Nejlevnější nákup celkem", not_found: "Teď není v akci",
    no_results: "Zadejte potraviny a zmáčkněte Hledat.", nothing: "Žádná z potravin teď není v okolí v akci 😢",
    navigate: "Navigovat", leaflet: "Leták", home: "Vaše poloha", zoom_in: "Přiblížit", zoom_out: "Oddálit",
    fit: "Ukázat všechny obchody", cheapest: "nejlevněji", items_here: "potravin v akci", online: "online",
    upcoming: "Připravované akce", valid_to: "do", loyalty: "jen s kartou/aplikací", clear: "Smazat",
    stores_error: "Pobočky z OpenStreetMap se teď nepodařilo načíst – zobrazují se akce bez adres.",
    need_entity: "Zadejte entitu (senzor Výsledky hledání)", not_found_entity: "Entita nenalezena",
    updated: "hledáno", no_tiles: "Mapový podklad se nepodařilo načíst", error: "Hledání selhalo", remove: "Odebrat",
  },
  sk: {
    title: "Nákupný košík v akcii", placeholder: "Napíšte potraviny, napr. mlieko, chlieb, maslo",
    search: "Hľadať", searching: "Hľadám v letákoch…", shops: "Obchody", items: "Potraviny",
    found: "Nájdené", of: "z", total: "Najlacnejší nákup spolu", not_found: "Teraz nie je v akcii",
    no_results: "Zadajte potraviny a stlačte Hľadať.", nothing: "Žiadna z potravín teraz nie je v okolí v akcii 😢",
    navigate: "Navigovať", leaflet: "Leták", home: "Vaša poloha", zoom_in: "Priblížiť", zoom_out: "Oddialiť",
    fit: "Ukázať všetky obchody", cheapest: "najlacnejšie", items_here: "potravín v akcii", online: "online",
    upcoming: "Pripravované akcie", valid_to: "do", loyalty: "len s kartou/aplikáciou", clear: "Zmazať",
    stores_error: "Pobočky z OpenStreetMap sa teraz nepodarilo načítať – zobrazujú sa akcie bez adries.",
    need_entity: "Zadajte entitu (senzor Výsledky hľadania)", not_found_entity: "Entita sa nenašla",
    updated: "hľadané", no_tiles: "Mapový podklad sa nepodarilo načítať", error: "Hľadanie zlyhalo", remove: "Odobrať",
  },
  en: {
    title: "Grocery basket deals", placeholder: "Type groceries, e.g. milk, bread, butter",
    search: "Search", searching: "Searching flyers…", shops: "Stores", items: "Groceries",
    found: "Found", of: "of", total: "Cheapest basket total", not_found: "Not on sale now",
    no_results: "Type some groceries and press Search.", nothing: "None of the items is on sale nearby now 😢",
    navigate: "Navigate", leaflet: "Flyer", home: "Your location", zoom_in: "Zoom in", zoom_out: "Zoom out",
    fit: "Show all stores", cheapest: "cheapest", items_here: "items on sale", online: "online",
    upcoming: "Upcoming deals", valid_to: "until", loyalty: "loyalty card/app only", clear: "Clear",
    stores_error: "Store branches from OpenStreetMap could not be loaded – deals are shown without addresses.",
    need_entity: "Set the entity (Search results sensor)", not_found_entity: "Entity not found",
    updated: "searched", no_tiles: "Map tiles could not be loaded", error: "Search failed", remove: "Remove",
  },
};
const LOCALES = { cs: "cs-CZ", sk: "sk-SK", en: "en-GB" };
const UNIT_LABELS = { kg: "kg", l: "l", ks: "ks" };
const pickLang = (...candidates) => {
  for (const c of candidates) {
    const base = String(c || "").toLowerCase().split("-")[0];
    if (I18N[base]) return base;
  }
  return "cs";
};
let EDITOR_LANG = "cs";

// Mapové podklady. Dlaždice přímo z tile.openstreetmap.org OSM blokuje ("Access blocked"),
// protože Home Assistant neposílá hlavičku Referer – proto výchozí CARTO (data z OpenStreetMap).
const RETINA = (window.devicePixelRatio || 1) > 1.5;
const OSM_ATTR = '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>';
const CARTO_ATTR = `${OSM_ATTR} © <a href="https://carto.com/attributions" target="_blank" rel="noopener">CARTO</a>`;
const TILE_PROVIDERS = {
  carto: {
    url: (z, x, y) => `https://${"abcd"[(x + y) % 4]}.basemaps.cartocdn.com/rastertiles/voyager/${z}/${x}/${y}${RETINA ? "@2x" : ""}.png`,
    attribution: CARTO_ATTR,
  },
  carto_dark: {
    url: (z, x, y) => `https://${"abcd"[(x + y) % 4]}.basemaps.cartocdn.com/dark_all/${z}/${x}/${y}${RETINA ? "@2x" : ""}.png`,
    attribution: CARTO_ATTR,
  },
  osm: { url: (z, x, y) => `https://tile.openstreetmap.org/${z}/${x}/${y}.png`, attribution: OSM_ATTR },
  // bez podkladu – jen špendlíky (pro zařízení, která dlaždice nenačtou, např. kvůli SSL)
  none: { url: null, attribution: "" },
};
// Když se po sobě nenačte tolik dlaždic (a žádná se nenačte), podklad se vypne, aby
// zařízení s chybou SSL / bez internetu nezahlcovalo chybami při každém posunu mapy.
const TILE_FAIL_LIMIT = 3;
const TILE_STATE = { failed: 0, loaded: 0, broken: false };
const TILE = 256;

// Oranžový nákupní košík (SVG)
const BASKET_SVG = `
<svg viewBox="0 0 64 64" aria-hidden="true">
  <path d="M20 26 L28 8" stroke="#7a3d00" stroke-width="4" stroke-linecap="round" fill="none"/>
  <path d="M44 26 L36 8" stroke="#7a3d00" stroke-width="4" stroke-linecap="round" fill="none"/>
  <rect x="4" y="24" width="56" height="9" rx="4.5" fill="#ffb74d"/>
  <path d="M8 33 H56 L50.5 56 a4 4 0 0 1 -3.9 3 H17.4 a4 4 0 0 1 -3.9 -3 Z" fill="#f57c00"/>
  <g stroke="#ffe0b2" stroke-width="2.6" stroke-linecap="round">
    <path d="M22 38 V53"/><path d="M32 38 V53"/><path d="M42 38 V53"/>
  </g>
</svg>`;

console.info(
  `%c AKCE-NA-JIDLO-CARD %c v${CARD_VERSION} `,
  "color:#fff;background:#f57c00;font-weight:700",
  "color:#f57c00;background:#fff3e0"
);

// Web Mercator – převod GPS na pixely světové mapy v daném zoomu
const project = (lat, lon, z) => {
  const scale = TILE * 2 ** z;
  const sin = Math.sin((Math.max(-85, Math.min(85, lat)) * Math.PI) / 180);
  return {
    x: ((lon + 180) / 360) * scale,
    y: (0.5 - Math.log((1 + sin) / (1 - sin)) / (4 * Math.PI)) * scale,
  };
};

const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const shortDate = (iso) => {
  if (!iso) return "";
  const d = new Date(`${iso}T00:00:00`);
  return `${d.getDate()}. ${d.getMonth() + 1}.`;
};

const splitItems = (text) => {
  const seen = new Set();
  return String(text || "")
    .split(/[,;\n\r]+/)
    .map((s) => s.trim())
    .filter((s) => {
      const key = s.toLowerCase();
      if (!s || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
};

class AkceNaJidloCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._result = null; // odpověď služby z tohoto prohlížeče (má přednost před senzorem)
    this._draft = null;
    this._busy = false;
    this._error = "";
    this._tab = null;
    this._selected = -1;
    this._view = null;
    this._resize = null;
    this._lastKey = "";
    this._built = false;
  }

  static getConfigElement() {
    return document.createElement("akce-na-jidlo-card-editor");
  }

  static getStubConfig(hass) {
    const entity = Object.keys(hass.states).find(
      (id) => id.startsWith("sensor.") && "searching" in hass.states[id].attributes && "entry_id" in hass.states[id].attributes
    );
    return { entity: entity || "" };
  }

  setConfig(config) {
    if (!config || !config.entity) throw new Error(I18N[pickLang(config?.language, navigator.language)].need_entity);
    this._config = {
      show_map: true,
      map_height: 260,
      show_images: true,
      view: "shops",
      ...config,
    };
    this._built = false;
    this._lastKey = "";
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    const state = hass.states[this._config?.entity];
    const key = state ? `${state.last_updated}|${state.state}|${hass.themes?.darkMode}` : "missing";
    if (key !== this._lastKey) {
      this._lastKey = key;
      // novější výsledek v senzoru (třeba z automatizace nebo z jiné karty) nahradí ten lokální
      const updated = state?.attributes?.updated;
      if (this._result && updated && updated > (this._result.updated || "")) this._result = null;
      this._render();
    }
  }

  getCardSize() {
    return 3 + (this._data().shops || []).length * 2 + (this._mapEnabled() ? 5 : 0);
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6 };
  }

  // ------------------------------------------------------------------ data
  _attrs() {
    return this._hass?.states[this._config?.entity]?.attributes || {};
  }

  _data() {
    return this._result || this._attrs();
  }

  _mapEnabled() {
    // mapu povoluje nastavení integrace; v kartě jde navíc vypnout
    const attrs = this._attrs();
    const allowed = attrs.show_map ?? this._data().show_map;
    return Boolean(allowed) && this._config?.show_map !== false;
  }

  _lang() {
    const a = this._attrs();
    const lang = a.language && a.language !== "auto" ? a.language : "";
    return pickLang(this._config?.language, lang, this._hass?.language, a.country === "SK" ? "sk" : "");
  }

  _t(key) {
    return I18N[this._lang()][key] ?? I18N.cs[key] ?? key;
  }

  _locale() {
    return LOCALES[this._lang()];
  }

  _money(value) {
    if (value === null || value === undefined || value === "") return "–";
    const symbol = this._data().currency_symbol || "Kč";
    return `${Number(value).toLocaleString(this._locale(), { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${symbol}`;
  }

  _km(value) {
    return `${Number(value).toLocaleString(this._locale(), { maximumFractionDigits: 1 })} km`;
  }

  // ---------------------------------------------------------------- hledání
  async _search() {
    const input = this.shadowRoot.getElementById("q");
    const items = splitItems(input?.value);
    if (!items.length || this._busy) return;
    this._busy = true;
    this._error = "";
    this._selected = -1;
    this._view = null;
    this._renderResults();
    const data = { items };
    const entryId = this._attrs().entry_id;
    if (entryId) data.config_entry_id = entryId;
    try {
      const res = await this._hass.connection.sendMessagePromise({
        type: "call_service",
        domain: DOMAIN,
        service: "search",
        service_data: data,
        return_response: true,
      });
      this._result = res?.response || null;
    } catch (err) {
      this._error = err?.message || String(err);
    } finally {
      this._busy = false;
      this._renderResults();
    }
  }

  // ----------------------------------------------------------------- render
  _render() {
    if (!this._config || !this._hass) return;
    const state = this._hass.states[this._config.entity];
    if (!state) {
      this._built = false;
      this.shadowRoot.innerHTML = `<ha-card><div class="warn">${this._t("not_found_entity")}: ${esc(this._config.entity)}</div></ha-card>`;
      return;
    }
    if (!this._built) this._build();
    this._renderResults();
  }

  // hlavička a řádek pro zadání se kreslí jen jednou, aby se při psaní neztrácel text
  _build() {
    const data = this._data();
    if (this._draft === null) this._draft = (data.query || []).join(", ");
    const flag = FLAGS[this._attrs().country] || "";
    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <ha-card>
        <div class="head">
          <div class="basket">${BASKET_SVG}</div>
          <div class="head-text">
            <div class="title">${esc(this._config.title || this._t("title"))} ${flag}</div>
            <div class="sub" id="sub"></div>
          </div>
        </div>
        <form class="search" id="form">
          <textarea id="q" rows="1" placeholder="${esc(this._t("placeholder"))}" enterkeyhint="search">${esc(this._draft)}</textarea>
          <button type="submit" class="go" id="go">
            <span class="mini">${BASKET_SVG}</span><span>${esc(this._t("search"))}</span>
          </button>
        </form>
        <div class="chips" id="chips"></div>
        <div id="results"></div>
      </ha-card>`;
    const q = this.shadowRoot.getElementById("q");
    const grow = () => {
      q.style.height = "auto";
      q.style.height = `${Math.min(q.scrollHeight, 140)}px`;
    };
    q.addEventListener("input", () => {
      this._draft = q.value;
      grow();
      this._renderChips();
    });
    q.addEventListener("keydown", (ev) => {
      // Enter = hledat, Shift+Enter = nový řádek
      if (ev.key === "Enter" && !ev.shiftKey) {
        ev.preventDefault();
        this._search();
      }
    });
    this.shadowRoot.getElementById("form").addEventListener("submit", (ev) => {
      ev.preventDefault();
      this._search();
    });
    this._built = true;
    requestAnimationFrame(grow);
  }

  _renderChips() {
    const box = this.shadowRoot.getElementById("chips");
    if (!box) return;
    const data = this._data();
    const notFound = new Set((data.not_found || []).map((s) => s.toLowerCase()));
    const found = new Set((data.found || []).map((s) => s.toLowerCase()));
    const items = splitItems(this.shadowRoot.getElementById("q")?.value);
    box.innerHTML = items
      .map((item, i) => {
        const k = item.toLowerCase();
        const cls = found.has(k) ? "ok" : notFound.has(k) ? "no" : "";
        return `<span class="chip ${cls}">${found.has(k) ? "✓ " : notFound.has(k) ? "✗ " : ""}${esc(item)}<button data-i="${i}" title="${esc(this._t("remove"))}">×</button></span>`;
      })
      .join("");
    box.querySelectorAll("button[data-i]").forEach((b) =>
      b.addEventListener("click", () => {
        const list = splitItems(this.shadowRoot.getElementById("q").value);
        list.splice(Number(b.dataset.i), 1);
        const q = this.shadowRoot.getElementById("q");
        q.value = list.join(", ");
        this._draft = q.value;
        this._renderChips();
      })
    );
  }

  _renderResults() {
    const root = this.shadowRoot.getElementById("results");
    if (!root) return;
    const data = this._data();
    const busy = this._busy || this._attrs().searching;
    const go = this.shadowRoot.getElementById("go");
    if (go) go.disabled = Boolean(busy);

    const sub = this.shadowRoot.getElementById("sub");
    if (sub) {
      const updated = data.updated ? new Date(data.updated) : null;
      sub.textContent = updated
        ? `${this._t("updated")} ${updated.toLocaleString(this._locale(), { day: "numeric", month: "numeric", hour: "2-digit", minute: "2-digit" })}`
        : "";
    }
    this._renderChips();

    if (busy) {
      root.innerHTML = `<div class="busy"><div class="spinner"></div>${esc(this._t("searching"))}</div>`;
      return;
    }
    const items = data.items || [];
    const shops = data.shops || [];
    let html = this._error ? `<div class="error">⚠️ ${esc(this._t("error"))}: ${esc(this._error)}</div>` : "";
    if (!items.length) {
      root.innerHTML = `${html}<div class="empty">${esc(this._t("no_results"))}</div>`;
      return;
    }
    const found = (data.found || []).length;
    html += `
      <div class="summary">
        <span><b>${esc(this._t("found"))} ${found} ${esc(this._t("of"))} ${items.length}</b></span>
        ${data.total != null ? `<span>${esc(this._t("total"))}: <b class="orange">${this._money(data.total)}</b></span>` : ""}
      </div>
      ${(data.not_found || []).length ? `<div class="nosale">❌ ${esc(this._t("not_found"))}: ${data.not_found.map(esc).join(", ")}</div>` : ""}
      ${data.stores_error ? `<div class="nosale">⚠️ ${esc(this._t("stores_error"))}</div>` : ""}`;
    if (!found) {
      root.innerHTML = `${html}<div class="empty">${esc(this._t("nothing"))}</div>`;
      return;
    }
    const tab = this._tab || this._config.view || "shops";
    html += `
      <div class="tabs">
        <button data-tab="shops" class="${tab === "shops" ? "on" : ""}">🏪 ${esc(this._t("shops"))} (${shops.length})</button>
        <button data-tab="items" class="${tab === "items" ? "on" : ""}">🧺 ${esc(this._t("items"))} (${found})</button>
      </div>
      ${this._mapEnabled() && shops.some((s) => s.latitude != null) ? `<div id="map" style="height:${Number(this._config.map_height) || 260}px"></div>` : ""}
      <div class="list">${tab === "shops" ? shops.map((s, i) => this._shopRow(s, i)).join("") : items.map((it) => this._itemBlock(it)).join("")}</div>`;
    root.innerHTML = html;

    root.querySelectorAll("button[data-tab]").forEach((b) =>
      b.addEventListener("click", () => {
        this._tab = b.dataset.tab;
        this._renderResults();
      })
    );
    root.querySelectorAll(".shop[data-index]").forEach((row) =>
      row.addEventListener("click", (ev) => {
        if (ev.target.closest("a")) return;
        this._select(Number(row.dataset.index));
      })
    );
    if (this._mapEnabled()) this._setupMap();
    else {
      this._resize?.disconnect();
      this._resize = null;
    }
  }

  _where(o) {
    return [
      o.store_name && o.store_name !== o.shop ? esc(o.store_name) : "",
      o.address ? esc(o.address) : "",
      o.distance_km != null ? `<b>${this._km(o.distance_km)}</b>` : o.online ? esc(this._t("online")) : "",
    ].filter(Boolean).join(" · ");
  }

  _unitPrice(o) {
    if (o.unit_price == null || !o.unit) return "";
    return `${this._money(o.unit_price)} / ${UNIT_LABELS[o.unit] || esc(o.unit)}`;
  }

  _shopRow(s, i) {
    const selected = i === this._selected;
    const where = this._where(s);
    const lines = (s.items || [])
      .map(
        (it) => `
        <div class="line ${it.best ? "best" : ""}">
          <span class="q">${esc(it.query)}</span>
          <span class="p">${esc(it.product)}${it.amount ? ` <span class="muted">${esc(it.amount)}</span>` : ""}${it.loyalty ? ` <ha-icon class="small" icon="mdi:card-account-details-outline" title="${esc(this._t("loyalty"))}"></ha-icon>` : ""}</span>
          <span class="v">${it.best ? `<span class="crown" title="${esc(this._t("cheapest"))}">🏆</span>` : ""}${this._money(it.price)}${it.discount_percent ? ` <span class="disc">−${Number(it.discount_percent)} %</span>` : ""}</span>
        </div>`
      )
      .join("");
    return `
      <div class="shop ${selected ? "selected" : ""}" data-index="${i}">
        <div class="shop-head">
          <div class="rank">${i + 1}</div>
          <div class="shop-info">
            <div class="shop-name">${esc(s.shop)}</div>
            ${where ? `<div class="where">📍 ${where}</div>` : ""}
            ${s.opening_hours && selected ? `<div class="where">🕒 ${esc(s.opening_hours)}</div>` : ""}
          </div>
          <div class="shop-total">
            <div class="price">${this._money(s.total)}</div>
            <div class="muted small-t">${s.item_count} ${esc(this._t("items_here"))}${s.best_count ? ` · ${s.best_count}× 🏆` : ""}</div>
          </div>
        </div>
        <div class="lines">${lines}</div>
        ${s.navigate_url || s.map_url ? `<div class="links">
            ${s.navigate_url ? `<a href="${esc(s.navigate_url)}" target="_blank" rel="noopener">🧭 ${esc(this._t("navigate"))}</a>` : ""}
            ${s.map_url ? `<a href="${esc(s.map_url)}" target="_blank" rel="noopener">🗺️ Mapy.com</a>` : ""}
          </div>` : ""}
      </div>`;
  }

  _offerRow(o, rank) {
    const validity = o.valid_from && o.valid_to && o.upcoming
      ? `${shortDate(o.valid_from)} – ${shortDate(o.valid_to)}`
      : o.valid_to ? `${this._t("valid_to")} ${shortDate(o.valid_to)}` : esc(o.validity || "");
    const where = this._where(o);
    return `
      <div class="offer">
        <div class="rank sm ${rank === 0 ? "gold" : ""}">${rank === 0 ? "🏆" : rank + 1}</div>
        ${this._config.show_images && o.image ? `<img class="img" src="${esc(o.image)}" alt="" loading="lazy">` : ""}
        <div class="info">
          <div class="product">${o.url ? `<a href="${esc(o.url)}" target="_blank" rel="noopener">${esc(o.product)}</a>` : esc(o.product)}</div>
          <div class="shop-l">${esc(o.shop)}${o.amount ? ` · ${esc(o.amount)}` : ""}${o.loyalty ? ` · <ha-icon class="small" icon="mdi:card-account-details-outline" title="${esc(this._t("loyalty"))}"></ha-icon>` : ""}</div>
          ${where ? `<div class="where">${where}</div>` : ""}
          ${validity ? `<div class="valid">${validity}</div>` : ""}
        </div>
        <div class="prices">
          <div class="price">${this._money(o.price)}</div>
          ${o.old_price ? `<div class="old">${this._money(o.old_price)}</div>` : ""}
          ${o.discount_percent ? `<div class="disc">−${Number(o.discount_percent)} %</div>` : ""}
          ${this._unitPrice(o) ? `<div class="unit">${this._unitPrice(o)}</div>` : ""}
        </div>
      </div>`;
  }

  _itemBlock(it) {
    const offers = it.offers || [];
    const upcoming = it.upcoming || [];
    return `
      <div class="item">
        <div class="item-head">🧺 ${esc(it.query)} ${offers.length ? "" : `<span class="muted">– ${esc(this._t("not_found"))}</span>`}</div>
        ${offers.map((o, i) => this._offerRow(o, i)).join("")}
        ${upcoming.length ? `<div class="upc">${esc(this._t("upcoming"))}</div>${upcoming.map((o, i) => this._offerRow({ ...o, upcoming: true }, i + 1)).join("")}` : ""}
      </div>`;
  }

  disconnectedCallback() {
    this._resize?.disconnect();
    this._resize = null;
  }

  _select(index) {
    this._selected = this._selected === index ? -1 : index;
    const shop = (this._data().shops || [])[index];
    if (this._selected >= 0 && shop?.latitude != null) {
      const z = Math.max(this._view?.z || 0, 15);
      const p = project(shop.latitude, shop.longitude, z);
      this._view = { z, cx: p.x, cy: p.y };
    }
    const list = this.shadowRoot.querySelector(".list");
    if (list && (this._tab || this._config.view || "shops") === "shops") {
      list.innerHTML = (this._data().shops || []).map((s, i) => this._shopRow(s, i)).join("");
      list.querySelectorAll(".shop[data-index]").forEach((row) =>
        row.addEventListener("click", (ev) => {
          if (ev.target.closest("a")) return;
          this._select(Number(row.dataset.index));
        })
      );
    }
    this._drawMap();
  }

  // ------------------------------------------------------------------ mapa
  _mapPoints() {
    const data = this._data();
    const points = (data.shops || [])
      .map((s, i) => ({ s, i }))
      .filter(({ s }) => s.latitude != null && s.longitude != null);
    const home = data.location?.latitude != null ? data.location : null;
    return { points, home };
  }

  _setupMap() {
    const el = this.shadowRoot.getElementById("map");
    if (!el) return;
    this._resize?.disconnect();
    this._resize = new ResizeObserver(() => this._drawMap());
    this._resize.observe(el);
    let drag = null;
    el.addEventListener("pointerdown", (ev) => {
      if (ev.target.closest(".pin, .zoom")) return;
      const v = this._currentView();
      if (!v) return;
      drag = { x: ev.clientX, y: ev.clientY, v };
      el.setPointerCapture(ev.pointerId);
    });
    el.addEventListener("pointermove", (ev) => {
      if (!drag) return;
      this._view = { z: drag.v.z, cx: drag.v.cx - (ev.clientX - drag.x), cy: drag.v.cy - (ev.clientY - drag.y) };
      this._drawMap();
    });
    const end = () => (drag = null);
    el.addEventListener("pointerup", end);
    el.addEventListener("pointercancel", end);
    this._drawMap();
  }

  // automatický výřez, do kterého se vejdou všechny obchody i domov
  _fitView(width, height) {
    const { points, home } = this._mapPoints();
    const coords = points.map(({ s }) => [s.latitude, s.longitude]);
    if (home) coords.push([home.latitude, home.longitude]);
    if (!coords.length) return null;
    for (let z = 16; z >= 3; z--) {
      const px = coords.map(([lat, lon]) => project(lat, lon, z));
      const xs = px.map((p) => p.x);
      const ys = px.map((p) => p.y);
      if ((Math.max(...xs) - Math.min(...xs) <= width - 60 && Math.max(...ys) - Math.min(...ys) <= height - 60) || z === 3) {
        return { z, cx: (Math.max(...xs) + Math.min(...xs)) / 2, cy: (Math.max(...ys) + Math.min(...ys)) / 2 };
      }
    }
    return null;
  }

  _tileProvider() {
    let style = this._config.map_style || "auto";
    if (style === "auto") style = this._hass?.themes?.darkMode ? "carto_dark" : "carto";
    if (TILE_STATE.broken) return TILE_PROVIDERS.none;
    return TILE_PROVIDERS[style] || TILE_PROVIDERS.carto;
  }

  _currentView() {
    const el = this.shadowRoot.getElementById("map");
    if (!el) return null;
    return this._view || this._fitView(el.clientWidth || 400, el.clientHeight || 260);
  }

  _zoom(delta) {
    const v = this._currentView();
    if (!v) return;
    const z = Math.max(3, Math.min(18, v.z + delta));
    const f = 2 ** (z - v.z);
    this._view = { z, cx: v.cx * f, cy: v.cy * f };
    this._drawMap();
  }

  _drawMap() {
    const el = this.shadowRoot.getElementById("map");
    if (!el) return;
    const width = el.clientWidth;
    const height = el.clientHeight;
    if (!width || !height) return; // karta ještě není vykreslená – překreslí ResizeObserver
    const v = this._currentView();
    if (!v) {
      el.innerHTML = "";
      return;
    }
    const provider = this._tileProvider();
    const left = v.cx - width / 2;
    const top = v.cy - height / 2;
    const n = 2 ** v.z;
    let tiles = "";
    for (let ty = Math.floor(top / TILE); provider.url && ty <= Math.floor((top + height) / TILE); ty++) {
      if (ty < 0 || ty >= n) continue;
      for (let tx = Math.floor(left / TILE); tx <= Math.floor((left + width) / TILE); tx++) {
        const x = ((tx % n) + n) % n;
        tiles += `<img class="tile" alt="" draggable="false" referrerpolicy="strict-origin-when-cross-origin" src="${provider.url(v.z, x, ty)}" style="left:${Math.round(tx * TILE - left)}px;top:${Math.round(ty * TILE - top)}px">`;
      }
    }
    const { points, home } = this._mapPoints();
    const pin = (lat, lon, cls, label, title, index) => {
      const p = project(lat, lon, v.z);
      return `<div class="pin ${cls}" ${index != null ? `data-index="${index}"` : ""} title="${esc(title)}" style="left:${Math.round(p.x - left)}px;top:${Math.round(p.y - top)}px">${label}</div>`;
    };
    let pins = home ? pin(home.latitude, home.longitude, "home", "🏠", this._t("home")) : "";
    const ordered = [...points].sort((a, b) => (a.i === this._selected) - (b.i === this._selected));
    for (const { s, i } of ordered) {
      pins += pin(s.latitude, s.longitude, i === this._selected ? "sel" : "", i + 1, `${i + 1}. ${s.store_name || s.shop}${s.address ? ` – ${s.address}` : ""}`, i);
    }
    el.innerHTML = `
      <div class="tiles">${tiles}</div>
      ${pins}
      <div class="zoom">
        <button data-zoom="1" title="${esc(this._t("zoom_in"))}">+</button>
        <button data-zoom="-1" title="${esc(this._t("zoom_out"))}">−</button>
        <button data-fit="1" title="${esc(this._t("fit"))}">⤢</button>
      </div>
      ${TILE_STATE.broken ? `<div class="attribution">${esc(this._t("no_tiles"))}</div>` : provider.attribution ? `<div class="attribution">${provider.attribution}</div>` : ""}`;
    el.querySelectorAll("img.tile").forEach((img) => {
      img.addEventListener("load", () => (TILE_STATE.loaded += 1), { once: true });
      img.addEventListener(
        "error",
        () => {
          TILE_STATE.failed += 1;
          if (!TILE_STATE.broken && !TILE_STATE.loaded && TILE_STATE.failed >= TILE_FAIL_LIMIT) {
            TILE_STATE.broken = true;
            console.warn("akce-na-jidlo-card: mapový podklad se nenačítá (SSL / síť), mapa bude bez podkladu");
            this._drawMap();
          }
        },
        { once: true }
      );
    });
    el.querySelectorAll(".pin[data-index]").forEach((node) =>
      node.addEventListener("click", () => {
        if (!this.shadowRoot.querySelector(".shop")) {
          // klepnutí na obchod v mapě přepne na seznam obchodů
          this._tab = "shops";
          this._selected = -1;
          this._renderResults();
        }
        this._select(Number(node.dataset.index));
      })
    );
    el.querySelectorAll("button[data-zoom]").forEach((b) => b.addEventListener("click", () => this._zoom(Number(b.dataset.zoom))));
    el.querySelector("button[data-fit]")?.addEventListener("click", () => {
      this._view = null;
      this._drawMap();
    });
  }
}

const STYLE = `
  :host { --orange: #f57c00; --orange-light: #ffb74d; --orange-soft: rgba(245,124,0,.12); }
  ha-card { overflow: hidden; }
  .head { display:flex; align-items:center; gap:12px; padding:14px 16px;
          background: linear-gradient(135deg, #ff9800 0%, #f57c00 60%, #ef6c00 100%); color:#fff; }
  .basket { flex:0 0 52px; height:52px; border-radius:50%; background:#fff3e0; display:flex; align-items:center; justify-content:center;
            box-shadow: inset 0 -3px 0 rgba(0,0,0,.08); }
  .basket svg { width:36px; height:36px; }
  .title { font-size:1.25em; font-weight:700; line-height:1.2; }
  .sub { font-size:.8em; opacity:.9; margin-top:2px; min-height:1em; }
  .search { display:flex; gap:8px; align-items:flex-end; padding:12px 12px 4px; }
  textarea { flex:1 1 auto; min-width:0; resize:none; font: inherit; font-size:1em; line-height:1.35; padding:10px 12px; border-radius:12px;
             border:2px solid var(--orange-light); background: var(--card-background-color, #fff); color: var(--primary-text-color);
             outline:none; box-sizing:border-box; max-height:140px; }
  textarea:focus { border-color: var(--orange); box-shadow: 0 0 0 3px var(--orange-soft); }
  .go { flex:0 0 auto; display:flex; align-items:center; gap:6px; height:44px; padding:0 16px; border:0; border-radius:12px;
        background: var(--orange); color:#fff; font: inherit; font-weight:700; cursor:pointer; box-shadow:0 2px 6px rgba(245,124,0,.35); }
  .go:hover { background:#ef6c00; }
  .go:disabled { opacity:.6; cursor:progress; }
  .go .mini { width:22px; height:22px; background:#fff3e0; border-radius:50%; display:flex; align-items:center; justify-content:center; }
  .go .mini svg { width:17px; height:17px; }
  .chips { display:flex; flex-wrap:wrap; gap:6px; padding:4px 12px 8px; }
  .chip { display:inline-flex; align-items:center; gap:2px; font-size:.8em; padding:2px 4px 2px 10px; border-radius:14px;
          background: var(--orange-soft); color: var(--primary-text-color); }
  .chip.ok { background: rgba(46,125,50,.15); }
  .chip.no { background: rgba(198,40,40,.12); text-decoration: line-through; }
  .chip button { border:0; background:none; cursor:pointer; color: var(--secondary-text-color); font-size:1.1em; padding:0 4px; }
  .busy { display:flex; align-items:center; gap:10px; padding:18px 16px; color: var(--secondary-text-color); }
  .spinner { width:20px; height:20px; border-radius:50%; border:3px solid var(--orange-soft); border-top-color: var(--orange); animation: spin .8s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) { .spinner { animation-duration: 3s; } }
  .summary { display:flex; flex-wrap:wrap; justify-content:space-between; gap:6px; padding:4px 16px; font-size:.9em; }
  .orange { color: var(--orange); }
  .nosale { padding: 2px 16px 4px; font-size:.85em; color: var(--secondary-text-color); }
  .error { padding: 8px 16px; color: var(--error-color, #c62828); }
  .empty, .warn { padding: 16px; color: var(--secondary-text-color); }
  .tabs { display:flex; gap:6px; padding:8px 12px; }
  .tabs button { flex:1; border:1px solid var(--divider-color); background:none; color: var(--primary-text-color); border-radius:10px;
                 padding:7px 8px; font: inherit; font-size:.9em; cursor:pointer; }
  .tabs button.on { background: var(--orange); border-color: var(--orange); color:#fff; font-weight:700; }
  #map { position: relative; width: 100%; overflow: hidden; background: #e8e4d8; touch-action: none; cursor: grab; user-select: none; }
  #map .tiles { position:absolute; inset:0; }
  #map .tile { position:absolute; width:256px; height:256px; pointer-events:none; }
  #map .zoom { position:absolute; top:8px; right:8px; display:flex; flex-direction:column; gap:4px; z-index:3; }
  #map .zoom button { width:30px; height:30px; border:0; border-radius:8px; background: rgba(255,255,255,.92); color:#333;
         font-size:18px; font-weight:700; cursor:pointer; box-shadow:0 1px 4px rgba(0,0,0,.3); }
  #map .attribution { position:absolute; right:0; bottom:0; font-size:10px; padding:1px 5px; background: rgba(255,255,255,.8); color:#333; z-index:3; }
  #map .attribution a { color:#333; }
  .pin { position:absolute; transform: translate(-50%, -50%); cursor:pointer; z-index:2; width:28px; height:28px; border-radius:50%;
         background: var(--orange); color:#fff; display:flex; align-items:center; justify-content:center; border:2px solid #fff;
         box-shadow:0 1px 4px rgba(0,0,0,.4); font: 700 13px sans-serif; }
  .pin.sel { background:#2e7d32; transform: translate(-50%, -50%) scale(1.15); z-index:3; }
  .pin.home { background:#1976d2; font-size:14px; cursor:default; }
  .list { padding: 4px 8px 10px; }
  .shop { padding:10px 8px; border-radius:12px; cursor:pointer; }
  .shop + .shop { border-top:1px solid var(--divider-color); }
  .shop.selected { background: var(--orange-soft); }
  .shop-head { display:flex; gap:10px; align-items:flex-start; }
  .rank { flex:0 0 28px; height:28px; border-radius:50%; background: var(--orange); color:#fff; font-weight:700;
          display:flex; align-items:center; justify-content:center; font-size:.9em; }
  .rank.sm { flex-basis:24px; height:24px; font-size:.8em; background: var(--secondary-background-color); color: var(--primary-text-color); }
  .rank.gold { background:none; font-size:1.1em; }
  .shop-info { flex:1 1 auto; min-width:0; }
  .shop-name { font-weight:700; font-size:1.05em; }
  .where { color: var(--secondary-text-color); font-size:.82em; margin-top:2px; }
  .shop-total { text-align:right; flex:0 0 auto; }
  .small-t { font-size:.75em; white-space:nowrap; }
  .lines { margin:6px 0 0 38px; display:flex; flex-direction:column; gap:3px; }
  .line { display:grid; grid-template-columns: minmax(60px, 28%) 1fr auto; gap:8px; align-items:baseline; font-size:.88em; }
  .line .q { font-weight:600; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .line .p { color: var(--secondary-text-color); min-width:0; }
  .line .v { white-space:nowrap; font-weight:600; }
  .line.best .v { color:#2e7d32; }
  .crown { margin-right:3px; }
  .links { display:flex; gap:14px; margin:8px 0 0 38px; font-size:.85em; }
  .links a, .product a { color: var(--primary-color); text-decoration:none; font-weight:500; }
  .item { padding:6px 4px 10px; }
  .item + .item { border-top:1px solid var(--divider-color); }
  .item-head { font-weight:700; padding:6px 4px; }
  .upc { font-size:.8em; color: var(--secondary-text-color); padding:4px 8px; }
  .offer { display:flex; gap:10px; align-items:flex-start; padding:7px 6px; }
  .img { width:44px; height:44px; object-fit:contain; border-radius:8px; background:#fff; flex:0 0 44px; }
  .info { flex:1 1 auto; min-width:0; }
  .product { font-weight:600; line-height:1.25; }
  .shop-l { font-size:.88em; margin-top:2px; }
  .valid { font-size:.75em; color: var(--secondary-text-color); margin-top:2px; }
  .prices { text-align:right; flex:0 0 auto; }
  .price { font-size:1.15em; font-weight:700; color: var(--orange); white-space:nowrap; }
  .old { text-decoration: line-through; color: var(--secondary-text-color); font-size:.8em; }
  .disc { display:inline-block; background:#c62828; color:#fff; border-radius:6px; padding:0 5px; font-size:.75em; font-weight:700; }
  .unit { color: var(--secondary-text-color); font-size:.75em; white-space:nowrap; margin-top:2px; }
  .muted { color: var(--secondary-text-color); font-weight:400; }
  ha-icon.small { --mdc-icon-size: 16px; vertical-align: -3px; }
  @media (max-width: 420px) {
    .go span:last-child { display:none; }
    .go { padding: 0 12px; }
    .lines, .links { margin-left: 0; }
    .line { grid-template-columns: 1fr auto; }
    .line .p { grid-column: 1 / -1; grid-row: 2; }
  }
`;

class AkceNaJidloCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._form) this._form.hass = hass;
    else this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (s) => (LABELS[EDITOR_LANG] || LABELS.cs)[s.name] || s.name;
      this._form.addEventListener("value-changed", (ev) => {
        this._config = ev.detail.value;
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    EDITOR_LANG = pickLang(this._config.language, this._hass.language);
    this._form.schema = editorSchema(EDITOR_LANG);
    this._form.data = { show_map: true, map_height: 260, show_images: true, view: "shops", ...this._config };
  }
}

const LABELS = {
  cs: {
    entity: "Entita (senzor Výsledky hledání)", title: "Nadpis (prázdné = výchozí)", language: "Jazyk karty",
    view: "Výchozí zobrazení", show_map: "Mapa (když je povolená v nastavení integrace)", map_height: "Výška mapy (px)",
    map_style: "Mapový podklad", show_images: "Obrázky produktů",
  },
  sk: {
    entity: "Entita (senzor Výsledky hľadania)", title: "Nadpis (prázdne = predvolený)", language: "Jazyk karty",
    view: "Predvolené zobrazenie", show_map: "Mapa (keď je povolená v nastaveniach integrácie)", map_height: "Výška mapy (px)",
    map_style: "Mapový podklad", show_images: "Obrázky produktov",
  },
  en: {
    entity: "Entity (Search results sensor)", title: "Title (empty = default)", language: "Card language",
    view: "Default view", show_map: "Map (when enabled in the integration settings)", map_height: "Map height (px)",
    map_style: "Map style", show_images: "Product images",
  },
};

const editorSchema = (lang) => [
  { name: "entity", required: true, selector: { entity: { domain: "sensor", integration: DOMAIN } } },
  { name: "title", selector: { text: {} } },
  {
    name: "language",
    selector: {
      select: {
        mode: "dropdown",
        options: [
          { value: "", label: "Auto (HA / integrace)" },
          { value: "cs", label: "Čeština" },
          { value: "sk", label: "Slovenčina" },
          { value: "en", label: "English" },
        ],
      },
    },
  },
  {
    type: "grid",
    name: "",
    schema: [
      {
        name: "view",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "shops", label: `🏪 ${I18N[lang].shops}` },
              { value: "items", label: `🧺 ${I18N[lang].items}` },
            ],
          },
        },
      },
      { name: "show_images", selector: { boolean: {} } },
      { name: "show_map", selector: { boolean: {} } },
      { name: "map_height", selector: { number: { min: 120, max: 600, step: 10, mode: "box" } } },
      {
        name: "map_style",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "auto", label: "Auto" },
              { value: "carto", label: "CARTO Voyager" },
              { value: "carto_dark", label: "CARTO Dark" },
              { value: "osm", label: "OpenStreetMap" },
              { value: "none", label: "Bez podkladu (jen špendlíky)" },
            ],
          },
        },
      },
    ],
  },
];

if (!customElements.get("akce-na-jidlo-card")) customElements.define("akce-na-jidlo-card", AkceNaJidloCard);
if (!customElements.get("akce-na-jidlo-card-editor")) customElements.define("akce-na-jidlo-card-editor", AkceNaJidloCardEditor);

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "akce-na-jidlo-card")) {
  window.customCards.push({
    type: "akce-na-jidlo-card",
    name: "Akce na jídlo",
    description: "Nákupní košík – napište potraviny a karta najde, kde jsou v okolí v akci nejlevněji (s mapou).",
    preview: true,
    documentationURL: "https://github.com/joshuaaaaa/HA-akce-na-jidlo#lovelace-karta",
  });
}
