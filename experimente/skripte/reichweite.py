#!/usr/bin/env python3
"""REICHWEITE DER RUECKWAERTSABLEITUNG (Fable, 2026-10-22). python -I reichweite.py
Drei Messungen, alle auf Kopien, CPU, ohne Suchlauf:
M1 Auffrisch-Kaestchen am Kettenende (Christians Idee, kette.py): wirkt es auf kleinen SHA-Netzen?
M2 Reichweite am echten Fall F1 (U-voll, echtes Target, 8 freie Noncebits, nur E3): wie weit traegt das Ziel rueckwaerts,
   wie weit traegt der Header vorwaerts, wie gross ist die Luecke dazwischen?
M3 Haengt die Vorwaertsreichweite an der Gruppengroesse? Freie Noncebits 1, 2, 4, 8, 16."""
import sys, json, time, random, resource, pathlib, platform
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent.parent / 'src' / 'kaestchen'))
import ziffern_komp as ZK, ziffern_sha as ZS, sha_ziffern as SZ, kette as KE
from ziffern import Netz
T0 = time.perf_counter()
ERG = dict(erstellt='2026-10-22', python=platform.python_version(),
           rechner='Fable-Container Linux, Intel Xeon 2.10 GHz (2 Kerne), CPU, reines Python', messungen={})
def peak(): return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)

def sha_netz(runden, seed=2):
    N = Netz(32); ops = SZ.ZiffernOps(N); ops.phase = 'T'; r = random.Random(seed)
    K = [0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1]
    a, b, c, d, e, f, g, h = [N.wort(n) for n in 'abcdefgh']
    for i in range(runden):
        s1 = ops.xor(ops.rot(e, 6), ops.rot(e, 11), ops.rot(e, 25)); s0 = ops.xor(ops.rot(a, 2), ops.rot(a, 13), ops.rot(a, 22))
        t1 = ops.add(h, s1, ops.ch(e, f, g), ops.const(K[i % 6]), N.wort('w%d' % i)); t2 = ops.add(s0, ops.maj(a, b, c))
        a, b, c, d, e, f, g, h = ops.add(t1, t2), a, b, c, ops.add(d, t1), e, f, g
    dom = list(N.dom)
    for v in a + e: dom[v] = 1 << r.randrange(4)          # Ausgang der letzten Runde fest = rueckwaerts
    return N, dom

# ---------------- M1: Auffrischer ----------------
m1 = {}
for runden in (2, 6):
    N, dom0 = sha_netz(runden)
    t = time.perf_counter(); st, dom, paare, inf = ZK.e4(N, dom0, max_paare=400000); t_basis = time.perf_counter() - t
    basis_dom = list(dom); ks = KE.benannte_ketten(N, dom)
    extra = dict(paare); runden_auf = 0; stat = {}
    for it in range(4):
        ge, stat = KE.auffrischen_benannt(N, extra, dom); runden_auf = it + 1
        if ge == 0: break
        st2, dom, paare2, inf2 = ZK.e4(N, dom0, max_paare=600000, start_paare=extra)
        if st2 != 'FIXPUNKT': stat['abbruch'] = st2; break
        extra = dict(paare2)
    m1['%d_runden' % runden] = dict(variablen=len(N.dom), beziehungen=len(N.bez), basis_status=st, basis_paare=len(paare), basis_s=round(t_basis, 2),
        rechenketten=len(ks), kettenlaengen=sorted({len(k) for _, k in ks}), auffrisch_runden=runden_auf,
        neue_langstreckenpaare=stat.get('neue_paare'), geaenderte_paare=stat.get('geaenderte_paare'), abbruch=stat.get('abbruch'),
        domaenen_enger_durch_auffrischen=sum(1 for p, q in zip(basis_dom, dom) if p != q))
ERG['messungen']['M1_auffrischer'] = dict(beschreibung='Auffrisch-Kaestchen am Ende der Rechenketten (Uebertragsketten, Zielkette): '
    'Beziehung Anfang<->Ende durch Verkettung aller Glieder, sound (nur Schnitte). Gemessen: aendern die neuen Langstreckenbeziehungen etwas?',
    ergebnis=m1, peak_mib=peak(), t_s=round(time.perf_counter() - T0, 1))
print('M1 fertig', json.dumps(m1))

