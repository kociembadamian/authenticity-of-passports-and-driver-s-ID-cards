# adr-id-check

A simple, static link aggregator for verifying ADR drivers' identity: for
each country party to the ADR Agreement (UNECE), it shows direct links to
the official **PRADO** (EU Council — ID card, passport and driving licence
specimens) and **UNECE** (ADR driver certificate specimens) pages.

## Notes on the PRADO terms of use

PRADO explicitly prohibits "framing or mirroring" (i.e. embedding their
content on another site — iframe, proxy, copying images) without written
permission. **But it explicitly allows plain hyperlinking** to its pages,
with no need to ask for permission:

> "authorisation to create Internet links to the PRADO pages is given
> herewith; to publish such a link you do not need further permission"
> — https://www.consilium.europa.eu/en/about-site/copyright/

That's why this tool **only links** (`target="_blank"`) to PRADO and
UNECE — no iframe, no proxy, no downloading or storing document images, no
parsing of those pages' content to reproduce it. `generate.py
--check-links` checks only the link's **HTTP response code**; it neither
reads nor stores its content.

## Structure

```
adr-id-check/
├── data/countries.json          # list of ADR Agreement parties + PRADO code + UNECE accordion position + exceptions (edit here)
├── data/locales.json            # all PL/EN page text (edit page content here)
├── data/country-borders.geo.json# borders of 55 countries (Natural Earth) for the map
├── assets/styles.css            # shared stylesheet (dark/light, "glass" header)
├── assets/leaflet/               # map library (Leaflet 1.9.4, MIT), bundled locally
├── template.html                 # HTML/JS template — a single page, both languages (no external dependencies)
├── generate.py                    # builds index.html from template.html + the JSON files
└── index.html                     # GENERATED file — a SINGLE file with the full PL and EN content
```

**One file, two languages:** both language versions live in the same
`index.html` — both full content blocks sit in the DOM at once, and JS
hides/shows one of them via the `hidden` attribute and remembers the
choice in `localStorage` (two PL/EN buttons in the header). This was a
deliberate choice at your explicit request — separate per-language files
with `hreflang` tags are usually stronger for SEO (Google sees ready-made
content in each language at its own address right away), but we went with
a single file.

**Before publishing:** set the real domain in the `DOMAIN_BASE` constant
at the top of `generate.py` (used only for `<link rel="canonical">` — the
rest of the site works without it).

## Manually confirmed exceptions (`data/countries.json`)

Some PRADO/UNECE links don't work as they should even though the entry
technically exists — this can't be detected automatically without parsing
the page's content (which we deliberately avoid), so these exceptions are
entered manually and need manual re-verification once a year:

- **`"prado_broken": ["id_card", "driving_licence"]`** — for this
  country/category, PRADO serves a direct file download instead of a page
  (a bug on PRADO's end — an empty file gets downloaded; the document
  simply doesn't exist in that registry yet). The button is greyed out,
  and the real link stays in the page source as an HTML comment right
  above the button — easy to restore once PRADO fixes it (remove the
  relevant category from this list and run `generate.py` again).
- **`"unece_unavailable": true`** — the UNECE accordion for this country
  exists (it has its own `#accordion_N`), but inside there's only
  "Information not available", with no actual certificate specimen.
  Same handling: the button is greyed out, the link is kept in a comment.
- **`"note_pl"` / `"note_en"`** — any extra note shown under a country's
  buttons (e.g. a warning about the stripe in the Croatian certificate
  photo, or a note about the three Dutch certificate templates). Purely
  informational, doesn't disable any button.

## The UNECE ADR certificate link — how it works and what to watch for

The UNECE page (`unece.org/transport/dangerous-goods/adr-certificates`)
uses an accordion where each country has its own URL fragment in the
format `#accordion_N`, counting from 0 in the order countries appear on
the page (Albania = 0, Andorra = 1, ..., Poland = 35, ...). The
`adr_cert_index` field in `data/countries.json` is exactly this number.

