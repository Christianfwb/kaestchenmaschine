# Lizenz und Herkunftshinweise

Christian hat die Veröffentlichung als Open Source freigegeben. Seit dem 23. Oktober 2026 gilt die [MIT-Lizenz](../LICENSE) für den eigenen Code, die Dokumentation und die eigenen Ergebnisdateien dieses Repositorys. Der frühere Vorschlag einer getrennten Textlizenz wurde nicht übernommen. Der Dateiname bleibt für bestehende Links erhalten.

Urheberhinweis: Christian Berrang. Entwicklung mit Unterstützung der KI-Assistenten Ghost und Fable (Claude); siehe [README](../README.md). Drittbestandteile behalten ihre eigenen Lizenzbedingungen. Die folgende Herkunftsliste dokumentiert den bisherigen Projektstand und ersetzt keine Rechteprüfung neuer Fremdbeiträge.

## Geprüfte Bestandteile

| Bestandteil | Herkunft | Lizenzlage | Befund |
|---|---|---|---|
| `gatter.py`, `pruefung.py`, `teilbits.py` | aus dem Kästchenminer-Projekt (Christian/Ghost, früher mit anderen KI-Werkzeugen entstanden); unverändert übernommen | Eigenes Projekt | keine fremden Lizenzhinweise enthalten; `gatter.py` enthält am Ende eine ältere SAT-Probe (`main`), die optional `z3` nutzt – nicht Teil der Forschung, kann entfernt oder belassen werden (Entscheidung) |
| alle übrigen Module und Skripte | in diesem Projekt von Fable geschrieben (22./23.10.2026) | Eigenes Projekt | keine Fremdübernahme; Algorithmen sind Lehrbuchwissen (Bogen-/Pfadkonsistenz, Gauß über GF(2)) |
| SHA-256-Konstanten (K, IV) | FIPS 180-4 | gemeinfrei (US-Bundesstandard) | – |
| Genesis-Blockdaten (`pruefung.py`: MERKLE, NONCE, BITS; `FAELLE_SHA256D.json` F2) | Bitcoin-Blockchain / Bitcoin Core `chainparams.cpp` | öffentliche Daten; Bitcoin Core ist MIT | nur Daten, kein Code übernommen |
| Template F1 (`FAELLE_SHA256D.json`) | von Christians Node gespeicherte Vorlage (Höhe 972 527), Header ohne Nonce | eigene Daten; enthält Vorgängerhash und Merkle-Wurzel, keine Adressen, keine Zugangsdaten | lokaler Dateipfad in der Veröffentlichungskopie entfernt (Feld `quelle.source`) |
| numpy | Drittbibliothek, nicht enthalten, nur `pip`-Abhängigkeit | BSD-3 | verträglich |
| z3 (optional, nur `gatter.main`) | Drittbibliothek, nicht enthalten | MIT | verträglich; Abhängigkeit kann entfallen |
| Python-Standardbibliothek | – | PSF | – |

Nicht enthalten und nicht zu veröffentlichen: Miner-Betriebscode mit RPC/Wallet-Logik (`betrieb.py`, `safety.py`,
`bauen_live.cjs`, `blockpruefer.py`, `bridge.cjs`), GPU-Kernel, Konfigurationen, Korrespondenz, Unterlagen zu anderen
Projekten. Das Paket wurde auf Pfade, E-Mail-Adressen, Zugangsdaten und Wallet-Begriffe durchsucht (Befund: keine).
