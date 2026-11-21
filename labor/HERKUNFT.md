# Herkunft des Laborstands

Die Veröffentlichung integriert das lokale Projekt GLAS_MINER_20261120, Stand Version 3.1 vom 21. November 2026, in die Kästchenmaschine von Christian Berrang. Die Quellen wurden mit Ghost und Fable entwickelt und gegenseitig geprüft. Diese KI-gestützten Gegenprüfungen ersetzen keine externe unabhängige wissenschaftliche Validierung.

`kaestchen_basis/gemeinsam.py`, `runden_modell.py` und `engine_f4/*.py` sind die für Beweis/Kante mitgelieferten Projektquellen aus FABLE_SAT_KAESTCHEN_20261114. Es werden keine SAT-Läufe, Wallets, Node-Zugänge oder privaten Konfigurationsdateien mitgeliefert. Die Quelltexte verbleiben unter der Projektlizenz (MIT, Christian Berrang). Der vollständige lokale Versuchsdatenbestand ist nicht Bestandteil dieses Laborpakets.

Anpassungen für das Repository gegenüber Version 3.1:

- Abhängigkeitspfad zeigt standardmäßig auf die mitgelieferte `kaestchen_basis` statt auf einen benachbarten lokalen Arbeitsordner. Die vorhandenen Umgebungsvariablen GLAS_KAESTCHEN/KAESTCHEN_ENGINE können den Pfad ausdrücklich überschreiben.
- `tests_glas.py --ohne-suche` lässt G10/G11 ausdrücklich aus, ohne synthetische Treffer als Originalprüfungen auszugeben.
- Eingabegrenzen für Nonce, Bitindex, Statistikanzahl und Bitliste sind validiert; GUI meldet ungültige Bitindizes verständlich.
- Kante meldet eine bestätigte rekonstruierte Nonce nur bei null Prüferfehlern.
- Die GUI erklärt die Vereinigung der Flips ohne die unbewiesene Verknüpfung zu älteren Schrankenexperimenten. Die Beschreibung des intern ungenutzten Targetflags ist präzisiert.
- Die alte Vorschau mit dem falschen Satz zu 128 wird nicht als aktuelle Vorschau übernommen.

Historische Berichte im übrigen Repository bleiben unverändert. Die Reproduktionsanleitung dokumentiert aktuelle Ergebnisse samt Grenzen; die bisherigen lokalen Versionen werden nicht nachträglich umgeschrieben.
