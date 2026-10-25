"""N4r10 STRUKTURVERGLEICH DREI ELIMINATIONSORDNUNGEN (GO Christian 2026-10-25 14:49): HEUR=minfill (Referenz: Fill, Grad, Name) | mindegree (Grad, dann Fill, dann Name) | minfill_rev (Fill, Grad, Name UMGEKEHRT nur bei Gleichstand).
Dasselbe vereinfachte N4r10-Netz (D6-Grundgeruest, Umbau aus n4r10_struktur.py, 764 Kaestchen). Keine Tabellen, Masken, Austausch. Groessen ausschliesslich aus Breiten gerechnet (keine grossen Ganzzahlen).
ANNAHME Objekt-Overhead (getrennt ausgewiesen): CPython 3.13 64-bit Ganzzahl mit B Bits = 28 + 4*ceil(B/30) Bytes; Tupel (x,) 48; frozenset mit 1 Element 216; Liste mit n Eintraegen 56 + 8n. Reine Bitzahlen stehen daneben."""
import sys, os, json, time, itertools, resource, hashlib, collections, math
HERE = os.path.dirname(os.path.abspath(__file__)); L1 = os.path.dirname(HERE); ST = os.path.join(L1, 'stern'); sys.path.insert(0, L1); sys.path.insert(0, ST); sys.path.insert(0, HERE)
os.environ.setdefault('FALL', 'DU'); os.environ.setdefault('STAND', 'exakt'); os.environ.setdefault('NETZ', 'N3'); os.environ.setdefault('N4R10_MAX_K', '100000')
import gruppen; from stern import Kaestchen; import pruefstand as P, d6, n4r10_struktur as NS
HEUR = os.environ.get('HEUR', 'mindegree')
def ib(bits): return 28 + 4 * math.ceil(max(bits, 1) / 30)          # Ganzzahl-Objektbytes (Annahme)
def lb(n): return 56 + 8 * n

def ordnung(kaestchen, heur):
    nachbarn = {}
    for k in kaestchen:
        for v in k.vars: nachbarn.setdefault(v, set()).update(w for w in k.vars if w != v)
    rest = set(nachbarn); ordn = []; buckets = {}
    while rest:
        def fill(v):
            Nn = [w for w in nachbarn[v] if w in rest]; return sum(1 for a, b in itertools.combinations(Nn, 2) if b not in nachbarn[a])
        def grad(v): return len([w for w in nachbarn[v] if w in rest])
        if heur == 'minfill': key = lambda v: (fill(v), grad(v), v)
        elif heur == 'mindegree': key = lambda v: (grad(v), fill(v), v)
        elif heur == 'minfill_rev': key = lambda v: (fill(v), grad(v), tuple(-ord(c) for c in v))   # Name umgekehrt NUR bei Gleichstand von Fill und Grad
        v = min(rest, key=key); Nn = sorted(w for w in nachbarn[v] if w in rest)
        for a, b in itertools.combinations(Nn, 2): nachbarn[a].add(b); nachbarn[b].add(a)
        ordn.append(v); buckets[v] = Nn; rest.remove(v)
    return ordn, buckets

def baue_mit_ordnung(kaestchen, ordn, buckets):
    """Wie gruppen.baue, nur mit vorgegebener Ordnung (gleiche Eltern-/Zuordnungsregel)."""
    pos = {v: i for i, v in enumerate(ordn)}; gr = {v: gruppen.Gruppe('G_' + v, [v] + buckets[v]) for v in ordn}; kanten = []
    for v in ordn:
        spaeter = [w for w in buckets[v] if pos[w] > pos[v]]
        if spaeter:
            e = min(spaeter, key=lambda w: pos[w]); gr[v].eltern = gr[e]; gr[e].kinder.append(gr[v]); kanten.append((gr[v].name, gr[e].name, tuple(sorted(set(gr[v].vars) & set(gr[e].vars)))))
    for k in kaestchen: gr[min(k.vars, key=lambda x: pos[x])].kaestchen.append(k)
    return [gr[v] for v in ordn], kanten

