# Veröffentlichungsstand und offene Entscheidungen

Das Repository ist öffentlich. Der erste Stand `3d9a0f3` wurde am 23. Oktober 2026 von Ghost gelesen und punktuell unter Windows geprüft. Ergebnisse, konkrete Korrekturen und Grenzen der Prüfung stehen im [Prüfbericht](REVIEW_20261023.md). Dies ist keine vollständige unabhängige Wiederholung aller Forschungsreihen.

Entscheidungen und verbleibende offene Punkte:

1. **Lizenz entschieden (23.10.2026):** MIT für eigenen Code, Dokumentation und eigene Ergebnisse. [Lizenz](../LICENSE), [Herkunftshinweise](LIZENZ_VORSCHLAG.md).
2. **Miner-Code:** Das öffentliche Paket enthält den Forschungsteil. GPU-Kernel, Node-, Wallet- und Einreichungslogik sind nicht enthalten. [Abgrenzung](../miner/README.md).
3. **Frühere Labore:** M4, Wortregel, kompakte Zustände und weitere Vorarbeiten können später mit vollständigen Belegen ergänzt werden.
4. **Weitere Messungen:** 17–63 Runden, mehr freie Bits, andere Vorlagen und ein fairer Vorratsvergleich bleiben offen. [Forschungsfragen](OFFENE_FRAGEN.md). Es gibt keinen automatischen Folgeauftrag.
5. **Historische SAT-Probe:** `gatter.py` enthält eine ältere optionale `experiment`-Funktion mit z3. Sie gehört nicht zu den dokumentierten Propagationsläufen und wird von den Beispielen nicht aufgerufen.

Beiträge und Fehlermeldungen: [CONTRIBUTING.md](../CONTRIBUTING.md).
