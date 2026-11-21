# Abschluss der bisherigen Kästchenforschung: ein offenes SHA-256-Labor

Stand: 21. November 2026. Dieser Abschluss bündelt die bisherige Forschungsphase und macht ihre Werkzeuge benutzbar. Er beendet keine mathematisch offene Frage.

Ausgangspunkt war die Frage, wie weit sich Wissen über die Bits einer SHA256d-Rechnung mit kleinen überprüfbaren Regeln vorwärts und rückwärts tragen lässt. Das Ergebnis ist ein lokales Labor mit sichtbaren Rechenwegen, Beweisbüchern, reduzierten Kontrollmodellen und reproduzierbaren Avalanche-Versuchen. Ein bestätigter Mining-Vorteil wurde nicht gefunden.

## Was bleibt

1. **Nachvollziehbare Rechnung:** Ein 80-Byte-Header durchläuft drei Kompressionen; die Protokollrechnung stimmt in den geprüften Fällen mit hashlib überein. Midstate, konstante Paddingwörter und die Early-Exit-Identität werden sichtbar.
2. **Prüfbare Beweisbücher:** Für die bekannte Beispielnonce entstehen 329.279 Zeilen. Die aktuelle Vollständigkeitsprüfung rekonstruiert den Digest aus Buchzeilen und verlangt 256 belegte Ausgabebits sowie null Prüferfehler. Das ist eine Hashberechnung, keine Lösung einer unbekannten Miningaufgabe.
3. **Eine konkrete Grenze der untersuchten Regeln:** Bei 16 reduzierten Runden werden im Beispiel 16 freie Noncebits hergeleitet; bei 17 bleiben sie unbekannt. Die Lösung existiert durch die Konstruktion des Zielhashs. Stillstand ist daher kein Unlösbarkeitsbeweis.
4. **Empirische Sensitivität:** Ein gekipptes Eingabebit breitet Unterschiede über die Runden aus. Der 300-Paare-Versuch mit Seed 20261121 liefert einen mittleren Hash-Abstand von 127,72 bei Streuung 8,20. Die ideale Referenz ist Mittelwert 128 und Standardabweichung 8, keine Obergrenze.
5. **Negative Ergebnisse und Korrekturen gehören dazu:** Instabile Chancenberechnung, falsch beschriftetes Padding, fehlerhafte Byteordnung in der Anzeige, unzureichende Vollständigkeitsbewertung und zu starke Zufallsaussagen wurden gefunden und korrigiert. Die ältere Forschungshistorie bleibt nachlesbar.

## Selbst ausprobieren

Die [Bedienungsanleitung](../labor/README.md) führt von der Installation über den ersten Bitflip bis zum JSON-Export der vollständigen Bit-Matrix. Das Labor bringt seine Kästchen-Abhängigkeiten mit. Im Normalstart laufen weder Suche noch Vergleichsmessung; der bekannte Lebenslauf wird berechnet. Alle Laborfunktionen arbeiten offline.

## Reichweite der Prüfung

Die lokalen Gegenprüfungen liefen unter Windows mit Python 3.14.5. Die Version-3.1-Avalanchetests bestanden 10/10; für beide Matrizen wurden alle 32.768 Wortmasken und 128 Vereinigungszählungen kontrolliert. Die vier Beweisbuchvarianten bestanden in der vorigen Gegenprüfung 4/4. Die Originaltests G10/G11 wurden dabei nur synthetisch ausgeführt; im Repository gibt es deshalb einen ehrlichen Modus mit 14 Originalprüfungen und zwei ausdrücklich ausgelassenen Suchtests.

Keine dieser Prüfungen beweist die Sicherheit von SHA-256 oder die Unmöglichkeit anderer Verfahren. Getrennte Prüfroutinen teilen Teile der Modellverdrahtung. Die externe Herkunft des Headers und ein vollständiger GUI-Test auf allen Plattformen sind keine bestätigten Ergebnisse dieser historischen Läufe. Aktuelle Repository-Tests werden separat dokumentiert und automatisiert.

## Wobei Unterstützung hilft

Willkommen sind externe Code- und Beweisprüfungen, didaktische Rückmeldungen, plattformübergreifende Tests und Beiträge zur verständlichen Bit-Matrixansicht. Weitergehende Versuche benötigen vorab definierte Aufgaben und Erfolgskriterien. Eine Förderung wäre Unterstützung für offene Werkzeuge und nachvollziehbare Forschung, kein Kauf eines Mining-Ertrags.

[Frühere Ergebnisse](EXPERIMENTE.md) · [Nachtrag November](NACHTRAG_20261113.md) · [Offene Fragen](OFFENE_FRAGEN.md) · [Unterstützung](SPONSOREN.md)

## Prüfung der Repository-Integration

Am 21. November unter Windows / Python 3.14.5 bestanden: sechs bestehende Regressionstests, fünf Schnelltests, 14 Glasprüfungen ohne G10/G11, zehn Avalanchetests, vier Beweisbuchtests und die vollständige Matrix-/Eingabeprüfung. Ein zurückgezogenes Tk-Fenster wurde tatsächlich erzeugt; Start, ungültiger Bitindex, Kippen, Statistik und Karte liefen ohne Suche oder Vergleichsmessung. Dieser automatisierte GUI-Funktionstest ist kein Sichttest von Layout, Skalierung oder Bedienung. Reproduktion: `python -B -I labor/tests_gui.py` auf Windows mit Tkinter.
