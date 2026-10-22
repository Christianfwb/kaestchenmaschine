# Technische Dokumentation des Kästchenlösers

Alles hier beschriebene ist in `src/kaestchen/` enthalten und wurde in den Experimenten verwendet. Die Beschreibung folgt
dem Code; Zeilenangaben sind weggelassen, Funktionsnamen stimmen.

## 1. Abgrenzung: Miner und Forschung

| | Kästchenminer (Betrieb) | Forschungscode (dieses Paket) |
|---|---|---|
| Zweck | sucht laufend nach gültigen Blöcken | misst, was Propagation ableiten kann |
| Ort | Christians Windows-Rechner, GPU, Bitcoin-Node | Linux-Container, nur CPU, offline |
| Graph | `gatter.py` (identische Datei) | `gatter.py` + Ziffernnetz |
| Regeln | E1 (Bitregeln) auf der GPU, max. 12 Durchläufe, Baumsuche über freie Bits | E1, E3, E4, Dreier, Auffrischer u. a., **keine Baumsuche** |
| Trefferprüfung | Graph + Kästchen + unabhängiges hashlib | nur nachträglich als Orakel, nie als Eingabe |
| Enthalten | **nein** (RPC, Wallet, Betrieb, GPU-Kernel – siehe `miner/README.md`) | ja, vollständig |

Der einzige gemeinsame Baustein ist der Graphaufbau (`gatter.py`, `pruefung.py`, `teilbits.py`). Ein Treffer in der
Forschung wäre nichts weiter als ein Zahlenergebnis; nichts hier reicht etwas ein oder spricht mit einem Node.

## 2. Bitgraph (`gatter.py`, `pruefung.py`)

* `pruefung.compress(state, words, op, trace)` ist die Referenz-SHA-256-Kompression als Rechenweg über eine
  Operatorklasse `op` (`const, rot, shr, xor, ch, maj, add`). Mit `IntegerOps` rechnet sie Zahlen (gegen `hashlib`
  geprüft), mit `gatter.Ops` baut sie Gatter, mit `ZiffernOps` Ziffernbeziehungen – **derselbe Code, drei Auslegungen.**
  `sha_ziffern.compress_r` ist dieselbe Funktion mit Parameter `runden` (Rundenkurve); `runden=64` ist textgleich.
* `gatter.Graph`: Knotenliste. Knoten 0 und 1 sind die Konstanten, Eingänge sind `('input', i)`, Gatter sind
  `('and', a, b)` und `('xor', a, b)`. Ein negativer Index bedeutet Negation. `Graph.gate` vereinfacht beim Aufbau:
  Konstanten werden herausgerechnet, gleiche Gatter nur einmal angelegt (Hash-Consing), doppelte und negierte Eingänge
  zusammengefasst. Folge: Mit einem einzigen freien Bit kollabiert der Graph auf drei Knoten, weil jede Funktion
  eines Bits eine Konstante, das Bit oder seine Negation ist. **Aufbau-Vereinfachung ist symbolische Ableitung, aber kein Gewinn durch nachgelagerte Propagationsregeln** – deshalb
  wird in allen Berichten Graphgröße und Art der Wurzel nach dem Aufbau mitgemessen.
* `sha_ziffern.baue_bitgraph(header76, base, bits, target, runden=64, mit_ziel=True)`: Midstate des ersten Blocks als
  Konstante (nonce-frei), zweiter Block mit freiem Nonce-Wort (nur die angegebenen Bits sind Eingänge), zweite Anwendung
  mit Padding, danach Vergleichskette „Hash ≤ Target" über die 256 Digestbits in Bitcoin-Byteordnung (Wurzel). Bei
  8 freien Bits am Template F1: 207 917 Knoten.

## 3. Kästchen und Bitregel E1 (`e1_bit.py`)

Jeder Knoten hat eine Maske: 1 = {0}, 2 = {1}, 3 = {0,1}, 0 = leer (Widerspruch). `e1_lauf(g, d, max_sweeps)` ist
Bogenkonsistenz über jedes Gatter: aus den Masken der beiden Eingänge und des Ausgangs werden über eine vorberechnete
Tabelle die noch gestützten Werte aller drei berechnet und geschnitten. Ein Durchlauf geht vorwärts und rückwärts über
alle Gatter. Ergebnis `FIXPUNKT` (nichts mehr ändert sich), `WIDERSPRUCH` (eine Maske leer) oder `OFFEN`
(Durchlaufgrenze). Der Miner nutzt dieselbe Regel mit Grenze 12; in der Forschung wurde die Grenze zuletzt aufgehoben,
weil sie Ergebnisse verfälscht hatte (Zielhash-Vergleich: Fixpunkt erst nach 41 Durchläufen).

Die Regeln entfernen Werte ohne Unterstützung in der jeweiligen Gatterrelation. Soundness beruht auf der korrekten Relation und Projektion, nicht allein darauf, dass Mengen geschnitten werden. Einzelne Domänen speichern keine beliebigen gemeinsamen Belegungen. Ein Fixpunkt auf dem SHA-Netz ist keine vollständige Entscheidung.

Seit der Repository-Prüfung werden auch bereits leere Domänen und widersprüchliche Konstanten vor dem ersten Gatter geprüft. Das betrifft insbesondere Graphen, deren Ziel beim Aufbau zu einer Konstanten vereinfacht wurde. Historische Messdaten werden deshalb nicht rückwirkend überschrieben.

## 4. Ziffernnetz (`ziffern.py`, `bausteine.py`, `ziffern_sha.py`, `sha_ziffern.py`)

