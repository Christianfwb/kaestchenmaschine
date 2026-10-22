#!/usr/bin/env python3
"""STUFE 1c – WURZELTEST ARRAY-PAARE, PRUEFSPEICHER REPARIERT (Fable, 2026-10-22). python -I wurzel_kind3.py <E1|E4|E4D> <F1|F2> <ausgabe.json> <paargrenze>
Wie wurzel_kind2.py; Aenderungen NUR: (1) Zeugenpruefung ueber Paarmasken streaming (PaarSpeicher.zeuge_ok, kein dict), (2) Austauschschleife in austausch.py
(unveraenderte Regeln) mit Freigabe des alten Paarspeichers vor dem naechsten E4-Aufbau. Rechenregeln/E1-Code unveraendert.
Eine Wurzelauswertung (8 freie Noncebits, echtes Target gesetzt, U-voll), frischer isolierter Zustand:
  E1  : Bogenkonsistenz auf dem Bitgraphen (12-Durchlauf-Regel).
  E4  : E1 + Ziffernnetz (E3 + kompakte Paarbeziehungen ziffern_komp.e4, nachpruefung) im Austausch (nur Schneiden), bis Fixpunkt oder 20 Runden (dann OPEN).
  E4D : wie E4 plus 32 Dreierbeziehungen an Sigma1(e60) in Runde 60 der zweiten Anwendung (Join XOR/ROT1, erschoepfend geprueft, Traces abgeglichen).
Referenz (FAELLE_SHA256D.json, hashlib) nur als Orakel: Zeuge (F2) in allen Domaenen/Paaren, Ausschluesse gegen Orakel. Keine Referenzwerte in Netze.
Fortschritt nach jedem Schritt in FORTSCHRITT_<...>.json (bei externem Abbruch = OFFEN mit Fortschritt)."""
import sys, json, time, struct, resource, pathlib, platform, hashlib
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent.parent / 'src' / 'kaestchen'))
import sha_ziffern as SZ, ziffern_sha as ZS, ziffern_array as ZA, pruefung as P, gatter as G
from ziffern import TABELLEN, GROESSEN
from e1_bit import e1_lauf
ART, FALL, AUS = sys.argv[1], sys.argv[2], sys.argv[3]; T0 = time.perf_counter(); MAXP = int(sys.argv[4]) if len(sys.argv) > 4 else 2500000
FD = next(F for F in json.loads((HERE / 'FAELLE_SHA256D.json').read_text())['faelle'] if F['name'].startswith(FALL))
h76 = bytes.fromhex(FD['header_hex_ohne_nonce']); T = int(FD['target_hex'], 16); base = FD['basis_nonce']; bits = FD['freie_nonce_bits']
ERG = dict(art=ART, fall=FD['name'], umfang='U-voll', target_nullbits=FD['target_nullbits'], python=platform.python_version(),
           rechner='Fable-Container Linux, Intel Xeon 2.10 GHz (2 Kerne), CPU, reines Python', status='LAEUFT', schritte=[])
def peak(): return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
def speichern(): (HERE / AUS).write_text(json.dumps(ERG, indent=1, default=str))
def fort(t): sys.stderr.write('\r%s %s %s' % (ART, FALL, t[:100].ljust(100))); sys.stderr.flush()
def schritt(name, **k): k.update(name=name, t_s=round(time.perf_counter() - T0, 2), peak_mib=round(peak(), 1)); ERG['schritte'].append(k); speichern(); return k
def ende(status, **k):
    ERG.update(k); ERG['status'] = status; ERG['gesamt_s'] = round(time.perf_counter() - T0, 2); ERG['peak_mib_kind'] = round(peak(), 1); speichern()
    fort('fertig ' + status); sys.stderr.write('\n'); sys.exit(0 if status in ('OK',) else 2)
def fehler(name, **k): schritt('FEHLER ' + name, **k); ende('FEHLER', fehler=dict(name=name, **k))
GRUPPE = [(base & ~0xff) | n for n in range(256)]; TREFFER = set(FD['referenz_treffer'])

# ---------- Aufbau ----------
t = time.perf_counter(); g, inputs, blog, bout, root = SZ.baue_bitgraph(h76, base, bits, T); tb = time.perf_counter() - t
schritt('Aufbau Bitgraph', knoten=len(g.nodes), s=round(tb, 2))
def e1_start():
    d = [3] * len(g.nodes); d[0] = 1; d[1] = 2; SZ.dom_schneiden(d, root, 2); return d
