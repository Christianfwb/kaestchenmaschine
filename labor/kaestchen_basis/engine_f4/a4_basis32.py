#!/usr/bin/env python3
"""A4-BASISTEST (Ghost 20261031T112532Z A4-BASIS-01..06, Christians GO): genau EIN verdecktes Noncebit an H970000.

Dieses Modul enthaelt den gemeinsamen AUFBAU der Aufgabe (fuer Loeser UND Vertrag der Pruefstelle - beide kennen das verdeckte
Bit nicht) und die LOESERSEITE (eigener Prozess). Der Loeser importiert nie pruefstelle32/sha256_ref/ghost_sha_reference/hashlib.

AUFGABE.json (nur Eingaben):
  art 'A4', header76_hex, basis (Nonce-Integer mit verdecktem Bit auf 0), maske (Bitmaske der verdeckten Noncebits),
  arm 'W' (ziel_hash_hex = exakter Wunschhash, 32 Bytes in Digest-Reihenfolge) oder 'M' (nbits).
Verdecktes Noncebit j liegt in Block-1-Wort W3 an Bit 8*(3 - j//8) + j%8 (little-endian Nonce als big-endian Wort).
Reine Propagation bis Fixpunkt oder Grenze; kein Ausprobieren der Belegungen, keine Fallaufspaltung."""
import sys, json, time
import bitkern32 as bk
import sha_verdrahtung32 as sv


