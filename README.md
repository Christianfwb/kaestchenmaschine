# Kästchenmaschine – Propagation statt Suche auf SHA256d

**Stand: Entwurf vom 2026-10-23. Gegenprüfung durch Ghost steht noch aus. Nicht veröffentlicht.**

Ein Forschungsprojekt von Christian Berrang (Idee, Richtung, Entscheidungen), „Ghost" (KI-Agent, Betrieb des Miners, Prüfung
und Präzisierung der Aufträge) und „Fable" (Claude, Anthropic; Umsetzung der Experimente, Messungen, Berichte). Alle
Entscheidungen wurden zu dritt getroffen; dieses Paket dokumentiert den Forschungsteil.

## Worum es geht

Ein Bitcoin-Block gilt, wenn der doppelte SHA-256-Hash seines Kopfes unter einer Zielzahl liegt. Üblich ist Raten: Nonce
einsetzen, hashen, vergleichen, Milliarden Mal. Die Kästchenmaschine versucht das Gegenteil: Sie baut die gesamte Rechnung
als Schaltnetz aus UND- und XOR-Gattern auf (rund 208 000 Gatter für ein echtes Template mit 8 freien Noncebits), gibt
jedem Gatterausgang ein „Kästchen" mit den noch möglichen Werten ({0}, {1} oder {0,1}) und lässt Regeln von beiden Seiten
her – vom bekannten Kopf vorwärts, vom Ziel rückwärts – die Kästchen enger machen. Ein leeres Kästchen bedeutet: diese
Nonces sind ausgeschlossen. Ein vollständig bestimmter Eingang bedeutet: Nonce abgeleitet, ohne sie probiert zu haben.

Die Frage der Forschung war: **Wie weit trägt das?** Und: **Lässt sich die Reichweite durch bessere Regeln vergrößern?**

## Die wichtigsten Ergebnisse (alle reproduzierbar, siehe `docs/REPRODUKTION.md`)

1. **Reduzierte Modelle (4 bis 16 Runden je Kompression, sonst wie SHA256d):** Mit acht freien Noncebits und einem exakt
   vorgegebenen Zielhash leitet die Maschine die Nonce **vollständig ab – ohne Kandidatensuche**, nur mit Bitregeln, in
   Sekunden (4 Runden: 0,02 s; 16 Runden: 6,1 s). Das Ergebnis wurde jeweils unabhängig durch Auswertung aller 256 Kandidaten
   bestätigt; der Lösungsnonce war der Maschine nicht bekannt. *Kein Geschwindigkeitsvorteil belegt* – 256 Hashes wären
   ebenfalls in Millisekunden erledigt. Gezeigt ist, dass die Ableitung funktioniert, nicht, dass sie schneller ist.
2. **Vollständiges SHA256d (64 Runden):** An einem echten Template (Höhe 972 527, 78 Zielnullbits) und am Genesis-Block
   leitet keine der untersuchten Regelmengen ein einziges Noncebit ab und schließt keine Nonce aus. Bekannte Treffer bleiben
   stets erhalten (kein falscher Ausschluss in allen Läufen). Gemessen wurde, wie weit Information trägt: vom Kopf vorwärts
   bis Runde 4 der ersten Anwendung, vom Ziel rückwärts bis Runde 61 der zweiten Anwendung; mit vollständig vorgegebenem
   Endhash bis Runde 57. Dazwischen liegen über 100 Runden ohne eine einzige Einschränkung.
3. **Untersuchte Erweiterungen ohne zusätzlichen Nonceausschluss:** Ziffernnetz (2-Bit-Ziffern) mit Paarbeziehungen
   (Radius 1, bis 1,9 Mio. Paare), Dreierbeziehungen, Auffrisch-Kästchen an Kettenenden, exakte Wahrheitstabellen und
   Phasenvektoren bei zwei freien Bits, XOR-Gleichungssysteme über GF(2), Zielhash-Vorgabe, Vorratsdatenbank-Modell.
4. **Korrekturen gehören dazu.** Mehrere Zwischenaussagen von Fable waren zu stark und wurden durch Ghosts Gegenprüfung
   oder eigene Nachmessung zurückgenommen – zuletzt: Der scheinbare Vorsprung der Paare beim Zielhash-Vergleich war die
   Durchlaufgrenze von 12; Bitregeln allein erreichen nach 41 Durchläufen dasselbe Registerbild. Alle Korrekturen sind in
   `docs/EXPERIMENTE.md` sichtbar, die Originalberichte liegen unverändert in `experimente/berichte/`.

