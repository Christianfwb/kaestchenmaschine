# Veröffentlichungsstand und offene Entscheidungen

Das Repository ist öffentlich. Der erste Stand `3d9a0f3` wurde am 23. Oktober 2026 von Ghost gelesen und punktuell unter Windows geprüft. Ergebnisse, konkrete Korrekturen und Grenzen der Prüfung stehen im [Prüfbericht](REVIEW_20261023.md). Dies ist keine vollständige unabhängige Wiederholung aller Forschungsreihen.

Noch offen:

1. **Lizenz:** Christian muss die Bedingungen für Code, Texte und Daten festlegen. [Vorschlag](LIZENZ_VORSCHLAG.md); noch keine LICENSE-Datei, keine Lizenzfreigabe durch diesen Dokumentationspatch.
2. **Miner-Code:** Das öffentliche Paket enthält den Forschungsteil. GPU-Kernel, Node-, Wallet- und Einreichungslogik sind nicht enthalten. [Abgrenzung](../miner/README.md).
3. **Frühere Labore:** M4, Wortregel, kompakte Zustände und weitere Vorarbeiten können später mit vollständigen Belegen ergänzt werden.
4. **Weitere Messungen:** 17–63 Runden, mehr freie Bits, andere Vorlagen und ein fairer Vorratsvergleich bleiben offen. [Forschungsfragen](OFFENE_FRAGEN.md). Es gibt keinen automatischen Folgeauftrag.
5. **Historische SAT-Probe:** `gatter.py` enthält eine ältere optionale `experiment`-Funktion mit z3. Sie gehört nicht zu den dokumentierten Propagationsläufen und wird von den Beispielen nicht aufgerufen.

Beiträge und Fehlermeldungen: [CONTRIBUTING.md](../CONTRIBUTING.md).
