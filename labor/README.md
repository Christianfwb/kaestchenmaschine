# Gläserner Miner und Avalanche-Labor

**English:** The desktop interface is available in English. Choose **English** under **Sprache / Language**, or run `python -B -I labor/oberflaeche.py --lang en` from the repository root. Use the bottom and right scrollbars on smaller screens; Shift + mouse wheel scrolls sideways. Existing results survive language changes. Opening the app traces one known nonce; mining and rate measurement require their own button clicks. See [bilingual usage notes](UI_HINWEISE_DE_EN.txt).

Ein lokales Lern- und Forschungslabor: SHA-256 Runde für Runde betrachten, ein Nonce-Bit kippen und die Unterschiede nachrechnen. Das Programm bündelt den anschaulichen Abschluss unserer bisherigen Kästchenforschung. Es findet keine nachgewiesene SHA-Abkürzung und ist kein rentabler Miner.

## Start in fünf Minuten

Voraussetzung: Python 3.10 oder neuer. Die Oberfläche benötigt Tkinter (bei der üblichen Windows-Python-Installation enthalten). Alle Laborfunktionen laufen lokal; kein Konto, keine Wallet, kein Node und keine zusätzlichen Python-Pakete sind erforderlich.

**Fenster und Sprache:** Oben bei **Sprache / Language** zwischen Deutsch und Englisch wechseln. Vorhandene Ergebnisse bleiben erhalten. Das Fenster lässt sich bis auf 640 × 420 Pixel verkleinern. Unten und rechts gibt es Bildlaufleisten; **Umschalt + Mausrad** verschiebt die Hauptansicht seitlich. Zeitlupe, Laborerklärungen und Beweisbuch haben eigene Bildlaufleisten. Unter Linux gegebenenfalls `python3-tk` installieren. Die ursprüngliche Header-Herkunftsangabe und maschinellen Beweisbezeichner bleiben unverändert.

1. Das Repository herunterladen oder klonen.
2. Unter Windows den Ordner `labor` öffnen und `OBERFLAECHE.cmd` doppelklicken. Alternativ vom Repository-Hauptordner:

   ```sh
   python -B -I labor/oberflaeche.py
   ```

3. Im Reiter **Glaswand** den bereits berechneten Lebenslauf der mitgelieferten bekannten Nonce betrachten.
4. Zum **Avalanche-Labor** wechseln, Bit `0` wählen und **Kippen** drücken.
5. **Statistik** oder **Abhängigkeitskarte** erst bei Bedarf anklicken.

Beim Öffnen wird genau der angezeigte Lebenslauf berechnet. Es startet weder eine Nonce-Suche noch die Vergleichsmessung. Die Knöpfe **Start** im Bereich Mining und **Messung: 100.000 Nonces hashen** führen hingegen echte Hashversuche aus. Für den Rundgang werden sie nicht gebraucht.

## Was sehe ich?

### Glaswand und Zeitlupe

- `k0` verarbeitet die ersten 64 Headerbytes, die keine Nonce enthalten.
- `k1` verarbeitet den Rest des Headers einschließlich Nonce und Padding.
- `k2` ist die zweite SHA-256-Rechnung über den Zwischenhash.

Die Zeitlupe zeigt Rotationen, logische Verknüpfungen und Additionen einer ausgewählten Runde. Rundentabellen sind **0-basiert**: `t=3` ist die vierte ausgeführte Runde. Der Early Exit steht nach der **61. Runde, t=60**, fest. Er zeigt eine mögliche Verwerfung, beschleunigt aber die verwendete vollständige hashlib-Rechnung nicht.

Die Hashzeile zeigt die als Little-Endian interpretierte Hashzahl mit der höchsten Stelle links. Erforderliche Nullbitpositionen sind grün bei 0 und rot bei 1. Die exakte Trefferprüfung bleibt `Hashzahl <= Target`; die Anzahl führender Nullbits allein reicht nicht.

### Kippen

Das gewählte Bit bezeichnet den Stellenwert 0 bis 31 in der Nonce-Zahl. Das Programm berechnet zwei vollständige Lebensläufe und markiert unterschiedliche Zustandsbits rot. Es vergleicht keine Kandidaten mit dem Ziel, um daraus eine Suche oder Auswahl zu steuern; die gemeinsam benutzte Lebenslauffunktion berechnet intern weiterhin ein ungenutztes Trefferflag gegen Target 0.

Für den gelieferten Header, Nonce `acc33125`, Bit 0 beginnt der Unterschied in `k1` bei `t=3`. Die folgenden Abstände sind 2, 18, 46, 86, 118, 129. Einzelne spätere Runden erreichen 149. **128 ist der Erwartungswert, keine Obergrenze.** Für zwei ideale unabhängige 256-Bit-Zufallswerte liegt der mögliche Abstand zwischen 0 und 256, mit Mittelwert 128 und Standardabweichung 8.

### Statistik

