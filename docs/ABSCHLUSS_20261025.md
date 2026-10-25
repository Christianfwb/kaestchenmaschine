# Abschluss der Kästchenmaschine – Stand 25. Oktober 2026

Dieses Dokument fasst zusammen, was wir drei – Christian, Ghost und Fable – vom 23. bis 25. Oktober 2026 gemessen haben, und warum das Projekt damit abgeschlossen ist. Alles Gemessene liegt in [experimente/l1](../experimente/l1) (Code, Ergebnisdateien mit Prüfsummen, Teamberichte) und in [experimente/skripte](../experimente/skripte) (Rundenkurve 17–63, Sicherheitslinie). Begriffe: **belegt** = gemessen und unabhängig kontrolliert; **Vermutung** = Lesart; **offen** = nicht gemessen.

Kurz: Im Kleinen funktioniert die Idee vollständig und nachprüfbar. Für das vollständige SHA256d trägt sie nicht – nicht wegen fehlender Rechenzeit, sondern weil die nötige Breite der gemeinsam zu haltenden Beziehungen exponentiell wächst. Beides ist gemessen, nicht vermutet.

## 1. Wo die Ableitung reißt: die Nachrichtenerweiterung (23. Oktober)

Rundenkurve am reduzierten SHA256d (8 freie Noncebits, exakter Zielhash): bis 16 Runden je Kompression leitet E1 alle 8 Bits ab; **ab 17 Runden kein einziges Bit mehr, bis 64** – ein Sprung um genau eine Runde, auch mit Paaren (E4). Kontrolle: dasselbe Modell ohne Nachrichtenerweiterung (W16..W63 als Konstanten) wird bis 64 Runden vollständig abgeleitet. Trenntests („Sicherheitslinie“): entscheidend ist nicht Drehen oder Addieren, sondern die **Wiederverwendung eines unbekannten Wortes 16 Runden später**; schon die bloße Kopie W[i] = W[i−16] reißt die Ableitung ab. Belegt für diese Vorlage und diese Regeln; keine Neuheit (die Erweiterung ist bekanntermaßen der Schutz gegen Rückwärtsrechnen). [Berichte](../experimente/berichte/BERICHT_RUNDENKURVE_17_63.txt), [Sicherheitslinie](../experimente/berichte/BERICHT_SICHERHEITSLINIE.txt), [Zeichnung](topologie_erweiterung.svg).

## 2. Das Labor L1: Mini-Netze mit Leine (24. Oktober)

Um die Wiederverwendung klein nachzubauen: Mini-Netze mit 4-Bit-Wörtern, 3 freien Wörtern (12 Bits) und einer „Leine“ W_i = W_(i−3) (N4r09 = 9 Runden, N4r10 = 10 Runden; N5 = Erweiterung mit kleinen Sigma-Funktionen). Prüfstand mit Dreiteilung **Speicherung / Ableitung (Erkennung) / Kontrollzählung**, Orakel erst nach dem Einfrieren, Sabotageproben, Watchdog (120 s / 400 MiB), alle Erwartungen vorab und automatisch.

Regelmaschine D6 (R1–R7, R1b, R8c/R8m exakte Ch/Maj, R9 gleiche Funktion, R9a affine Differenz, R9b „nie beide 1“, Brücke): N4r09 von 4096 Kandidaten → 512 → 128 (Grundgerüst) → **1 mit R9** (Ablation: R9 oder R9a allein genügt). N4r10: 4096 → 512 → 384 (R9a + R9b + R7), nicht weiter. N5-Varianten mit echter Sigma-Erweiterung: V3 bleibt bei 4096 (nichts abgeleitet). Alle Zählungen gegen unabhängige Vollzählung geprüft. [Berichte](../experimente/l1/berichte).

## 3. Der Stern: Kästchen behalten Beziehungen, die Mitte reicht weiter (24.–25. Oktober)

Christians Architektur: Kästchen als Relationen (Tabellen erlaubter Zeilen), eine Mitte, die über gemeinsame Variablen austauscht. Mathematisches Fundament: Join-Bäume (Yannakakis 1981; Beeri/Fagin/Maier/Yannakakis 1983), Bucket-Elimination (Dechter), Arbeitsliste = AC-3 (Mackworth 1977), Mini-Buckets (Dechter & Rish 2003), Bitmengen. Keine Neuheitsbehauptung – die Leistung liegt im sauberen Zusammensetzen und Messen.