def noncebits_fest(d): return [(i, SZ.dom_von(d, node) >> 1) for i, node in enumerate(inputs) if SZ.dom_von(d, node) in (1, 2)]
def ausgeschlossen_bits(d):
    f = dict(noncebits_fest(d)); return [n for n in GRUPPE if any(((n >> bits[i]) & 1) != v for i, v in f.items())]
def bits_fest_gesamt(d): return sum(1 for x in d[2:] if x in (1, 2))
def zeuge_bits_ok(d):
    if not TREFFER: return None
    z = next(iter(TREFFER)); vals = g.values(z - (base & ~0xff))
    return all((d[i] >> int(vals[i])) & 1 for i in range(2, len(d)))

# ---------- E1 ----------
t = time.perf_counter(); d = e1_start(); st1, sw = e1_lauf(g, d); t1 = time.perf_counter() - t
aus = ausgeschlossen_bits(d)
if any(n in TREFFER for n in aus): fehler('E1 schliesst Referenztreffer aus', ausgeschlossen=aus)
r1 = dict(status=st1, sweeps=sw, s=round(t1, 2), noncebits_abgeleitet=noncebits_fest(d), knoten_fest=bits_fest_gesamt(d), knoten_gesamt=len(g.nodes) - 2,
          ausgeschlossene_nonces_der_gruppe=len(aus), zeuge_in_allen_bitdomaenen=zeuge_bits_ok(d))
schritt('E1 Wurzel (Ziel = 1)', **r1)
if ART == 'E1': ende('OK' if st1 != 'WIDERSPRUCH' or not TREFFER else 'FEHLER', ergebnis=r1)
if st1 == 'WIDERSPRUCH': ende('OK', hinweis='E1 WIDERSPRUCH an der Wurzel (Orakel: Bereich leer) – E4 nicht noetig', ergebnis=r1)

# ---------- Ziffernnetz ----------
t = time.perf_counter(); N, zops, zout, eing, le = SZ.baue_ziffernnetz(h76, base, bits, T, 'voll'); zu = SZ.wortzuordnung(blog, zops)
zu.append(('H1_nonce', tuple(bout['H1_words'][3]), list(zout['H1_words'][3])))
schritt('Aufbau Ziffernnetz', variablen=len(N.dom), beziehungen=len(N.bez), zuordnungen_bit_ziffer=len(zu), s=round(time.perf_counter() - t, 2))

