# Abschluss der bisherigen Kﾃ､stchenforschung: ein offenes SHA-256-Labor

Stand: 21. November 2026. Dieser Abschluss bﾃｼndelt die bisherige Forschungsphase und macht ihre Werkzeuge benutzbar. Er beendet keine mathematisch offene Frage.

Ausgangspunkt war die Frage, wie weit sich Wissen ﾃｼber die Bits einer SHA256d-Rechnung mit kleinen ﾃｼberprﾃｼfbaren Regeln vorwﾃ､rts und rﾃｼckwﾃ､rts tragen lﾃ､sst. Das Ergebnis ist ein lokales Labor mit sichtbaren Rechenwegen, Beweisbﾃｼchern, reduzierten Kontrollmodellen und reproduzierbaren Avalanche-Versuchen. Ein bestﾃ､tigter Mining-Vorteil wurde nicht gefunden.

## Was bleibt

1. **Nachvollziehbare Rechnung:** Ein 80-Byte-Header durchlﾃ､uft drei Kompressionen; die Protokollrechnung stimmt in den geprﾃｼften Fﾃ､llen mit hashlib ﾃｼberein. Midstate, konstante Paddingwﾃｶrter und die Early-Exit-Identitﾃ､t werden sichtbar.
2. **Prﾃｼfbare Beweisbﾃｼcher:** Fﾃｼr die bekannte Beispielnonce entstehen 329.279 Zeilen. Die aktuelle Vollstﾃ､ndigkeitsprﾃｼfung rekonstruiert den Digest aus Buchzeilen und verlangt 256 belegte Ausgabebits sowie null Prﾃｼferfehler. Das ist eine Hashberechnung, keine Lﾃｶsung einer unbekannten Miningaufgabe.
3. **Eine konkrete Grenze der untersuchten Regeln:** Bei 16 reduzierten Runden werden im Beispiel 16 freie Noncebits hergeleitet; bei 17 bleiben sie unbekannt. Die Lﾃｶsung existiert durch die Konstruktion des Zielhashs. Stillstand ist daher kein Unlﾃｶsbarkeitsbeweis.
4. **Empirische Sensitivitﾃ､t:** Ein gekipptes Eingabebit breitet Unterschiede ﾃｼber die Runden aus. Der 300-Paare-Versuch mit Seed 20261121 liefert einen mittleren Hash-Abstand von 127,72 bei Streuung 8,20. Die ideale Referenz ist Mittelwert 128 und Standardabweichung 8, keine Obergrenze.
5. **Negative Ergebnisse und Korrekturen gehﾃｶren dazu:** Instabile Chancenberechnung, falsch beschriftetes Padding, fehlerhafte Byteordnung in der Anzeige, unzureichende Vollstﾃ､ndigkeitsbewertung und zu starke Zufallsaussagen wurden gefunden und korrigiert. Die ﾃ､ltere Forschungshistorie bleibt nachlesbar.

## Selbst ausprobieren

Die [Bedienungsanleitung](../labor/README.md) fﾃｼhrt von der Installation ﾃｼber den ersten Bitflip bis zum JSON-Export der vollstﾃ､ndigen Bit-Matrix. Das Labor bringt seine Kﾃ､stchen-Abhﾃ､ngigkeiten mit. Im Normalstart laufen weder Suche noch Vergleichsmessung; der bekannte Lebenslauf wird berechnet. Alle Laborfunktionen arbeiten offline.

## Reichweite der Prﾃｼfung

Die lokalen Gegenprﾃｼfungen liefen unter Windows mit Python 3.14.5. Die Version-3.1-Avalanchetests bestanden 10/10; fﾃｼr beide Matrizen wurden alle 32.768 Wortmasken und 128 Vereinigungszﾃ､hlungen kontrolliert. Die vier Beweisbuchvarianten bestanden in der vorigen Gegenprﾃｼfung 4/4. Die Originaltests G10/G11 wurden dabei nur synthetisch ausgefﾃｼhrt; im Repository gibt es deshalb einen ehrlichen Modus mit 14 Originalprﾃｼfungen und zwei ausdrﾃｼcklich ausgelassenen Suchtests.

Keine dieser Prﾃｼfungen beweist die Sicherheit von SHA-256 oder die Unmﾃｶglichkeit anderer Verfahren. Getrennte Prﾃｼfroutinen teilen Teile der Modellverdrahtung. Die externe Herkunft des Headers und ein vollstﾃ､ndiger GUI-Test auf allen Plattformen sind keine bestﾃ､tigten Ergebnisse dieser historischen Lﾃ､ufe. Aktuelle Repository-Tests werden separat dokumentiert und automatisiert.

## Wobei Unterstﾃｼtzung hilft

Willkommen sind externe Code- und Beweisprﾃｼfungen, didaktische Rﾃｼckmeldungen, plattformﾃｼbergreifende Tests und Beitrﾃ､ge zur verstﾃ､ndlichen Bit-Matrixansicht. Weitergehende Versuche benﾃｶtigen vorab definierte Aufgaben und Erfolgskriterien. Eine Fﾃｶrderung wﾃ､re Unterstﾃｼtzung fﾃｼr offene Werkzeuge und nachvollziehbare Forschung, kein Kauf eines Mining-Ertrags.

[Frﾃｼhere Ergebnisse](EXPERIMENTE.md) ﾂｷ [Nachtrag November](NACHTRAG_20261113.md) ﾂｷ [Offene Fragen](OFFENE_FRAGEN.md) ﾂｷ [Unterstﾃｼtzung](SPONSOREN.md)

## Prüfung der Repository-Integration

Am 21. November unter Windows / Python 3.14.5 bestanden: sechs bestehende Regressionstests, fünf Schnelltests, 14 Glasprüfungen ohne G10/G11, zehn Avalanchetests, vier Beweisbuchtests und die vollständige Matrix-/Eingabeprüfung. Ein zurückgezogenes Tk-Fenster wurde tatsächlich erzeugt; Start, ungültiger Bitindex, Kippen, Statistik und Karte liefen ohne Suche oder Vergleichsmessung. Dieser automatisierte GUI-Funktionstest ist kein Sichttest von Layout, Skalierung oder Bedienung. Reproduktion: `python -B -I labor/tests_gui.py` auf Windows mit Tkinter.
