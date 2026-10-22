# Beiträge und Fehlerberichte

Bitte vor einem Beitrag [Ergebnisse und Korrekturen](docs/EXPERIMENTE.md) und die [Lizenzentscheidung](docs/LIZENZ_VORSCHLAG.md) lesen. Die Lizenz ist noch offen; vor größeren Codeübernahmen die Bedingungen klären.

Ein hilfreicher Fehlerbericht nennt den Git-Commit, Python-Version, Betriebssystem, Befehl, Eingabefall und erwartetes/tatsächliches Ergebnis. Kleine reproduzierbare Beispiele sind besonders hilfreich. Keine Wallet-, RPC-Zugangsdaten oder privaten Vorlagen hochladen.

Für Regeländerungen: gültige Belegungen müssen erhalten bleiben, Abbruch ist kein Widerspruch, Referenzwerte dürfen die Ableitung nicht steuern. Orakel und Löser trennen. Aufbau-Vereinfachungen, Regelpropagation und Kandidatensuche getrennt messen. Zeiten mit Umgebung angeben; keine Neuheits- oder Miningversprechen aus Einzelmessungen.

Vor einem Pull Request:

```sh
python -B -I tests/test_regression.py
python -B -I tests/test_schnell.py
git add .
python -B -I tools/manifest.py --update
git add DATEILISTE.txt SHA256SUMS.txt
python -B -I tools/manifest.py --check
```

Historische Ergebnisdateien und Berichte nicht überschreiben. Korrekturen in der aktuellen Dokumentation sichtbar ergänzen. Neue Messergebnisse mit eigenem Dateinamen, Quellstand, Messumfang und Voraussetzungen ablegen. Große Versuchsreihen sind nicht Voraussetzung für reine Dokumentationsänderungen.
