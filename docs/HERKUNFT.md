# Herkunft: Verknüpfung mit den abgelieferten Paketen (Postfach Fable → Ghost)

Jedes Experiment wurde als Paket mit `SHA256SUMS.txt` an Ghost übergeben. Die Tabelle zeigt je Paket, wie viele seiner Dateien
**byte-identisch** in diesem Veröffentlichungspaket liegen, welche verändert wurden (und warum) und welche nicht übernommen sind.
Ghosts Gegenprüfung der Pakete ist – soweit sie erfolgt ist – in dessen Antworten festgehalten, nicht hier; für die beiden letzten
Pakete (ZIELHASH_VERSUCH, ABSCHLUSS_ZIELHASH_RUNDEN) **steht sie noch aus**.

Bekannte, beabsichtigte Änderungen: (1) alle Experimentskripte: eine Zeile, die zusätzlich `../../src/kaestchen` auf den Suchpfad
setzt; (2) `FAELLE_SHA256D.json`: lokaler Windows-Pfad im Feld `quelle.source` entfernt, Rechendaten unverändert; (3) `DIFF_*.txt`:
Containerpfade in den Kopfzeilen gekürzt; (4) ältere Fassungen gleichnamiger Dateien (z. B. `ziffern_sha.py` vor U5,
`sha_ziffern.py` vor dem Rundenparameter) sind durch die jeweils letzte Fassung ersetzt – die Diffs dokumentieren die Schritte.

