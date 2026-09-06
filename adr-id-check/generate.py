#!/usr/bin/env python3
"""
PL — Generator strony "ADR ID Check" — JEDEN plik index.html z dwoma językami
==============================================================================

Buduje pojedynczy, samodzielny index.html zawierający PEŁNĄ treść po
polsku i po angielsku (oba bloki są w DOM, JS chowa/pokazuje jeden z nich
atrybutem `hidden` i zapamiętuje wybór w localStorage).

Co jeszcze robi:
- Wczytuje data/countries.json (lista Umawiających się Stron Umowy ADR,
  kod PRADO, pozycja w akordeonie certyfikatów UNECE, oraz ręcznie
  potwierdzone wyjątki: linki PRADO, które serwują pobieranie pliku
  zamiast strony (`prado_broken`), wpisy UNECE bez realnego wzoru mimo
  istniejącego akordeonu (`unece_unavailable`), oraz dowolne dodatkowe
  notatki per kraj (`note_pl`/`note_en`)).
- Dla zepsutych/pustych linków NIE usuwa ich - wyłącza widoczny przycisk
  (szary, nieklikalny) i zostawia prawdziwy link w komentarzu HTML tuż
  obok, żeby ktoś czytający źródło strony wiedział dokładnie, o co
  chodzi i mógł go łatwo przywrócić, gdy PRADO/UNECE naprawi swoją stronę.
- Buduje linki DO OFICJALNYCH stron zewnętrznych (PRADO, UNECE) - nie
  pobiera, nie kopiuje ani nie przechowuje żadnej ich treści/zdjęć.
- Opcjonalnie (--check-links) sprawdza tylko kod HTTP każdego AKTYWNEGO
  linku (bez parsowania treści) - do rocznej konserwacji. Wyłączone
  (`prado_broken`/`unece_unavailable`) linki są pomijane, bo już
  wiadomo, że nie działają - to na nich właśnie polega to oznaczenie.

Uruchomienie:
    python3 generate.py                 # generuje index.html
    python3 generate.py --check-links   # + sprawdza żywotność aktywnych linków

Zależności: tylko biblioteka standardowa Pythona.


EN — Generator for the "ADR ID Check" site — ONE index.html file, two languages
================================================================================

Builds a single, self-contained index.html file containing the FULL
content in both Polish and English (both blocks live in the DOM, JS
hides/shows one of them via the `hidden` attribute and remembers the
choice in localStorage).

What else it does:
- Loads data/countries.json (the list of ADR Agreement contracting
  parties, PRADO code, position in the UNECE certificate accordion, and
  manually confirmed exceptions: PRADO links that serve a file download
  instead of a page (`prado_broken`), UNECE entries with no real specimen
  despite an existing accordion entry (`unece_unavailable`), and any
  extra per-country notes (`note_pl`/`note_en`)).
- For broken/empty links, it does NOT remove them - it disables the
  visible button (greyed out, unclickable) and leaves the real link in an
  HTML comment right next to it, so anyone reading the page source knows
  exactly what's going on and can easily restore it once PRADO/UNECE fix
  their page.
- Builds links TO OFFICIAL external pages (PRADO, UNECE) - it doesn't
  download, copy, or store any of their content/images.
- Optionally (--check-links) checks only the HTTP status code of each
  ACTIVE link (without parsing content) - for annual maintenance. Disabled
  (`prado_broken`/`unece_unavailable`) links are skipped, since they're
  already known not to work - that's the whole point of the flag.

Usage:
    python3 generate.py                 # generates index.html
    python3 generate.py --check-links   # + checks that active links are alive

Dependencies: only the Python standard library.
"""
import json
import sys
import time
import urllib.request
import urllib.error
from datetime import date, datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "data" / "countries.json"
LOCALES_FILE = BASE_DIR / "data" / "locales.json"
TEMPLATE_FILE = BASE_DIR / "template.html"
OUTPUT_FILE = BASE_DIR / "index.html"

# UZUPEŁNIJ przed publikacją - używane tylko w <link rel="canonical">.
DOMAIN_BASE = "https://TWOJA-DOMENA.pl/adr-id-check/"

