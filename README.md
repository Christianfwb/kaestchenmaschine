# Kästchenmaschine

**SHA-256 von innen: jedes Bit, jede Verbindung, jeder Schluss nachvollziehbar.**

Die Kästchenmaschine stellt die doppelte SHA-256-Rechnung eines Bitcoin-Headers als Netz kleiner Rechenregeln dar. Für jedes Bit hält ein „Kästchen“ fest, ob es 0, 1 oder noch beides sein kann. Bekannte Eingaben und die Zielbedingung am Ausgang engen die Möglichkeiten ein, vorwärts und rückwärts, und jeder Schluss wird in ein Beweisbuch geschrieben, das ein unabhängiger Prüfer Zeile für Zeile nachrechnet.

Das Projekt ist entstanden, um zu sehen, wie SHA-256 im Inneren arbeitet. Das Ergebnis: Man kann es jetzt **haargenau, Bit für Bit** verfolgen, wo Wissen hineinfließt, wie weit es trägt und wo es aufhört. Und so viel vorweg: **SHA256d ist sicher. Bisher.** 😉

Viel Spaß beim Erkunden.

**Stand:** 13. November 2026 · [Nachtrag vom 13. November](docs/NACHTRAG_20261113.md) · [Abschlussbericht vom 25. Oktober](docs/ABSCHLUSS_20261025.md) · [MIT-Lizenz](LICENSE)

