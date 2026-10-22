#!/usr/bin/env python3
"""EIN-BIT-GEGENPRUEFUNG, KINDPROZESS (Fable, 2026-10-22). python -I einbit_kind.py <F1|F2> <E3|E3Z|E4|E4Z> <ausgabe.json> [maxpaare]
Ein freies Noncebit (Bit 0) -> genau ZWEI Eingaben. Varianten: E3 / E3Z (mit Zielbedingung) / E4 = E1+E4 / E4Z (mit Zielbedingung).
Referenz: beide vollstaendigen Zustaende, getrennt vorwaerts ausgewertet (Nonce fest), Digest gegen hashlib geprueft. Die Referenz
wird AUSSCHLIESSLICH nach Abschluss der Propagation gelesen; kein Referenzwert geht in Domaenen, Paare oder Verzweigung ein.
Massgeblich: ohne Ziel beide Zustaende, mit Ziel nur die, deren Hash <= Target (keiner -> unloesbarer Referenzfall, ausgewiesen).
Messstellen je Runde beider Anwendungen: Register a..h, S1, S0, Ch, Maj, T1, T2 (14 je Runde). Je Messstelle getrennt:
Einzelwerte (Zifferndomaenen) und Paarbeziehungen (nur TATSAECHLICH gespeicherte Paare; fehlende gesondert gezaehlt)."""
import sys, json, time, struct, hashlib, resource, pathlib, platform
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent.parent / 'src' / 'kaestchen'))
import sha_ziffern as SZ, ziffern_sha as ZS, ziffern_array as ZA, pruefung as P, gatter as G
from e1_bit import e1_lauf
from austausch import austausch
FALL, VAR, AUS = sys.argv[1], sys.argv[2], sys.argv[3]; MAXP = int(sys.argv[4]) if len(sys.argv) > 4 else 2500000
T0 = time.perf_counter()
FD = next(F for F in json.loads((HERE / 'FAELLE_SHA256D.json').read_text())['faelle'] if F['name'].startswith(FALL))
h76 = bytes.fromhex(FD['header_hex_ohne_nonce']); T = int(FD['target_hex'], 16)
BASIS = (FD['referenz_treffer'][0] & ~1) if FD['referenz_treffer'] else 0      # F2: der bekannte Treffer liegt in der Gruppe
BITS = [0]; NONCEN = [BASIS, BASIS | 1]
MIT_ZIEL = VAR.endswith('Z'); MIT_PAARE = VAR.startswith('E4')
ERG = dict(fall=FD['name'], variante=VAR, mit_zielbedingung=MIT_ZIEL, regeln=('E1 (Bitgraph) + E3/E4 (Ziffern, Paare Radius 1), Austausch' if MIT_PAARE else 'E3 allein (Zifferndomaenen, keine Paare, kein Bitgraph)'),
           noncen=NONCEN, python=platform.python_version(), rechner='Fable-Container Linux, Intel Xeon 2.10 GHz (2 Kerne), CPU',
           status='LAEUFT', schritte=[], paargrenze=MAXP)
def peak(): return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
def speichern(): (HERE / AUS).write_text(json.dumps(ERG, indent=1, default=str))
def fort(t): sys.stderr.write('\r%s %s %s' % (FALL, VAR, t[:95].ljust(95))); sys.stderr.flush()
def schritt(n, **k): k.update(name=n, t_s=round(time.perf_counter() - T0, 2), peak_mib=peak()); ERG['schritte'].append(k); speichern()
def ende(st, **k):
    ERG.update(k); ERG['status'] = st; ERG['gesamt_s'] = round(time.perf_counter() - T0, 2); ERG['peak_mib_kind'] = peak()
    speichern(); fort('fertig ' + st); sys.stderr.write('\n'); sys.exit(0 if st == 'OK' else 2)
def fehler(n, **k): schritt('FEHLER ' + n, **k); ende('FEHLER', fehler=dict(name=n, **k))

# ---------- Netz ----------
N, zops, out, eing, le = SZ.baue_ziffernnetz(h76, BASIS, BITS, T, 'voll')
schritt('Aufbau Ziffernnetz', variablen=len(N.dom), beziehungen=len(N.bez), freie_eingangsziffern=[N.name[v] for v in eing if N.dom[v] == 15])
# Messstellen: Register a..h je Runde aus dem Trace, dazu S1,S0,Ch,Maj,T1,T2 aus dem Protokoll
def hole(phase, art, nr):
    return next(w for p, a, n, w in zops.log if p == phase and a == art and n == nr)