Der Knopf verwendet 300 deterministisch zufällig gewählte Nonce-/Bit-Paare, Seed 20261121. Derselbe Header und Seed ergeben denselben Versuch. Der Referenzlauf liefert Mittel 127,72 und Stichprobenstreuung 8,20, min 103, max 153. Der angezeigte z-Wert verwendet den idealen Standardfehler `8/sqrt(n)`.

Ein unauffälliger Mittelwert beweist weder Unabhängigkeit sämtlicher Bits noch die Sicherheit von SHA-256. Die Rechnung kann die Oberfläche kurz blockieren; ein Abbruchknopf ist noch nicht enthalten.

### Abhängigkeitskarte und Matrix

Die Karte kippt alle 32 Eingabebits einzeln an derselben Nonce. Die GUI zeigt, wie viele Zustandsbits sich bei **mindestens einem** dieser Flips ändern. Das ist eine empirische Vereinigung. Sie bedeutet nicht, dass jedes Eingabebit jedes Zustandsbit beeinflusst. Ein unverändertes Bit beweist ebenfalls keine strukturelle Unabhängigkeit.

Die vollständige Zuordnung lässt sich exportieren:

```sh
python -B -I labor/glas_miner.py avalanche --nonce acc33125 --bit 0 --ausgabe avalanche.json
```

Der Export enthält Kurven, 300-Paare-Statistik und `abhaengigkeitskarte.matrix`. Format:

```text
matrix["k1" oder "k2"][Nonce-Bit 0..31][Runde t 0..63][Wort 0..7]
```

Die acht Wörter sind `a` bis `h` nach der Runde. In jedem 32-Bit-Wort bedeutet ein gesetztes Bit i, dass sich dieses Zustandsbit beim betreffenden Flip änderte. Eine anklickbare Matrixansicht gehört noch nicht zur Oberfläche. Der Ausgabepfad wird bei vorhandenem Dateinamen überschrieben; für neue Versuche einen neuen Namen wählen.

### Beweisbuch

**Beweisbuch dieser Nonce** berechnet den bekannten Eingabefall im Kästchennetz. Vollständig heißt: alle 256 Ausgabebits stehen im Buch, der rekonstruierte Digest stimmt mit hashlib überein und der getrennte Schrittprüfer meldet null Fehler. Leere, gekürzte und manipulierte Bücher werden in den Tests abgefangen.

Der Vertrag verwendet Target `2^256-1`: Das Buch belegt hier die Hashberechnung, nicht die Bitcoin-Zielbedingung. Schrittprüfer und Erzeuger teilen die Verdrahtungsbasis; es handelt sich nicht um zwei vollständig unabhängige SHA-Spezifikationen.

### Die Kante

**Herleiten** untersucht ein reduziertes Modell mit r Runden je Kompression, 16 freien Noncebits und einem exakten, aus einer bekannten Nonce erzeugten Zielhash. Im gelieferten Fall werden bei r=16 alle 16 Bits hergeleitet; bei r=17 bleiben sie offen. Das ist ein Ergebnis dieses Regelwerks und Versuchs, kein Unmöglichkeitsbeweis und kein Ergebnis über echtes Mining mit einer Zielgrenze.

## Ohne Nonce-Suche prüfen

Vom Repository-Hauptordner:

```sh
python -B -I labor/tests_glas.py --ohne-suche
python -B -I labor/tests_avalanche.py
python -B -I labor/tests_beweis.py
python -B -I labor/tests_release.py
```

Erwartet: 14/14 Glasprüfungen mit ausdrücklich ausgelassenen G10/G11, 10/10 Avalanche, 4/4 Beweis und bestandene Releaseprüfungen. Die Programme berechnen Laborhashes, suchen aber in diesen Aufrufen keine Nonce. `tests_glas.py` **ohne** `--ohne-suche` führt zusätzlich die originalen Suchschleifen G10/G11 aus.

Weitere ungefährliche Einblicke:

```sh
python -B -I labor/glas_miner.py lebenslauf --nonce acc33125 --runde k2:60
python -B -I labor/glas_miner.py odds --hashrate 1000000
python -B -I labor/glas_miner.py kante --runden 16,17
```

`odds` ohne explizite Hashrate startet dagegen eine Hashratenmessung. Die angezeigte Netzrate wird aus dem gespeicherten nBits-Wert und 600 Sekunden angenommener Blockzeit abgeleitet; sie ist keine aktuelle Netzwerkmessung. Die Herkunft des mitgelieferten Headers als Block 970000 wurde bei der hier dokumentierten Gegenprüfung nicht extern bestätigt.

## Fehler melden und weiterarbeiten

Bitte Befehl, Python-/Windows-Version, Commit, Eingaben und tatsächliches Ergebnis nennen. Für GUI-Probleme auch Fenstergröße und Skalierung angeben. Einfache Eingabefehler sollen als Meldung erscheinen; bei fehlendem Tkinter funktioniert die Kommandozeile weiter.

[Abschluss und Grenzen](../docs/ABSCHLUSS_20261121.md) · [Herkunft der Laborquellen](HERKUNFT.md) · [MIT-Lizenz](../LICENSE)
