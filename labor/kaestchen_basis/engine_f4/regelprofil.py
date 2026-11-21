"""Explizite Orchestrierung vorhandener Regeln; keine neue Schlussregel."""
import time
import bitkern32 as bk

REGELN = ['BIT', 'RB-R1', 'Z-R1', 'Z-R2', 'Z-R3', 'RT-R1', 'RT-R2', 'RT-R3']
GRENZEN = {'anschluss_runden': 8, 'anschluss_neue_zeilen': 2000,
           'anschluss_max_eltern': 64, 'anschluss_max_breite': 128,
           'anschluss_eingang_freie_namen': [2,16], 'rt3_runden': 4,
           'rt3_paare': 1200, 'rt3_sekunden_je_runde': 15,
           'rt3_freie_namen': 8, 'rt3_gleichung_freie_namen': 5,
           'buchzeilen': 900000}

def plan(a):
    extended = a['profil'] == 'bits_erweitert'
    return {'profil': a['profil'], 'aktive_regeln': list(REGELN) if extended else
            (['BIT','RB-R1','MONOME','WORT/FORMEL/TEILWORT'] if a['profil']=='zwei' else ['BIT','RB-R1']),
            'nicht_aktiv': ['P-R1','PROJEKTION','GPU','NODE','SUBMIT'],
            'grenzen': dict(GRENZEN) if extended else {},
            'schritte': [], 'begrenzungen': [],
            'abschluss': 'NICHT_GESTARTET', 'mathematisch_vollstaendig': False,
            'hinweis': 'Begrenzte vorhandene Regeln; kein Nachweis aller moeglichen Schlussfolgerungen.'}

def ausfuehren(k, protokoll, meldung=lambda s: None):
    from zielbits import anwenden as zielbits
    from zielteil import anwenden as zielteil
    from zielrelation import anwenden as zielrelation
    from anschluss import saettigen
    from rt3_adapter import anwenden as rt3
    protokoll['abschluss'] = 'LAEUFT'
    def step(name, fn):
        if time.monotonic() > k.deadline: raise bk.Budget('Zeitgrenze vor '+name)
        entry={'regelstufe':name,'status':'GESTARTET','bits_vorher':len(k.wert),'zeilen_vorher':len(k.buch)}
        protokoll['schritte'].append(entry)
        try:
            info=fn(); entry['messung']=info; k.fixpunkt()
        except (bk.Budget,bk.Widerspruch) as e:
            entry['status']='ABGEBROCHEN';entry['grund']=str(e);raise
        entry.update(status='BEENDET',bits_nachher=len(k.wert),zeilen_nachher=len(k.buch))
        meldung('Regelstufe '+name+' beendet')
        return info
    def connection():
        info=saettigen(k, runden=GRENZEN['anschluss_runden'])
        rows=info.get('runden',[])
        clipped=any(x.get('breitengrenzen') or x.get('grenze') for x in rows)
        last=rows[-1] if rows else {}
        progress=bool(last.get('neu') or last.get('tabellen_neue_relationen') or last.get('zusaetzliche_bits'))
        if clipped:protokoll['begrenzungen'].append('RB-Auswahl/Breite/Eltern/Zeilen begrenzt')
        if len(rows)>=GRENZEN['anschluss_runden'] and progress:
            protokoll['begrenzungen'].append('Anschluss-Rundenende mit Fortschritt')
        # Existing bool is diagnostic only, never mathematical completeness.
        k.anschlussbericht=info
        return info
    try:
        step('Z-R1',lambda:zielbits(k))
        step('Z-R2',lambda:zielteil(k))
        step('Z-R3',lambda:zielrelation(k))
        k.tabellen_rueckgabe=True;k.relationstabellen_an=True
        step('RB/RT-R1/RT-R2',connection)
        k.rt3_einsetzen=True;k.rt3_maxgl=GRENZEN['rt3_gleichung_freie_namen']
        for turn in range(GRENZEN['rt3_runden']):
            info=step('RT-R3 Runde '+str(turn+1),lambda:rt3(k,max_pairs=GRENZEN['rt3_paare'],seconds=GRENZEN['rt3_sekunden_je_runde']))
            if not info['neue_zeilen']:break
            step('RB/RT nach RT-R3',connection)
        else:raise bk.Budget('RT-R3 Austauschgrenze')
        protokoll['abschluss']='BEGRENZT_BEENDET' if protokoll['begrenzungen'] else 'REGELFOLGE_BEENDET'
    except bk.Budget as e:
        protokoll['abschluss']='BUDGET';protokoll['begrenzungen'].append(str(e));raise
    except bk.Widerspruch:
        protokoll['abschluss']='WIDERSPRUCH';raise