**Limitation:** if UNECE ever adds, removes, or reorders a country in the
list, every number AFTER that point shifts, and the links will start
opening the wrong country. This also can't be detected automatically (see
the section above), so `--check-links` will only check whether the page
itself still responds, NOT whether the numbering has shifted. Once a year
it's worth manually opening the link for 2-3 random countries and
confirming they still show the right country — if something has shifted,
`adr_cert_index` needs to be recalculated for the whole list from that
point onward.

## Map of ADR Agreement party countries

Above the search box there is one shared map (Leaflet) that highlights the
**outlines** of matching countries (not pins) as text is typed. Clicking a
country on the map (or typing a name so that exactly one match remains)
opens a popup with the same document buttons (PRADO/UNECE, including
greyed-out/disabled ones and notes) as that country's card in the list
below — no need to scroll to the card to see the links.

- **Map tiles:** plain, free OpenStreetMap tiles (`tile.openstreetmap.org`)
  — **no API key**. (An earlier version used CARTO tiles, which in the
  meantime started requiring a key — hence the switch back to plain OSM.)
  OSM has no free dark variant without a key, so in dark mode the tiles are
  simply inverted with a CSS filter (`invert()+hue-rotate()` in
  `styles.css`) — country outlines are a separate vector layer and are not
  affected by this filter. The required "© OpenStreetMap contributors"
  attribution is displayed automatically in the corner of the map — don't
  remove it.
- **Country borders:** a local `data/country-borders.geo.json` file
  (Natural Earth, simplified administrative borders, public domain),
  generated once from publicly available datasets — the site doesn't query
  any API for borders at runtime, it just loads this one file.
- **Library:** `assets/leaflet/` (Leaflet 1.9.4, MIT) is bundled locally
  with the project — the site doesn't load it from a CDN at runtime.
- **Scroll-hijacking protection:** the mouse wheel over the map only
  starts zooming it after clicking on the map (a visible hint disappears
  after clicking) — scrolling the page with the mouse over the map is no
  longer captured.
- If the borders file fails to load (e.g. opening `index.html` directly
  from disk, without a server — `fetch()` won't work in that case), the
  whole map hides itself automatically, so it doesn't leave an empty
  rectangle on the page.

## Annual update

1. Check whether the list of ADR Agreement contracting parties has changed:
   https://treaties.un.org/Pages/ViewDetails.aspx?src=TREATY&mtdsg_no=XI-B-14&chapter=11&clang=_en
   (new countries happen once every few years — add them manually to
   `data/countries.json`).
2. Check whether the new country has an entry in PRADO:
   https://www.consilium.europa.eu/prado/en/search-by-document-country.html
3. Manually verify the `adr_cert_index` numbering (see above), and check
   whether any manually disabled link (`prado_broken` / `unece_unavailable`
   — see above) now works — if so, remove the corresponding entry.
4. Run:
   ```
   python3 generate.py --check-links
   ```
   The script checks every ACTIVE link (skipping those already flagged as
   broken — that's the whole point of that flag), with a 1-second delay
   between requests so as not to overload other people's servers, and
   writes an error report if anything has stopped working.
5. Upload the new `index.html` to your hosting.

Dependencies: only the Python standard library — nothing to install.

## What this site deliberately does NOT do

- It doesn't show or store document photos.
- It doesn't limit the list of document specimens to "the last 10 years"
  — which document version is current is shown live by PRADO itself (its
  latest version is visible there at all times, with no need to duplicate
  that data here).
- It's not a substitute for the training or identity-verification
  procedure required by regulations — it's just quick access to official
  sources.

## License

This project is released under the **Creative Commons Attribution 4.0
(CC BY 4.0)** license.

In short, you may:

* copy;
* modify;
* redistribute;
* use commercially;

provided you credit the source (attribution + a link to this repository).
</content>
