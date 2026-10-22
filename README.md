# Kästchenmaschine

**Experimente zur Constraint-Propagation auf SHA256d.**

Die Kästchenmaschine stellt eine Hashrechnung als Netz kleiner Rechenregeln dar. Für jedes Bit speichert ein „Kästchen“, ob 0, 1 oder noch beides möglich ist. Bekannte Eingaben und Bedingungen am Ausgang engen diese Möglichkeiten ein — vorwärts und rückwärts.

Dieses Repository enthält **Forschungscode, Offline-Beispiele und Messdaten**. Der produktive GPU-Miner mit Node-Anbindung und Einreichung ist [nicht enthalten](miner/README.md). Kein Mining-Geschwindigkeitsvorteil und kein neu gefundener Bitcoin-Block sind nachgewiesen.

**Stand:** 23. Oktober 2026 · öffentliches Forschungsrepository · [Prüfung und Änderungen](docs/REVIEW_20261023.md) · [MIT-Lizenz](LICENSE).

[Schnellstart](#schnellstart) · [Ergebnisse](#was-ist-gemessen) · [Technik](docs/TECHNIK.md) · [Experimente und Korrekturen](docs/EXPERIMENTE.md) · [Nachrechnen](docs/REPRODUKTION.md) · [Offene Fragen](docs/OFFENE_FRAGEN.md)

## Was ist gemessen?

**Im Kleinen haben wir es geschafft:** In den fünf geprüften, verkürzten SHA256d-Rechnungen mit 4 bis 16 Runden je Kompression hat die Kästchenmaschine alle acht unbekannten Noncebits aus der vorgegebenen Zielhash-Bedingung abgeleitet. Die gefundenen Eingaben wurden unabhängig nachgerechnet und bestätigt.

**Auch mit vollständigem Bitcoin-SHA256d gibt es einen konkreten Sucherfolg:** Unser separat entwickelter GPU-Kästchenminer hat die historische Genesis-Nonce **2083236893 selbst in einer Gruppe von 256 Kandidaten wiedergefunden**. Dabei waren acht Noncebits frei. Die Suche mit Kästchenregeln und Verzweigung meldete nach **8,67 Sekunden** einen Treffer; Graph, Kästchenbedingungen und eine unabhängige SHA256d-Nachrechnung bestätigten ihn. Das ist ein ermutigender praktischer Beleg dafür, dass unser Suchweg in diesem kontrollierten Fall funktioniert. [Original-Testprotokoll, Fall `first_hit_256`](experimente/ergebnisse/ERGEBNIS_MINER_GENESIS_SEARCH.json).

Die übrigen Headerfelder und der Suchbereich waren für diesen historischen Kontrollversuch festgelegt. Die Zeit ist eine Einzelmessung des damaligen Minerstands. Der Lauf endete beim ersten Treffer, nicht nach vollständiger Prüfung aller 256 Kandidaten. Er fand den gültigen historischen Header durch verzweigte Suche, ohne zusätzlich abgeleitete Noncebits; damit ist weder ein Vorteil gegenüber direktem Hashen noch ein neuer Blockfund belegt. Der produktive Minercode ist nicht Teil dieses Repositorys; das unveränderte Ergebnisprotokoll dokumentiert den damaligen Lauf.

**Beim vollständigen SHA256d steht der Nachweis einer vergleichbaren Ableitung ohne Kandidatensuche noch aus.** Unsere verfügbare Rechenleistung und unsere Zeit begrenzen, welche größeren Versuche wir durchführen können. Die bisherigen vollständigen Propagationsläufe zeigen aber auch eine Grenze der getesteten Regeln: Selbst wenn sie bis zum Stillstand rechnen, bestimmen sie in diesen Fällen keine Noncebits. Deshalb ist bisher offen, ob mehr Rechenleistung allein genügt oder stärkere Ableitungsregeln nötig sind. Der Genesis-Sucherfolg und die Ableitungserfolge der kleinen Modelle sind belegt; eine Übertragung dieser Ableitungskraft auf das vollständige Bitcoin-Verfahren ist noch nicht belegt.

**Warum wir weiterforschen möchten:** Die nachgewiesenen Erfolge im kleinen Modell motivieren weitere Versuche mit stärkeren Verfahren und mehr Rechenleistung. Unsere Forschungshypothese ist, dass sich die gemeinsame Ableitung auch für anspruchsvollere Fälle nutzbar machen lässt. Ob und wie weit das bis zum vollständigen SHA256d gelingt, ist offen. Die kleinen Erfolge sind ein konkreter Ausgangspunkt für diese Untersuchung, kein Beleg dafür, dass allein mehr Hardware das Problem löst.

Alle Aussagen gelten für die jeweils genannten Vorlagen, freien Bits und Regeln. Zeiten sind Einzelmessungen auf Fables CPU-Umgebung, keine Leistungsversprechen.

| Versuch | Vorgabe | Ergebnis | Beleg |
|---|---|---|---|
| Reduziertes SHA256d: 4, 6, 8, 12 und 16 Runden **je Kompression** | Acht freie Noncebits; exakter, erreichbarer Zielhash | E1 bestimmt in allen fünf Kontrollfällen alle acht Bits ohne Kandidatensuche. 0,02–6,1 s reine E1-Zeit. | [Rundenkurve](experimente/ergebnisse/ERGEBNIS_RUNDEN.json), [Bericht](experimente/berichte/BERICHT_ABSCHLUSS_ZIELHASH_RUNDEN.txt) |
| Vollständiges SHA256d: 64 Runden | Zwei gespeicherte Vorlagen, acht freie Bits, Hash ≤ Target | E1+E4 bestimmt an den untersuchten Wurzeln keine Noncebits; keine Nonces ausgeschlossen. Genesis-Zeuge bleibt erhalten. | [Basis und Dreier](experimente/ergebnisse/ERGEBNIS3_WURZEL.json) |
| Vollständiges SHA256d mit genauem Endhash | Eine Vorlage, ein vorab festgelegter Zielhash, acht freie Bits | Mehr feste innere Werte, aber weiterhin keine Noncebits. E1 erreicht nach 41 Durchläufen dasselbe H2-Registerbild wie E1+E4; Paare bestimmen zusätzlich 70 innere Bitknoten. | [Korrigierter Vergleich](experimente/ergebnisse/ERGEBNIS_ZIELHASH_FIX.json) |
| Exakte Tabellen und NumPy-Fallvektoren | Zwei freie Bits, also vier Kandidaten je Vorlage | Alle acht Digests und Zielentscheidungen stimmen mit hashlib überein. Diese Verfahren werten die Fälle gemeinsam aus; sie sind kein belegter Suchvorteil. | [Tabellen](experimente/ergebnisse/ERGEBNIS_TABELLEN4.json), [Vektoren](experimente/ergebnisse/ERGEBNIS_PHASEN.json) |
| XOR-Gleichungen | Zwei oder acht freie Bits; UND-Ausgänge als freie Variablen | Die untersuchte Lockerung liefert keine neue Eingangsbeziehung und keinen Widerspruch. | [XOR-Auswertung](experimente/ergebnisse/ERGEBNIS_XORSHA.json) |

Die reduzierten Rechnungen sind **kein Bitcoin-SHA256d**. Für diese Kontrollfälle wird der Zielhash aus einer vorher gewählten Nonce erzeugt; der Löser erhält nur die Vorlage, freie Bits und diesen Hash. Eine getrennte Referenzauswertung aller 256 Kandidaten prüft anschließend das Ergebnis. Der Versuch belegt Ableitung in diesen Fällen, keine allgemeine Urbildlösung und keinen Zeitgewinn gegenüber 256 direkten Auswertungen.

**Nicht fest bestimmte Bits bedeuten nicht fehlende Beziehungen.** Aus Registerkarten lässt sich keine „Lücke ohne Information“ oder Unmöglichkeit eines stärkeren Verfahrens ableiten. Auch Paare und Dreier können Zusammenhänge bewahren. Wir dokumentieren ihre gemessene Wirkung statt einer allgemeinen Grenze der Mathematik.

## Schnellstart

Python 3.10 oder neuer. Diese Befehle laufen offline auf Windows, Linux und macOS; für die ersten beiden Beispiele und Schnelltests sind keine Zusatzpakete nötig. Verwende gegebenenfalls `python3` statt `python`.

```sh
git clone https://github.com/Christianfwb/kaestchenmaschine.git
cd kaestchenmaschine
python -B -I tests/test_schnell.py
python -B -I tests/test_regression.py
python -B -I beispiele/01_reduzierte_runden.py 8
python -B -I beispiele/02_genesis_zeuge.py
```

Erwartet: fünf bestandene Schnelltests; bestandene Regressionen; im 8-Runden-Beispiel eine vollständig abgeleitete Kontrollnonce; beim Genesis-Beispiel keine neuen Noncebits, aber Erhaltung des bekannten Treffers in allen Bitdomänen.

Für E4 und NumPy-Experimente:

```sh
python -m pip install -r requirements.txt
```

Die archivierten vollständigen Experimentläufer benötigen **Linux** (`resource` und `/proc`); unter Windows bitte WSL verwenden. Sie sind keine plattformübergreifenden Minerprogramme. Siehe [Befehle, Voraussetzungen und Referenzpfade](docs/REPRODUKTION.md).

## Wie funktioniert ein Kästchen?

Bei `x XOR y = 0` müssen x und y gleich sein. Einzelne Bitkästchen lassen trotzdem bei beiden 0 und 1 zu. Eine Paarbeziehung kann zusätzlich festhalten: **nur 00 oder 11**. E1 arbeitet auf Bitgattern; E3 auf kleinen Zifferntabellen; E4 hält zusätzlich ausgewählte Paarbeziehungen. Die Regeln werden wiederholt angewendet, bis nichts enger wird oder eine Grenze erreicht ist.

- **FIXPUNKT:** Diese Regeln ändern nichts mehr. Das beweist weder Lösbarkeit noch Unlösbarkeit.
- **WIDERSPRUCH:** Eine notwendige Bedingung lässt keinen Wert mehr zu.
- **OFFEN/OPEN:** Noch nicht entschieden oder durch eine Ressourcengrenze beendet; niemals als Ausschluss zählen.
- **Treffer:** Eine abgeleitete Eingabe wird unabhängig nachgerechnet.

Die Bitregeln brauchen auf zyklisch gekoppelten Netzen keine vollständige Entscheidung zu liefern. [Darstellung, Schnittstellen und Messdisziplin](docs/TECHNIK.md).

## Code und Belege

| Pfad | Inhalt |
|---|---|
| [src/kaestchen](src/kaestchen) | Bitgraph, Referenzrechnung, Bit-/Ziffernregeln, Paarverwaltung und Austausch |
| [beispiele](beispiele) | Kleine Einstiege; das Vorratsmodell ist ausdrücklich illustrativ |
| [tests](tests) | Schnelltests und Regressionen; [automatischer Testlauf](.github/workflows/tests.yml) |
| [experimente/skripte](experimente/skripte) | Linux-Läufer und festgelegte Eingabedaten |
| [experimente/ergebnisse](experimente/ergebnisse) | Archivierte Messungen einschließlich früherer Fehler/Abbrüche |
| [experimente/berichte](experimente/berichte) | Historische Originalberichte; manche Aussagen wurden später korrigiert |
| [docs/EXPERIMENTE.md](docs/EXPERIMENTE.md) | Heutige Einordnung und sichtbare Korrekturen der Originalberichte |
| [docs/HERKUNFT.md](docs/HERKUNFT.md) | Herkunft der Dateien und Abweichungen zwischen Fassungen |

Historische Resultate bleiben unverändert. Korrekturen am heutigen Code können Details eines erneuten Laufs ändern; sie sind im [Prüfbericht](docs/REVIEW_20261023.md) benannt. Dateiliste und [SHA256-Prüfsummen](SHA256SUMS.txt) lassen sich mit `python -B -I tools/manifest.py --check` prüfen.

## Grenzen und nächste Fragen

17–63 Runden wurden in der Rundenkurve nicht untersucht; mehr freie Bits und andere Vorlagen ebenfalls nicht systematisch. Eine feste Ausgangsbedingung kann mehr innere Werte bestimmen, ohne eine Nonce herzuleiten. Das [Vorratsmodell](experimente/berichte/BERICHT_VORRAT_MODELL.txt) vergleicht unterschiedliche Spielräume und ist kein fairer abschließender Leistungsnachweis. Die [offenen Fragen](docs/OFFENE_FRAGEN.md) sind Forschungsfragen, keine versprochenen Verbesserungen.

## Warum ich diese Forschung veröffentliche

Ich habe sehr lange an der Kästchenmaschine gearbeitet: Ideen entwickelt, Versuche gemacht, Ergebnisse hinterfragt und immer wieder neu angesetzt. In diesem Projekt stecken viel Zeit, Ausdauer und persönliche Arbeit.

Jetzt mache ich den Forschungsstand öffentlich zugänglich, damit andere ihn nachvollziehen, prüfen und darauf aufbauende Ideen diskutieren können. Dazu gehören auch die Grenzen, Fehler und negativen Ergebnisse. Ich veröffentliche den eigenen Code, die Dokumentation und die eigenen Ergebnisdateien unter der [MIT-Lizenz](LICENSE), damit andere sie nutzen und weiterentwickeln können.

Wenn euch die Arbeit interessiert, freue ich mich über Rückmeldungen, unabhängige Nachprüfungen und Verbesserungsvorschläge. Wer meine bisherige Arbeit und mögliche weitere Forschung freiwillig finanziell unterstützen möchte, kann mir auch eine Bitcoin-Spende senden. Eine Spende ist ein Dankeschön für die Arbeit, kein Kauf und kein Versprechen auf Mining-Erträge oder bestimmte Forschungsergebnisse.

### Sponsoren und Forschungspartner gesucht

#### Welche Messungen eine Hardware-Schätzung braucht

Unabhängige Noncegruppen lassen sich grundsätzlich parallel bearbeiten. Ob eine größere GPU-/CPU-Ausstattung den gewünschten Durchsatz erreicht, muss jedoch an der konkreten Implementierung gemessen werden. Die Gruppenzahl allein und schnelle kleine Kontrollfälle reichen dafür nicht aus. Dafür benötigen wir:

- **Vollständige Laufzeit je Gruppe:** Aufbau beziehungsweise wiederverwendeter Aufbau, Datenübertragung, Propagation, weitere Verzweigungen und unabhängige Trefferprüfung; Mittelwert sowie Streuung und langsame Fälle, jeweils mit Hardware und Stapelgröße.
- **Tatsächlich eingesparte Kandidatenprüfungen:** Wie viele der 256 Kandidaten werden bereits durch gemeinsame Ableitungen ausgeschlossen, wie viele müssen einzeln entschieden werden? Innere Einschränkungen und ein Fixpunkt allein belegen noch keine eingesparte Sucharbeit.
- **Ergebnisanteile:** vollständig ausgeschlossene Gruppen, Gruppen mit bestätigten Treffern und weiterhin unentschiedene Gruppen (OPEN). Ein Fixpunkt ohne Entscheidung ist kein vollständig bearbeiteter Suchbereich.
- **Gemessene Skalierung:** vollständig entschiedene Gruppen pro Sekunde bei einer und mehreren Recheneinheiten, einschließlich Speicherbedarf, Verteilung und Übertragungsaufwand. Für einen Suchvorteil ist außerdem ein Vergleich mit direkter SHA256d-Auswertung derselben Kandidaten auf vergleichbarer Hardware nötig.

**Diese vollständige Durchsatz- und Skalierungsmessung liegt hier noch nicht vor.** In den dokumentierten Wurzeltests am vollständigen SHA256d mit acht freien Bits wurden keine Noncebits abgeleitet und keine Kandidaten ausgeschlossen. Daraus folgt weder eine schnelle vollständige Gruppenprüfung noch ein gemessener Hardwarebedarf. Beispielannahmen wie „50–200 Millisekunden pro Gruppe“ sind keine Ergebnisse dieses Projekts.

Bei einem gemessenen Gesamtdurchsatz von **G vollständig entschiedenen Gruppen pro Sekunde** benötigt der gesamte 32-Bit-Noncebereich einer festen Vorlage rechnerisch **16.777.216 / G Sekunden**. Das setzt voraus, dass dieser Durchsatz über den Bereich gehalten wird; OPEN-Fälle müssen berücksichtigt werden. Diese Rechnung beschreibt den Prüfaufwand, nicht die Wahrscheinlichkeit eines Blockfunds.

**Diese Erfolge machen Mut, hier weiterzuforschen:** Die kleinen Modelle liefern echte Ableitungen, und unser GPU-Kästchenminer hat den historischen Genesis-Treffer mit vollständigem SHA256d in einem begrenzten Suchbereich selbst wiedergefunden — unabhängig bestätigt, nicht nur als vorgegebenen Treffer erhalten. Darauf möchten wir aufbauen: mit größeren kontrollierten Versuchen, besseren Regeln und nachvollziehbaren Messungen. Ob sich dabei auch die Ableitungserfolge der kleinen Modelle auf die vollständige Rechnung übertragen lassen, bleibt die spannende offene Frage.

#### Was Unterstützung ermöglichen würde

**Was mehr Rechenleistung nachweisen könnte:** Ein festgelegter, endlicher Suchbereich lässt sich mit ausreichender Rechenzeit und geeignetem Speicher vollständig untersuchen. Bei einer festen Blockvorlage umfasst der gesamte 32-Bit-Noncebereich 4.294.967.296 Kandidaten beziehungsweise 16.777.216 Gruppen mit jeweils acht freien Bits. Damit wäre ein vollständiger Vergleich möglich: Findet die Kästchenmaschine genau die gültigen Kandidaten, die eine unabhängige SHA256d-Referenz bestätigt, und welchen Rechenaufwand benötigt sie dafür? Unentschiedene Gruppen zählen dabei nicht als geprüft und müssten vollständig aufgelöst werden.

**Ein solcher Korrektheitsnachweis ist grundsätzlich möglich; ein Blockfund ist nicht garantiert.** Auch ein vollständig geprüfter Bereich kann keinen Treffer enthalten. Für einen kontrollierten Versuch kann eine historische Vorlage mit bekanntem Treffer verwendet werden; das belegt die korrekte Suche in diesem Fall, aber keinen neuen Mainnet-Block und keinen Geschwindigkeitsvorteil. Mehr Ressourcen würden umfangreichere Nachweise und Messungen ermöglichen. Wie viel Hardware unsere konkrete Implementierung dafür benötigt und ob sie einen aktuellen Suchbereich rechtzeitig bewältigen kann, ist noch nicht bestimmt.

Ich suche Unterstützer, die helfen möchten, diese offene Forschungsfrage gründlicher zu untersuchen. Willkommen sind **bereitgestellte Rechenzeit, geeignete Hardware, finanzielle Unterstützung und fachliche Zusammenarbeit**. Damit könnten wir größere, kontrollierte Versuche durchführen, aufwendigere Ableitungsverfahren untersuchen und die Ergebnisse unabhängig nachprüfen lassen.

Die Unterstützung finanziert ergebnisoffene Forschung auf Grundlage der belegten kleinen Erfolge. Ein Mining-Vorteil oder ein gültiger neuer Bitcoin-Block kann daraus nicht zugesichert werden. Auch negative Ergebnisse und Grenzen sollen öffentlich dokumentiert werden. Wer eine Zusammenarbeit oder ein Sponsoring besprechen möchte, kann sich über die [GitHub-Issues](https://github.com/Christianfwb/kaestchenmaschine/issues) melden.

**Freiwillige Bitcoin-Spenden (Bitcoin-Mainnet):**

```text
14oJK42G3zJBjfzJsfHwYTmgJxDzMwNMAy
```

Vielen Dank an alle, die das Projekt mit Ideen, Tests oder einer Spende unterstützen. Die Nutzung des Projekts ist nicht an eine Spende gebunden.

— Christian Berrang

## Herkunft, Einordnung und Mitwirkung

Projekt von Christian Berrang, entwickelt mit den KI-Assistenten Ghost und Fable (Claude). KI-Ausgaben wurden geprüft und mehrfach korrigiert; diese Zusammenarbeit ersetzt keine unabhängige Validierung. Rückmeldungen mit reproduzierbaren Beispielen sind über [Issues](https://github.com/Christianfwb/kaestchenmaschine/issues) willkommen. Hinweise für Beiträge stehen in [CONTRIBUTING.md](CONTRIBUTING.md).

Wir beanspruchen keine Neuheit. Die Bausteine stammen aus der Constraint-Programmierung und booleschen Algebra. Die SHA-Rechnung orientiert sich an [NIST FIPS 180-4](https://doi.org/10.6028/NIST.FIPS.180-4); die Referenzprüfung nutzt [Python hashlib](https://docs.python.org/3/library/hashlib.html). E4 ist eine hier begrenzte Paarpropagation; die Versuche belegen keine allgemeine Vollständigkeit. Das Vorratsmodell ist nicht mit einem implementierten Hellman-Verfahren gleichzusetzen.

Der eigene Code, die Dokumentation und die eigenen Ergebnisdateien stehen unter der [MIT-Lizenz](LICENSE). Hinweise zu Herkunft und Drittbestandteilen stehen in den [Lizenzhinweisen](docs/LIZENZ_VORSCHLAG.md).

## English summary

This repository studies constraint propagation on Boolean and two-bit-digit representations of SHA256d. In five reduced-round control cases (4–16 rounds per compression, eight unknown nonce bits, a reachable exact output), bit propagation derives the nonce without enumerating candidates in the solver. Full-round experiments do not establish a mining speedup or a new valid block. Exact tables and NumPy vectors evaluate all selected candidates; they are separate baselines. Archived results, corrections and offline examples are included. The production miner is not included. Full historical experiment runners require Linux; the quick tests and first two examples are cross-platform. The project’s own code, documentation and result files are available under the [MIT License](LICENSE). Voluntary Bitcoin donations can support Christian’s work; see the donation address above.
