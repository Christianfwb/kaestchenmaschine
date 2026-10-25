"""MESSKORREKTUR-LAUF (GO Christian 2026-10-25 12:25): N3/N3u exakt, TUPEL gegen BIT. Gruppierung, Rechenlogik, Reihenfolge, Grenzen unveraendert.
1. Nachrichten werden WAEHREND des Austauschs aus dem echten Nachrichtenspeicher N gemessen (ereignis_mess, Messhaken) – keine Rekonstruktion.
2. Semijoin-Aufrufe direkt gezaehlt (TUPEL: begrenzt.GruppeZ; BIT: BitGruppeZ-Huelle hier).
3. Je Messpunkt gleichzeitig gehaltene Objektbytes: Tabellen | Masken | Nachrichten | Arbeitsstrukturen – mit EINER Identitaetsmenge je Messpunkt, Zuordnung in dieser Reihenfolge (ein Objekt zaehlt bei der ersten Kategorie, die es erreicht).
4. Getrennt: Pruefkopien (Initialrelationen, Original-Kaestchen-Kopien), Kontrollkopien (Loesungsliste, Projektionen), Messinstrumentierung (Messreihe, Zaehler).
5. Messpunkte dokumentiert; Maximum = beobachteter Hoechststand an den Messpunkten. MESSLUECKE: kurzlebige Zwischenobjekte innerhalb von proj()/semijoin() (TUPEL: Projektionsmenge, gefilterte Zeilenmenge; BIT: aufgeweitete Maske, P, Zwischen-Ints; beide: das frozenset vor dem Vergleich) liegen zwischen den Messpunkten und werden nicht erfasst; ihre Groessenordnung wird als Obergrenze gerechnet.
Aufruf: NETZ=N3|N3u FORM=TUPEL|BIT python3 -I bitmenge_mess.py"""
import sys, os, json, time, itertools, resource, hashlib, collections, copy
HERE = os.path.dirname(os.path.abspath(__file__)); L1 = os.path.dirname(HERE); sys.path.insert(0, HERE); sys.path.insert(0, L1)
os.environ.setdefault('FALL', 'DU'); os.environ.setdefault('STAND', 'exakt'); os.environ.setdefault('NETZ', 'N3')
import gruppen, ereignis, ereignis_mess, begrenzt, bitmenge, begrenzt_n3; import pruefstand as P
NETZ = os.environ.get('NETZ', 'N3'); FORM = os.environ.get('FORM', 'BIT'); nm = begrenzt_n3.nm
SEMI = dict(aufrufe=0)
class BitGruppeZ(bitmenge.BitGruppe):
    def semijoin(self, S, M): SEMI['aufrufe'] += 1; return super().semijoin(S, M)
class TupelGruppeZ(begrenzt.GruppeZ):
    def semijoin(self, S, M): SEMI['aufrufe'] += 1; return super().semijoin(S, M)

def bytes_rek(obj, seen):
    if id(obj) in seen: return 0
    seen.add(id(obj)); s = sys.getsizeof(obj)
    if isinstance(obj, (set, frozenset, list, tuple, collections.deque)): s += sum(bytes_rek(x, seen) for x in obj)
    elif isinstance(obj, dict): s += sum(bytes_rek(k, seen) + bytes_rek(v, seen) for k, v in obj.items())
    return s

def baue_gruppen(kaest, K):
    gr0, kanten, ordnung, buckets = gruppen.baue(kaest); gruppen.strukturpruefung(gr0, kanten, kaest); byn = {}
    for g in gr0: h = K(g.name, g.vars); h.kaestchen = g.kaestchen; byn[g.name] = (h, g)
    gr = [byn[g.name][0] for g in gr0]
    for h, g in byn.values(): h.eltern = byn[g.eltern.name][0] if g.eltern is not None else None
    leer = [g.name for g in gr if not g.init_zeilen()]
    if K is not TupelGruppeZ:
        for a, b, S in kanten: byn[a][0].masken(S); byn[b][0].masken(S)
    return gr, kanten, ordnung, leer