# ---------- Dreier (nur E4D) ----------
if ART == 'E4D':
    RUNDE = 60; e60_bits = bout['H2_trace'][RUNDE - 1][4]        # Register e VOR Runde 60 = e nach Runde 59 (Trace-Index 59), Position 4 = e
    e60 = zout['H2_trace'][RUNDE - 1][4]
    # Woerter der Runde 60 im Protokoll (Phase H2): rot6/rot11/rot25 Nr. RUNDE+1; s1 = xor Nr. 97 + 2*RUNDE (nach 96 xor der Erweiterung)
    def hole(art, nr): return next(w for p, a, n, w in zops.log if p == 'H2' and a == art and n == nr)
    def hole_bits(art, nr): return next(w for p, a, n, w in blog.log if p == 'H2' and a == art and n == nr)
    r6, r11, r25, s = hole('rot6', RUNDE + 1), hole('rot11', RUNDE + 1), hole('rot25', RUNDE + 1), hole('xor', 97 + 2 * RUNDE)
    # Vor-/Nachzustand belegen: r6 ist Umbenennung e60[j+3]; r11/r25 ROT1-Ausgaenge mit Quellen e60[j+5],e60[j+6] bzw. e60[j+12],e60[j+13]; s = (r6 xor r11) xor r25
    assert all(r6[j] == e60[(j + 3) % 16] for j in range(16))
    rot1 = {vs[0]: (vs[1], vs[2]) for typ, vs in N.bez if typ == 'ROT1'}
    assert all(rot1[r11[j]] == (e60[(j + 5) % 16], e60[(j + 6) % 16]) and rot1[r25[j]] == (e60[(j + 12) % 16], e60[(j + 13) % 16]) for j in range(16))
    xor_out = {vs[2]: (vs[0], vs[1]) for typ, vs in N.bez if typ == 'XOR'}
    tt = [xor_out[s[j]][0] for j in range(16)]
    assert all(xor_out[s[j]][1] == r25[j] and xor_out[tt[j]] == (r6[j], r11[j]) for j in range(16))
    # Bitseite: dieselben Woerter im Bitgraphen (Protokollfolge) – e60-Bits stimmen mit rot6-Umbenennung ueberein
    r6b = hole_bits('rot6', RUNDE + 1); assert all(r6b[i] == e60_bits[(i + 6) % 32] for i in range(32))
    # Dreiertabellen erschoepfend aus den Originaltabellen (Join ueber r11 bzw. r25, q frei):
    D1 = sorted({(a, t_, p) for (a, b, t_) in TABELLEN['XOR'] for (dst, p, q) in TABELLEN['ROT1'] if dst == b})     # (r6_j, t_j, p=e60[j+5])
    D2 = sorted({(t_, s_, p) for (t_, b, s_) in TABELLEN['XOR'] for (dst, p, q) in TABELLEN['ROT1'] if dst == b})   # (t_j, s_j, p=e60[j+12])
    assert len(D1) == 32 and len(D2) == 32
    brute = sorted({(a, t_, p) for a in range(4) for p in range(4) for q in range(4) for t_ in range(4) if t_ == a ^ (((p >> 1) & 1) | ((q & 1) << 1))})
    assert brute == D1 and brute == D2
    TABELLEN['D1'] = D1; TABELLEN['D2'] = D2; GROESSEN['D1'] = GROESSEN['D2'] = (4, 4, 4)
    dreier = [('D1', [r6[j], tt[j], e60[(j + 5) % 16]]) for j in range(16)] + [('D2', [tt[j], s[j], e60[(j + 12) % 16]]) for j in range(16)]
    # Abgleich mit konkreten Traces: alle 256 Nonces der Gruppe, Werte aus dem Netz (eine E3-Vorwaertsrunde, Ziel frei) muessen in den Dreiertabellen liegen
    t = time.perf_counter(); fehl = 0
    for n in GRUPPE:
        w3 = struct.unpack('>16I', P.padded(h76 + n.to_bytes(4, 'little'))[64:])[3]; dom = list(N.dom)
        for j, v in enumerate(eing):
            if dom[v] == 15: dom[v] = 1 << ((w3 >> (2 * j)) & 3)
        _, dm, _, _ = ZS.e3(N, dom, nur_eine_runde=True)
        val = lambda v: dm[v].bit_length() - 1 if dm[v] & (dm[v] - 1) == 0 and dm[v] else None
        for typ, vs in dreier:
            tup = tuple(val(v) for v in vs)
            if None in tup or tup not in set(TABELLEN[typ]): fehl += 1
    schritt('Dreier: 32 Beziehungen D1/D2 an Sigma1(e60), Runde 60, 2. Anwendung', tupel_je_tabelle=32, zuordnung_belegt=True, trace_abgleich_nonces=256,
            trace_abgleich_fehler=fehl, s=round(time.perf_counter() - t, 2), variablen=dict(e60=[N.name[v] for v in e60[:2]] + ['...'], t=[N.name[v] for v in tt[:2]] + ['...'], s=[N.name[v] for v in s[:2]] + ['...']))
    if fehl: fehler('Dreier-Traceabgleich', fehler=fehl)
    N.bez.extend(dreier)

# ---------- Zeugenwerte (F2) fuer alle Ziffernvariablen: aus dem Netz selbst (E3 mit Zeugen-Nonce fest, Ziel frei – in Stufe 0 gegen Referenz belegt) ----------
zeuge_val = None
if TREFFER:
    z = next(iter(TREFFER)); w3 = struct.unpack('>16I', P.padded(h76 + z.to_bytes(4, 'little'))[64:])[3]; dom = list(N.dom)
    for j, v in enumerate(eing):
        if dom[v] == 15: dom[v] = 1 << ((w3 >> (2 * j)) & 3)
    stz, dz, _, _ = ZS.e3(N, dom)
    if stz != 'FIXPUNKT' or any(m & (m - 1) or m == 0 for m in dz): fehler('Zeugenwerte nicht bestimmbar', status=stz)
    zeuge_val = [m.bit_length() - 1 for m in dz]
    hz = struct.pack('>8I', *[sum(zeuge_val[v] << (2 * j) for j, v in enumerate(w)) for w in zout['digest2']])
    if hz != hashlib.sha256(hashlib.sha256(h76 + z.to_bytes(4, 'little')).digest()).digest(): fehler('Zeugen-Digest != hashlib')
    if zeuge_val[le] != 1: fehler('Zeuge erfuellt LE-Kette nicht')
def zeuge_ziffern_ok(dom, paare):
    if zeuge_val is None: return None, None
    d_ok = all((dom[v] >> zeuge_val[v]) & 1 for v in range(len(dom)))
    p_ok = paare.zeuge_ok(zeuge_val)[0] if paare is not None else None      # Streaming ueber keys/masks, kein dict (Reparatur 2026-10-22)
    return d_ok, p_ok