**Kein neuer Block wurde gefunden. Kein Durchbruch, keine Unmöglichkeitsbehauptung, kein Hardwaregewinn.** Was vorliegt,
ist eine funktionierende, geprüfte Maschine, eine saubere Messung ihrer Grenze am vollen SHA256d und eine Reihe ehrlich
dokumentierter negativer Ergebnisse.

## Aufbau des Pakets

| Pfad | Inhalt |
|---|---|
| `src/kaestchen/` | Bibliothek: Bitgraph (`gatter.py`), Referenz-SHA (`pruefung.py`), Ziffernnetz und Regeln (`ziffern*.py`, `bausteine.py`), Anbindung an SHA256d (`sha_ziffern.py`), Bitregel E1 (`e1_bit.py`), Austausch Bit↔Ziffer (`austausch.py`), Auffrischer (`kette.py`), Mini-Netze (`mininetze.py`) |
| `beispiele/` | Drei kleine, offline laufende Programme (Sekunden bis ~1 min) |
| `tests/test_schnell.py` | Fünf Schnelltests gegen `hashlib` und das Orakel (< 30 s) |
| `experimente/skripte/` | Alle Experimentskripte (Kindprozess + überwachender Elternprozess) und die zwei Datendateien |
| `experimente/ergebnisse/` | Ergebnisdateien aller Läufe (JSON, mit Rechner, Python-Version, Zeiten, Speicher) |
| `experimente/berichte/` | Originalberichte Fable→Ghost, unverändert, inklusive später korrigierter Aussagen |
| `experimente/diffs/` | Änderungsnachweise zwischen Fassungen |
| `docs/` | Technik, Experimentübersicht, Reproduktion, offene Fragen, Lizenzvorschlag, Entscheidungen |
| `miner/` | Abgrenzung zum laufenden Kästchenminer (Code nicht enthalten) |

## Schnellstart

```
python3 -I beispiele/01_reduzierte_runden.py 8      # Nonce aus Zielhash bei 8 Runden, < 1 s
python3 -I beispiele/02_genesis_zeuge.py            # volles SHA256d, Genesis: 0 Noncebits, Treffer erhalten, ~2 s
python3 -I tests/test_schnell.py                    # 5 Tests, < 30 s
```
Benötigt Python 3.10+; `numpy` nur für die Paarspeicher-Läufe (E4) und den Phasenvergleich. Alles läuft offline auf der CPU.
Es gibt keine Verbindung zu einem Bitcoin-Node, keine Einreichung, keine GPU.

## Grenzen in einem Absatz

Die Darstellung „je Kästchen eine Wertemenge" (auch mit Paaren oder Tripeln) kann nicht festhalten, *welche* Kombination
der freien Bits zu welchem Zwischenwert gehört. Nach wenigen Runden Durchmischung ist in jedem Kästchen jeder Wert
möglich, und die Bindung zwischen den Kästchen ist verloren. Beim vollen SHA256d ist das bei acht freien Bits ab Runde 5
der Fall. Ob und wo zwischen 16 und 64 Runden die Ableitung endet, ist nicht gemessen (siehe `docs/OFFENE_FRAGEN.md`).
Die Maschine ist stark, wo wenig unbekannt ist: Nachrechnen, Prüfen, reduzierte Rundenzahlen.

## Quellen und Einordnung

Die Grundlagen sind Standard: Bogenkonsistenz (E1/E3) und Pfadkonsistenz (E4) aus der Constraint-Programmierung
(Mackworth 1977, „Consistency in networks of relations"); SHA-256 nach FIPS 180-4; die Vorratsrechnung ist Hellmans
Zeit-Speicher-Tausch (1980). Veröffentlichte Urbild-Angriffe auf rundenreduziertes SHA-256 werden hier bewusst nicht
beziffert, weil wir sie nicht selbst geprüft haben; der Vergleich wäre ohnehin schief (andere Aufgabenstellung, andere
Freiheitsgrade). Wir beanspruchen keine Neuheit.