def w3_bit(j): return 8 * (3 - j // 8) + j % 8


def aufbau(kern, aufgabe):
    """Verdrahtet die Aufgabe ohne Kenntnis der verdeckten Bits. Liefert (H2-Wortnamen, Namen der verdeckten W3-Bits, Zielbitname)."""
    header76 = bytes.fromhex(aufgabe['header76_hex']); basis = aufgabe['basis']; maske = aufgabe['maske']
    iv = sv.konstanten_woerter(kern, 'k0', 'IV', sv.IV, 'IV')
    W0 = sv.konstanten_woerter(kern, 'k0', 'W', sv.woerter_aus_bytes(header76[:64]), 'HEADER')
    H0, _, _ = sv.kompression(kern, 'k0', iv, W0, start_konst=sv.IV)
    W1 = sv.konstanten_woerter(kern, 'k1', 'W', sv.woerter_aus_bytes(header76[64:76]), 'HEADER')
    # W3: bekannte Noncebits per B-R1 aus dem maskierten Basiswort (START AUFGABE); verdeckte Bits bleiben Unbekannte
    # (kein START, kein B-R1, kein Wert). Der Kern merkt sich die verdeckten Namen; der Vertrag traegt sie als Sperrliste.
    w3_basis = int.from_bytes((basis & ~maske & 0xffffffff).to_bytes(4, 'little'), 'big')
    nr = kern.buche('START AUFGABE', [], 'WORT', ('k1_W3', w3_basis, 32))
    kern.worte['k1_W3'] = nr
    verdeckt = []
    for j in range(32):
        pos = w3_bit(j)
        if (maske >> j) & 1:
            verdeckt.append(f"k1_W3.{pos}")
        else:
            kern.setze(f"k1_W3.{pos}", (w3_basis >> pos) & 1, f"B-R1 k1_W3 bit {pos}", [nr])
    kern.verdeckt = set(verdeckt)
    W1.append('k1_W3')
    W1 += sv.konstanten_woerter(kern, 'k1', 'P', sv.PAD1, 'PAD')
    H1, _, _ = sv.kompression(kern, 'k1', H0, W1)
    iv2 = sv.konstanten_woerter(kern, 'k2', 'IV', sv.IV, 'IV')
    W2 = H1 + sv.konstanten_woerter(kern, 'k2', 'P', sv.PAD2, 'PAD')
    H2, _, _ = sv.kompression(kern, 'k2', iv2, W2, start_konst=sv.IV)
    hb = sv.hash_zahl_bits(H2)                       # Bit i der Zahl H (Digest little-endian)
    if aufgabe['arm'] == 'W':
        Z = int.from_bytes(bytes.fromhex(aufgabe['ziel_hash_hex']), 'little')
        nrz = kern.buche('START ZIEL', [], 'WORT', ('ZIELHASH', Z, 256)); kern.worte['ZIELHASH'] = nrz
        for i in range(256):                          # Zielgleichung: H-Bit i = Zielbit i (eine Unbekannte, Paritaet = Zielbit)
            kern.xor_gl([hb[i]], (Z >> i) & 1, f"B-R4 Ziel W bit {i}", [nrz])
        zielbit = None
    else:
        T = aufgabe['nbits_ziel']                     # Ganzzahl-Ziel aus nBits (vom Aufgabensteller vorgerechnet, Teil der Aufgabe)
        zielbit = kern.vergleich(hb, T, 256, praefix='V')
        kern.xor_gl([zielbit], 1, 'B-R4 Ziel M treffer', [])
    return H2, verdeckt, zielbit


def lauf(aufgabe, buchpfad):
    """Nur im Loeserprozess: Referenzmodule duerfen nicht geladen sein (aufbau() allein darf die Pruefstelle fuer den Vertrag nutzen)."""
    for verboten in ('pruefstelle32', 'sha256_ref', 'ghost_sha_reference', 'hashlib', 'a4_lauf32'):
        assert verboten not in sys.modules, verboten
    t0 = time.time()
    erg = {'art': 'A4', 'arm': aufgabe['arm'], 'maske': aufgabe['maske'], 'status': None, 'fehler': None, 'linearformen': bool(aufgabe.get('linearformen'))}
    verdeckt_vorab = [f"k1_W3.{w3_bit(j)}" for j in range(32) if (aufgabe['maske'] >> j) & 1]
    k = bk.KernLF(32, verdeckt=verdeckt_vorab) if aufgabe.get('linearformen') else bk.Kern(32)
    try:
        H2, verdeckt, zielbit = aufbau(k, aufgabe)
        erg['verdeckte_bits'] = verdeckt
        erg['vorher'] = {'bekannte_noncebits': 32 - bin(aufgabe['maske']).count('1'), 'C': 'alle 2^k', 'bits_bekannt': len(k.wert)}
        k.fixpunkt()
        werte = {v: k.bit(v) for v in verdeckt}
        erg['nachher'] = {'verdeckte_bits': werte, 'bits_bekannt': len(k.wert), 'groesse': k.groesse(), 'zaehler': dict(k.zb)}
        # Kandidatenmenge C ueber die verdeckten Bits (Nonce-Belegungen), nur aus bestimmten Bits, keine Aufspaltung
        if any(v is None for v in werte.values()):
            erg['status'] = 'OFFEN'; erg['C'] = 'unbestimmt: alle Belegungen der unbestimmten Bits bleiben Kandidaten'
            erg['T'] = []
        else:
            erg['status'] = 'BESTIMMT'; erg['T'] = [werte]
            erg['belege'] = {v: {'buch': k.her[v], 'regel': k.buch[k.her[v]][0], 'eltern': list(k.buch[k.her[v]][1])} for v in verdeckt}
        # Wissen entlang der Strecke (Messung): bestimmte Bits je Wortgruppe
        def bestimmt(praefix, n): return sum(1 for j in range(n) for i in range(32) if k.bit(f"{praefix}{j}.{i}") is not None)
        erg['wissen'] = {'k1_W16..63': sum(1 for j in range(16, 64) for i in range(32) if k.bit(f"k1_W{j}.{i}") is not None),
                         'k1_W3': sum(1 for i in range(32) if k.bit(f"k1_W3.{i}") is not None),
                         'k1_H': bestimmt('k1_H', 8), 'k2_H': bestimmt('k2_H', 8),
                         'k1_a1..64': sum(1 for t in range(1, 65) for i in range(32) if k.bit(f"k1_a{t}.{i}") is not None),
                         'k2_a1..64': sum(1 for t in range(1, 65) for i in range(32) if k.bit(f"k2_a{t}.{i}") is not None)}
        if zielbit: erg['wissen']['V_treffer'] = k.bit(zielbit)
        if aufgabe.get('linearformen'):
            # M1: Bits mit Form, die ein verdecktes Bit enthaelt, je Abschnitt; M2: Bindungen; M3: Beziehungen/Pivots; M4: Herkunft des Werts
            vx = set(verdeckt)
            # M1 aus dem BUCH: Bits, die irgendwann eine Form mit einem verdeckten Bit trugen ("wie weit trug x"), unabhaengig von spaeterer Aufloesung
            trug = set()
            for regel, eltern, art, info in k.buch:
                if art == 'FORM' and set(info[2]) & vx: trug.add(info[0])
            def traegt(praefix, n, start=0):
                return sum(1 for j in range(start, n) for i in range(32) if f"{praefix}{j}.{i}" in trug)
            m1 = {'k1_W3': sum(1 for i in range(32) if f"k1_W3.{i}" in trug),
                  'k1_W16..63': traegt('k1_W', 64, 16), 'k1_H': traegt('k1_H', 8), 'k2_W16..63': traegt('k2_W', 64, 16), 'k2_H': traegt('k2_H', 8),
                  'k1_a_je_runde': [sum(1 for i in range(32) if f"k1_a{t}.{i}" in trug) for t in range(1, 65)],
                  'k2_a_je_runde': [sum(1 for i in range(32) if f"k2_a{t}.{i}" in trug) for t in range(1, 65)],
                  'V_kette': sum(1 for n in trug if n.startswith('V_')), 'bits_mit_x_form_gesamt': len(trug)}
            m2 = {'bindungen_h': len(k.bindung), 'bindungen_bestimmt': sum(1 for h, _ in k.bindung.values() if h in k.u_wert)}
            erste = next((b for b in k.buch if b[2] == 'BINDUNG'), None)
            if erste:
                tnr = erste[3][1]; t_regel = k.buch[tnr][0]; t_namen = k.buch[tnr][3][1]
                m2['erste_bindung'] = {'h': erste[3][0], 'tabelle_buch': tnr, 'tabelle_regel': t_regel, 'namen': list(t_namen),
                                       'eingangsformen': [[n, (k.lesart(n)[0], sorted(k.lesart(n)[1])) if k.lesart(n) else None] for n in t_namen[:-1]]}
                # Herkunft der Instanz: Addition Ak -> Wortgleichung
                if t_regel.startswith('B-R5') or t_regel.startswith('B-R6'):
                    kid = t_regel.split()[1]; m2['erste_bindung']['addition'] = str(k.additionen[kid][1]) if kid in k.additionen else '?'
                m2['bindungen_je_abschnitt'] = {}
                for b in k.buch:
                    if b[2] == 'BINDUNG':
                        reg = k.buch[b[3][1]][0]; nm = k.buch[b[3][1]][3][1][-1]
                        key = nm.split('_')[0] + '_' + nm.split('_')[1].rstrip('0123456789.') if '_' in nm else nm
                        m2['bindungen_je_abschnitt'][key] = m2['bindungen_je_abschnitt'].get(key, 0) + 1
            m3 = {'beziehungen': k.zb['beziehungen'], 'pivotschritte': k.zb['pivotschritte'], 'abgleiche': k.zb['abgleiche'], 'formen_gebucht': k.zb['formen'], 'formen_aktiv': len(k.form), 'pivots_offen': len(k.pivot)}
            m4 = {}
            for xname in verdeckt:
                if xname in k.wert:
                    nr = k.her[xname]; kette = [nr]
                    while True:
                        regel, eltern, art, info = k.buch[kette[-1]]
                        if art == 'BEZIEHUNG' and regel == 'L-R4 pivot': kette.append(eltern[0]); continue
                        if art == 'BIT' and regel == 'L-R4 wert': kette.append(eltern[0]); continue
                        break
                    regel, eltern, art, info = k.buch[kette[-1]]
                    quelle = regel
                    if '[' in regel:
                        q = int(regel.split('[')[-1].rstrip(']')); quelle += ' <- ' + k.buch[q][0]
                    m4[xname] = {'wert': k.wert[xname], 'beleg': nr, 'ursprung': quelle, 'kettenlaenge': len(kette)}
            erg['messung'] = {'M1_formen_mit_x': m1, 'M2_bindungen': m2, 'M3_beziehungen': m3, 'M4_herkunft_des_werts': m4}
    except bk.Widerspruch as e:
        erg['status'] = 'WIDERSPRUCH'; erg['fehler'] = str(e); erg['T'] = []
    except bk.Budget as e:
        erg['status'] = 'OFFEN'; erg['fehler'] = 'Budget: ' + str(e); erg['T'] = []
    except MemoryError:
        erg['status'] = 'OFFEN'; erg['fehler'] = 'Speichergrenze'; erg['T'] = []
    erg['zeit_s'] = round(time.time() - t0, 2)
    with open(buchpfad, 'w') as f:
        for regel, eltern, art, info in k.buch:
            f.write(json.dumps([regel, list(eltern), art, info]) + '\n')
    return erg


if __name__ == '__main__':
    aufgabe = json.load(open(sys.argv[1]))
    erg = lauf(aufgabe, sys.argv[3])
    json.dump(erg, open(sys.argv[2], 'w'))
    print(erg['status'], erg['zeit_s'], 's')
