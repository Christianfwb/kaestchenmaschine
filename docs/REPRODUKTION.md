# Reproduktion

Voraussetzungen: Python 3.10 oder neuer. Die Schnelltests und Beispiele 1/2 laufen unter Windows, Linux und macOS ohne Zusatzpakete. Für E4-Paarläufe und Phasenvektoren wird NumPy benötigt; die archivierten Messungen nennen Python 3.13.16 und NumPy 2.5.3.

**Die historischen vollständigen Experimentläufer benötigen Linux.** Elternprozesse lesen `/proc/<pid>/status`; Kindprozesse importieren `resource` und werten dessen Linux-Speichereinheiten aus. Unter Windows bitte WSL verwenden. Native Windows- und macOS-Ausführung dieser Reihen wird nicht unterstützt. Alles offline, CPU, kein Node, keine GPU.

```
pip install numpy            # optional, siehe oben
```

## Plattformunabhängige Schnelltests

```
python -B -I tests/test_schnell.py
python -B -I tests/test_regression.py
```
Erwartet: `5/5 Tests bestanden`. Geprüft wird: Referenz-SHA == hashlib (64 Runden, beide Fälle), Bitgraph == hashlib,
Adapter-Rundreise, Nonceableitung bei 4 und 6 Runden == Orakel, Genesis-Treffer in allen E1-Domänen erhalten.

## Beispiele

```
python3 -I beispiele/01_reduzierte_runden.py 8     # auch 4, 6, 12, 16; 64 = echtes SHA256d (OFFEN, ~2 min, ~90 MiB)
python3 -I beispiele/02_genesis_zeuge.py           # ~2 s
python3 -I beispiele/03_vorrat_modell.py           # ~70 s, 16-Bit-Labor
```

## Vollständige Experimentreihen

**Diese historischen Reihen benötigen Linux.** Die Beispiele 1/2 und Schnelltests benötigen nur Python und laufen auch unter Windows.

Alle Skripte liegen in `experimente/skripte/` und werden **aus diesem Verzeichnis** gestartet (sie finden die
Bibliothek über `../../src/kaestchen` und schreiben ihre Ergebnisdateien neben sich). Die Referenzergebnisse liegen in
`experimente/ergebnisse/`; ein neuer Lauf erzeugt neue Dateien mit gleichem Namen im Skriptverzeichnis, die sich dann
vergleichen lassen (Zeiten und Peak-Speicher weichen rechnerbedingt ab). Zähler sind nur bei derselben Codefassung und denselben Einstellungen direkt vergleichbar; seit dem Erststand wurde die Erkennung bereits leerer Bitdomänen korrigiert. Siehe [Prüfbericht](REVIEW_20261023.md).

`lauf_wurzel3.py` und `lauf_zielhash_fix.py` lesen ihre Vergleichsbelege explizit aus `experimente/ergebnisse/`. Eigene Ausgaben bleiben in `experimente/skripte/`; sie ersetzen nie stillschweigend diese Referenzen. Deshalb müssen keine historischen Läufe zur Vorbereitung wiederholt werden. Neue Läufe im Skriptordner überschreiben dort gleichnamige eigene Ergebnisse: diese bei Bedarf vorab separat sichern.

