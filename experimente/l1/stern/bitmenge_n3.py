"""BITMENGEN-VERGLEICH an N3/N3u exakt (Gatterebene, genau die B2-Staende). FORM=TUPEL (begrenzt.GruppeZ, wie B2) | FORM=BIT (bitmenge.BitGruppe).
Gleiche Kaestchen (begrenzt_n3.gatter_kaestchen), gleiche Gruppierung (gruppen.baue), gleiche Arbeitsliste (ereignis.arbeitsliste). Drei Ausweise + Speicher-/Operationszaehlung.
Speicher: (a) theoretische Bits; (b) 'rekursiv gezaehlte Objektbytes' (sys.getsizeof, jedes Objekt per Identitaet nur einmal; NICHT der RAM-Verbrauch), getrennt Tabellen / Nachrichten / Masken;
Nachrichtenspeicher am Ende rekonstruiert aus den Endprojektionen je gerichteter Kante (bei FIXPUNKT = gespeicherter Stand; bei WIDERSPRUCH Obergrenze). (c) RSS – bei dieser Groesse vom Interpreter dominiert.
Aufruf: NETZ=N3|N3u FORM=TUPEL|BIT python3 -I bitmenge_n3.py"""
import sys, os, json, time, itertools, resource, hashlib, collections
HERE = os.path.dirname(os.path.abspath(__file__)); L1 = os.path.dirname(HERE); sys.path.insert(0, HERE); sys.path.insert(0, L1)
os.environ.setdefault('FALL', 'DU'); os.environ.setdefault('STAND', 'exakt'); os.environ.setdefault('NETZ', 'N3')
import gruppen, ereignis, begrenzt, bitmenge, begrenzt_n3; import pruefstand as P
NETZ = os.environ.get('NETZ', 'N3'); FORM = os.environ.get('FORM', 'BIT'); nm = begrenzt_n3.nm

def bytes_rek(obj, seen):
    if id(obj) in seen: return 0
    seen.add(id(obj)); s = sys.getsizeof(obj)
    if isinstance(obj, (set, frozenset, list, tuple)): s += sum(bytes_rek(x, seen) for x in obj)
    elif isinstance(obj, dict): s += sum(bytes_rek(k, seen) + bytes_rek(v, seen) for k, v in obj.items())
    return s