PRADO_BASE = "https://www.consilium.europa.eu/prado/en/prado-documents/{code}/{cat}/docs-per-category.html"
UNECE_CERT_BASE = "https://unece.org/transport/dangerous-goods/adr-certificates"
CATEGORY_ID_CARD = "b"
CATEGORY_PASSPORT = "a"
CATEGORY_DRIVING_LICENCE = "f"

DOC_CATEGORIES = ("id_card", "passport", "driving_licence")

USER_AGENT = "adr-id-check-link-checker/1.0 (+https://kocie.mba; roczna weryfikacja linkow, nie pobiera tresci)"


def prado_link(iso3: str, category: str) -> str:
    return PRADO_BASE.format(code=iso3.lower(), cat=category)


def unece_cert_link(index) -> str | None:
    if index is None:
        return None
    return f"{UNECE_CERT_BASE}#accordion_{index}"


def build_country_row(c: dict) -> dict:
    iso3 = c["iso3"]
    cert_url = unece_cert_link(c.get("adr_cert_index"))
    broken = set(c.get("prado_broken", []))
    row = {
        "iso3": iso3,
        "name_pl": c["name_pl"],
        "name_en": c["name_en"],
        "adr_since": c.get("adr_since", ""),
        "prado": c.get("prado", True),
        "broken": broken,
        "unece_unavailable": bool(c.get("unece_unavailable", False)),
        "note_pl": c.get("note_pl"),
        "note_en": c.get("note_en"),
        "links": {"adr_cert": cert_url},
    }
    if row["prado"]:
        row["links"]["id_card"] = prado_link(iso3, CATEGORY_ID_CARD)
        row["links"]["passport"] = prado_link(iso3, CATEGORY_PASSPORT)
        row["links"]["driving_licence"] = prado_link(iso3, CATEGORY_DRIVING_LICENCE)
    return row


def check_url(url: str, timeout: int = 10) -> tuple[bool, str]:
    """Sprawdza tylko kod odpowiedzi HTTP - nie czyta ani nie zapisuje treści strony."""
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return (200 <= resp.status < 400), str(resp.status)
    except urllib.error.HTTPError as e:
        return False, str(e.code)
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def active_links(row: dict):
    """Yields (kind, url) for links NOT already known-broken - those are the
    only ones worth spending an HTTP request to check."""
    for kind in DOC_CATEGORIES:
        if kind in row["links"] and kind not in row["broken"]:
            yield kind, row["links"][kind]
    if row["links"].get("adr_cert") and not row["unece_unavailable"]:
        yield "adr_cert", row["links"]["adr_cert"]


def check_all_links(rows: list[dict]) -> list[str]:
    problems = []
    seen = {}
    unique_links = []
    for row in rows:
        for kind, url in active_links(row):
            unique_links.append((row, kind, url))
    total = len(unique_links)
    for done, (row, kind, url) in enumerate(unique_links, start=1):
        if url in seen:
            ok, code = seen[url]
        else:
            ok, code = check_url(url)
            seen[url] = (ok, code)
            time.sleep(1.0)  # nie zasypujemy serwera zapytaniami
        print(f"  [{done}/{total}] {row['iso3']} / {kind}: {'OK' if ok else 'BLAD'} ({code})")
        if not ok:
            problems.append(f"{row['iso3']} ({row['name_pl']}) / {kind}: {url} -> {code}")
    return problems


def doc_button(url: str | None, label: str, broken: bool, comment_reason: str) -> tuple[str, str | None]:
    """Returns (html, note_text_or_None) for one document button.
    - url is None entirely (no PRADO/UNECE entry at all): disabled span, no comment (nothing to restore).
    - broken (manually confirmed dead/unavailable): disabled span + the real
      link preserved right above it as an HTML comment, plus a visible note.
    - otherwise: a normal working link.
    """
    if url is None:
        return f'<span class="doc-link" aria-disabled="true">{label}</span>', None
    if broken:
        html = (
            f'<!-- Wylaczone ({comment_reason}, sprawdzone 2026-09-04). Docelowy link:\n'
            f'     <a class="doc-link" href="{url}" target="_blank" rel="noopener">{label}</a> -->\n'
            f'      <span class="doc-link" aria-disabled="true">{label}</span>'
        )
        return html, None
    return f'<a class="doc-link" href="{url}" target="_blank" rel="noopener">{label}</a>', None