[Was wir sehen](#was-wir-sehen) · [Schnellstart](#schnellstart) · [Der Weg dahin](#der-weg-dahin) · [Code und Belege](#code-und-belege) · [Offene Fragen](docs/OFFENE_FRAGEN.md) · [Technik](docs/TECHNIK.md) · [Nachrechnen](docs/REPRODUKTION.md)

## Was wir sehen

Alle Aussagen gelten für die jeweils genannte Aufgabe (Header, freie Bits, Regelprofil); Belege und Grenzen stehen im [Nachtrag](docs/NACHTRAG_20261113.md) und im [Abschlussbericht](docs/ABSCHLUSS_20261025.md).

* **Die Karte.** Am untersuchten Header mit 32 freien Noncebits sind 66.837 von 158.212 Bitnamen belegt: der Header bis Runde 3, die Nachrichtenwörter außer der Nonce, am Ziel e61 und e62 vollständig, e63 und H5 teilweise. In den inneren Zustandswörtern dazwischen ist mit den geprüften Regeln kein fester Bitwert belegt; die Gleichungen verbinden die Bereiche dennoch. ([Nachtrag, Abschnitt 1](docs/NACHTRAG_20261113.md#1-kästchenkarte-wo-werte-feststehen-und-wo-nicht-2-november--belegt))
* **Die Kante.** In verkürzten Rechnungen leitet die Maschine bis 16 Runden je Kompression alle Noncebits aus der Zielbedingung ab, ab 17 Runden keines mehr. Der Grund ist die Nachrichtenerweiterung: die Wiederverwendung eines unbekannten Wortes 16 Runden später. ([Abschluss](docs/ABSCHLUSS_20261025.md))
* **Die stärkeren Werkzeuge.** Exakter Join-Baum („Stern“), Zweigvergleich (Dilemma-Regel), gemeinsame Auswertung von Addition, Rotation und Ziel: im Kleinen vollständig, am vollen Header nur bereits bekanntes Wissen. Eine konkrete Anschlusslücke in der Wissensweitergabe wurde im Kontrollmodell gefunden und repariert. ([Nachtrag, Abschnitte 2–5](docs/NACHTRAG_20261113.md))
* **Die Mining-Frage.** Kein bestätigter Vorteil: weder durch Ableitung noch durch Aussortieren noch durch ein ausgewähltes Noncemuster (1.942 Paare, 49,74 % kleiner). Keine SHA-Abkürzung. ([Nachtrag, Abschnitt 6](docs/NACHTRAG_20261113.md#6-nonce-sampler-methodik-und-historischer-nullbefund-9-november--belegt-als-negativbefund))

## Schnellstart

Python 3.10 oder neuer, offline, ohne Zusatzpakete:

```sh
git clone https://github.com/Christianfwb/kaestchenmaschine.git
cd kaestchenmaschine
python -B -I tests/test_schnell.py
python -B -I beispiele/01_reduzierte_runden.py 8
python -B -I beispiele/02_genesis_zeuge.py
```

Erwartet: fünf bestandene Schnelltests; im 8-Runden-Beispiel eine vollständig abgeleitete Kontrollnonce; beim Genesis-Beispiel keine neuen Noncebits, aber Erhaltung des bekannten Treffers. Für E4 und NumPy-Experimente `python -m pip install -r requirements.txt`; die archivierten vollständigen Läufer brauchen Linux. [Befehle und Referenzpfade](docs/REPRODUKTION.md).

Ein Kästchen in einem Satz: Bei `x XOR y = 0` lässt jedes einzelne Kästchen noch 0 und 1 zu, eine Paarbeziehung hält zusätzlich fest, dass nur 00 oder 11 geht. Die Regeln laufen, bis nichts enger wird (**FIXPUNKT**: beweist weder Lösbarkeit noch Unlösbarkeit), ein Wert unmöglich wird (**WIDERSPRUCH**) oder eine Grenze erreicht ist (**OFFEN**: nie als Ausschluss zählen). [Darstellung und Messdisziplin](docs/TECHNIK.md).

## Der Weg dahin

Die Reihenfolge, in der das Bild entstanden ist. Alles bleibt nachprüfbar im Repository; die [ausführliche README vom Abschluss](docs/README_ABSCHLUSS_20261025.md) ist archiviert.

| Wann | Was | Wo |
|---|---|---|
| bis 23. Okt. | Bitregeln, Paare, Tabellen, XOR-Gleichungen; Rundenkurve 4–16 (alle Noncebits), Genesis-Zeuge; Prüfung und Korrekturen | [EXPERIMENTE](docs/EXPERIMENTE.md), [REVIEW](docs/REVIEW_20261023.md) |
| 24./25. Okt. | Labor L1: Rundenkurve 17–63, Sicherheitslinie, Stern (Join-Baum mit Bitmengen) an N4r09/N4r10, Ausdünnen; Abschluss | [ABSCHLUSS](docs/ABSCHLUSS_20261025.md), [experimente/l1](experimente/l1) |
| 2.–9. Nov. | Kästchenkarte, H5-Gruppe, Zweigvergleich, Anschlusslücke n314 und XOR-Rückfluss, Altwissen und Additionen, Nonce-Sampler | [NACHTRAG](docs/NACHTRAG_20261113.md), [experimente/nachtrag_2026_11](experimente/nachtrag_2026_11) |

Offen bleiben Forschungsfragen, keine Vorhaben: drei unbestätigte lokale Kandidaten, die Skalierung der Gruppenbreite, weitere Additionen mit Querbeziehungen. [Offene Fragen](docs/OFFENE_FRAGEN.md).

## Code und Belege

| Pfad | Inhalt |
|---|---|
| [src/kaestchen](src/kaestchen) | Bitgraph, Referenzrechnung, Bit-/Ziffernregeln, Paarverwaltung und Austausch |
| [beispiele](beispiele) | Kleine Einstiege |
| [tests](tests) | Schnelltests und Regressionen; [automatischer Testlauf](.github/workflows/tests.yml) |
| [experimente](experimente) | Läufer, archivierte Messungen (auch Fehler und Abbrüche), Originalberichte, Labor L1, Nachtrag November |
| [docs](docs) | Technik, Reproduktion, Herkunft der Dateien, Entscheidungen, Lizenzhinweise |

Historische Resultate bleiben unverändert; Korrekturen werden benannt, nicht eingearbeitet. Dateiliste und [SHA256-Prüfsummen](SHA256SUMS.txt): `python -B -I tools/manifest.py --check`. Der produktive GPU-Miner mit Node-Anbindung ist [nicht enthalten](miner/README.md).

## Warum ich das veröffentliche

Ich habe lange an der Kästchenmaschine gearbeitet: Ideen entwickelt, Versuche gemacht, Ergebnisse hinterfragt und immer wieder neu angesetzt. Jetzt ist der Stand öffentlich, mit Grenzen, Fehlern und negativen Ergebnissen, damit andere ihn nachvollziehen, prüfen und weiterdenken können. Code, Dokumentation und eigene Ergebnisdateien stehen unter der [MIT-Lizenz](LICENSE).

Wer mitforschen, nachprüfen oder die Arbeit unterstützen möchte, mit Rechenzeit, Hardware, fachlicher Zusammenarbeit oder finanziell, ist willkommen. Was dafür gemessen werden müsste und was aus Unterstützung nicht folgt (kein Mining-Vorteil, kein neuer Block), steht in [docs/SPONSOREN.md](docs/SPONSOREN.md). Eine Spende ist ein Dankeschön für die Arbeit, kein Kauf und kein Versprechen.

**Kontakt:** Christian Berrang · [christianfwb@gmail.com](mailto:christianfwb@gmail.com) · [GitHub-Issues](https://github.com/Christianfwb/kaestchenmaschine/issues)

**Freiwillige Bitcoin-Spenden (Mainnet):**

```text
14oJK42G3zJBjfzJsfHwYTmgJxDzMwNMAy
```

— Christian Berrang

## Herkunft und Einordnung

Projekt von Christian Berrang, entwickelt mit den KI-Assistenten Ghost und Fable (Claude); KI-Ausgaben wurden geprüft und mehrfach korrigiert, jedes Paket von der jeweils anderen Seite gegengelesen. Diese Zusammenarbeit ersetzt keine unabhängige Validierung. Wir beanspruchen keine Neuheit: Die Bausteine stammen aus Constraint-Programmierung und boolescher Algebra (Join-Bäume, Bucket-Elimination, AC-3, Dilemma-Regel nach Stålmarck). Die SHA-Rechnung folgt [NIST FIPS 180-4](https://doi.org/10.6028/NIST.FIPS.180-4), die Referenzprüfung nutzt [Python hashlib](https://docs.python.org/3/library/hashlib.html). Hinweise für Beiträge: [CONTRIBUTING.md](CONTRIBUTING.md); Lizenzhinweise: [docs/LIZENZ_VORSCHLAG.md](docs/LIZENZ_VORSCHLAG.md).

## English summary

The Kästchenmaschine („box machine“) represents Bitcoin's double SHA-256 as a network of small rules with one „box“ per bit, propagates known inputs and the target condition forwards and backwards, and records every inference in a proof book that an independent checker recomputes line by line. It was built to see how SHA-256 works inside, and it lets you trace that bit by bit: where knowledge enters, how far it travels, where it stops. In reduced-round controls it derives all nonce bits up to 16 rounds per compression and none from 17 on (message schedule). On the full header, stronger tools (exact join tree, dilemma rule, joint carry/rotation/target evaluation) recover only known facts; one concrete propagation gap was found and fixed in a control model. No mining advantage is established and no SHA shortcut is claimed. So far, SHA256d is safe. Production miner not included; MIT License; voluntary donations welcome (address above).