| Paket | identisch | verändert | nicht übernommen | veränderte Dateien |
|---|---|---|---|---|
| FABLE_AN_GHOST_ABSCHLUSS_ZIELHASH_RUNDEN_20261023 | 25 | 3 | 0 | FAELLE_SHA256D.json, runden_kind.py, zielhash_kind.py |
| FABLE_AN_GHOST_ARRAY_PAARE_WURZEL_20261022 | 21 | 9 | 0 | ERGEBNIS_GATE_TEST.json, FAELLE_SHA256D.json, array_kind.py, gate_test.py, sha_ziffern.py, wurzel_kind.py, wurzel_kind2.py, ziffern_array.py, ziffern_komp.py |
| FABLE_AN_GHOST_DIREKT_20261020_1910 | 0 | 0 | 8 |  |
| FABLE_AN_GHOST_DIREKT_PLAN_20261020_1845 | 0 | 0 | 1 |  |
| FABLE_AN_GHOST_DISKUSSION_ANTWORT_20261022 | 0 | 1 | 0 | BERICHT.txt |
| FABLE_AN_GHOST_DISKUSSION_ERSTMEINUNG_20261022 | 0 | 1 | 0 | BERICHT.txt |
| FABLE_AN_GHOST_EINBIT_GEGENPRUEFUNG_20261022 | 21 | 3 | 0 | FAELLE_SHA256D.json, einbit_kind.py, sha_ziffern.py |
| FABLE_AN_GHOST_F2_ABSCHLUSS_UND_DREIER_20261022 | 21 | 10 | 0 | DIFF_gate_test.txt, DIFF_ziffern_array_zeuge_ok.txt, FAELLE_SHA256D.json, gate_test.py, lauf_wurzel3.py, pruefspeicher_test.py, sha_ziffern.py, wurzel_kind2.py, wurzel_kind3.py, ziffern_komp.py |
| FABLE_AN_GHOST_GEKOPPELTE_2BIT_PLAN_20261022 | 0 | 1 | 0 | BERICHT.txt |
| FABLE_AN_GHOST_GEKOPPELTE_2BIT_TEST_20261022 | 3 | 2 | 16 | lauf_2bit.py, ziffern.py |
| FABLE_AN_GHOST_KAESTCHENMINER_AUDIT_20261022_0830 | 0 | 0 | 1 |  |
| FABLE_AN_GHOST_KOMPAKT_20261020_1905 | 0 | 0 | 8 |  |
| FABLE_AN_GHOST_KOMPAKT_ABLAUFKORREKTUR_20261020_1850 | 0 | 0 | 5 |  |
| FABLE_AN_GHOST_KOMPOSITION_UND_GEDAECHTNIS_20261022 | 17 | 5 | 0 | FAELLE_SHA256D.json, dreier_beispiel.py, komposition_kind.py, sha_ziffern.py, ziffern_komp.py |
| FABLE_AN_GHOST_M4_VERGLEICH_20261022 | 5 | 0 | 9 |  |
| FABLE_AN_GHOST_NACHPRUEFUNG_20261022_0945 | 0 | 1 | 2 | BERICHT.txt |
| FABLE_AN_GHOST_PATCH_312_20261022 | 0 | 0 | 18 |  |
| FABLE_AN_GHOST_PHASENVERGLEICH_20261022 | 10 | 3 | 0 | FAELLE_SHA256D.json, phasen_kind.py, sha_ziffern.py |
| FABLE_AN_GHOST_PLAN_ECHTER_SHA256D_20261022 | 0 | 2 | 0 | BERICHT.txt, FAELLE_SHA256D.json |
| FABLE_AN_GHOST_PLAN_ZIELHASH_20261022 | 2 | 1 | 0 | FAELLE_SHA256D.json |
| FABLE_AN_GHOST_PRAEZISIERUNG_REICHWEITE_20261022 | 2 | 1 | 0 | reichweite.py |
| FABLE_AN_GHOST_REICHWEITE_UND_AUFFRISCHER_20261022 | 13 | 4 | 0 | DIFF_ziffern_komp_start_paare.txt, FAELLE_SHA256D.json, reichweite.py, sha_ziffern.py |
| FABLE_AN_GHOST_ROTATIONEN_KOMBINATION_PLAN_20261022 | 1 | 1 | 3 | ziffern.py |
| FABLE_AN_GHOST_RUECKWAERTS_FORSCHUNGSPLAN_20261022 | 0 | 1 | 1 | BERICHT.txt |
| FABLE_AN_GHOST_SHA256D_STUFE0_20261022 | 19 | 5 | 0 | DIFF_ziffern_zu_ziffern_sha.txt, FAELLE_SHA256D.json, sha_ziffern.py, stufe0_kind.py, ziffern_sha.py |
| FABLE_AN_GHOST_TABELLEN4_ZWEIBIT_20261022 | 8 | 3 | 0 | FAELLE_SHA256D.json, sha_ziffern.py, tabellen4_kind.py |
| FABLE_AN_GHOST_TREFFERABSICHERUNG_20261022_0900 | 0 | 0 | 7 |  |
| FABLE_AN_GHOST_V311_UND_LEISTUNGSIDEEN_20261022_1100 | 0 | 1 | 3 | BERICHT.txt |
| FABLE_AN_GHOST_W7_DIREKT_20261020_1930 | 0 | 0 | 9 |  |
| FABLE_AN_GHOST_W7_DIREKT_PLAN_20261020_1915 | 0 | 0 | 1 |  |
| FABLE_AN_GHOST_W7_LAEUFERKORREKTUR_20261022_0750 | 0 | 0 | 10 |  |
| FABLE_AN_GHOST_WORTREGEL_PLAN_20261022 | 0 | 1 | 0 | BERICHT.txt |
| FABLE_AN_GHOST_WORTREGEL_STUFE_A_20261022 | 3 | 0 | 6 |  |
| FABLE_AN_GHOST_WURZELTEST_20261022 | 17 | 4 | 0 | FAELLE_SHA256D.json, sha_ziffern.py, wurzel_kind.py, ziffern_komp.py |
| FABLE_AN_GHOST_XOR_BEISPIEL_20261022 | 10 | 2 | 0 | sha_ziffern.py, xor_beispiel.py |
| FABLE_AN_GHOST_XOR_SHA_ANALYSE_20261022 | 17 | 3 | 0 | FAELLE_SHA256D.json, sha_ziffern.py, xor_sha_kind.py |
| FABLE_AN_GHOST_ZIELHASH_VERSUCH_20261022 | 18 | 3 | 0 | FAELLE_SHA256D.json, sha_ziffern.py, zielhash_kind.py |
| FABLE_AN_GHOST_ZWEIBIT_E1_GEGEN_E4_20261022 | 22 | 3 | 0 | FAELLE_SHA256D.json, mehrbit_kind.py, sha_ziffern.py |

"identisch" = derselbe Inhalt (gleicher SHA-256) liegt in diesem Paket, ggf. unter anderem Namen (Berichte wurden beim Ablegen
nach Thema benannt). "nicht übernommen" betrifft Pakete vor dem SHA256d-Teil (Kompakt, W7, Wortregel, Rotationen, Miner-Audit,
Patches, Diskussionsantworten) - siehe ENTSCHEIDUNGEN.md.

## Nachtrag: öffentliche Repository-Prüfung

Die Tabelle oben beschreibt die erste Paketfassung. Spätere Code- und Dokumentationskorrekturen sind in [REVIEW_20261023.md](REVIEW_20261023.md) und der Git-Historie nachvollziehbar. Historische Ergebnisse wurden nicht umgeschrieben. Aktuelle Dateiprüfsummen stehen in [SHA256SUMS.txt](../SHA256SUMS.txt).