| Schritt | Ergebnis (belegt) |
|---|---|
| Stern-Prüfstand, fünf Fälle; N3 (zwei gekoppelte 3-Bit-Addierer) mit Handgruppen | Speicherung exakt; mit Join-Gruppen alle Gruppen = Projektionen der 12 Lösungen; N3u Widerspruch im ersten Takt |
| Automatische Gruppenfindung (Min-Fill, Baum, Running Intersection), vier Absicherungen nach Ghosts Prüfung | 16 Gruppen max 4 Variablen an N3; Sabotagen erkannt; globale Konsistenz verbindlich |
| Arbeitsliste statt Rundenlauf | gleiche Endrelationen, 65 statt 120 Projektionen, Semijoins direkt gezählt |
| Begrenzte Gruppen (Mini-Buckets) am Dreieck und an N3-Gattern | keine echte Lösung verloren; Widerspruch wird bei zu kleinen Gruppen übersehen; bei N3 bleiben 2 von 5 ableitbaren Innenknoten offen; **kleinere Gruppen kosten Erkennung und Arbeit** |
| Bitmengen statt Tupel, schlanke Masken, blockweiser Abgleich | bitgleiche Ergebnisse (Selbsttests 4784 / 4784 / 9168 Fälle); Tabellen 20–50× kleiner; Masken 41 KB → 17 KB → 12 KiB; N4r09-Austausch 62 s → 2,5 s |
| **Exakter Stern an N4r09** (nach D6-Grundgerüst, 531 Kästchen, 492 Gruppen, größte 18 Variablen) | Gleichwertigkeit Bedingung für Bedingung nachgewiesen (1314 Gatter = 520 + 783 + 11, 32 Zielbits); Fixpunkt nach 62 s; **in jeder Gruppe genau eine Zeile = die eine Lösung, alle 12 Eingangsbits, ohne R9** – von der Kontrolle (4096 Vorwärtsauswertungen) bestätigt |
| N4r10 strukturell | größte Gruppe **28** (Min-Fill), 29 (Min-Degree), 28 (Min-Fill umgekehrt); gerechneter Bedarf: Tabellen ~120 MiB, schlanke Masken ~6 GiB, Austausch ~1000× N4r09 – nicht im Budget; die Breite entsteht dort, wo die Leine die Eingangsbits ein viertes Mal durch die Runden zieht |

Deutung (Vermutung, konsistent mit allen Messungen): Ein exakter Stern kostet 2 hoch Türbreite. Eine Runde mehr kostete hier zehn Leitungen mehr. Drei Heuristiken landen an derselben Netzstelle. Für das vollständige SHA256d (32-Bit-Wörter, 64 Runden) liegt die Breite jenseits jeder Maschine. Das ist keine Aussage über die minimal mögliche Baumweite und keine Unmöglichkeitsaussage über andere Verfahren.

## 4. Die richtige Frage des Miners: billig aussortieren statt lösen (25. Oktober)

Mining sucht nicht die eine Lösung, sondern irgendeinen von vielen passenden Nonces. Die Frage ist daher: Kann man Kandidaten **sicher und billiger ausschließen, als sie zu hashen?** Bilanz: r·H_nonce > c + C_pre/N. 48 Fälle (8 feste Köpfe aus Prüfsummen, k = 2/3/4 Zielbits, 6 und 9 Runden, 256 Nonces), Filter vor der Kontrolle eingefroren, alle Kosten in Gattern, Vorarbeit getrennt.

**Ergebnis: negativ in allen 48 Fällen, bei voller Sicherheit.** Das Grundgerüst leitet aus Kopf und Zielbits keine Einschränkung über die Nonce-Bits ab (affiner Rang 0). Die billigen abgeleiteten Tatsachen folgen vorwärts aus dem Kopf und gelten für jeden Nonce. Alles, was Nonces ausschließt, sitzt am Ziel und kostet 60–70 % des Hashes. Dazwischen: nichts. [Bericht](../experimente/l1/berichte/AUSDUENNEN_ERGEBNIS_20261025_BERICHT.txt). Nicht gemessen: R9 in diesem Aufbau.

## 5. Was bleibt

- Ein Prüflabor, das Speicherung, Erkennung und Kontrolle trennt, seine Erwartungen vorab festlegt, Sabotagen erkennt und Ergebnisse bitgenau nachprüfbar macht – alle Läufe wiederholbar (`tests/test_stern.py`, ~20 s).
- Eine gemessene Antwort: Die Kästchenmaschine löst kleine Netze vollständig und zeigt präzise, wo und warum die Ableitung bei Hashfunktionen reißt – an der Wiederverwendung unbekannter Wörter, als exponentiell wachsende Breite. Ein Vorteil beim Mining ist damit nicht belegt und wird von uns nicht mehr verfolgt.
- Fehler, die wir unterwegs gemacht und dokumentiert haben (128 „Lösungen“ waren Kandidaten; 1322 statt 1314; vier Aliase im Abschlusstest; tautologische Filter in Lauf 1): Sie stehen in den Berichten, weil die Korrektur Teil des Ergebnisses ist.

Keine Aussage über Mainnet, Hardware, Neuheit oder Unmöglichkeit. Zeiten sind Einzelmessungen auf Fables CPU-Umgebung (Xeon 2,10 GHz, 2 Kerne, Python 3.13). Der produktive Miner ist nicht Teil des Repositorys und wurde durch diese Arbeit nicht verändert.
