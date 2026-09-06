# adr-id-check

Prosty, statyczny agregator linków do weryfikacji tożsamości kierowców ADR:
dla każdego państwa-strony Umowy ADR (UNECE) pokazuje bezpośrednie linki do
oficjalnych stron **PRADO** (Rada UE — wzory dowodów, paszportów i praw
jazdy) oraz **UNECE** (wzory zaświadczeń ADR kierowcy).

## Uwagi związane z regulaminem PRADO

PRADO ma wyraźny zakaz "framing or mirroring" (czyli osadzania ich treści
w cudzej stronie — iframe, proxy, kopiowanie zdjęć) bez pisemnej zgody.
**Ale wprost zezwala na zwykłe hiperlinkowanie** do swoich stron, bez
potrzeby pytania o zgodę:

> "authorisation to create Internet links to the PRADO pages is given
> herewith; to publish such a link you do not need further permission"
> — https://www.consilium.europa.eu/en/about-site/copyright/

Dlatego to narzędzie **wyłącznie linkuje** (`target="_blank"`) do PRADO i
UNECE — bez iframe, proxy, pobierania czy przechowywania zdjęć dokumentów,
bez parsowania treści tych stron w celu ich powielenia. `generate.py
--check-links` sprawdza wyłącznie **kod odpowiedzi HTTP** linku, nie czyta
ani nie zapisuje jego treści.

## Struktura

```
adr-id-check/
├── data/countries.json          # lista stron Umowy ADR + kod PRADO + pozycja w akordeonie UNECE + wyjątki (edytuj tu)
├── data/locales.json            # wszystkie teksty PL/EN (edytuj tu treść strony)
├── data/country-borders.geo.json# granice 55 krajów (Natural Earth) do mapy
├── assets/styles.css            # wspólny arkusz stylów (dark/light, "glass" header)
├── assets/leaflet/               # biblioteka mapy (Leaflet 1.9.4, MIT), dołączona lokalnie
├── template.html                 # szablon HTML/JS — jedna strona, oba języki (bez zależności zewnętrznych)
├── generate.py                    # buduje index.html z template.html + JSON-y
└── index.html                     # WYGENEROWANY plik — JEDEN, z pełną treścią PL i EN
```

**Jeden plik, dwa języki:** obie wersje językowe są w tym samym `index.html`
— oba pełne bloki treści siedzą w DOM-ie naraz, JS chowa/pokazuje jeden z
nich atrybutem `hidden` i zapamiętuje wybór w `localStorage` (dwa przyciski
PL/EN w nagłówku). To był świadomy wybór na Twoje wyraźne życzenie —
osobne pliki per język z tagami `hreflang` są zwykle mocniejsze pod SEO
(Google widzi od razu gotową treść w każdym języku pod osobnym adresem),
ale zdecydowaliśmy się na jeden plik.

**Przed publikacją:** ustaw prawdziwą domenę w stałej `DOMAIN_BASE` na
górze `generate.py` (używana tylko do `<link rel="canonical">` — reszta
strony działa bez tego).

## Ręcznie potwierdzone wyjątki (`data/countries.json`)

Część linków PRADO/UNECE nie działa tak, jak powinna, mimo że wpis
teoretycznie istnieje — to nie da się wykryć automatycznie bez
parsowania treści strony (a tego celowo unikamy), więc te wyjątki są
ręcznie wpisane i wymagają ręcznej weryfikacji raz w roku:

- **`"prado_broken": ["id_card", "driving_licence"]`** — PRADO dla tego
  kraju/kategorii serwuje bezpośrednie pobieranie pliku zamiast strony
  (błąd po stronie PRADO — pobierany jest pusty plik, dokumentu po prostu
  jeszcze nie ma w tym rejestrze). Przycisk jest wyszarzony, a prawdziwy
  link zostaje w kodzie strony jako komentarz HTML tuż nad przyciskiem —
  łatwo go przywrócić, gdy PRADO to naprawi (usuń odpowiednią kategorię z
  tej listy i uruchom `generate.py` ponownie).
- **`"unece_unavailable": true`** — akordeon UNECE dla tego kraju istnieje
  (ma swój `#accordion_N`), ale w środku jest tylko „Information not
  available", bez realnego wzoru zaświadczenia. Tak samo: przycisk
  wyszarzony, link zachowany w komentarzu.
- **`"note_pl"` / `"note_en"`** — dowolna dodatkowa notatka pod
  przyciskami danego kraju (np. ostrzeżenie o pasku na zdjęciu
  chorwackiego zaświadczenia, albo informacja o trzech wzorach
  holenderskiego zaświadczenia). Czysto informacyjne, nie wyłącza
  żadnego przycisku.

## Link do certyfikatu ADR (UNECE) — jak to działa i na co uważać

Strona UNECE (`unece.org/transport/dangerous-goods/adr-certificates`)
używa akordeonu, gdzie każdy kraj ma swój fragment adresu w formacie
`#accordion_N`, licząc od 0 w kolejności krajów na stronie (Albania = 0,
Andora = 1, ..., Polska = 35, ...). Pole `adr_cert_index` w
`data/countries.json` to właśnie ten numer.