if __name__ == '__main__':
    t0 = time.perf_counter(); N = P._n4r(10, True); d = d6.D6_R567bCM(); d.laufen(N); z = d._zustand; wert = dict(z['wert']); find = z['find']; kaest, gl = NS.umbau(N, wert, find); t1 = time.perf_counter()
    ordn, buckets = ordnung(kaest, HEUR); t2 = time.perf_counter(); gr, kanten = baue_mit_ordnung(kaest, ordn, buckets)
    try: gruppen.strukturpruefung(gr, kanten, kaest); strukt = dict(bestanden=True)
    except gruppen.Strukturfehler as f: strukt = dict(bestanden=False, fehler=str(f))
    sizes = [len(g.vars) for g in gr]; ss = [len(S) for a, b, S in kanten]; byn = {g.name: g for g in gr}; erst = []; seen = 0
    for i, s in enumerate(sizes, 1):
        if s > seen: seen = s; erst.append((i, s))
    bits = dict(tabellen=sum(2 ** k for k in sizes), nachrichten=sum(2 * 2 ** s for s in ss), masken_schlank=sum(2 * k * 2 ** k for k in sizes), groesste_tabelle=2 ** max(sizes), groesste_nachricht=2 ** max(ss))
    objekt = dict(tabellen=sum(ib(2 ** k) for k in sizes), nachrichten=sum(2 * (ib(2 ** s) + 48 + 216) for s in ss), masken_schlank=sum(2 * k * ib(2 ** k) + 2 * lb(k) for k in sizes),
                  zwischenobjekt_je_aufruf=2 * ib(2 ** max(sizes)) + ib(2 ** max(ss)), arbeitsstrukturen_schaetzung=int(578272 * len(gr) / 492))
    aufwand = sum(2 ** s * max(s - 1, 0) for s in ss)
    erg = dict(heuristik=HEUR, netz=N.name, kaestchen=len(kaest), variablen=len(ordn), gleichwertigkeit_E2=gl['E2'], struktur=dict(strukt, gruppen=len(gr), kanten=len(kanten), wurzeln=sum(1 for g in gr if g.eltern is None), groesste_gruppe=max(sizes), groesste_schnittstelle=max(ss),
               histogramm_k=dict(sorted(collections.Counter(sizes).items())), histogramm_s=dict(sorted(collections.Counter(ss).items())), gruppen_ueber_18=sum(1 for s in sizes if s > 18), gruppen_ueber_8=sum(1 for s in sizes if s > 8), erstmals=erst, ordnung_anfang=ordn[:20], ordnung_ende=ordn[-20:]),
               bits=bits, objektbytes_gerechnet=objekt, annahme='Ganzzahl B Bit = 28 + 4*ceil(B/30) Bytes (CPython 3.13 64-bit); Tupel 48; frozenset(1) 216; Liste 56+8n – Overhead-Annahme, keine Messung; keine Ganzzahlen angelegt',
               summe_objektbytes=objekt['tabellen'] + objekt['nachrichten'] + objekt['masken_schlank'], summe_MiB=round((objekt['tabellen'] + objekt['nachrichten'] + objekt['masken_schlank']) / 2 ** 20, 1),
               austausch_aufwand_summe_2s_mal_s_minus_1=aufwand, zeiten_s=dict(ableitung_und_umbau=round(t1 - t0, 3), ordnung=round(t2 - t1, 3), gesamt=round(time.perf_counter() - t0, 3)),
               maxrss_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1), python=sys.version.split()[0],
               abhaengigkeiten={m: dict(pfad=sys.modules[m].__file__, sha256=hashlib.sha256(open(sys.modules[m].__file__, 'rb').read()).hexdigest()) for m in ('pruefstand', 'd6', 'gatter', 'e1_bit', 'gruppen', 'stern', 'n4r10_struktur') if m in sys.modules})
    json.dump(erg, open(os.path.join(HERE, 'ERGEBNIS_N4R10_HEUR_%s.json' % HEUR), 'w'), indent=1, default=str)
    print('%-12s | Struktur %s | Gruppen %d | groesste Gruppe %d, Schnittstelle %d | >18: %d >8: %d | Bits Tab %.3g Nachr %.3g Masken %.3g | Objektbytes gesamt %.1f MiB | Aufwand %.3g | Zeit %.2f s RSS %.1f MiB' % (
        HEUR, strukt['bestanden'], len(gr), max(sizes), max(ss), erg['struktur']['gruppen_ueber_18'], erg['struktur']['gruppen_ueber_8'], bits['tabellen'], bits['nachrichten'], bits['masken_schlank'], erg['summe_MiB'], aufwand, erg['zeiten_s']['gesamt'], erg['maxrss_mib']))
    sys.exit(0 if strukt['bestanden'] and gl['E2'] else 3)