* `ziffern.Netz(32)`: Variablen mit Domänen als Bitmasken über 2 oder 4 Werte („Ziffer" = 2 Bit, ein 32-Bit-Wort =
  16 Ziffern); Beziehungen sind benannte Tupeltabellen (`TABELLEN`, `GROESSEN`).
* Bausteine (`bausteine.py`): Rotation um gerade Zahlen = Umbenennung, ungerade = `ROT1`-Tabelle über zwei Nachbarziffern;
  `CH`, `MAJ` als 4-stellige Tabellen; Addition als Kette von `ADD` mit Übertragsvariablen; XOR dreifach = zwei XOR;
  Zielvergleich als `LE`-Kette über 128 Ziffern der little-endian-Zahl. Alle Bausteine wurden erschöpfend (w = 8) und
  stichprobenartig (w = 32) gegen die Integer-Referenz geprüft (Stufe 0, 0 Fehler).
* `sha_ziffern.ZiffernOps` führt `pruefung.compress` über das Netz aus und protokolliert jedes Ergebniswort in derselben
  Reihenfolge wie `BitLog` (Bitgraph) und `IntLog` (Zahlen). `wortzuordnung` ordnet Bit- und Ziffernwörter
  **semantisch** (Phase, Art, laufende Nummer) zu, nie über Knoten-IDs.
* Adapter: `bits_zu_ziffern`, `ziffer_zu_bits`, `dom_von`, `dom_schneiden` (Negation über negative Indizes).

## 5. Regeln auf dem Ziffernnetz

* **E3** (`ziffern_sha.e3`): verallgemeinerte Bogenkonsistenz je Beziehung über einen Tupelindex – aus jeder Tabelle
  werden nur die Tupel betrachtet, deren Werte alle noch in den Domänen liegen; Projektion auf jede Variable.
* **E4** (`ziffern_komp.e4`, `ziffern_array.e4`): zusätzlich Paarbeziehungen (Radius 1 = Paare, die eine gemeinsame
  Beziehung oder einen gemeinsamen Nachbarn haben). Paarmasken über (vx·gy + vy); Einschränkung R(x,z) ← R(x,z) ∩ (R(x,y)∘R(y,z))
  über vorberechnete Zeilen-/Spalten-/Transpositionstabellen je Größenpaar. `ziffern_array.PaarSpeicher` hält alle
  Paare, die die Radius-1-Schließung je anlegen kann, **vorab gezählt** in Arrays (Schlüssel per numpy aufgebaut);
  liegt die Zahl über der Paargrenze, endet der Lauf vor jeder Anlage mit `OPEN`. `zeuge_ok` prüft streamend, ob eine
  bekannte Lösung in allen Paarmasken liegt. `nachpruefung=True` lässt nach dem Fixpunkt einen vollen E3-Durchlauf
  über alle Beziehungen laufen; er darf nichts ändern.
* **Austausch** (`austausch.py`): Bitdomänen → Zifferndomänen (Schnitt), E4, Zifferndomänen → Bitdomänen, E1, bis
  nichts mehr enger wird; alter Paarspeicher wird vor dem nächsten Aufbau freigegeben.
* **Dreier** (`dreier_beispiel.py`, `wurzel_kind*.py`): 32 dreistellige Beziehungen an Σ1(e60) als Versuch, Herkunft
  über drei Variablen zu halten. **Auffrischer** (`kette.py`): Komposition aller Paarmasken entlang benannter
  Rechenketten (Übertragsketten, Zielkette) in das Paar (Anfang, Ende).
* Zusätzliche Darstellungen, als eigene kleine Experimente: 4-Wege-Wahrheitstabellen (`tabellen4_kind.py`, exakt bei
  2 freien Bits), NumPy-Phasenvektoren (`phasen_kind.py`, dieselbe Kodierung), XOR-Gleichungen über GF(2)
  (`xor_sha_kind.py`, UND-Ausgänge als freie Basisvektoren – eine Lockerung, sound).

## 6. Messdisziplin (gilt für alle Läufe)

* Die überwachten Experimentreihen verwenden Kindprozesse; die einfachen Beispiele und Schnelltests laufen direkt. Bei den Reihen gilt: ein Elternprozess (`lauf_*.py`) überwacht Wandzeit und RSS alle 0,1 s und bricht bei
  Überschreitung ab. Abbruch wird als `OFFEN` mit erreichtem Fortschritt berichtet, nie als Ergebnis gewertet.
* Referenzwerte (hashlib, Integer-Referenz) werden **nie** in das Netz eingespeist; sie dienen nur der nachträglichen
  Kontrolle (Orakel über alle Kandidaten). Jeder Ausschluss wird gegen das Orakel geprüft; ein falscher Ausschluss
  stoppt die Reihe mit `FEHLER` (kam in keinem gültigen Lauf vor).
* Bekannte Treffer (Genesis) müssen in allen Bit-, Ziffern- und Paarmasken erhalten bleiben (`zeuge_ok`).
* Vergleiche nur an gemeinsamen, eindeutig zugeordneten Messstellen (Register a..h je Runde beider Anwendungen).
* Zeiten sind Einzelmessungen auf dem genannten Rechner (Linux-Container, Intel Xeon 2,10 GHz, 2 Kerne, Python 3.13.16,
  numpy 2.5.3), keine Eigenschaft der Methode.
* Gate-Regel (`lauf_wurzel*.py`, `gate_test.py`): ein Folgelauf startet nur nach gültigem Vorlauf (Status OK,
  FIXPUNKT, kein Abbruch); 12 Szenarien geprüft.