def fall():
    N = P.NETZE[NETZ](); kaest, typ = begrenzt_n3.gatter_kaestchen(N); alle_vars = sorted({v for k in kaest for v in k.vars}); erw_loes = {'N3': 12, 'N3u': 0}[NETZ]
    begrenzt.ZAEHL.update(semijoins=0, proj_zeilen=0); bitmenge.OPS.update(und=0, oder=0, popcount=0, masken_gebaut=0, masken_bits=0, masken_bau_s=0.0)
    t0 = time.perf_counter(); z = dict(bearbeitungen=0, nachrichten_geprueft=0, nachrichten_gesendet=0, gestrichen=0); prot = []
    gr0, kanten, ordnung, buckets = gruppen.baue(kaest); gruppen.strukturpruefung(gr0, kanten, kaest)
    K = begrenzt.GruppeZ if FORM == 'TUPEL' else bitmenge.BitGruppe; byn = {}
    for g in gr0: h = K(g.name, g.vars); h.kaestchen = g.kaestchen; byn[g.name] = (h, g)
    gr = [byn[g.name][0] for g in gr0]
    for h, g in byn.values(): h.eltern = byn[g.eltern.name][0] if g.eltern is not None else None
    leer = [g.name for g in gr if not g.init_zeilen()]
    init_rel = {g.name: sorted(set(g.zeilen)) for g in gr}; ps = begrenzt.pruefsumme(gr, kanten)
    if FORM == 'BIT':                                   # Masken fuer alle Kanten vorab bauen (gehoert zu T1 und zum Speicher)
        for a, b, S in kanten: byn[a][0].masken(S); byn[b][0].masken(S)
    t1 = time.perf_counter()
    if leer: status = 'WIDERSPRUCH'; prot.append(dict(ereignis='WIDERSPRUCH: Gruppe beim Initialisieren leer', gruppen=leer))
    else: w = ereignis.arbeitsliste(gr, kanten, prot, z); status = 'WIDERSPRUCH' if w else 'FIXPUNKT'
    t2 = time.perf_counter()
    # ERKANNTE FOLGERUNGEN (vor der Kontrolle)
    end_rel = {g.name: sorted(set(g.zeilen)) for g in gr}; fest = {}
    for g in gr:
        rows = set(g.zeilen)
        if not rows: continue
        for k, v in enumerate(g.vars):
            w = {zl[k] for zl in rows}
            if len(w) == 1: fest[v] = w.pop()
    ops_abl = dict(bitmenge.OPS) if FORM == 'BIT' else dict(gepruefte_tupel_projektionen=begrenzt.ZAEHL['proj_zeilen'])
    folg = dict(status=status, gestrichen=z['gestrichen'], fest=fest, entnahmen=z['bearbeitungen'], semijoins=(begrenzt.ZAEHL['semijoins'] if FORM == 'TUPEL' else None), projektionen=z['nachrichten_geprueft'], nachrichten_gesendet=z['nachrichten_gesendet'], max_liste=z.get('max_schlange'), elementaroperationen=ops_abl, protokoll=prot)
    byname = {g.name: g for g in gr}; kanten_gleich = {('%s-%s' % (a, b)): (byname[a].proj(S) == byname[b].proj(S)) for a, b, S in kanten} if status == 'FIXPUNKT' else None; t3 = time.perf_counter()
    # SPEICHER (rekursiv gezaehlte Objektbytes, Identitaet nur einmal)
    seen = set(); tab = sum(bytes_rek(g.zeilen if FORM == 'TUPEL' else g.rel, seen) for g in gr)
    nachr_obj = []
    for a, b, S in kanten: nachr_obj.append(frozenset(byname[a].proj(S))); nachr_obj.append(frozenset(byname[b].proj(S)))
    nachr = sum(bytes_rek(o, seen) for o in nachr_obj)
    mask = sum(bytes_rek(g._masken, seen) for g in gr) if FORM == 'BIT' else 0
    bits_tab = sum(2 ** len(g.vars) for g in gr); bits_nachr = sum(2 * 2 ** len(S) for a, b, S in kanten); bits_mask = bitmenge.OPS['masken_bits'] if FORM == 'BIT' else 0
    zeilen_ende = sum(len(g.zeilen) for g in gr)
    speicher = dict(einheit='rekursiv gezaehlte Objektbytes (sys.getsizeof, jedes Objekt einmal) – NICHT tatsaechlicher RAM', tabellen_bytes=tab, nachrichten_bytes=nachr, masken_bytes=mask, summe_bytes=tab + nachr + mask,
                    tabellen_bits_theoretisch=bits_tab, nachrichten_bits_theoretisch=bits_nachr, masken_bits_theoretisch=bits_mask, masken_anzahl=(bitmenge.OPS['masken_gebaut'] if FORM == 'BIT' else 0), masken_bau_s=(round(bitmenge.OPS['masken_bau_s'], 5) if FORM == 'BIT' else 0),
                    zeilen_ende_gesamt=zeilen_ende, hinweis_nachrichten='aus Endprojektionen je gerichteter Kante rekonstruiert')
    # KONTROLLE (danach)
    wahr = []
    for bel in itertools.product((0, 1), repeat=len(N.frei)):
        v = N.wert(list(bel))
        if all((v[abs(zk)] ^ (1 if zk < 0 else 0)) == val for zk, val in N.ziel.items()): wahr.append({nm(i): v[i] for i in range(2, len(v))})
    je = {}
    for g in gr:
        rows = set(g.zeilen); Pj = {tuple(w[x] for x in g.vars) for w in wahr}; je[g.name] = dict(zeilen=len(rows), zu_viel=len(rows - Pj), fehlend=len(Pj - rows))
    fest_falsch = {v: w for v, w in fest.items() if any(s[v] != w for s in wahr)}; t4 = time.perf_counter()
    pruef = dict(E4_speicherung=(sum(d['fehlend'] for d in je.values()) == 0 and not fest_falsch), E5_kanten=(kanten_gleich is None or all(kanten_gleich.values())), status_erwartet=(status == ('FIXPUNKT' if erw_loes else 'WIDERSPRUCH')), kontrolle_erwartet=(len(wahr) == erw_loes),
                 zu_viel_null_bei_fixpunkt=(status != 'FIXPUNKT' or sum(d['zu_viel'] for d in je.values()) == 0))
    k8 = dict(hinweis='HOCHRECHNUNG – reine Rechnung, keine Messung', gruppe_k8_tabelle_bits=256, gruppe_k8_tabelle_bytes_bit=sys.getsizeof((1 << 256) - 1), gruppe_k8_tabelle_bytes_tupel_256_zeilen=bytes_rek({tuple((b >> j) & 1 for j in range(8)) for b in range(256)}, set()),
              masken_je_kante_s7=dict(anzahl=128, bits=128 * 256, bytes_bit=128 * sys.getsizeof((1 << 256) - 1) + sys.getsizeof([0] * 128)), masken_je_kante_s4=dict(anzahl=16, bits=16 * 256, bytes_bit=16 * sys.getsizeof((1 << 256) - 1) + sys.getsizeof([0] * 16)))
    erg = dict(netz=NETZ, form=FORM, name=N.name, variablen=len(alle_vars), kaestchen=len(kaest), gruppen=len(gr), kanten=len(kanten), groesste_gruppe=max(len(g.vars) for g in gr), pruefsumme_struktur=ps,
               initialrelationen=init_rel, endrelationen=end_rel, endrelationen_pruefsumme=hashlib.sha256(json.dumps(end_rel, sort_keys=True).encode()).hexdigest(), FOLGERUNGEN=folg, kanten_projektionen_gleich=kanten_gleich,
               SPEICHER=speicher, KONTROLLE=dict(echte_loesungen=len(wahr), je_gruppe=je, zu_viel_gesamt=sum(d['zu_viel'] for d in je.values()), fehlend_gesamt=sum(d['fehlend'] for d in je.values()), fest_widerspricht_kontrolle=fest_falsch),
               hochrechnung_k8=k8, pruefung=pruef, bestanden=all(pruef.values()), zeiten_s=dict(T1_gruppierung_masken_init=round(t1 - t0, 5), T2_austausch=round(t2 - t1, 5), T3_kantenpruefung=round(t3 - t2, 5), T4_kontrolle=round(t4 - t3, 5)),
               maxrss_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1), rss_hinweis='bei dieser Groesse vom Interpreter dominiert; sagt nichts ueber die Speicherform', rlimit_as=resource.getrlimit(resource.RLIMIT_AS), python=sys.version.split()[0],
               abhaengigkeiten={m: dict(pfad=sys.modules[m].__file__, sha256=hashlib.sha256(open(sys.modules[m].__file__, 'rb').read()).hexdigest()) for m in ('gruppen', 'ereignis', 'begrenzt', 'begrenzt_n3', 'bitmenge', 'stern', 'pruefstand', 'gatter', 'd6', 'e1_bit') if m in sys.modules})
    json.dump(erg, open(os.path.join(HERE, 'ERGEBNIS_BIT_%s_%s.json' % (NETZ, FORM)), 'w'), indent=1, default=str)
    print('%-3s %-5s %-11s | gestrichen %3d fest %2d | Entn/Proj/Nachr %d/%d/%d | Bytes Tab/Nachr/Masken %d/%d/%d = %d | Bits Tab/Nachr/Masken %d/%d/%d | Ops %s | T1 %.4f T2 %.4f | %s' % (
        NETZ, FORM, status[:11], z['gestrichen'], len(fest), z['bearbeitungen'], z['nachrichten_geprueft'], z['nachrichten_gesendet'], tab, nachr, mask, tab + nachr + mask, bits_tab, bits_nachr, bits_mask, ops_abl, t1 - t0, t2 - t1, 'BESTANDEN' if erg['bestanden'] else 'FEHLER'))
    sys.exit(0 if erg['bestanden'] else 3)
if __name__ == '__main__': fall()