MESS = []   # (phase, runde, name, [16 var-ids])
for phase, tr in (('H1', out['H1_trace']), ('H2', out['H2_trace'])):
    for i in range(64):
        reg = tr[i]
        for k, nm in enumerate('abcdefgh'): MESS.append((phase, i + 1, nm, list(reg[k])))
        s1 = hole(phase, 'xor', 97 + 2 * i); s0 = hole(phase, 'xor', 98 + 2 * i)
        ch = hole(phase, 'ch', i + 1); mj = hole(phase, 'maj', i + 1)
        t1 = hole(phase, 'add2', 144 + 7 * i + 4); t2 = hole(phase, 'add2', 144 + 7 * i + 5)
        a_neu = hole(phase, 'add2', 144 + 7 * i + 6); e_neu = hole(phase, 'add2', 144 + 7 * i + 7)
        if list(a_neu) != list(reg[0]) or list(e_neu) != list(reg[4]): fehler('Messstellen-Zuordnung', phase=phase, runde=i + 1)
        for nm, w in (('S1', s1), ('S0', s0), ('Ch', ch), ('Maj', mj), ('T1', t1), ('T2', t2)): MESS.append((phase, i + 1, nm, list(w)))
schritt('Messstellen bestimmt', anzahl=len(MESS), je_runde=14, zuordnung_gegen_trace_geprueft=True)

# ---------- Referenz: zwei vollstaendige Zustaende (Orakel, erst nach der Propagation gelesen) ----------
REF = []
for n in NONCEN:
    w3 = struct.unpack('>16I', P.padded(h76 + n.to_bytes(4, 'little'))[64:])[3]
    dom = list(N.dom)
    for j, v in enumerate(eing):
        if dom[v] == 15: dom[v] = 1 << ((w3 >> (2 * j)) & 3)
    st, dz, _, _ = ZS.e3(N, dom)
    if st != 'FIXPUNKT' or any(m & (m - 1) or m == 0 for m in dz): fehler('Referenzzustand nicht bestimmbar', nonce=n, status=st)
    werte = [m.bit_length() - 1 for m in dz]
    dig = struct.pack('>8I', *[sum(werte[v] << (2 * j) for j, v in enumerate(w)) for w in out['digest2']])
    echt = hashlib.sha256(hashlib.sha256(h76 + n.to_bytes(4, 'little')).digest()).digest()
    if dig != echt: fehler('Referenzdigest != hashlib', nonce=n)
    treffer = int.from_bytes(echt, 'little') <= T
    REF.append(dict(nonce=n, werte=werte, treffer=treffer, hash_bitcoin=echt[::-1].hex(), fuehrende_nullbits=256 - int.from_bytes(echt, 'little').bit_length(), le=werte[le]))
    if werte[le] != int(treffer): fehler('LE-Kette widerspricht Orakel', nonce=n)
MASSG = [r for r in REF if (r['treffer'] or not MIT_ZIEL)]
schritt('Referenz (Orakel, zwei vollstaendige Zustaende)', zustaende=[{k: r[k] for k in ('nonce', 'treffer', 'fuehrende_nullbits', 'hash_bitcoin')} for r in REF],
        massgeblich=[r['nonce'] for r in MASSG], unloesbarer_referenzfall=(MIT_ZIEL and not MASSG))

# ---------- Propagation ----------
zd = list(N.dom)
if MIT_ZIEL: zd[le] &= 2
paare = None; info = {}
if not MIT_PAARE:
    t = time.perf_counter(); st, zd, _, inf = ZS.e3(N, zd, max_runden=200)
    schritt('E3', status=st, runden=inf['runden'], tupelops=inf['tupelops'], s=round(time.perf_counter() - t, 2))
    status = st
else:
    g, inputs, blog, bout, root = SZ.baue_bitgraph(h76, BASIS, BITS, T)
    d = [3] * len(g.nodes); d[0] = 1; d[1] = 2
    if MIT_ZIEL: SZ.dom_schneiden(d, root, 2)
    t = time.perf_counter(); st1, sw = e1_lauf(g, d)
    schritt('E1 Start', status=st1, sweeps=sw, s=round(time.perf_counter() - t, 2), bitknoten_fest=sum(1 for x in d[2:] if x in (1, 2)))
    if st1 == 'WIDERSPRUCH': ende('OK', ergebnis=dict(status='WIDERSPRUCH_E1'))
    zu = SZ.wortzuordnung(blog, zops); zu.append(('H1_nonce', tuple(bout['H1_words'][3]), list(out['H1_words'][3])))
    R = austausch(g, inputs, root, d, N, zu, zd, ZA.e4, MAXP, True, schritt=schritt, fort=fort, fehler=fehler)
    status, zd, paare, info = R['status'], R['zd'], R['paare'], R['info4']
    if R['open_grund'] is not None: ERG['open_grund'] = R['open_grund']
    np_ = info.get('nachpruefung_e3')
    if np_ is not None and (np_['geaendert'] or np_['status'] != 'FIXPUNKT'): fehler('Nachpruefung E3', nachpruefung=np_)
    ERG['bitknoten_fest_ende'] = sum(1 for x in d[2:] if x in (1, 2))