def fall():
    N = P.NETZE[NETZ](); kaest, typ = begrenzt_n3.gatter_kaestchen(N); erw_loes = {'N3': 12, 'N3u': 0}[NETZ]
    K = TupelGruppeZ if FORM == 'TUPEL' else BitGruppeZ
    # E0: Original-Arbeitsliste auf eigener Gruppenkopie (Referenz), danach instrumentierte Kopie auf der Messkopie
    begrenzt.ZAEHL.update(semijoins=0, proj_zeilen=0); bitmenge.OPS.update(und=0, oder=0, popcount=0, masken_gebaut=0, masken_bits=0, masken_bau_s=0.0); SEMI['aufrufe'] = 0
    grR, kantenR, _, leerR = baue_gruppen(kaest, K); zR = dict(bearbeitungen=0, nachrichten_geprueft=0, nachrichten_gesendet=0, gestrichen=0); protR = []
    statusR = 'WIDERSPRUCH' if leerR else ('WIDERSPRUCH' if ereignis.arbeitsliste(grR, kantenR, protR, zR) else 'FIXPUNKT'); endR = {g.name: sorted(set(g.zeilen)) for g in grR}; semiR = SEMI['aufrufe']
    # Messlauf
    begrenzt.ZAEHL.update(semijoins=0, proj_zeilen=0); bitmenge.OPS.update(und=0, oder=0, popcount=0, masken_gebaut=0, masken_bits=0, masken_bau_s=0.0); SEMI['aufrufe'] = 0
    t0 = time.perf_counter(); gr, kanten, ordnung, leer = baue_gruppen(kaest, K); pruefkopie_init = {g.name: sorted(set(g.zeilen)) for g in gr}; ps = begrenzt.pruefsumme(gr, kanten); t1 = time.perf_counter()
    messreihe = []; zaehl_semi_vor = [0]
    def messen(punkt, zu):
        seen = set(); tab = sum(bytes_rek(g.zeilen if FORM == 'TUPEL' else g.rel, seen) for g in gr)
        mask = sum(bytes_rek(g._masken, seen) for g in gr) if FORM == 'BIT' else 0
        gesendet = [v for v in zu['N'].values() if v is not None]; nachr = sum(bytes_rek(v, seen) for v in gesendet)
        arbeit = bytes_rek(zu['N'], seen) + bytes_rek(zu['schlange'], seen) + bytes_rek(zu['drin'], seen) + bytes_rek(zu['neu_eingang'], seen) + bytes_rek(zu['nachbarn'], seen)
        messreihe.append(dict(nr=len(messreihe), punkt=punkt, semijoins_bisher=SEMI['aufrufe'], tabellen=tab, masken=mask, nachrichten=nachr, nachrichten_anzahl=len(gesendet), arbeitsstrukturen=arbeit, summe=tab + mask + nachr + arbeit, schlange=len(zu['schlange']), zeilen_gesamt=sum(len(g.zeilen) for g in gr)))
    z = dict(bearbeitungen=0, nachrichten_geprueft=0, nachrichten_gesendet=0, gestrichen=0); prot = []
    if leer: status = 'WIDERSPRUCH'; prot.append(dict(ereignis='WIDERSPRUCH: Gruppe beim Initialisieren leer', gruppen=leer))
    else: w = ereignis_mess.arbeitsliste(gr, kanten, prot, z, messen); status = 'WIDERSPRUCH' if w else 'FIXPUNKT'
    t2 = time.perf_counter(); semi = SEMI['aufrufe']
    end = {g.name: sorted(set(g.zeilen)) for g in gr}; fest = {}
    for g in gr:
        rows = set(g.zeilen)
        if rows:
            for k, v in enumerate(g.vars):
                w_ = {zl[k] for zl in rows}
                if len(w_) == 1: fest[v] = w_.pop()
    ops = dict(bitmenge.OPS) if FORM == 'BIT' else dict(gepruefte_tupel_projektionen=begrenzt.ZAEHL['proj_zeilen'])
    byname = {g.name: g for g in gr}; kanten_gleich = {('%s-%s' % (a, b)): (byname[a].proj(S) == byname[b].proj(S)) for a, b, S in kanten} if status == 'FIXPUNKT' else None; t3 = time.perf_counter()
    # Kontrolle (danach)
    wahr = []
    for bel in itertools.product((0, 1), repeat=len(N.frei)):
        v = N.wert(list(bel))
        if all((v[abs(zk)] ^ (1 if zk < 0 else 0)) == val for zk, val in N.ziel.items()): wahr.append({nm(i): v[i] for i in range(2, len(v))})
    je = {}
    for g in gr:
        rows = set(g.zeilen); Pj = {tuple(w_[x] for x in g.vars) for w_ in wahr}; je[g.name] = dict(zeilen=len(rows), zu_viel=len(rows - Pj), fehlend=len(Pj - rows))
    fest_falsch = {v: w_ for v, w_ in fest.items() if any(s[v] != w_ for s in wahr)}; t4 = time.perf_counter()
    # getrennte Ausweise der Nicht-Rechenobjekte
    sp = set(); pruefkopien = bytes_rek(pruefkopie_init, sp) + bytes_rek(endR, sp) + sum(bytes_rek(g.zeilen if FORM == 'TUPEL' else g.rel, sp) for g in grR)
    sk = set(); kontrollkopien = bytes_rek(wahr, sk) + bytes_rek(je, sk)
    sm = set(); instrumentierung = bytes_rek(messreihe, sm) + bytes_rek(z, sm) + bytes_rek(prot, sm) + bytes_rek(ops, sm)
    # Messluecke: Obergrenze kurzlebiger Zwischenobjekte
    kmax = max(len(g.vars) for g in gr); smax = max(len(S) for a, b, S in kanten)
    if FORM == 'TUPEL': luecke = dict(beschreibung='Projektionsmenge (bis 2^s Tupel) + gefilterte Zeilenmenge (bis 2^k Tupel) + frozenset-Huelle', obergrenze_bytes=bytes_rek({tuple((b >> j) & 1 for j in range(smax)) for b in range(1 << smax)}, set()) + bytes_rek({tuple((b >> j) & 1 for j in range(kmax)) for b in range(1 << kmax)}, set()) + sys.getsizeof(frozenset()))
    else: luecke = dict(beschreibung='aufgeweitete Maske (2^k Bit) + Projektions-Ganzzahl (2^s Bit) + 1-Tupel + frozenset-Huelle', obergrenze_bytes=sys.getsizeof((1 << (1 << kmax)) - 1) + sys.getsizeof((1 << (1 << smax)) - 1) + sys.getsizeof((0,)) + sys.getsizeof(frozenset({0})))
    hoechst = max(messreihe, key=lambda m: m['summe']) if messreihe else None
    pruef = dict(E0_instrumentierte_kopie_gleich_original=(end == endR and status == statusR and semi == semiR), E4_speicherung=(sum(d['fehlend'] for d in je.values()) == 0 and not fest_falsch), E5_kanten=(kanten_gleich is None or all(kanten_gleich.values())),
                 status_erwartet=(status == ('FIXPUNKT' if erw_loes else 'WIDERSPRUCH')), kontrolle_erwartet=(len(wahr) == erw_loes), zu_viel_null_bei_fixpunkt=(status != 'FIXPUNKT' or sum(d['zu_viel'] for d in je.values()) == 0))
    erg = dict(netz=NETZ, form=FORM, gruppen=len(gr), kanten=len(kanten), pruefsumme_struktur=ps, status=status, endrelationen=end, fest=fest,
               zaehler=dict(entnahmen=z['bearbeitungen'], semijoin_aufrufe_direkt=semi, projektionen=z['nachrichten_geprueft'], nachrichten_gesendet=z['nachrichten_gesendet'], gestrichen=z['gestrichen'], max_schlange=z.get('max_schlange'), elementaroperationen=ops),
               messpunkte=dict(definition=['M0 nach Aufbau der Arbeitsstrukturen (vor der ersten Entnahme)', 'Ma nach jedem Empfang (Semijoin)', 'Mb nach jeder Entnahme (nach dem Senden)', 'ME Ende'], anzahl=len(messreihe), zuordnungsreihenfolge=['tabellen', 'masken', 'nachrichten', 'arbeitsstrukturen'], einheit='rekursiv gezaehlte Objektbytes, Identitaet je Messpunkt einmal – NICHT RAM'),
               hoechststand_beobachtet=hoechst, endstand=(messreihe[-1] if messreihe else None), anfangsstand=(messreihe[0] if messreihe else None), messreihe=messreihe,
               messluecke=luecke, getrennt=dict(pruefkopien_bytes=pruefkopien, kontrollkopien_bytes=kontrollkopien, messinstrumentierung_bytes=instrumentierung, hinweis='nicht Teil des Rechenzustands; nur zur Vollstaendigkeit'),
               KONTROLLE=dict(echte_loesungen=len(wahr), zu_viel_gesamt=sum(d['zu_viel'] for d in je.values()), fehlend_gesamt=sum(d['fehlend'] for d in je.values()), fest_widerspricht_kontrolle=fest_falsch),
               pruefung=pruef, bestanden=all(pruef.values()), zeiten_s=dict(T1=round(t1 - t0, 5), T2_instrumentiert=round(t2 - t1, 5), T3=round(t3 - t2, 5), T4=round(t4 - t3, 5), hinweis='instrumentierter Millisekundenlauf – keine Geschwindigkeitsaussage'),
               maxrss_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1), rlimit_as=resource.getrlimit(resource.RLIMIT_AS), python=sys.version.split()[0],
               abhaengigkeiten={m: dict(pfad=sys.modules[m].__file__, sha256=hashlib.sha256(open(sys.modules[m].__file__, 'rb').read()).hexdigest()) for m in ('gruppen', 'ereignis', 'ereignis_mess', 'begrenzt', 'begrenzt_n3', 'bitmenge', 'stern', 'pruefstand', 'gatter', 'd6', 'e1_bit') if m in sys.modules})
    json.dump(erg, open(os.path.join(HERE, 'ERGEBNIS_MESS_%s_%s.json' % (NETZ, FORM)), 'w'), indent=1, default=str)
    h = hoechst or {}
    print('%-3s %-5s %-11s | Semijoins direkt %d | Messpunkte %d | Hoechststand (Nr %s, %s): Tab %s Masken %s Nachr %s (%s Stueck) Arbeit %s = %s | Ende: %s | Luecke <= %s | %s' % (
        NETZ, FORM, status[:11], semi, len(messreihe), h.get('nr'), h.get('punkt'), h.get('tabellen'), h.get('masken'), h.get('nachrichten'), h.get('nachrichten_anzahl'), h.get('arbeitsstrukturen'), h.get('summe'), (messreihe[-1]['summe'] if messreihe else None), luecke['obergrenze_bytes'], 'BESTANDEN' if erg['bestanden'] else 'FEHLER'))
    sys.exit(0 if erg['bestanden'] else 3)
if __name__ == '__main__': fall()
