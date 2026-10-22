# Lizenzvorschlag und Prüfung fremder Bestandteile

**Die Lizenzentscheidung ist offen** und liegt bei Christian. Dies ist ein Vorschlag mit Prüfung.

## Vorschlag

* Quellcode (`src/`, `beispiele/`, `tests/`, `experimente/skripte/`): **MIT-Lizenz** oder **Apache-2.0**. Beide sind
  freizügig und passen zu „alles wird Open Source". Apache-2.0 enthält zusätzlich eine ausdrückliche Patentklausel;
  MIT ist kürzer. Beides ist mit numpy (BSD-3) verträglich.
* Dokumentation, Berichte, Ergebnisdaten (`docs/`, `experimente/berichte/`, `experimente/ergebnisse/`, `README.md`):
  **CC BY 4.0**, damit Zitate und Nachnutzung mit Namensnennung möglich sind.
* Urheber-/Namensnennung: „Christian Berrang, in Zusammenarbeit mit Ghost (KI-Agent) und Claude (Anthropic)".
  Der Code wurde überwiegend von KI-Agenten unter Christians Leitung geschrieben; die Rechtslage zu KI-erzeugtem Code
  unterscheidet sich nach Land. Eine Lizenz ist trotzdem sinnvoll, weil sie die Nutzungsbedingungen klärt, auch wenn
  der Schutzumfang offen bleibt. Das sollte im LICENSE-Hinweis in einem Satz stehen.

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
