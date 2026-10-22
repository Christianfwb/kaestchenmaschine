#!/usr/bin/env python3
"""STUFE 1c – F2-ABSCHLUSS UND DREIER (Fable, 2026-10-22). Wie lauf_wurzel2.py (gleiche Grenzen 600 s / 400 MiB / 2 500 000 Paare, gleiche
Gate-Regel), aber: F1-Basis wird NICHT neu gemessen, sondern der vorige bestandene Lauf (ERGEBNIS2_E4_F1.json, lauf_wurzel2.py / wurzel_kind2.py,
FIXPUNKT) wird als Beleg wiederverwendet und so gekennzeichnet; F2-Basis EINMAL neu mit wurzel_kind3.py (repariertes Pruef-/Speicherverhalten).
Dreier (E4D F1, F2) nur bei bestandenem Gate (gueltiger F1-Beleg + neuer vollstaendiger F2-Beleg)."""
import json, sys, time, pathlib, platform, hashlib
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent.parent / 'src' / 'kaestchen'))
import lauf_wurzel2 as LW
def kind3(art, fall, aus):
    import subprocess
    return subprocess.Popen([sys.executable, '-I', str(HERE / 'wurzel_kind3.py'), art, fall, aus, str(LW.MAXP)], cwd=str(HERE))
def f1_beleg():
    p = HERE / 'ERGEBNIS2_E4_F1.json'; k = json.loads(p.read_text()); vor = json.loads((HERE / 'ERGEBNIS2_WURZEL.json').read_text())
    e = next(a for a in vor['auswertungen'] if a['art'] == 'E4' and a['fall'] == 'F1')
    e = dict(e); e.update(wiederverwendet=True, herkunft=dict(datei='ERGEBNIS2_E4_F1.json', sha256=hashlib.sha256(p.read_bytes()).hexdigest(), lauf='lauf_wurzel2.py / wurzel_kind2.py, 2026-10-22',
             kind_status=k.get('status'), ergebnis_status=(k.get('ergebnis') or {}).get('status'), paare=(k.get('ergebnis') or {}).get('interne_einschraenkungen', {}).get('paare')))
    # Gueltigkeit des Belegs selbst pruefen (gleiche Kriterien wie Gate)
    if not (k.get('status') == 'OK' and (k.get('ergebnis') or {}).get('status') == 'FIXPUNKT' and not k.get('fehler') and e.get('rueckgabe') == 0 and not e.get('abbruchgrund')):
        e['status'] = 'UNGUELTIGER_BELEG'
    return e
erg = dict(stufe='1c F2-Abschluss + Dreier', beginn=time.strftime('%Y-%m-%d %H:%M:%S'), python=platform.python_version(), grenze=dict(zeit_s=LW.ZEIT_S, ram_mib=LW.RAM_MIB, paare=LW.MAXP), auswertungen=[])
basis = {}
f1 = f1_beleg(); erg['auswertungen'].append(f1); basis[('E4', 'F1')] = f1
print('E4   F1  %s (wiederverwendet: %s)' % (f1['status'], f1['herkunft']['datei']))
basis[('E4', 'F2')] = LW.lauf('E4', 'F2', erg, starter=kind3, ausgabe_dir=HERE)
ok, grund = LW.freigabe(basis); erg['gate'] = dict(freigabe=ok, grund=grund)
if ok:
    for fall in ('F1', 'F2'): LW.lauf('E4D', fall, erg, starter=kind3, ausgabe_dir=HERE)
else:
    for fall in ('F1', 'F2'): erg['auswertungen'].append(dict(art='E4D', fall=fall, status='NOT_RUN', grund=grund))
    print('E4D NOT_RUN:', grund)
erg['ende'] = time.strftime('%Y-%m-%d %H:%M:%S'); erg['gesamt_wall_s'] = round(sum(x.get('wall_s', 0) for x in erg['auswertungen'] if not x.get('wiederverwendet')), 1)
(HERE / 'ERGEBNIS3_WURZEL.json').write_text(json.dumps(erg, indent=1))
