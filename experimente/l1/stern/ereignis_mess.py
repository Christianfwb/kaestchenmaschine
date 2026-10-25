"""INSTRUMENTIERTE KOPIE von ereignis.arbeitsliste (GO Christian 2026-10-25 12:25). Gleiche Logik Zeile fuer Zeile; zusaetzlich ein Messhaken mess(punkt, zustand),
der an definierten MESSPUNKTEN den tatsaechlichen Zustand der Arbeitsstrukturen (Nachrichtenspeicher N, Schlange, drin, neu_eingang, nachbarn, byname) uebergibt.
Messpunkte: 'M0 nach Aufbau' | 'Ma nach Empfang' (nach jedem Semijoin) | 'Mb nach Entnahme' (nach dem Senden) | 'ME Ende'.
Der Haken liest nur; er veraendert nichts. Dass die Kopie identisch arbeitet, wird im Vergleichslauf gegen das Original ereignis.arbeitsliste geprueft (E0). ereignis.py bleibt unveraendert."""
import time, collections, gruppen
NIE = None
def arbeitsliste(gruppen_, kanten, prot, z, mess=lambda punkt, zustand: None):
    t_aufbau = time.perf_counter()
    byname = {g.name: g for g in gruppen_}; nachbarn = collections.defaultdict(list)
    for a, b, S in kanten: nachbarn[a].append((b, S)); nachbarn[b].append((a, S))
    N = {(a, b): NIE for a, b, S in kanten}; N.update({(b, a): NIE for a, b, S in kanten})
    neu_eingang = {g.name: set() for g in gruppen_}
    schlange = collections.deque(g.name for g in gruppen_); drin = set(schlange)
    for g in gruppen_: neu_eingang[g.name] = set()
    z['aufbau_s'] = round(time.perf_counter() - t_aufbau, 6); z['max_schlange'] = len(schlange)
    zustand = dict(N=N, schlange=schlange, drin=drin, neu_eingang=neu_eingang, nachbarn=nachbarn, byname=byname)
    mess('M0 nach Aufbau', zustand)
    while schlange:
        if len(drin) != len(schlange): raise gruppen.Strukturfehler('Arbeitsliste: Doppeleintrag')
        name = schlange.popleft(); drin.discard(name); g = byname[name]; z['bearbeitungen'] += 1
        for h in sorted(neu_eingang[name]):
            S = dict(nachbarn[name])[h]; M = N[(h, name)]; assert M is not NIE
            s = g.semijoin(S, M); z['gestrichen'] += s
            if s: prot.append(dict(bearbeitung=z['bearbeitungen'], gruppe=name, von=h, gestrichen=s, verbleibend=len(g.zeilen)))
            mess('Ma nach Empfang', zustand)
            if not g.zeilen: prot.append(dict(bearbeitung=z['bearbeitungen'], gruppe=name, ereignis='WIDERSPRUCH: Gruppe leer')); mess('ME Ende', zustand); return True
        neu_eingang[name] = set()
        for h, S in nachbarn[name]:
            P = frozenset(g.proj(S)); z['nachrichten_geprueft'] += 1
            if N[(name, h)] is NIE or N[(name, h)] != P:
                N[(name, h)] = P; z['nachrichten_gesendet'] += 1; neu_eingang[h].add(name)
                if h not in drin: schlange.append(h); drin.add(h); z['max_schlange'] = max(z['max_schlange'], len(schlange))
        mess('Mb nach Entnahme', zustand)
    mess('ME Ende', zustand); return False
