#!/usr/bin/env python3
"""AUSTAUSCHSCHLEIFE E1 <-> E4 (Fable, 2026-10-22), unveraendert aus wurzel_kind2.py herausgeloest (gleiche Regeln/Semantik), als Funktion,
damit der Speicherlebenszyklus (freigeben=True: alten Paarspeicher vor dem naechsten E4-Aufbau freigeben) gegen den alten Stand (freigeben=False)
auf kleinen Faellen verglichen werden kann. Nur Schneiden; Fixpunkt = keine Aenderung in einer vollen Runde; hoechstens 20 Runden (dann OPEN)."""
import time
import sha_ziffern as SZ
from e1_bit import e1_lauf

def austausch(g, inputs, root, d, N, zu, zd, e4_fn, maxp, freigeben, schritt=lambda *a, **k: None, fort=lambda t: None, fehler=lambda *a, **k: None, zaehler=None):
    """Liefert dict(status, d, zd, paare, stat, info4, open_grund). zaehler(d, zd) -> dict fuer Schrittprotokoll (optional)."""
    zd0 = list(zd); paare = None; info4 = {}; status = None; open_grund = None
    stat = dict(austausch=0, e1=0, e4=0, e4_s=0.0, e1_s=0.0, bits_zu_ziffern_schnitte=0, ziffern_zu_bits_schnitte=0)
    for runde in range(1, 21):
        stat['austausch'] = runde; geaendert = False
        for name, bw, zw in zu:
            for j in range(16):
                m = SZ.bits_zu_ziffern(SZ.dom_von(d, bw[2 * j]), SZ.dom_von(d, bw[2 * j + 1]))
                if zd[zw[j]] & m != zd[zw[j]]: zd[zw[j]] &= m; stat['bits_zu_ziffern_schnitte'] += 1; geaendert = True
                if zd[zw[j]] == 0: status = 'WIDERSPRUCH'
        if status == 'WIDERSPRUCH': break
        if freigeben: paare = None                      # alten Paarspeicher (samt Referenz) VOR dem Neuaufbau freigeben; alle Zaehler daraus liegen bereits im Protokoll
        t = time.perf_counter(); fort('Austausch %d: E4' % runde)
        st4, zd_neu, paare, info4 = e4_fn(N, zd, max_runden=200, max_paare=maxp, nachpruefung=True, pruef=lambda r, o: fort('Austausch %d: E4 Runde %d ops %d' % (runde, r, o)))
        stat['e4'] += 1; stat['e4_s'] += time.perf_counter() - t
        np_ = info4.get('nachpruefung_e3')
        if np_ is not None and (np_['geaendert'] or np_['status'] != 'FIXPUNKT'): fehler('Nachpruefung E3 nach E4', nachpruefung=np_)
        if zd_neu != zd: geaendert = True
        zd = zd_neu; del zd_neu
        schritt('Austausch %d E4' % runde, status=st4, runden=info4.get('runden'), tupelops=info4.get('tupelops'), paare=(len(paare) if paare is not None else info4.get('paare')),
                paare_eingeschraenkt=(paare.eingeschraenkt() if paare is not None else None), s=round(time.perf_counter() - t, 2), **(zaehler(d, zd) if zaehler else {}))
        if st4 == 'WIDERSPRUCH': status = 'WIDERSPRUCH'; break
        if st4 != 'FIXPUNKT': status = 'OPEN'; open_grund = dict(e4_status=st4, info=info4); break
        for name, bw, zw in zu:
            for j in range(16):
                b0, b1 = SZ.ziffer_zu_bits(zd[zw[j]])
                for bb, mk in ((bw[2 * j], b0), (bw[2 * j + 1], b1)):
                    alt = SZ.dom_von(d, bb)
                    if alt & mk != alt:
                        neu = SZ.dom_schneiden(d, bb, mk); stat['ziffern_zu_bits_schnitte'] += 1; geaendert = True
                        if neu == 0: status = 'WIDERSPRUCH'
        if status == 'WIDERSPRUCH': break
        t = time.perf_counter(); st1, sw = e1_lauf(g, d); stat['e1'] += 1; stat['e1_s'] += time.perf_counter() - t
        schritt('Austausch %d E1' % runde, status=st1, sweeps=sw, s=round(time.perf_counter() - t, 2), **(zaehler(d, zd) if zaehler else {}))
        if st1 == 'WIDERSPRUCH': status = 'WIDERSPRUCH'; break
        if st1 == 'OFFEN': status = 'OPEN'; open_grund = 'E1 OFFEN (12 Durchlaeufe)'; break
        if not geaendert: status = 'FIXPUNKT'; break
    else:
        status = 'OPEN'; open_grund = '20 Austauschrunden'
    return dict(status=status, d=d, zd=zd, zd0=zd0, paare=paare, stat=stat, info4=info4, open_grund=open_grund)