fort('Auswertung')

# ---------- Auswertung je Messstelle ----------
def wahre_menge(v): return {r['werte'][v] for r in MASSG}
def wahres_paar(x, y): return {(r['werte'][x], r['werte'][y]) for r in MASSG}
verletzt = []
zeilen = []; gesamt = dict(ziffern=0, ziffern_exakt=0, ziffern_verloren=0, ziffern_wahr2=0, ziffern_wahr2_exakt=0,
                           paare_moeglich=0, paare_gespeichert=0, paare_fehlend=0, paare_exakt=0, paare_schwaecher=0,
                           kombis_gespeichert=0, kombis_wahr=0)
for phase, runde, nm, ids in MESS:
    zf = zf_ex = zf_verl = zf2 = zf2_ex = 0; dsum = 0
    for v in ids:
        W = wahre_menge(v); dmask = zd[v]; dset = {z for z in range(4) if dmask >> z & 1}
        if MASSG and not W <= dset: verletzt.append(dict(art='Ziffer', phase=phase, runde=runde, messstelle=nm, var=N.name[v], wahr=sorted(W), domaene=sorted(dset)))
        zf += 1; dsum += len(dset)
        if dset == W: zf_ex += 1
        elif len(dset) > len(W): zf_verl += 1
        if len(W) == 2:
            zf2 += 1
            if dset == W: zf2_ex += 1
    pm = pg = pf = pe = ps = 0; ksum = 0; kwahr = 0
    for i in range(16):
        for j in range(i + 1, 16):
            x, y = ids[i], ids[j]
            if x == y: continue
            pm += 1; Wp = wahres_paar(x, y); kwahr += len(Wp)
            m = paare.get(x, y) if paare is not None else None
            if m is None: pf += 1; continue
            pg += 1
            erl = {(vx, vy) for vx in range(4) for vy in range(4) if m >> (vx * 4 + vy) & 1}
            ksum += len(erl)
            if MASSG and not Wp <= erl: verletzt.append(dict(art='Paar', phase=phase, runde=runde, messstelle=nm, vars=[N.name[x], N.name[y]], wahr=sorted(Wp), erlaubt=sorted(erl)))
            if erl == Wp: pe += 1
            else: ps += 1
    zeilen.append(dict(phase=phase, runde=runde, messstelle=nm, ziffern=zf, ziffern_exakt=zf_ex, ziffern_verloren=zf_verl,
                       ziffern_mit_zwei_wahren_werten=zf2, davon_exakt=zf2_ex, mittel_domaenengroesse=round(dsum / zf, 2),
                       paare_moeglich=pm, paare_gespeichert=pg, paare_fehlend=pf, paare_exakt=pe, paare_schwaecher=ps,
                       mittel_kombis_gespeichert=(round(ksum / pg, 2) if pg else None), mittel_kombis_wahr=round(kwahr / pm, 2)))
    for k, v in (('ziffern', zf), ('ziffern_exakt', zf_ex), ('ziffern_verloren', zf_verl), ('ziffern_wahr2', zf2), ('ziffern_wahr2_exakt', zf2_ex),
                 ('paare_moeglich', pm), ('paare_gespeichert', pg), ('paare_fehlend', pf), ('paare_exakt', pe), ('paare_schwaecher', ps),
                 ('kombis_gespeichert', ksum), ('kombis_wahr', kwahr)): gesamt[k] += v
if verletzt: fehler('Gueltige Referenzbelegung ausgeschlossen', anzahl=len(verletzt), erste=verletzt[:3])
erste_unscharf = next((dict(phase=z['phase'], runde=z['runde'], messstelle=z['messstelle']) for z in zeilen if z['ziffern_mit_zwei_wahren_werten'] and z['davon_exakt'] < z['ziffern_mit_zwei_wahren_werten']), None)
letzte_scharf = None
for z in zeilen:
    if z['ziffern'] == z['ziffern_exakt']: letzte_scharf = dict(phase=z['phase'], runde=z['runde'], messstelle=z['messstelle'])
ERG['karte'] = zeilen
ERG['ergebnis'] = dict(status=status, gesamt=gesamt, erste_unscharfe_messstelle=erste_unscharf, letzte_vollstaendig_scharfe_messstelle=letzte_scharf,
    alle_gueltigen_referenzbelegungen_erhalten=(len(verletzt) == 0), massgebliche_zustaende=len(MASSG),
    unloesbarer_referenzfall=(MIT_ZIEL and not MASSG), paare_insgesamt=(len(paare) if paare is not None else 0),
    hinweis='Paarmasken allein beweisen keine Erhaltung der zwei Gesamtzustaende; "exakt" heisst nur: die Maske enthaelt genau die wahren Kombinationen dieser zwei Zustaende.')
ende('OK')