| Reihe | Aufruf | Dauer / Spitze (gemessen) |
|---|---|---|
| Stufe 0 | `python3 -I lauf_stufe0.py` | 191 s |
| Wurzeltest (alte Grenze 500 000) | `python3 -I lauf_wurzel.py` | 145 s |
| Array-Paare + Wurzel 2,5 Mio. | `python3 -I lauf_array.py` dann `python3 -I lauf_wurzel2.py` | 5,5 s + 310 s, 384 MiB |
| F2-Abschluss + Dreier | `python3 -I pruefspeicher_test.py; python3 -I gate_test.py; python3 -I lauf_wurzel3.py` | 547 s, 370 MiB |
| Ein-Bit / Zwei-Bit | `python3 -I lauf_einbit.py`, `python3 -I lauf_2bit.py` | 205 s / 731 s |
| Wahrheitstabellen / Phasen | `python3 -I lauf_tabellen4.py`, `python3 -I lauf_phasen.py` | Sekunden |
| Komposition (Gleichheit, Mini-Beispiel) | `python3 -I lauf_komposition.py` | 60 s, 119 MiB |
| Reichweite + Auffrischer | `python3 -I reichweite.py` | 41 s, 170 MiB |
| XOR-Beispiel / XOR am Graphen | `python3 -I xor_beispiel.py`, `python3 -I lauf_xor_sha.py` | < 1 s / 134 s |
| Zielhash (4 Läufe) | `python3 -I lauf_zielhash.py` | 451 s, 366 MiB |
| Zielhash E1 bis Fixpunkt | `python3 -I lauf_zielhash_fix.py` | 12 s |
| Rundenkurve 4–16 | `python3 -I lauf_runden.py` | 11 s |
| Vorratsmodell | `python3 -I vorrat_modell.py` | 70 s |

Grenzen je Lauf: 600 s Wandzeit, 400 MiB RSS, 2,5 Mio. Paare (ältere Reihen 500 000 bzw. 120 s/400 MiB für kleine
Tests). Ein Lauf, der die Grenze erreicht, wird mit `OFFEN` und Abbruchgrund gespeichert – das ist ein gültiges
Ergebnis, kein Fehler. `FEHLER` (falscher Ausschluss, Nachprüfung geändert) stoppt die Reihe; er kam in keinem
gültigen Lauf vor.

## Was ein Ergebnisdokument enthält

Jede `ERGEBNIS_*.json` nennt Rechner, Python-Version, Zeiten je Schritt, Peak-RSS (intern und extern), Status, Zähler
(feste Knoten, Ziffern, Paare, Noncebits, Ausschlüsse), Orakel-Treffer und – wo vorhanden – die Karte aller Messstellen
(Register a..h je Runde beider Anwendungen). Kindprozess-Logs (`LAUF_*.log`) halten den Elternprozess fest.

## Prüfsummen

`SHA256SUMS.txt` deckt die gelisteten Veröffentlichungsdateien ab (nicht sich selbst, `.git/` oder neue lokale Ergebnisse):

```sh
python -B -I tools/manifest.py --check
```

Alternativ unter Linux: `sha256sum -c SHA256SUMS.txt`. `.gitattributes` legt LF-Zeilenenden fest, auch für Windows-Checkouts. Bei einem älteren Checkout mit CRLF neu klonen, bevor Prüfsummen verglichen werden. Die Prüfsummen belegen Dateiintegrität, nicht mathematische Korrektheit.

## Labor L1 (24./25. Oktober 2026, Linux)

```sh
python -B -I tests/test_stern.py            # ~20 s: Gruppenfindung, Arbeitsliste, Dreieck, Selbsttests, ein Ausduenn-Fall
python -B -I experimente/l1/stern_n4/stern_n4_bit_lauf.py   # N4r09 exakter Stern: V0/V1/V2, ~95 s (V2 meldet den dokumentierten E7-Formfehler, siehe Bericht)
python -B -I experimente/l1/stern/blockweise_lauf.py       # blockweiser Abgleich inkl. N4r09 in 3,5 s (liest experimente/l1/stern_n4/UEBERGABE_V0.json)
python -B -I experimente/l1/ausduennen/ausduennen_lauf.py  # 48 Ausduenn-Faelle, ~30 s
```

Die Skripte unter `experimente/skripte` für Rundenkurve 17–63 und Sicherheitslinie: `lauf_runden3.py 17 18 19`, `lauf_runden2.py 20 24 28 32 40 48 56` (Minuten), `erweiterung_kontrolle.py`, `erweiterung_wo.py`, `erweiterung_was.py`, `erweiterung_kopie.py`.
