# Sponsoren und Forschungspartner gesucht

*Ausgelagert aus der README am 13. November 2026; Stand der Aussagen: 25. Oktober 2026, Nachtrag siehe [NACHTRAG_20261113.md](NACHTRAG_20261113.md).*

#### Welche Messungen eine Hardware-Schätzung braucht

Unabhängige Noncegruppen lassen sich grundsätzlich parallel bearbeiten. Ob eine größere GPU-/CPU-Ausstattung den gewünschten Durchsatz erreicht, muss jedoch an der konkreten Implementierung gemessen werden. Die Gruppenzahl allein und schnelle kleine Kontrollfälle reichen dafür nicht aus. Dafür benötigen wir:

- **Vollständige Laufzeit je Gruppe:** Aufbau beziehungsweise wiederverwendeter Aufbau, Datenübertragung, Propagation, weitere Verzweigungen und unabhängige Trefferprüfung; Mittelwert sowie Streuung und langsame Fälle, jeweils mit Hardware und Stapelgröße.
- **Tatsächlich eingesparte Kandidatenprüfungen:** Wie viele der 256 Kandidaten werden bereits durch gemeinsame Ableitungen ausgeschlossen, wie viele müssen einzeln entschieden werden? Innere Einschränkungen und ein Fixpunkt allein belegen noch keine eingesparte Sucharbeit.
- **Ergebnisanteile:** vollständig ausgeschlossene Gruppen, Gruppen mit bestätigten Treffern und weiterhin unentschiedene Gruppen (OPEN). Ein Fixpunkt ohne Entscheidung ist kein vollständig bearbeiteter Suchbereich.
- **Gemessene Skalierung:** vollständig entschiedene Gruppen pro Sekunde bei einer und mehreren Recheneinheiten, einschließlich Speicherbedarf, Verteilung und Übertragungsaufwand. Für einen Suchvorteil ist außerdem ein Vergleich mit direkter SHA256d-Auswertung derselben Kandidaten auf vergleichbarer Hardware nötig.

**Diese vollständige Durchsatz- und Skalierungsmessung liegt hier noch nicht vor.** In den dokumentierten Wurzeltests am vollständigen SHA256d mit acht freien Bits wurden keine Noncebits abgeleitet und keine Kandidaten ausgeschlossen. Daraus folgt weder eine schnelle vollständige Gruppenprüfung noch ein gemessener Hardwarebedarf. Beispielannahmen wie „50–200 Millisekunden pro Gruppe“ sind keine Ergebnisse dieses Projekts.

Bei einem gemessenen Gesamtdurchsatz von **G vollständig entschiedenen Gruppen pro Sekunde** benötigt der gesamte 32-Bit-Noncebereich einer festen Vorlage rechnerisch **16.777.216 / G Sekunden**. Das setzt voraus, dass dieser Durchsatz über den Bereich gehalten wird; OPEN-Fälle müssen berücksichtigt werden. Diese Rechnung beschreibt den Prüfaufwand, nicht die Wahrscheinlichkeit eines Blockfunds.

**Stand nach Abschluss (25. Oktober 2026):** Die Übertragung der kleinen Ableitungserfolge auf die vollständige Rechnung haben wir mit stärkeren Verfahren (exakter Join-Baum mit Bitmengen) geprüft und mit der Mining-Frage (billiges Aussortieren) konfrontiert. Beides ist gemessen und negativ für das vollständige SHA256d; die Begründung – exponentiell wachsende Breite durch die Wiederverwendung unbekannter Wörter – steht im [Abschlussbericht](ABSCHLUSS_20261025.md). Wir verfolgen die Mining-Frage nicht weiter; das Repository bleibt als nachprüfbares Labor offen.

#### Was Unterstützung ermöglichen würde

**Was mehr Mittel wirklich klären könnten:** Die gemessene Grenze liegt nicht an fehlender Rechenzeit. Beim vollständigen SHA256d rechnen die geprüften Regeln in Sekunden bis Minuten bis zum Fixpunkt und bestimmen keine Noncebits. Der Miner sucht deshalb mit Verzweigungen über die freien Bits; die Regeln schließen dabei in den gemessenen Fällen keine Bereiche vorzeitig aus, und die SHA256d-Referenz bestätigt die gefundenen Treffer. Dass dieser Suchweg funktioniert, ist am Genesis-Block belegt (bekannter Treffer gefunden, Erhaltung in allen Domänen). Ein vollständiger Durchlauf des 32-Bit-Noncebereichs würde diesen Befund nur wiederholen; mehr Laufzeit verändert einen erreichten Fixpunkt nicht.

Offen und messbar – jeweils mit festen Zeit- und Speichergrenzen, weil der Aufwand noch nicht bekannt ist – sind dagegen:

- **Rundenkurve 17 bis 63:** inzwischen gemessen – scharfe Kante bei 17 Runden, Ursache Nachrichtenerweiterung (siehe Abschluss).
- **Mehr freie Bits im reduzierten Modell:** Alle Rundenläufe hatten 8 freie Bits. Ob die Ableitung bei 16 oder 32 freien Bits vollständig bleibt, trennt „die Regeln lösen es“ von „256 Kandidaten sind wenig“.
- **Stärkere Ableitungsregeln:** Paare, Tripel und Gleichungssysteme auf reduzierten Runden, um zu sehen, welche Beziehung die Reichweite tatsächlich verlängert.
- **Unabhängige Nachprüfung:** Wiederholung der archivierten Läufe auf anderer Hardware und durch andere Personen.

**Was daraus nicht folgt:** Kein Mining-Vorteil, kein neuer Block, kein Beleg, dass mehr Hardware das vollständige SHA256d erreichbar macht. Die Unterstützung finanziert ergebnisoffene Forschung an diesen Fragen; negative Ergebnisse werden genauso veröffentlicht wie positive.

Ich suche Unterstützer, die helfen möchten, diese offene Forschungsfrage gründlicher zu untersuchen. Willkommen sind **bereitgestellte Rechenzeit, geeignete Hardware, finanzielle Unterstützung und fachliche Zusammenarbeit**. Damit könnten wir größere, kontrollierte Versuche durchführen, aufwendigere Ableitungsverfahren untersuchen und die Ergebnisse unabhängig nachprüfen lassen.

Die Unterstützung finanziert ergebnisoffene Forschung auf Grundlage der belegten kleinen Erfolge. Ein Mining-Vorteil oder ein gültiger neuer Bitcoin-Block kann daraus nicht zugesichert werden. Auch negative Ergebnisse und Grenzen sollen öffentlich dokumentiert werden. Wer eine Zusammenarbeit oder ein Sponsoring besprechen möchte, kann sich direkt per E-Mail oder über die [GitHub-Issues](https://github.com/Christianfwb/kaestchenmaschine/issues) melden.


**Kontakt:** Christian Berrang · [christianfwb@gmail.com](mailto:christianfwb@gmail.com) · [GitHub-Issues](https://github.com/Christianfwb/kaestchenmaschine/issues). Bitcoin-Spendenadresse in der [README](../README.md).
