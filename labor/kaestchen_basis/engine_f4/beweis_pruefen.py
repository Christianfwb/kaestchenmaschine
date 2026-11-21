"""Gespeichertes Buch erneut prüfen, ohne den Löser auszuführen."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import bitkern32 as bk
from maschine import validiere, vertrag
from pruefer_rueckweg import herleitung_pruefen


def pruefe(folder):
    p=Path(folder)
    a=validiere(json.loads((p/'AUFGABE.json').read_text(encoding='utf-8')))
    v=vertrag(a)
    k=bk.Kern(32)
    def tup(x): return tuple(tup(v) for v in x) if isinstance(x,list) else x
    with gzip.open(p/'BEWEIS.jsonl.gz','rt',encoding='utf-8') as f:
        k.buch=[tup(json.loads(line)) for line in f]
    errors=herleitung_pruefen(k,v)
    if errors:return {'status':'FEHLER','fehler':errors}
    values={}
    for rule,parents,art,info in k.buch:
        if art=='BIT':values[info[0]]=info[1]
    import a4_basis32
    unknown=[j for j in range(32) if a['maske']>>j&1]
    if any(r[2]=='WIDERSPRUCH' for r in k.buch):
        return {'status':'KEINE_LOESUNG','bedingte_aufgabe':a.get('test_w22') is not None,'fehler':[]}
    if any(f'k1_W3.{a4_basis32.w3_bit(j)}' not in values for j in unknown):
        return {'status':'OFFEN','fehler':[]}
    if any(f'k2_H{j}.{i}' not in values for j in range(8) for i in range(32)):
        return {'status':'OFFEN','fehler':[]}
    nonce=a['basis']
    for j in unknown:nonce |= values[f'k1_W3.{a4_basis32.w3_bit(j)}']<<j
    header=bytes.fromhex(a['header76_hex'])+nonce.to_bytes(4,'little')
    digest=hashlib.sha256(hashlib.sha256(header).digest()).digest()
    book_digest=b''.join(sum(values[f'k2_H{j}.{i}']<<i for i in range(32)).to_bytes(4,'big') for j in range(8))
    if book_digest != digest:return {'status':'FEHLER','fehler':['Endhash im Buch weicht von hashlib ab']}
    yes=int.from_bytes(digest,'little')<=a['nbits_ziel'] if a['arm']=='M' else digest.hex()==a['ziel_hash_hex']
    return {'status':'TREFFER' if yes else 'OFFEN','nonce':f'{nonce:08x}','fehler':[],
            'bedingte_aufgabe':a.get('test_w22') is not None}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('ordner');args=p.parse_args()
    try:
        result=pruefe(args.ordner);print(json.dumps(result,ensure_ascii=False,indent=2))
        raise SystemExit(2 if result['fehler'] else 0)
    except Exception as e:
        print('FEHLER:',str(e));raise SystemExit(2)