def render_cards(rows: list[dict], loc: dict, lang: str) -> str:
    cards = []
    for r in rows:
        links = r["links"]
        primary_name = r["name_pl"] if lang == "pl" else r["name_en"]
        secondary_name = r["name_en"] if lang == "pl" else r["name_pl"]

        buttons = []
        notes = []

        for kind, label_key, cat_name in (
            ("id_card", "lbl_id_card", "PRADO / dowod osobisty"),
            ("passport", "lbl_passport", "PRADO / paszport"),
            ("driving_licence", "lbl_driving_licence", "PRADO / prawo jazdy"),
        ):
            if kind not in links:
                continue
            is_broken = kind in r["broken"]
            html, _ = doc_button(links[kind], loc[label_key], is_broken, cat_name)
            buttons.append(html)
            if is_broken:
                notes.append(loc["note_prado_broken"].format(loc[label_key]))

        cert_url = links.get("adr_cert")
        cert_broken = bool(cert_url) and r["unece_unavailable"]
        html, _ = doc_button(cert_url, loc["lbl_adr_cert"], cert_broken, "UNECE / zaswiadczenie ADR")
        buttons.append(html)
        if cert_broken:
            notes.append(loc["note_unece_unavailable"])

        missing_note = "" if r["prado"] else f'<p class="note-missing">{loc["no_prado_note"]}</p>'
        no_cert_note = "" if (cert_url or cert_broken) else f'<p class="note-missing">{loc["no_cert_note"]}</p>'
        broken_notes = "".join(f'<p class="note-missing">{n}</p>' for n in notes)
        extra_note_text = r["note_pl"] if lang == "pl" else r["note_en"]
        extra_note = f'<p class="note-info">{extra_note_text}</p>' if extra_note_text else ""

        search_key = f"{r['name_pl']} {r['name_en']} {r['iso3']}".lower()
        cards.append(f"""      <article class="country-card" data-name="{search_key}" data-iso3="{r['iso3']}">
        <h3>{primary_name} <span class="name-secondary">({secondary_name})</span><span class="iso3-badge">{r['iso3']}</span></h3>
        <p class="adr-since">{loc['since_label']} {r['adr_since']}</p>
        {missing_note}{no_cert_note}{broken_notes}{extra_note}
        <div class="doc-links">{''.join(buttons)}</div>
      </article>""")
    return "\n".join(cards)


