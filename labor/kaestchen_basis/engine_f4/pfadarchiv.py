"""Vergleichbare Struktur und Wissensstände aus bereits geprüften Büchern.
Keine Referenzwerte werden in den Löser zurückgespeist.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path


def lesen(path):
    with gzip.open(path, 'rt', encoding='utf-8') as f: return json.load(f)


def export(ordner):
    p=Path(ordner)
    result=json.loads((p/'ERGEBNIS.json').read_text(encoding='utf-8'))
    check=result.get('getrennte_pruefung',{})
    if result['prueffehler'] or not check or check.get('fehler') or check.get('status')=='FEHLER':
        raise ValueError('Ein fehlerfrei getrennt geprüftes Buch ist erforderlich')
    with gzip.open(p/'BEWEIS.jsonl.gz','rt',encoding='utf-8') as f:
        rows=[json.loads(line) for line in f]
    known={info[0]:{'wert':info[1],'beleg':nr,'quelle':'EINGABE' if rule.startswith('START ') or rule.startswith('B-R1 ') else 'HERLEITUNG'}
           for nr,(rule,parents,art,info) in enumerate(rows) if art=='BIT'}
    links=[]
    for nr,(rule,parents,art,info) in enumerate(rows):
        if art=='GL':
            names=sorted(info[0]); relation={'art':art,'bits':names,'paritaet':info[1]}
        elif art=='TAF':
            names=list(info[1]); relation={'art':art,'operator':info[0],'bits':names}
        else: continue
        key=hashlib.sha256(json.dumps(relation,sort_keys=True).encode()).hexdigest()
        links.append(dict(relation,id=key,buch=nr,eltern=parents,regel=rule,
                          unbekannt=[n for n in names if n not in known]))
    sources={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in Path(__file__).parent.glob('*.py')}
    data={'schema':1,'aufgabe':result['aufgabe'],'status':result['status'],
          'programmdateien':sources,'buch_sha256':hashlib.sha256((p/'BEWEIS.jsonl.gz').read_bytes()).hexdigest(),
          'bits':known,'verbindungen':links,
          'hinweis':'Unbekannt-Liste ist lokaler Regelbedarf, kein Beweis globaler Unlösbarkeit. Vollständige Elternketten stehen im BEWEIS.jsonl.gz.'}
    with gzip.open(p/'PFADE.json.gz','wt',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False)
    focus=['k1_W3','k1_W18','k1_W20','k1_W22']
    lines=['Gespeicherte Arbeitsgrundlage – keine Lösung vorausgesetzt',
           f"Status: {result['status']}; getrennte Prüfung ohne Fehler",
           'Vollständige Verbindungen: PFADE.json.gz; Herleitungsketten: BEWEIS.jsonl.gz',
           'Eine offene Gleichung kann mehrere alternative Ergänzungen zulassen. Tabellen können auch mit unvollständigen Eingaben entscheiden.']
    for w in focus:
        count=sum(f'{w}.{i}' in known for i in range(32))
        lines.append(f'\n{w}: {count}/32 Bits bekannt')
        target=next((f'{w}.{i}' for i in range(32) if f'{w}.{i}' not in known),None)
        if target:
            candidates=[r for r in links if r['art']=='GL' and target in r['bits']]
            candidates.sort(key=lambda r:len(r['unbekannt']))
            for r in candidates[:2]:
                needs=[n for n in r['unbekannt'] if n!=target]
                lines.append(f"  Für {target}, Alternative Buchzeile {r['buch']}: noch {', '.join(needs) or 'bereit'}")
    (p/'PFADKARTE.txt').write_text('\n'.join(lines),encoding='utf-8')
    return {'bekannte_bits':len(known),'verbindungen':len(links)}


def vergleichen(alt,neu):
    a,b=lesen(Path(alt)/'PFADE.json.gz'),lesen(Path(neu)/'PFADE.json.gz')
    fields=['maske','basis','arm','profil','test_w22','rueckweg']
    differences=[f for f in fields if a['aufgabe'].get(f)!=b['aufgabe'].get(f)]
    ai={r['id'] for r in a['verbindungen']};bi={r['id'] for r in b['verbindungen']}
    ak,bk=set(a['bits']),set(b['bits'])
    return {'aufgabenbedingungen_unterschiedlich':differences,
            'programm_identisch':a['programmdateien']==b['programmdateien'],
            'header_identisch':a['aufgabe']['header76_hex']==b['aufgabe']['header76_hex'],
            'ziel_identisch':a['aufgabe'].get('nbits_ziel')==b['aufgabe'].get('nbits_ziel') and a['aufgabe'].get('ziel_hash_hex')==b['aufgabe'].get('ziel_hash_hex'),
            'gemeinsame_verbindungen':len(ai&bi),'nur_alt_verbindungen':len(ai-bi),'nur_neu_verbindungen':len(bi-ai),
            'neu_bekannte_bits':sorted(bk-ak),'nicht_mehr_bekannte_bits':sorted(ak-bk),
            'andere_bitwerte':sorted(n for n in ak&bk if a['bits'][n]['wert']!=b['bits'][n]['wert']),
            'hinweis':'Andere Headerwerte sind kein Fehler. Unterschiedliche Bedingungen oder Programmstände erlauben keine isolierte Fortschrittsbehauptung.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('ordner');parser.add_argument('--vergleich')
    args=parser.parse_args()
    print(json.dumps(vergleichen(args.ordner,args.vergleich) if args.vergleich else export(args.ordner),ensure_ascii=False,indent=2))
