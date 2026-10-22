# Reproduktion

Voraussetzungen: Python 3.10 oder neuer (gemessen mit 3.13.16), für E4-Paarläufe und den Phasenvergleich `numpy`
(gemessen mit 2.5.3). Linux empfohlen (die Elternprozesse lesen `/proc/<pid>/status` für den Speicherwächter; unter
Windows/macOS laufen die Kindprozesse direkt, nur die Überwachung fehlt). Alles offline, CPU, kein Node, keine GPU.

```
pip install numpy            # optional, siehe oben
```

## Schnelltests (< 30 s)

```
python3 -I tests/test_schnell.py
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

Alle Skripte liegen in `experimente/skripte/` und werden **aus diesem Verzeichnis** gestartet (sie finden die
Bibliothek über `../../src/kaestchen` und schreiben ihre Ergebnisdateien neben sich). Die Referenzergebnisse liegen in
`experimente/ergebnisse/`; ein neuer Lauf erzeugt neue Dateien mit gleichem Namen im Skriptverzeichnis, die sich dann
vergleichen lassen (Zeiten und Peak-Speicher weichen rechnerbedingt ab, alle Zähler müssen gleich sein).

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

`SHA256SUMS.txt` im Paketstamm deckt jede Datei ab: `sha256sum -c SHA256SUMS.txt`.
