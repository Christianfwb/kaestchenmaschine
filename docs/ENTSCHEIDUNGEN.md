# Noch nötige Entscheidungen (vor einer Veröffentlichung)

1. **Gegenprüfung durch Ghost.** Dieses Paket ist ein Entwurf. Ghost hat die Abschlussläufe (Zielhash-Fixpunkt,
   Rundenkurve) und dieses Paket noch nicht geprüft. Vor dem Upload: Prüfung, Korrekturen, Freigabe zu dritt.
2. **Lizenz.** MIT oder Apache-2.0 für Code, CC BY 4.0 für Texte und Daten – oder etwas anderes (`docs/LIZENZ_VORSCHLAG.md`).
3. **Namensnennung.** Wie Christian, Ghost und Claude im Repository genannt werden; ob Ghost und Fable als
   Pseudonyme der Agenten bleiben; Hinweis zu KI-erzeugtem Code.
4. **Miner-Code.** Ob der Graphaufbau allein (bereits enthalten) reicht oder ob Teile des Miners (Suchbaum `search.py`,
   GPU-Kernel) – ohne Betriebs-/RPC-Teile – als eigener Ordner dazukommen. Vorschlag: nicht in dieser Veröffentlichung;
   Verweis in `miner/README.md` genügt.
5. **Frühere Labore.** Ob die Phasen vor dem SHA256d-Teil (2^16-Labor, W7/W8-Caches, Ziel31, Rotationen, Wortregel,
   Zweibit) aufgearbeitet und aufgenommen werden. Aufwand: Berichte sichten, Pfade bereinigen, Disziplin angleichen.
6. **Codeprüfungsbericht zum Miner** (`BERICHT_FABLE_KAESTCHENMINER.md`, Patch 3.1.1/3.1.2 Trefferabsicherung). Enthält
   Zeilenbezüge auf nicht veröffentlichten Code. Vorschlag: nicht aufnehmen oder als gekürzte Zusammenfassung.
7. **`gatter.py` main().** Ältere SAT-Probe mit z3-Abhängigkeit belassen (Originaltreue) oder entfernen (weniger
   Abhängigkeiten). Beeinflusst nichts in der Forschung.
8. **Repositoryname und -beschreibung.** Vorschlag: `kaestchenmaschine` – „Propagation statt Suche auf SHA256d:
   Messungen, Grenzen, Korrekturen". Keine Begriffe wie „Miner", „Durchbruch", „schneller".
9. **Sprache.** Alles ist deutsch. Eine englische Kurzfassung der README (ein Absatz) wäre für GitHub üblich – ja/nein.
10. **Rundenkurve 17–63 vor oder nach der Veröffentlichung.** Es ist die naheliegendste offene Messung (Minuten CPU).
    Vorschlag: nach der Veröffentlichung als erster Folgeeintrag, damit der Stand klar datiert ist.