**Ograniczenie:** jeśli UNECE kiedyś doda, usunie lub przestawi kraj na
liście, wszystkie numery PO tym miejscu się przesuną i linki zaczną
otwierać złe kraje. Tego też nie da się wykryć automatycznie (patrz sekcja
wyżej), więc `--check-links` sprawdzi tylko, czy sama strona nadal
odpowiada, NIE czy numeracja się nie przesunęła. Raz w roku warto ręcznie
otworzyć link dla 2-3 losowych krajów i potwierdzić, że nadal pokazują
właściwy kraj — jeśli coś się przesunęło, trzeba przeliczyć
`adr_cert_index` dla całej listy od tego miejsca w dół.

## Mapa krajów-stron Umowy ADR

Nad wyszukiwarką jest jedna wspólna mapa (Leaflet), która podświetla
**kontury** pasujących krajów (nie pinezki) w reakcji na wpisywany tekst.
Kliknięcie kraju na mapie (albo wpisanie nazwy tak, że zostaje dokładnie
jedno trafienie) otwiera dymek z tymi samymi przyciskami dokumentów
(PRADO/UNECE, razem z wyszarzonymi/wyłączonymi i notatkami), co karta tego
kraju na liście poniżej — nie trzeba przewijać do karty, żeby zobaczyć linki.

- **Kafelki mapy:** zwykłe, darmowe kafelki OpenStreetMap
  (`tile.openstreetmap.org`) — **bez klucza API**. (Wcześniejsza wersja
  używała kafelków CARTO, które w międzyczasie zaczęły wymagać klucza —
  dlatego wróciliśmy do zwykłego OSM). OSM nie ma darmowego ciemnego
  wariantu bez klucza, więc w trybie ciemnym kafelki są po prostu odwracane
  filtrem CSS (`invert()+hue-rotate()` w `styles.css`) — kontury krajów są
  osobną warstwą wektorową i nie są tym filtrem dotknięte. Wymagana
  atrybucja "© OpenStreetMap contributors" jest wyświetlana automatycznie
  w rogu mapy — nie usuwaj jej.
- **Granice krajów:** lokalny plik `data/country-borders.geo.json`
  (Natural Earth, uproszczone granice administracyjne, domena publiczna),
  wygenerowany raz z publicznie dostępnych zbiorów — strona nie odpytuje
  żadnego API o granice w czasie działania, tylko wczytuje ten jeden plik.
- **Biblioteka:** `assets/leaflet/` (Leaflet 1.9.4, MIT) jest dołączona do
  projektu lokalnie — strona nie ładuje jej z CDN w runtime.
- **Zabezpieczenie przed "porywaniem" scrolla:** kółko myszy nad mapą
  zaczyna ją zoomować dopiero po kliknięciu w mapę (widoczna podpowiedź,
  która znika po kliknięciu) — przewijanie strony myszką nad mapą nie jest
  już przechwytywane.
- Jeśli plik granic nie wczyta się (np. otwarcie `index.html` bezpośrednio
  z dysku, bez serwera — `fetch()` tego nie obsłuży), cała mapa chowa się
  automatycznie, żeby nie zostawiać pustego prostokąta na stronie.

## Coroczna aktualizacja

1. Sprawdź, czy lista Umawiających się Stron Umowy ADR się zmieniła:
   https://treaties.un.org/Pages/ViewDetails.aspx?src=TREATY&mtdsg_no=XI-B-14&chapter=11&clang=_en
   (nowe kraje zdarzają się raz na kilka lat — dopisz ręcznie do `data/countries.json`).
2. Sprawdź, czy nowy kraj ma wpis w PRADO:
   https://www.consilium.europa.eu/prado/en/search-by-document-country.html
3. Ręcznie zweryfikuj numerację `adr_cert_index` (patrz wyżej) oraz czy
   któryś z ręcznie wyłączonych linków (`prado_broken` / `unece_unavailable`
   — patrz sekcja wyżej) już działa — jeśli tak, usuń odpowiedni wpis.
4. Uruchom:
   ```
   python3 generate.py --check-links
   ```
   Skrypt sprawdzi każdy AKTYWNY link (pomija te już oznaczone jako
   zepsute — po to właśnie jest to oznaczenie), z 1-sekundowym odstępem
   między zapytaniami, żeby nie obciążać cudzych serwerów, i zapisze
   raport błędów, jeśli któryś przestał działać.
5. Wrzuć nowy `index.html` na hosting.

Zależności: tylko standardowa biblioteka Pythona — nic do instalowania.

## Czego ta strona NIE robi (świadomie)

- Nie pokazuje ani nie przechowuje zdjęć dokumentów.
- Nie ogranicza listy wzorów dokumentów do "ostatnich 10 lat" — o tym, która
  wersja dokumentu jest aktualna, informuje sama strona PRADO (najnowsza
  wersja jest tam widoczna na bieżąco, bez potrzeby kopiowania tych danych
  tutaj).
- Nie jest substytutem szkolenia / procedury weryfikacji tożsamości
  wymaganej przepisami — to tylko szybki dostęp do oficjalnych źródeł.

## Licencja

Projekt jest udostępniony na licencji **Creative Commons Uznanie autorstwa
4.0 (CC BY 4.0)**.

W skrócie możesz:

* kopiować;
* modyfikować;
* rozpowszechniać;
* wykorzystywać komercyjnie;

zachowując informację o źródle (autorstwo + link do tego repozytorium).
</content>
