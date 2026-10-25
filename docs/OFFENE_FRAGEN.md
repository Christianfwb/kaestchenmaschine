# Offene Fragen und Voraussetzungen für spätere Forschung

**Nachtrag 25. Oktober 2026:** Frage 1 (Rundenkurve 17–63) ist gemessen – scharfe Kante bei 17 Runden, Ursache Nachrichtenerweiterung ([Bericht](../experimente/berichte/BERICHT_RUNDENKURVE_17_63.txt)). Die Voraussetzung „welche Beziehung hält die Erweiterung zusätzlich“ wurde mit dem Stern (Join-Baum, Bitmengen) umgesetzt und an N4r09/N4r10 gemessen; die Mining-Frage (billiges Aussortieren) ist in 48 Fällen negativ. Siehe [Abschluss](ABSCHLUSS_20261025.md). Das Projekt ist abgeschlossen; die übrigen Fragen bleiben als Fragen stehen, nicht als Vorhaben.

Keine der Fragen ist ein Versprechen. Sie sind das, was wir messen würden, wenn wir weitermachen – mit derselben
Disziplin (Watchdog, Orakel erst danach, Vergleich an Messstellen, keine automatischen Folgeläufe).

## Offen (nicht gemessen)

1. **Rundenkurve 17–63.** Gemessen: bis 16 Runden vollständige Ableitung durch E1; bei 64 Runden keine Noncebits in den getesteten Fällen. Wo endet sie,
   abrupt oder allmählich? Erster Verdacht (Vermutung): bis 16 Runden gibt es keine Nachrichtenerweiterung, die Nonce
   tritt nur über W3 in Runde 4 ein. Ein Lauf je Rundenzahl, Sekunden bis Minuten.
2. **Zweiter Zielhash.** „Rückwärts bis Runde 57" beruht auf einem H*. Ob die Reichweite am Wert oder an der Struktur
   hängt, zeigt ein zweiter, ebenso eingefrorener Zielhash.
3. **Mehr freie Bits im reduzierten Modell.** Alle Rundenläufe hatten 8 freie Bits. Bleibt die Ableitung bei 16 oder 32
   freien Bits (echte Nonce) im reduzierten Modell vollständig? Das trennt „Propagation löst es" von „256 Kandidaten
   sind wenig".
4. **Paare auf reduzierten Runden.** E4 wurde dort nicht gebraucht und nicht gemessen. Ab welcher Rundenzahl helfen
   Paare, wo E1 allein nicht mehr durchkommt?
5. **Faires Vorratsmodell.** Gleiche erlaubte Änderungen (Extranonce, Zeit) beim direkten Suchen und beim Nachschlagen;
   8-Register-Modell mit e-Kette. Erwartung bleibt dieselbe, aber dann wäre es gemessen.
6. **E1-Durchlaufgrenze im Miner.** Der Miner bricht nach 12 Durchläufen ab (Status 0 = offen). Die Forschung hat
   gezeigt, dass der Fixpunkt beim Zielhash erst nach 41 Durchläufen kommt. Ob eine höhere Grenze im Miner Zweige
   entscheidet, die heute offen bleiben, ist eine Betriebsfrage für Ghost – nicht gemessen, nichts verändert.

## Voraussetzungen, falls jemand weiterforscht

* Die Darstellung „Wertemenge je Kästchen" hält keine gemeinsamen Belegungen. Jede Erweiterung, die mehr erreichen
  will, muss sagen, **welche Beziehung** sie zusätzlich hält (Paare, Tripel, Gleichungen, Fallindex) und was das kostet.
  Die exakten Darstellungen (Wahrheitstabellen, Fallvektoren) halten alles – und sind genau das, was sie vermeiden
  sollten: alle Fälle rechnen.
* Jede Aussage über das vollständige SHA256d muss am vollständigen SHA256d gemessen werden. Erfolge an reduzierten
  Modellen sind kein Nachweis für vollständiges SHA256d; das ist hier zweimal vorgeführt (16 Runden ja, 64 Runden nein).
* Referenzwerte nie in das Netz einspeisen. Bekannte Treffer müssen erhalten bleiben. Graphgröße nach dem Aufbau
  mitmessen (Aufbau-Vereinfachung getrennt von Regelpropagation ausweisen).
* Zeiten als Einzelmessungen mit Rechnerangabe. Keine Hochrechnung auf Hardware.

## Was wir nicht behaupten

Weder dass die Kästchenmaschine das Mining beschleunigen kann, noch dass sie es nicht kann – beides ist nicht
gezeigt. Gezeigt sind keine zusätzlichen Noncebits bei den untersuchten vollständigen SHA256d-Fällen mit acht freien Bits; innere Werte werden sehr wohl eingeschränkt. In den fünf reduzierten Kontrollfällen bis 16 Runden wurden alle acht Eingangsbits abgeleitet. Das ist keine Aussage über sämtliche Vorlagen oder Ziele.
