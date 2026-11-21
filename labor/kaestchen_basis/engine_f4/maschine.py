"""Lokale Arbeitsmaschine: Aufgabenvertrag, beidseitige Propagation, Prüfung.

Kein Netzwerk, keine Bereichsschleife und keine Übermittlung an einen Node.
Jeder Lauf ist eine einzelne, explizite Aufgabe.
"""
import argparse
import gc
import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import time
import bitkern32 as bk
import a4_basis32 as basis
import sha_verdrahtung32 as sv
from rueckweg import KernRueckweg, KernZweiBit
from pruefer_rueckweg import herleitung_pruefen

ROOT = Path(__file__).resolve().parent


def ziel_nbits(n):
    e, m = n >> 24, n & 0x7fffff
    if n & 0x800000 or not m: raise ValueError('Ungültiges nBits')
    t = m >> (8*(3-e)) if e <= 3 else m << (8*(e-3))
    if not 0 < t < 1 << 256: raise ValueError('Ziel außerhalb von 256 Bit')
    return t


def validiere(a):
    h = bytes.fromhex(a['header76_hex'])
    if len(h) != 76: raise ValueError('Genau 76 feste Headerbytes erforderlich')
    for n in ('basis', 'maske'):
        if type(a[n]) is not int or not 0 <= a[n] <= 0xffffffff:
            raise ValueError(n + ' muss ein 32-Bit-Wert sein')
    if a['basis'] & a['maske']: raise ValueError('Freie Bits müssen in der Basis null sein')
    if a['arm'] not in ('M', 'W'): raise ValueError('Unbekannter Zieltyp')
    if a['arm'] == 'M':
        if a['nbits_ziel'] != ziel_nbits(int.from_bytes(h[72:76], 'little')):
            raise ValueError('Ziel passt nicht zu nBits im Header')
    elif len(bytes.fromhex(a['ziel_hash_hex'])) != 32:
        raise ValueError('Wunschhash muss 32 Bytes haben (Digest-Reihenfolge)')
    if a.get('profil') not in ('bits', 'zwei', 'bits_erweitert'):
        raise ValueError('Profil muss bits, bits_erweitert oder zwei sein')
    if a['profil'] == 'zwei' and a['maske'].bit_count() != 2:
        raise ValueError('Das MONOME-Profil benötigt genau zwei freie Bits')
    if a['profil'] == 'bits_erweitert' and (a['arm'] != 'M' or a.get('rueckweg', True) is not True):
        raise ValueError('Erweitertes Profil verlangt Arm M und aktivierten Rueckweg')
    q = a.get('test_w22')
    if q is not None and (type(q) is not int or not 0 <= q <= 0xffffffff):
        raise ValueError('Ungültiger Testwert W22')
    return a


def aufbau(k, a):
    outputs, hidden, goal = basis.aufbau(k, a)
    if a.get('test_w22') is not None:
        # Die zusätzliche Annahme steht sichtbar im Vertrag; kein Zielwissen vortäuschen.
        nr = k.wort_start('TEST_W22', a['test_w22'], 'TEST')
        for i in range(32):
            k.xor_gl([f'k1_W22.{i}', f'TEST_W22.{i}'], 0,
                     f'B-R4 zugelassene TEST-Annahme W22 bit {i}', [])
    return outputs, hidden, goal


def vertrag(a):
    # Eigener Aufbau ausschließlich aus der Aufgabe, ohne Lösungsbuch.
    if a['profil'] == 'zwei':
        hidden = [f'k1_W3.{basis.w3_bit(j)}' for j in range(32) if a['maske'] >> j & 1]
        k = bk.KernMonome(32, verdeckt=hidden)
    else: k = bk.Kern(32)
    aufbau(k, a)
    return bk.vertrag_aus(k)


def snapshot(k):
    names = set()
    edges = []
    for nr, (reg, parents, art, info) in enumerate(k.buch):
        if art == 'GL':
            words = sorted({n.rsplit('.', 1)[0] for n in info[0] if '_' in n})
            names.update(words)
        if art == 'ADD':
            kid, key = info
            names.update(n for n in key[1:3] if isinstance(n, str))
            if key[0] == 'B-R6': names.add(key[3])
            edges.append({'buch': nr, 'regel': reg, 'kennung': kid, 'gleichung': key})
    boxes = []
    for word in sorted(n for n in names if n.startswith(('k0_', 'k1_', 'k2_'))):
        bits = [k.bit(f'{word}.{i}') for i in range(32)]
        n = sum(b is not None for b in bits)
        value = sum((b or 0) << i for i, b in enumerate(bits)) if n == 32 else None
        proofs = [{'bit': i, 'wert': b, 'buch': k.her[f'{word}.{i}'],
                   'regel': k.buch[k.her[f'{word}.{i}']][0]} for i, b in enumerate(bits) if b is not None]
        forms = sum(f'{word}.{i}' in getattr(k, 'form', {}) for i in range(32))
        boxes.append({'wort': word, 'bekannte_bits': n, 'formen': forms,
                      'wert': None if value is None else f'{value:08x}',
                      'bitbild': ''.join('?' if b is None else str(b) for b in reversed(bits)),
                      'belege': proofs})
    return boxes, edges


