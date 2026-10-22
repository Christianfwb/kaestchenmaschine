#!/usr/bin/env python3
"""ABLAUFREGRESSION GATE (Fable, 2026-10-22): Simulierte Basisergebnisse -> beide Zusatzlaeufe E4D muessen NOT_RUN sein und es darf KEIN Kindprozess
fuer E4D gestartet werden. Faelle: Basis OPEN (Paargrenze), OFFEN (Timeout extern), RAM-Abbruch, FEHLER, Rueckgabecode != 0, fehlende Datei,
ungueltige Datei, nur ein Fall FIXPUNKT; Positivfall: beide FIXPUNKT -> E4D gestartet. Kein echter Wurzellauf, Laufzeit < 5 s."""
import json, sys, pathlib, tempfile, time
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent.parent / 'src' / 'kaestchen'))
import lauf_wurzel2 as LW
class Fake:
    def __init__(self, rc, dauer=0.0): self.rc = rc; self.pid = 0; self.t = time.perf_counter() + dauer; self.returncode = None
    def poll(self):
        if time.perf_counter() >= self.t: self.returncode = self.rc; return self.rc
        return None
    def kill(self): self.returncode = -9
    def wait(self): return self.returncode
def szenario(name, basis_f1, basis_f2, erwartet_freigabe):
    """basis_*: dict(datei=<json-dict|None|'kaputt'>, rc=int, dauer=s) fuer E4; E1 immer OK."""
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td); gestartet = []
        def starter(art, fall, aus):
            gestartet.append((art, fall)); p = td / aus
            if art == 'E1':
                p.write_text(json.dumps(dict(status='OK', ergebnis=dict(status='FIXPUNKT'), schritte=[dict(name='E1')]))); return Fake(0)
            if art == 'E4D':
                p.write_text(json.dumps(dict(status='OK', ergebnis=dict(status='FIXPUNKT'), schritte=[]))); return Fake(0)
            b = basis_f1 if fall == 'F1' else basis_f2
            if b['datei'] == 'kaputt': p.write_text('{nicht json')
            elif b['datei'] is not None: p.write_text(json.dumps(b['datei']))
            return Fake(b.get('rc', 0), b.get('dauer', 0.0))
        LW.ZEIT_S = 0.5 if 'Timeout' in name else 600.0
        LW.RAM_MIB = 400.0
        if 'RAM' in name: LW.rss_mib = lambda pid: 999.0
        else: LW.rss_mib = lambda pid: 10.0
        erg = LW.hauptlauf(starter=starter, ausgabe_dir=td, protokoll='gate.json')
        e4d = [a for a in erg['auswertungen'] if a['art'] == 'E4D']
        not_run = all(a['status'] == 'NOT_RUN' for a in e4d); e4d_gestartet = any(a == 'E4D' for a, _ in gestartet)
        ok = (erg['gate']['freigabe'] == erwartet_freigabe) and (not_run != erwartet_freigabe) and (e4d_gestartet == erwartet_freigabe)
        return dict(szenario=name, freigabe=erg['gate']['freigabe'], grund=erg['gate']['grund'], e4d_not_run=not_run, e4d_kind_gestartet=e4d_gestartet, bestanden=ok)
FIX = dict(status='OK', ergebnis=dict(status='FIXPUNKT'), schritte=[dict(name='x')])
OPEN = dict(status='OK', ergebnis=dict(status='OPEN'), schritte=[dict(name='x')], open_grund='Paargrenze')
FEHL = dict(status='FEHLER', fehler=dict(name='Zeuge verloren'), schritte=[dict(name='x')])
res = [
    szenario('Positiv: beide FIXPUNKT', dict(datei=FIX), dict(datei=FIX), True),
    szenario('Basis F1 OPEN (Paargrenze)', dict(datei=OPEN), dict(datei=FIX), False),
    szenario('Basis F2 OPEN (Paargrenze)', dict(datei=FIX), dict(datei=OPEN), False),
    szenario('Basis F1 Timeout extern', dict(datei=FIX, dauer=2.0), dict(datei=FIX), False),
    szenario('Basis F2 RAM-Abbruch extern', dict(datei=FIX), dict(datei=FIX, dauer=2.0), False),
    szenario('Basis F1 FEHLER', dict(datei=FEHL, rc=2), dict(datei=FIX), False),
    szenario('Basis F2 Rueckgabecode 1 trotz FIXPUNKT-Datei', dict(datei=FIX), dict(datei=FIX, rc=1), False),
    szenario('Basis F1 Datei fehlt', dict(datei=None), dict(datei=FIX), False),
    szenario('Basis F2 Datei ungueltig', dict(datei=FIX), dict(datei='kaputt'), False),
    szenario('Basis F1 Status-Feld fehlt (ergebnis ohne status)', dict(datei=dict(status='OK', ergebnis={}, schritte=[])), dict(datei=FIX), False),
    szenario('Basis F2 RAM-Abbruch in der ABSCHLUSSPRUEFUNG trotz zuvor FIXPUNKT (Schritte FIXPUNKT, kein ergebnis-Block)',
             dict(datei=FIX), dict(datei=dict(status='LAEUFT', schritte=[dict(name='Austausch 2 E4', status='FIXPUNKT'), dict(name='Austausch 2 E1', status='FIXPUNKT')]), dauer=2.0), False),
    szenario('Basis F1 wiederverwendet (gueltiger Beleg) + F2 neu FIXPUNKT', dict(datei=FIX), dict(datei=FIX), True),
]
alle = all(r['bestanden'] for r in res)
json.dump(dict(bestanden=alle, szenarien=res), open(HERE / 'ERGEBNIS_GATE_TEST.json', 'w'), indent=1)
for r in res: print('%-5s %s -> freigabe=%s not_run=%s gestartet=%s' % ('OK' if r['bestanden'] else 'FEHL', r['szenario'], r['freigabe'], r['e4d_not_run'], r['e4d_kind_gestartet']))
print('GATE-TEST', 'BESTANDEN' if alle else 'NICHT BESTANDEN'); sys.exit(0 if alle else 1)
