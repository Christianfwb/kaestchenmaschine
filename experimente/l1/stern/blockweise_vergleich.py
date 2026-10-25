"""S1 – GEGENPROBEN VARIANTE A (Arbeitsliste wie bisher, Nachrichten gespeichert) mit blockweisen Relationen. FALL=DU|DL|N3|N3u|N4R09.
Vergleich bitgleich gegen gespeicherte Ergebnisse: Dreieck (ERGEBNIS_BEGRENZT_*_exakt), N3/N3u Gatter (ERGEBNIS_MESS_*_TUPEL), N4r09 Stufe B (stern_n4/UEBERGABE_V0 + ERGEBNIS_STERN_N4R09_V1).
Verbindlich: gleiche Initialrelationen, Endrelationen, Status, feste Werte; Zaehler (Entnahmen, Projektionen, Nachrichten, gestrichen) identisch; Semijoins direkt gezaehlt.
Gemessen: Zeit je Phase, gehaltene Bytes (Tabellen = bytearray-Laengen, Nachrichten = bytes-Laengen im echten Speicher N, Indextabellen, Maskentabellen-Maximum), RSS; Messpunkte M0, jede 25. Entnahme, Ende. Nichts fliesst zurueck."""
import sys, os, json, time, itertools, resource, hashlib, collections
HERE = os.path.dirname(os.path.abspath(__file__)); L1 = os.path.dirname(HERE); N4 = os.path.join(L1, 'stern_n4'); sys.path.insert(0, HERE); sys.path.insert(0, L1); sys.path.insert(0, N4)
os.environ.setdefault('FALL', 'DU'); os.environ.setdefault('STAND', 'exakt'); os.environ.setdefault('NETZ', 'N3')
import gruppen, ereignis_mess, blockweise; from stern import Kaestchen
FALL = os.environ.get('BFALL', 'DU'); M = int(os.environ.get('BLOCK_M', '12'))
def h(x): return hashlib.sha256(x).hexdigest()
def rows_to_hex(rows, vars_): return format(sum(1 << sum(r[j] << j for j in range(len(vars_))) for r in rows), 'x')

def lade():
    if FALL in ('DU', 'DL'):
        os.environ['FALL'] = FALL; import begrenzt; kaest, erw, beschr = begrenzt.faelle(); ref = json.load(open(os.path.join(HERE, 'ERGEBNIS_BEGRENZT_%s_exakt.json' % FALL)))
        return kaest, dict(end_counts=ref['FOLGERUNGEN']['zeilen_je_gruppe'], fest_ref=ref['FOLGERUNGEN']['fest'], status=ref['FOLGERUNGEN']['status'], zaehler=dict(entnahmen=ref['FOLGERUNGEN']['entnahmen'], projektionen=ref['FOLGERUNGEN']['projektionen'], nachrichten_gesendet=ref['FOLGERUNGEN']['nachrichten_gesendet'], gestrichen=ref['FOLGERUNGEN']['gestrichen']), init=None), 'Dreieck ' + FALL
    if FALL in ('N3', 'N3u'):
        import begrenzt_n3, pruefstand as P; N = P.NETZE[FALL](); kaest, typ = begrenzt_n3.gatter_kaestchen(N); ref = json.load(open(os.path.join(HERE, 'ERGEBNIS_MESS_%s_TUPEL.json' % FALL)))
        vars_of = {}
        return kaest, dict(end_rows=ref['endrelationen'], status=ref['status'], zaehler={k: ref['zaehler'][k] for k in ('entnahmen', 'projektionen', 'nachrichten_gesendet', 'gestrichen')}, init=None), 'N3-Gatter ' + FALL
    U = json.load(open(os.path.join(N4, 'UEBERGABE_V0.json'))); V1 = json.load(open(os.path.join(N4, 'ERGEBNIS_STERN_N4R09_V1.json')))
    kaest = [Kaestchen(k['name'], tuple(k['vars']), {tuple(r) for r in k['rows']}) for k in U['kaestchen']]
    return kaest, dict(end=V1['endrelationen'], status=V1['FOLGERUNGEN']['status'], zaehler={k: V1['FOLGERUNGEN']['zaehler'][k] for k in ('entnahmen', 'projektionen', 'nachrichten_gesendet', 'gestrichen')}, init={g['name']: g['rel'] for g in U['gruppen']}, feste_eingaenge=V1['FOLGERUNGEN']['feste_eingangsbits']), 'N4r09 Stufe B'