def rechne(a, out=None, meldung=lambda s: None):
    validiere(a)
    start = time.monotonic()
    meldung('Aufgabenvertrag aufbauen …')
    v = vertrag(a)
    gc.collect()
    hidden = [f'k1_W3.{basis.w3_bit(j)}' for j in range(32) if a['maske'] >> j & 1]
    k = KernZweiBit(32, verdeckt=hidden) if a['profil'] == 'zwei' else KernRueckweg(32)
    k.deadline = time.monotonic() + min(max(float(a.get('sekunden', 60)), 1), 300)
    k.rueckweg_an = a.get('rueckweg', True)
    from regelprofil import plan, ausfuehren as erweiterte_regeln
    regelprotokoll = plan(a)
    stopped = None
    meldung('Kästchen verbinden; Vorwärts- und Rückregeln bereitstellen …')
    try:
        outputs, _, _ = aufbau(k, a)
        if a['profil'] == 'zwei': k.anschluss_start()
        meldung('Bekanntes Wissen in beide Richtungen weitergeben …')
        k.fixpunkt()
        if a['profil'] == 'bits_erweitert':
            erweiterte_regeln(k, regelprotokoll, meldung)
        else:
            regelprotokoll['abschluss'] = 'BASIS_FIXPUNKT'
    except bk.Widerspruch:
        stopped = 'Widerspruch'
        regelprotokoll['abschluss'] = 'WIDERSPRUCH'
    except bk.Budget as e:
        stopped = 'Budget: ' + str(e)
        regelprotokoll['abschluss'] = 'BUDGET'
        if str(e) not in regelprotokoll['begrenzungen']: regelprotokoll['begrenzungen'].append(str(e))
    meldung('Herleitungen unabhängig vom Inversionsverfahren nachrechnen …')
    errors = herleitung_pruefen(k, v)
    # Freigabe liest Werte aus dem geprüften Buch, niemals nur aus dem Laufzustand.
    proven = {row[3][0]: row[3][1] for row in k.buch if row[2] == 'BIT'}
    result = {'aufgabe': a, 'status': 'OFFEN', 'grund': stopped or 'Fixpunkt ohne vollständige Nonce',
              'prueffehler': errors, 'nonce': None, 'hash': None,
              'bedingte_aufgabe': a.get('test_w22') is not None,
              'buchzeilen': len(k.buch), 'zaehler': dict(k.zb), 'regelprofil': regelprotokoll}
    if stopped is None and a['profil'] == 'bits_erweitert':
        result['grund'] = 'Begrenzte Regelarbeit beendet; keine vollstaendige Nonce hergeleitet'
    if errors:
        result.update(status='FEHLER', grund='Beweisprüfung fehlgeschlagen')
    elif stopped == 'Widerspruch':
        if any(row[2] == 'WIDERSPRUCH' for row in k.buch):
            result.update(status='KEINE_LOESUNG', grund='Geprüfter Widerspruch unter genau diesen Aufgabenbedingungen')
    elif stopped is None and all(n in proven for n in hidden) and all(f'k2_H{j}.{i}' in proven for j in range(8) for i in range(32)):
        nonce = a['basis']
        for j in range(32):
            if a['maske'] >> j & 1: nonce |= proven[f'k1_W3.{basis.w3_bit(j)}'] << j
        header = bytes.fromhex(a['header76_hex']) + nonce.to_bytes(4, 'little')
        digest = hashlib.sha256(hashlib.sha256(header).digest()).digest()
        book_digest=b''.join(sum(proven[f'k2_H{j}.{i}']<<i for i in range(32)).to_bytes(4,'big') for j in range(8))
        passed = int.from_bytes(digest, 'little') <= a['nbits_ziel'] if a['arm'] == 'M' else digest.hex() == a['ziel_hash_hex']
        result.update(nonce=f'{nonce:08x}', hash=digest[::-1].hex())
        if book_digest != digest:
            result.update(status='FEHLER', grund='Buch-Endhash stimmt nicht mit der unabhängigen Referenz überein')
        elif passed:
            result.update(status='TREFFER', grund='Nonce im geprüften Buch hergeleitet; vollständiger Header zusätzlich mit hashlib geprüft')
        else:
            # Kein Bereichsurteil aus einem einzigen abgelehnten Header.
            result.update(status='OFFEN', grund='Abgeleitete Belegung erfüllt das vollständige Ziel nicht')
    meldung('Kästchenliste und Herkunft der Bits zusammenstellen …')
    # Ein Budget kann unmittelbar vor dem Buchen eines Werts greifen.
    # Die Anzeige enthält deshalb nur tatsächlich gebuchte Werte.
    k.wert={n:val for n,val in k.wert.items() if n in proven and n in k.her}
    result['kaestchen'], result['additionen'] = snapshot(k)
    result['sekunden'] = round(time.monotonic() - start, 3)
    result['rueckwegzeilen'] = sum(r[0] == 'RB-R1 XOR-Elimination' for r in k.buch)
    if out:
        out = Path(out); out.mkdir(parents=True, exist_ok=True)
        with gzip.open(out/'BEWEIS.jsonl.gz', 'wt', encoding='utf-8', compresslevel=1) as f:
            for row in k.buch: f.write(json.dumps(row, ensure_ascii=False) + '\n')
        (out/'ERGEBNIS.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        (out/'AUFGABE.json').write_text(json.dumps(a, ensure_ascii=False, indent=2), encoding='utf-8')
        lines = [result['status'], result['grund'], f"Dauer: {result['sekunden']} s; Prüffehler: {len(errors)}",
                 'Zusätzliche W22-Testannahme: ' + str(result['bedingte_aufgabe']),
                 'Wort | bekannte Bits | Wert | Bits (? = offen)']
        (out/'REGELPROTOKOLL.json').write_text(json.dumps(regelprotokoll, ensure_ascii=False, indent=2), encoding='utf-8')
        lines += [f"{b['wort']} | {b['bekannte_bits']}/32 | {b['wert'] or 'offen'} | {b['bitbild']}" for b in result['kaestchen']]
        (out/'KAESTCHEN.txt').write_text('\n'.join(lines), encoding='utf-8')
    return result


def beispiel(art):
    header = bytes.fromhex((ROOT/'H970000.hex').read_text().strip())
    nonce = int.from_bytes(header[76:], 'little')
    mask = {'bekannt': 0, 'zwei': 3, 'offen': 0xffffffff, 'rueckweg': 0xffffffff, 'erweitert': 0xffffffff}[art]
    a = dict(header76_hex=header[:76].hex(), basis=nonce & ~mask, maske=mask,
             arm='M', nbits_ziel=ziel_nbits(int.from_bytes(header[72:76], 'little')),
             profil='zwei' if art == 'zwei' else ('bits_erweitert' if art == 'erweitert' else 'bits'), sekunden=90,
             beschreibung='Historischer Block H970000 – Offline-Kontrollaufgabe')
    if art == 'erweitert':
        a['beschreibung'] += '; erweiterte belegte Ziel- und Tabellenregeln, begrenzt'
    if art == 'rueckweg':
        # Nur zur Erzeugung einer ausdrücklich gekennzeichneten Kontrollaufgabe.
        a['test_w22'] = referenz_fahrplan(header)[22]
        a['beschreibung'] += '; W22 aus bekannter Lösung vorgegeben (künstliche Zusatzinformation)'
    return a


def referenz_fahrplan(header):
    def r(x, n): return ((x >> n) | (x << (32-n))) & 0xffffffff
    w = [int.from_bytes(header[j:j+4], 'big') for j in range(64, 80, 4)] + [0x80000000] + [0]*10 + [640]
    for t in range(16, 64):
        x,y = w[t-15],w[t-2]
        w.append((w[t-16] + (r(x,7)^r(x,18)^(x>>3)) + w[t-7] + (r(y,17)^r(y,19)^(y>>10))) & 0xffffffff)
    return w


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--beispiel', choices=['bekannt','zwei','offen','rueckweg','erweitert'])
    parser.add_argument('--aufgabe')
    parser.add_argument('--ausgabe', default=str(ROOT/'letzter_lauf'))
    args=parser.parse_args()
    try:
        if __import__('os').name == 'nt':
            from windows_limits import install
            install(2*1024**3)
        a=json.loads(Path(args.aufgabe).read_text(encoding='utf-8-sig')) if args.aufgabe else beispiel(args.beispiel or 'rueckweg')
        result=rechne(a, args.ausgabe, lambda s: print(s, flush=True))
        print('Gespeichertes Buch in einem getrennten Prüfprozess kontrollieren …',flush=True)
        check=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'beweis_pruefen.py'),str(Path(args.ausgabe).resolve())],
                             capture_output=True,text=True,encoding='utf-8',timeout=60,
                             creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        fresh=json.loads(check.stdout) if check.returncode==0 else {'status':'FEHLER','fehler':[check.stdout,check.stderr]}
        result['getrennte_pruefung']=fresh
        if fresh.get('fehler') or (result['status'] in ('TREFFER','KEINE_LOESUNG') and
                                  (fresh['status']!=result['status'] or (result['status']=='TREFFER' and fresh['nonce']!=result['nonce']))):
            result.update(status='FEHLER',grund='Getrennter Prüfprozess bestätigt das Ergebnis nicht')
        (Path(args.ausgabe)/'ERGEBNIS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        if result['status'] != 'FEHLER':
            from pfadarchiv import export
            print('Pfade und offene Voraussetzungen speichern …',flush=True)
            export(args.ausgabe)
        print(result['status'], result['nonce'], result['sekunden'], 's', flush=True)
        raise SystemExit(2 if result['status']=='FEHLER' else 0)
    except Exception as e:
        print('FEHLER:', type(e).__name__, str(e), flush=True)
        raise SystemExit(2)