def ziffern_fest(dom): return [(j, dom[v].bit_length() - 1) for j, v in enumerate(eing) if N.dom[v] == 15 and dom[v] & (dom[v] - 1) == 0]
def noncebits_aus_ziffern(dom):
    out = []
    for j, v in enumerate(eing):
        if N.dom[v] != 15: continue
        b0, b1 = SZ.ziffer_zu_bits(dom[v])
        for k, bm in ((0, b0), (1, b1)):
            if bm in (1, 2): out.append((j, k, bm >> 1))
    return out
def ausgeschlossen_ziffern(dom):
    out = []
    for n in GRUPPE:
        w3 = struct.unpack('>16I', P.padded(h76 + n.to_bytes(4, 'little'))[64:])[3]
        if any(not (dom[v] >> ((w3 >> (2 * j)) & 3)) & 1 for j, v in enumerate(eing)): out.append(n)
    return out
def eingeschraenkt(dom, ref): return sum(1 for a, b in zip(dom, ref) if a != b)

# ---------- Austausch E1 <-> E4 (austausch.py, Speicherlebenszyklus: alten Paarspeicher vor Neuaufbau freigeben) ----------
from austausch import austausch
zd = list(N.dom); zd[le] &= 2
def zaehler(d_, zd_): return dict(noncebits=noncebits_fest(d_), knoten_fest=bits_fest_gesamt(d_), nonceziffern_fest=ziffern_fest(zd_), noncebits_aus_ziffern=noncebits_aus_ziffern(zd_))
R = austausch(g, inputs, root, d, N, zu, zd, ZA.e4, MAXP, True, schritt=schritt, fort=fort, fehler=fehler, zaehler=zaehler)
status, d, zd, zd0, paare, stat, info4 = R['status'], R['d'], R['zd'], R['zd0'], R['paare'], R['stat'], R['info4']
if R['open_grund'] is not None: ERG['open_grund'] = R['open_grund']
# ---------- Abschluss, Pruefungen gegen Orakel ----------
aus_b = ausgeschlossen_bits(d) if status != 'WIDERSPRUCH' else list(GRUPPE); aus_z = ausgeschlossen_ziffern(zd) if status != 'WIDERSPRUCH' else list(GRUPPE)
if any(n in TREFFER for n in set(aus_b) | set(aus_z)): fehler('Ausschluss trifft Referenztreffer', bits=aus_b[:10], ziffern=aus_z[:10])
zd_ok, zp_ok = zeuge_ziffern_ok(zd, paare) if status != 'WIDERSPRUCH' else (None, None)
if TREFFER and status == 'WIDERSPRUCH': fehler('WIDERSPRUCH an der Wurzel trotz Referenztreffer')
if TREFFER and (zd_ok is False or zp_ok is False or zeuge_bits_ok(d) is False): fehler('Zeuge verloren', ziffern=zd_ok, paare=zp_ok, bits=zeuge_bits_ok(d))
ERG['ergebnis'] = dict(status=status, austauschrunden=stat['austausch'], e1_aufrufe=stat['e1'], e4_aufrufe=stat['e4'], e1_s=round(stat['e1_s'], 2), e4_s=round(stat['e4_s'], 2),
    schnitte_bits_zu_ziffern=stat['bits_zu_ziffern_schnitte'], schnitte_ziffern_zu_bits=stat['ziffern_zu_bits_schnitte'],
    noncebits_abgeleitet_bitgraph=noncebits_fest(d), noncebits_abgeleitet_ziffern=noncebits_aus_ziffern(zd), nonceziffern_fest=ziffern_fest(zd),
    ausgeschlossene_nonces_bitgraph=len(aus_b), ausgeschlossene_nonces_ziffern=len(aus_z), ausgeschluss_gegen_orakel_ok=True,
    interne_einschraenkungen=dict(bitknoten_fest=bits_fest_gesamt(d), bitknoten_gesamt=len(g.nodes) - 2, ziffernvariablen_eingeschraenkt_gegen_start=eingeschraenkt(zd, zd0),
                                  ziffernvariablen_gesamt=len(zd), paare=(len(paare) if paare is not None else info4.get('paare')), paare_eingeschraenkt=(paare.eingeschraenkt() if paare is not None else None),
                                  speicher_paare_mib=(round(paare.bytes_gesamt() / 2**20, 1) if paare is not None else None)),
    zeuge=dict(in_allen_ziffern=zd_ok, in_allen_paaren=zp_ok, in_allen_bits=zeuge_bits_ok(d)), e4_letzte_info=info4, paargrenze=MAXP)
ende('OK', hinweis='Status %s; "OK" = Auswertung sauber beendet, nicht "Ableitung gefunden"' % status)