if __name__ == '__main__':
    t0 = time.perf_counter(); kaest, ref, beschr = lade(); gr0, kanten, ordnung, buckets = gruppen.baue(kaest); gruppen.strukturpruefung(gr0, kanten, kaest)
    gr = []; byn = {}
    for x in gr0: g = blockweise.BlockGruppe(x.name, x.vars, M); g.kaestchen = x.kaestchen; byn[x.name] = (g, x); gr.append(g)
    for g, x in byn.values(): g.eltern = byn[x.eltern.name][0] if x.eltern is not None else None
    t1 = time.perf_counter(); leer = [g.name for g in gr if not g.init_zeilen()]; t2 = time.perf_counter()
    init_ok = True if ref['init'] is None else all(format(g.als_int(), 'x') == ref['init'][g.name] for g in gr)
    blockweise.OPS.update(und=0, oder=0, bloecke=0, nullbloecke=0, masken_tabellen=0, masken_tabellen_bytes_max=0, semijoins=0, projektionen=0)
    z = dict(bearbeitungen=0, nachrichten_geprueft=0, nachrichten_gesendet=0, gestrichen=0); prot = []; mess = []
    def messen(punkt, zu):
        if punkt.startswith('Ma'): return
        if punkt.startswith('Mb') and z['bearbeitungen'] % 25 != 0: return
        ges = [v for v in zu['N'].values() if v is not None]
        mess.append(dict(nr=len(mess), punkt=punkt, zeit_s=round(time.perf_counter() - t2, 3), entnahmen=z['bearbeitungen'], semijoins=blockweise.OPS['semijoins'], zeilen_gesamt=sum(g.n for g in gr), tabellen_bytes=sum(len(g.rel) for g in gr),
                         nachrichten_bytes=sum(len(next(iter(v))) for v in ges), nachrichten=len(ges), indextabellen_bytes=sum(sys.getsizeof(o) + 8 * len(o) for g in gr for (lo, hi, o) in g._idx.values()), maskentabelle_max_bytes=blockweise.OPS['masken_tabellen_bytes_max'],
                         schlange=len(zu['schlange']), rss_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)))
    if leer: status = 'WIDERSPRUCH'
    else: w = ereignis_mess.arbeitsliste(gr, kanten, prot, z, messen); status = 'WIDERSPRUCH' if w else 'FIXPUNKT'
    t3 = time.perf_counter()
    end_hex = {g.name: format(g.als_int(), 'x') for g in gr}
    if 'end' in ref: end_ok = (end_hex == ref['end'])
    elif 'end_rows' in ref: end_ok = all(sorted(g.als_tupel()) == [tuple(r) for r in ref['end_rows'][g.name]] for g in gr)
    else: end_ok = all(g.n == ref['end_counts'][g.name] for g in gr)   # Dreieck: Referenz hat nur Zeilenzahlen und feste Werte gespeichert
    zae = dict(entnahmen=z['bearbeitungen'], projektionen=z['nachrichten_geprueft'], nachrichten_gesendet=z['nachrichten_gesendet'], gestrichen=z['gestrichen'])
    fest = {}
    for g in gr:
        if g.n == 0: continue
        E, N0, alle = blockweise.masken(g.w); on = [0] * g.k; off = [0] * g.k
        for t in range(g.T):
            blk = g.block(t)
            if not blk: continue
            for j in range(g.k):
                if j < g.w:
                    if blk & E[j]: on[j] = 1
                    if blk & N0[j]: off[j] = 1
                else:
                    if (t >> (j - g.w)) & 1: on[j] = 1
                    else: off[j] = 1
        for j, v in enumerate(g.vars):
            if on[j] and not off[j]: fest[v] = 1
            elif off[j] and not on[j]: fest[v] = 0
    kg = all(byn[a][0].proj(S) == byn[b][0].proj(S) for a, b, S in kanten) if status == 'FIXPUNKT' else None; t4 = time.perf_counter()
    hoechst = max(mess, key=lambda m_: m_['tabellen_bytes'] + m_['nachrichten_bytes'] + m_['indextabellen_bytes'] + m_['maskentabelle_max_bytes']) if mess else None
    pruef = dict(E_init_gleich=init_ok, E_status_gleich=(status == ref['status']), E_endrelationen_gleich=end_ok, E_zaehler_gleich=(zae == ref['zaehler']), E_kanten=(kg is None or kg))
    if 'feste_eingaenge' in ref: pruef['E_feste_eingaenge_gleich'] = all(fest.get(v) == w_ for v, w_ in ref['feste_eingaenge'].items())
    if 'fest_ref' in ref: pruef['E_fest_gleich'] = ({k: v for k, v in fest.items()} == {k: v for k, v in ref['fest_ref'].items()})
    erg = dict(fall=FALL, beschreibung=beschr, block_m=M, gruppen=len(gr), kanten=len(kanten), groesste_gruppe=max(g.k for g in gr), status=status, zaehler=dict(zae, semijoins_direkt=blockweise.OPS['semijoins']), ops=dict(blockweise.OPS), feste_variablen=len(fest),
               endrelationen_pruefsumme=h(json.dumps(end_hex, sort_keys=True).encode()), messreihe=mess, hoechststand_beobachtet=hoechst, pruefung=pruef, bestanden=all(pruef.values()),
               zeiten_s=dict(gruppierung=round(t1 - t0, 3), initialisierung=round(t2 - t1, 3), austausch=round(t3 - t2, 3), kantenpruefung_und_fest=round(t4 - t3, 3), gesamt=round(t4 - t0, 3)),
               maxrss_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1), rlimit_as=resource.getrlimit(resource.RLIMIT_AS), python=sys.version.split()[0],
               abhaengigkeiten={m_: dict(pfad=sys.modules[m_].__file__, sha256=h(open(sys.modules[m_].__file__, 'rb').read())) for m_ in ('gruppen', 'stern', 'ereignis_mess', 'blockweise', 'bitmenge', 'bitmenge_schlank', 'begrenzt', 'begrenzt_n3', 'pruefstand', 'gatter', 'd6', 'e1_bit') if m_ in sys.modules})
    json.dump(erg, open(os.path.join(HERE, 'ERGEBNIS_BLOCK_%s.json' % FALL), 'w'), indent=1, default=str)
    hb = hoechst or {}
    print('%-6s %-11s | init %s end %s status %s zaehler %s kanten %s | Semijoins %d | Zeiten init %.2f austausch %.2f gesamt %.2f s | Hoechst Tab %s Nachr %s Idx %s MaskTab %s | RSS %.1f | %s' % (
        FALL, status[:11], init_ok, end_ok, pruef['E_status_gleich'], pruef['E_zaehler_gleich'], pruef['E_kanten'], blockweise.OPS['semijoins'], t2 - t1, t3 - t2, t4 - t0, hb.get('tabellen_bytes'), hb.get('nachrichten_bytes'), hb.get('indextabellen_bytes'), hb.get('maskentabelle_max_bytes'), erg['maxrss_mib'], 'BESTANDEN' if erg['bestanden'] else 'FEHLER'))
    sys.exit(0 if erg['bestanden'] else 3)
