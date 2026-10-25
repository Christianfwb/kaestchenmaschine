"""Sabotageproben (EIGENE Ergebnisdatei ERGEBNIS_GRUPPEN_SABOTAGE.json von Anfang an; ERGEBNIS_GRUPPEN.json wird nie angefasst).
S-A: absichtlich falsche Erwartung bei F1 -> FEHLER, SystemExit 3.
S-B: Austausch stillgelegt (Gruppen behalten Initialzeilen) bei F2 -> Speicherung ueber den Verbund bleibt exakt, aber
     globale Konsistenz je Gruppe verletzt -> muss FEHLER/Stopp ausloesen (GF-07 verbindlich).
S-C: Gruppengraph mit Kreis direkt an die Strukturpruefung -> Strukturfehler (GF-08 echte Zykluserkennung)."""
import sys, os, json; HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import gruppen; from stern import Kaestchen
AUS='ERGEBNIS_GRUPPEN_SABOTAGE.json'; p=os.path.join(HERE,AUS); r={}
def lauf(nr, name, ks, frei, erw):
    try:
        gruppen.fall(name, ks, frei, [], erw, ausgabe=AUS); r[nr]=dict(erkannt=False, hinweis='Lauf ging weiter – Sofortstopp NICHT ausgeloest')
    except SystemExit as e:
        r[nr]=dict(erkannt=(e.code==3), exit=e.code, hinweis='FEHLER erkannt, SystemExit 3', protokoll=(json.load(open(p)) if os.path.exists(p) else None))
lauf('S-A','SABOTAGE A: F1 Erwartung absichtlich FIXPUNKT',[Kaestchen('K1',('a','b'),{(0,0),(1,1)}), Kaestchen('K2',('a','b'),{(0,1),(1,0)})],['a','b'],dict(loesungen=0,status='FIXPUNKT'))
echt=gruppen.austausch
def kein_austausch(gr, ka, prot): return False, 0, {}
gruppen.austausch=kein_austausch; gruppen.austausch.aufwand=0; gruppen.austausch.zwischen=[]
lauf('S-B','SABOTAGE B: F2 ohne Austausch',[Kaestchen('K1',('a','b'),{(0,0),(1,1)}), Kaestchen('K2',('a',),{(0,)})],['a','b'],dict(loesungen=1,status='FIXPUNKT'))
gruppen.austausch=echt
class G:  # Attrappe fuer die Strukturpruefung
    def __init__(s,n,v,e): s.name=n; s.vars=v; s.eltern=e; s.kaestchen=[]
try:
    gruppen.strukturpruefung([G('g1',('a',),None),G('g2',('a',),'g1'),G('g3',('a',),'g2')], [('g1','g2',{'a'}),('g2','g3',{'a'}),('g3','g1',{'a'})], [])
    r['S-C']=dict(erkannt=False, hinweis='Kreis NICHT erkannt')
except gruppen.Strukturfehler as f: r['S-C']=dict(erkannt=True, hinweis='Strukturfehler: %s' % f)
alle=all(x['erkannt'] for x in r.values())
json.dump(dict(alle_erkannt=alle, proben=r), open(p,'w'), indent=1, default=str)
for k,v in r.items(): print(k, v['erkannt'], v['hinweis'])
sys.exit(0 if alle else 3)