def render_lang_content(lang: str, rows: list[dict], loc: dict, link_check_note: str) -> str:
    country_count = f"{len(rows)} {'krajów' if lang == 'pl' else 'countries'}"
    return f"""    <section class="hero">
      <h1>{loc['hero_title']}</h1>
      <p>{loc['hero_p1']}</p>
      <p>{loc['hero_p2']}</p>
    </section>

    <div class="notice-card notice-card--tip notice-card--top">
      <h2>{loc['tip_label']}</h2>
      <p>{loc['tip_body']}</p>
      <p>{loc['tip_body2']}</p>
    </div>

    <div class="search-box">
      <input class="lang-search-input" type="text" placeholder="{loc['search_placeholder']}" autocomplete="off">
    </div>

    <main class="grid">
{render_cards(rows, loc, lang)}
    </main>
    <p class="no-results">{loc['no_results']}</p>

    <div class="notice-card">
      <h2>{loc['disclaimer_title']}</h2>
      <p>{loc['disclaimer_body']}</p>
    </div>

    <p class="legal-note">{loc['legal_note']}</p>

    <footer>
      <p class="footer-row footer-heading">{loc['footer_made_by']} DGSA drs. D. Kociemba — <a href="https://kocie.mba" target="_blank" rel="noopener">kocie.mba</a></p>
      <p class="footer-row">{loc['contact_title']}: <a href="mailto:damian@kocie.mba">damian@kocie.mba</a> &middot; {loc['phone_pl_label']} <a href="tel:+48728719527">+48 728 719 527</a> / {loc['phone_nl_label']} <a href="tel:+31640668505">+31 6 40 66 85 05</a></p>
      <p class="footer-row footer-muted">Spalaan 6, 5628 ZG Eindhoven (NL) &middot; KvK: 95907130 &middot; BTW/VAT: NL005178103B20</p>
      <p class="footer-row footer-links">
        {loc['footer_sources']}
        <a href="https://www.consilium.europa.eu/prado/en/prado-start-page.html" target="_blank" rel="noopener">PRADO</a>
        <a href="https://unece.org/transport/dangerous-goods/adr-certificates" target="_blank" rel="noopener">UNECE — ADR Certificates</a>
        <a href="https://treaties.un.org/Pages/ViewDetails.aspx?src=TREATY&amp;mtdsg_no=XI-B-14&amp;chapter=11&amp;clang=_en" target="_blank" rel="noopener">UN Treaty Collection — ADR status</a>
      </p>
      <p class="footer-row">{loc['license_line']} <a href="#" target="_blank" rel="noopener">GitHub</a></p>
      <p class="footer-row footer-copyright">&copy; Copyright 2026 &ndash; &#8734; kocie.mba &middot; {loc['group_line']}</p>
    </footer>
    <!-- build: {datetime.now().strftime('%Y-%m-%d %H:%M')} · {link_check_note} · {country_count} -->"""


def render_page(rows: list[dict], locales: dict, link_check_note: str) -> str:
    template = TEMPLATE_FILE.read_text(encoding="utf-8")
    loc_pl, loc_en = locales["pl"], locales["en"]

    replacements = {
        "{{PAGE_TITLE_PL}}": loc_pl["page_title"],
        "{{PAGE_TITLE_EN}}": loc_en["page_title"],
        "{{META_DESCRIPTION_PL}}": loc_pl["meta_description"],
        "{{SELF_HREF}}": DOMAIN_BASE,
        "{{BRAND_TAGLINE_PL}}": loc_pl["brand_tagline"],
        "{{BRAND_TAGLINE_EN}}": loc_en["brand_tagline"],
        "{{THEME_TOGGLE_LABEL_PL}}": loc_pl["theme_toggle_label"],
        "{{CONTENT_PL}}": render_lang_content("pl", rows, loc_pl, link_check_note),
        "{{CONTENT_EN}}": render_lang_content("en", rows, loc_en, link_check_note),
    }
    for token, value in replacements.items():
        template = template.replace(token, value)
    return template


def main():
    check_links = "--check-links" in sys.argv

    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    locales = json.loads(LOCALES_FILE.read_text(encoding="utf-8"))
    rows = [build_country_row(c) for c in data["countries"]]

    link_check_note = "Linki nie byly jeszcze automatycznie sprawdzane w tym uruchomieniu."
    if check_links:
        print(f"Sprawdzam zywotnosc aktywnych linkow dla {len(rows)} krajow (to potrwa kilka minut)...")
        problems = check_all_links(rows)
        if problems:
            print("\nZNALEZIONE PROBLEMY:")
            for p in problems:
                print(" -", p)
            report_path = BASE_DIR / f"link-check-report-{date.today().isoformat()}.txt"
            report_path.write_text("\n".join(problems), encoding="utf-8")
            print(f"\nZapisano raport: {report_path}")
            link_check_note = f"Ostatnie sprawdzenie linkow: {date.today().isoformat()} - {len(problems)} problem(ow)."
        else:
            print("\nWszystkie aktywne linki odpowiadaja poprawnie.")
            link_check_note = f"Ostatnie sprawdzenie linkow: {date.today().isoformat()} - wszystko OK."

    html = render_page(rows, locales, link_check_note)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"Zapisano {OUTPUT_FILE} ({len(rows)} krajow, PL+EN w jednym pliku).")


if __name__ == "__main__":
    main()
