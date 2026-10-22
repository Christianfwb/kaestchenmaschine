# Abgrenzung: der Kästchenminer

Der laufende Kästchenminer (Christians Windows-Rechner, GPU, Bitcoin-Node) ist **nicht** Teil dieses Pakets. Er wurde
während der gesamten Forschung nicht angefasst: kein Stop, kein Neustart, keine Änderung, keine GPU-Last, keine
Node-Abfragen, keine Einreichung. Alle Experimente liefen auf Kopien, offline, auf der CPU eines anderen Rechners.

Was der Miner tut (nach Codeprüfung vom 22.10.2026, nicht veröffentlichter Code):
* baut je Blockvorlage denselben Bitgraphen wie `src/kaestchen/gatter.py` (Midstate als Konstante, 32 Noncebits als
  Eingänge, Wurzel „Hash ≤ Ziel"),
* teilt den Noncebereich in Gruppen zu 256 (8 freie Bits) und diese in einen Baum nach dem niedrigsten freien Bit,
* lässt die Bitregel E1 auf der GPU je Zweig vorwärts und rückwärts laufen, höchstens 12 Durchläufe
  (Status 0 offen, 1 Fixpunkt, 2 Widerspruch); „offen" wird nie als ausgeschlossen gewertet,
* prüft vollständig bestimmte Zeugen am Graphen, an den Kästchen und unabhängig mit hashlib-SHA256d,
* reicht Blöcke nur über eine gesonderte, abgesicherte Betriebsschicht ein (nicht enthalten).

Was die Forschung für den Miner bedeutet (Stand 23.10.2026): Am vollständigen SHA256d schließt keine der untersuchten
Regelerweiterungen zusätzliche Nonces aus; der Miner arbeitet damit faktisch als Prüfer von 256er-Gruppen, dessen
Ausschlusswirkung bei 8 freien Bits null ist. Ein Suchvorteil gegenüber normalem Hashen ist nicht belegt. Ein gültiger
Mainnet-Block wurde nicht gefunden. Die einzige Betriebsfrage, die aus der Forschung folgt (E1-Durchlaufgrenze 12 gegen
Fixpunkt bei 41 im Zielhash-Fall), ist nicht gemessen und wird hier nur benannt.

Ob Teile des Miner-Codes später veröffentlicht werden, ist eine offene Entscheidung (`docs/ENTSCHEIDUNGEN.md`, Punkt 4).