# ---------------- M2: Reichweite am echten Fall ----------------
F = json.loads((HERE / 'FAELLE_SHA256D.json').read_text())['faelle'][0]
h76 = bytes.fromhex(F['header_hex_ohne_nonce']); T = int(F['target_hex'], 16)
N, ops, out, eing, le = SZ.baue_ziffernnetz(h76, F['basis_nonce'], F['freie_nonce_bits'], T, 'voll')
dom = list(N.dom); dom[le] &= 2; start = list(dom)
t = time.perf_counter(); st, d, _, inf = ZS.e3(N, dom, max_runden=60); t_e3 = time.perf_counter() - t
def enger(ids): return sum(1 for v in ids if d[v] != start[v])
def fest(ids): return sum(1 for v in ids if d[v] and d[v] & (d[v] - 1) == 0 and start[v] & (start[v] - 1))
def offen(ids): return sum(1 for v in ids if bin(d[v]).count('1') > 1)
tr1, tr2 = out['H1_trace'], out['H2_trace']
rueck = [dict(runde=i + 1, a_enger=enger(tr2[i][0]), a_fest=fest(tr2[i][0]), e_enger=enger(tr2[i][4]), e_fest=fest(tr2[i][4])) for i in range(63, 55, -1)]
letzte_rueck = max((i + 1 for i in range(64) if enger(tr2[i][0]) or enger(tr2[i][4])), default=None)
erste_rueck = min((i + 1 for i in range(64) if enger(tr2[i][0]) or enger(tr2[i][4])), default=None)
vor = [dict(runde=i + 1, a_offen=offen(tr1[i][0]), e_offen=offen(tr1[i][4])) for i in range(8)]
letzte_vor = max((i + 1 for i in range(64) if offen(tr1[i][0]) < 16 or offen(tr1[i][4]) < 16), default=None)
ERG['messungen']['M2_reichweite_F1'] = dict(beschreibung='Echte Vorlage F1, U-voll, echtes Target (78 Nullbits), 8 freie Noncebits, Ziel gesetzt, nur E3 (ohne Paare).',
    e3_status=st, e3_s=round(t_e3, 1), zielkette_eingeschraenkt=sum(1 for v in range(len(d)) if N.name[v].startswith('le_') and d[v] != start[v]),
    zielkette_gesamt=sum(1 for v in range(len(d)) if N.name[v].startswith('le_')),
    digest2_enger_je_wort=[enger(w) for w in out['digest2']],
    rueckwaerts_letzte_beruehrte_runde=letzte_rueck, rueckwaerts_frueheste_beruehrte_runde=erste_rueck, rueckwaerts_profil=rueck,
    vorwaerts_letzte_bestimmte_runde=letzte_vor, vorwaerts_profil=vor,
    luecke_runden=(64 - letzte_vor) + (erste_rueck - 1) if (letzte_vor and erste_rueck) else None,
    nonce_wort_enger=enger(out['H1_words'][3]), digest1_offen=[offen(w) for w in out['digest1']], peak_mib=peak())
print('M2 fertig: vorwaerts bis H1-Runde', letzte_vor, ', rueckwaerts bis H2-Runde', erste_rueck)

# ---------------- M3: Gruppengroesse ----------------
m3 = {}
for nb in (1, 2, 4, 8, 16):
    N2, o2, out2, eing2, le2 = SZ.baue_ziffernnetz(h76, 0, list(range(nb)), T, 'voll')
    dom2 = list(N2.dom); dom2[le2] &= 2
    st2, d2, _, _ = ZS.e3(N2, dom2, max_runden=60)
    def off2(ids): return sum(1 for v in ids if bin(d2[v]).count('1') > 1)
    t2 = out2['H1_trace']
    erste_offen = next((i + 1 for i in range(64) if off2(t2[i][0]) == 16 and off2(t2[i][4]) == 16), None)
    m3['%d_freie_bits' % nb] = dict(gruppengroesse=1 << nb, erste_vollstaendig_offene_runde=erste_offen,
        profil_a_runde1_bis_8=[off2(t2[i][0]) for i in range(8)], digest1_offene_ziffern=sum(off2(w) for w in out2['digest1']))
ERG['messungen']['M3_gruppengroesse'] = dict(beschreibung='Haengt die Vorwaertsreichweite an der Gruppengroesse? Freie Noncebits 1..16, sonst identisch.',
    ergebnis=m3, peak_mib=peak())
print('M3 fertig', json.dumps(m3))
ERG['gesamt_s'] = round(time.perf_counter() - T0, 1); ERG['peak_mib'] = peak()
(HERE / 'ERGEBNIS_REICHWEITE.json').write_text(json.dumps(ERG, indent=1))
print('gesamt %.1f s, Peak %.1f MiB' % (ERG['gesamt_s'], ERG['peak_mib']))
