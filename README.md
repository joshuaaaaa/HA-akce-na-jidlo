# 🧺 Akce na jídlo – Home Assistant

Integrace pro Home Assistant s kartou **nákupního košíku**. Do karty napíšete jednu nebo víc
potravin (např. `mléko, chleba, máslo`), zmáčknete **Hledat** a karta vypíše **obchody v okolí**,
kde jsou potraviny **v akci za nejlepší cenu**, s **názvem a adresou pobočky**, vzdáleností
a otevírací dobou. Když to povolíte v nastavení, ukáže i **mapu** s očíslovanými obchody.

Vychází z integrace [Akce na pivo](https://github.com/joshuaaaaa/HA-akce-na-pivo), jen se
nehledá pivo každou noc, ale **cokoli, co napíšete, ve chvíli, kdy to napíšete**.

- **Česko 🇨🇿 i Slovensko 🇸🇰**: zemi vyberete při přidání integrace.
- **Čeština, slovenčina, angličtina**: integrace i karta.
- Akce z letákových webů (Kupi.cz, Kompas Slev, AkcniCeny.cz; na Slovensku Kimbino, Letakomat,
  KdeJeAkcia, Kompas Zliav, Kupino, AkčnéLetáky, Promotheus) a z vlastních URL.
- Pobočky, adresy a otevírací doby z OpenStreetMap (Overpass + Nominatim).

## Jak to funguje

1. V kartě napíšete potraviny, oddělené **čárkou** nebo **novým řádkem** (Shift+Enter).
   Enter nebo tlačítko **Hledat** spustí hledání (max. 15 potravin najednou).
2. Integrace pro každou potravinu prohledá zapnuté weby s akcemi. Nechá si jen akce, jejichž
   název potravinu opravdu obsahuje („mléko“ najde „Mléko polotučné“ i „Trvanlivé mléko“,
   ale ne „Jogurt“; „rohlík“ najde „Rohlíky“), které ještě platí a odpovídají nastavení.
3. Ke každému řetězci najde **nejbližší pobočku** v nastaveném okruhu.
4. Karta ukáže dva pohledy:
   - **🏪 Obchody**: seznam obchodů s názvem, adresou a vzdáleností. U každého jsou potraviny,
     které tam jsou v akci, a jejich cena. 🏆 = tady je potravina nejlevněji ze všech.
     Nahoře jsou obchody, kde se toho nejvíc koupí nejlevněji. Odkazy **Navigovat** a **Mapy.com**.
   - **🧺 Potraviny**: pro každou potravinu žebříček nejlevnějších akcí (cena, stará cena,
     sleva, cena za kg/l/ks, platnost, obchod a adresa).
5. Nahoře je souhrn: kolik potravin se našlo, co **teď není v akci** a kolik stojí celý nákup,
   když každou potravinu koupíte tam, kde je nejlevnější.

Stejné hledání se 3 hodiny bere z mezipaměti. Pobočky z OpenStreetMap se ukládají na 7 dní
(a přenačtou se, když se posunete o víc než 2 km).

## Instalace integrace

### HACS
1. HACS → Integrace → ⋮ → *Vlastní repozitáře* → `https://github.com/joshuaaaaa/HA-akce-na-jidlo`, kategorie *Integrace*.
2. Nainstalujte **Akce na jídlo** a restartujte Home Assistant.

### Ručně
Zkopírujte `custom_components/akce_na_jidlo` do `/config/custom_components/` a restartujte HA.

Potom: **Nastavení → Zařízení a služby → Přidat integraci → Akce na jídlo**.

## Nastavení

| Volba | Popis | Výchozí |
|---|---|---|
| Země | Česko / Slovensko (měna, weby, hranice pro pobočky) | Česko |
| Jazyk | Automaticky / čeština / slovenčina / angličtina | automaticky |
| **Zobrazovat v kartě mapu obchodů** | Zapne mapu v kartě (v kartě jde ještě vypnout) | **vypnuto** |
| Poloha | Domov HA, nebo `person` / `device_tracker` / `zone` (telefon) | domov |
| Okruh hledání obchodů | 1–50 km | 10 km |
| Jen obchody s pobočkou v okruhu | Akce řetězců bez pobočky v okolí se nezobrazí | zapnuto |
| Typ obchodu | Kamenné i online / jen kamenné / jen online (Rohlik, Košík…) | jen kamenné |
| Počet akcí na jednu potravinu | 1–10 | 5 |
| Řazení | Cena balení / cena za kg, l, ks / nejbližší obchod | cena balení |
| Vynechat akce jen s kartou | Lidl Plus, Clubcard, Můj Albert… | vypnuto |
| Připravované akce | Akce z nových letáků, které teprve začnou | vypnuto |
| Weby s akcemi | Které zdroje prohledávat | všechny pro zemi |
| Vlastní URL | Jedna na řádek, `{query}` = hledaný text (`ml%C3%A9ko`), `{slug}` = `mleko` | – |

Všechno jde později změnit přes **Konfigurovat**.

## Lovelace karta

Karta je samostatný soubor [`www/akce-na-jidlo-card.js`](www/akce-na-jidlo-card.js):

1. Uložte ho do Home Assistantu jako `/config/www/akce-na-jidlo-card.js` (např. doplňkem
   *File editor* nebo *Samba share*). Když složka `www` ještě neexistuje, vytvořte ji a restartujte HA.
2. **Nastavení → Ovládací panely → ⋮ → Zdroje → Přidat zdroj**
   (zobrazí se jen se zapnutým *Rozšířeným režimem* v profilu):
   - URL: `/local/akce-na-jidlo-card.js`
   - Typ zdroje: **JavaScript modul**
3. Obnovte prohlížeč (Ctrl+F5).
4. Upravit ovládací panel → **Přidat kartu** → **Akce na jídlo**. Karta má grafický editor.

**Aktualizace karty:** přepište soubor a u zdroje zvyšte verzi v URL, např.
`/local/akce-na-jidlo-card.js?v=2`.

```yaml
type: custom:akce-na-jidlo-card
entity: sensor.akce_na_jidlo_vysledky_hledani   # senzor Výsledky hledání
title: ""          # prázdné = „Nákupní košík v akci“
view: shops        # výchozí pohled: shops (obchody) | items (potraviny)
show_images: true  # obrázky produktů v pohledu Potraviny
show_map: true     # mapa – zobrazí se, jen když je povolená v nastavení integrace
map_height: 260
map_style: auto    # auto | carto | carto_dark | osm
language: ""       # "" = podle integrace / HA, nebo cs | sk | en
```

Mapa se kreslí přímo z dlaždic CARTO (data OpenStreetMap), bez externích knihoven. Mapou jde
posouvat, **+ / −** mění přiblížení, **⤢** ukáže všechny obchody. Klepnutí na obchod v seznamu
nebo na špendlík obchod na mapě přiblíží. 🏠 je vaše poloha.

## Entity a služba

| Entita | Stav | Poznámka |
|---|---|---|
| `sensor.*_vysledky_hledani` | počet nalezených potravin | atributy `query`, `items`, `shops`, `found`, `not_found`, `total`, `show_map`… (zdroj dat pro kartu) |
| `sensor.*_kam_na_nakup` | název obchodu | kde se toho z posledního hledání nejvíc koupí nejlevněji; `address`, `distance_km`, `items`, `navigate_url` |

**Služba `akce_na_jidlo.search`** (vrací i odpověď s celým výsledkem):

```yaml
action: akce_na_jidlo.search
data:
  items: "mléko, chleba, máslo"   # nebo seznam; prázdné = zopakovat poslední hledání
response_variable: vysledek
```

Po dokončení se vyvolá událost `akce_na_jidlo_vysledky` (`query`, `found`, `not_found`,
`total`, `best_shop`).

### Příklad: každý pátek nákupní seznam do mobilu

```yaml
automation:
  - alias: Kam na nákup
    triggers:
      - trigger: time
        at: "17:00:00"
    conditions:
      - condition: time
        weekday: fri
    actions:
      - action: akce_na_jidlo.search
        data:
          items: "mléko, máslo, vejce, kuřecí prsa"
        response_variable: r
      - action: notify.mobile_app_telefon
        data:
          title: "🧺 Nejvýhodněji: {{ r.shops[0].shop if r.shops else 'nic v akci' }}"
          message: >
            {% for s in r.shops[:3] %}{{ s.shop }} ({{ s.address }}):
            {% for i in s['items'] %}{{ i.query }} {{ i.price }} {{ r.currency_symbol }}{{ ' 🏆' if i.best }}, {% endfor %}
            {% endfor %}
```

## Řešení potíží

- **Nic se nenašlo.** Podívejte se do atributu `sources` senzoru *Výsledky hledání*: pro každý
  web je tam počet akcí a chyby (např. `HTTP 403`). Zkuste potravinu napsat obecněji
  („mléko“ místo „mléko polotučné Madeta“), nebo vypněte *Jen obchody s pobočkou v okruhu*.
- **Obchody bez adresy.** Veřejné servery OpenStreetMap (Overpass) bývají přetížené. Karta pak
  ukáže upozornění a akce bez adres. Stačí hledat znovu za chvíli.
- **Na mapě „Access blocked“.** Nepoužívejte `map_style: osm`. OpenStreetMap blokuje dlaždice
  bez hlavičky Referer, kterou HA neposílá.

> ⚠️ Weby s akcemi se při vývoji nedaly otevřít, takže adresy vyhledávání a parser nebyly
> vyzkoušené na jejich skutečném obsahu (parser kupi.cz je převzatý z Akce na pivo). Když některý
> zdroj nic nevrací, zadejte funkční adresu do **Vlastní URL**.

## Výkon a zatížení Home Assistantu (Raspberry Pi)

- Integrace **na pozadí nic nestahuje**. Pracuje jen ve chvíli, kdy zmáčknete Hledat
  (nebo zavoláte službu). Po startu HA nic nestahuje.
- Zpracování stránek, filtrování akcí i přiřazení poboček běží **ve vlákně mimo hlavní
  smyčku HA**, takže HA během hledání nezamrzne.
- Stránka se stáhne nejvýš do 3 MB a zpracuje se z ní nejvýš 600 akcí. Jedno stažení má
  limit 15 s a celé hledání 2 minuty. Weby, na které už nezbyde čas, se přeskočí.
- Výsledky se na disk (SD kartu) zapisují s odstupem 30 s, ne po každém hledání.

## Upozornění a odpovědnost

- **Vývojář neodpovídá za žádné problémy ani škody** vzniklé používáním integrace a karty,
  včetně nesprávných nebo neaktuálních cen, akcí, adres a otevíracích dob. Software se
  poskytuje „tak, jak je“, bez záruky.
- Ceny pocházejí z webů třetích stran a z OpenStreetMap. Před nákupem si je ověřte v letáku
  nebo v obchodě. Integrace není spojena s žádným obchodním řetězcem ani provozovatelem webů.
- Uživatel odpovídá za to, že používání je v souladu s podmínkami zdrojových webů
  a služeb OpenStreetMap a CARTO.
- Licence **MIT**, viz [LICENSE](LICENSE).

## http://buymeacoffee.com/jakubhruby
