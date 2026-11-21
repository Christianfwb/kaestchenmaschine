#!/usr/bin/env python3
"""Aufgabenobjekt fuer die Zielmaschine (Fable, 2026-10-26, Schritt 1 "eigener Block").
Liest AUFGABE.json, baut daraus den 76-Byte-Header-Vorsatz, berechnet die aufgabe_id und erzeugt die Anzeige
GEGEBEN / GESUCHT / ERFUELLT WENN. Keine Suche, kein Loeser - nur Festlegung und Anzeige.

AUFGABE.json (Schritt 1, Ziel aus nBits wie in V2):
{
 "modus": "nbits",
 "gegeben": {"version": "20000000",
             "vorgaenger_text": "...", ODER "vorgaenger_hash": "<64 hex, Anzeigeform>",
             "merkle_text": "...",     ODER "merkle_wurzel": "<64 hex, Anzeigeform>",
             "zeit": 1792935000, "nbits": "1e00ffff"},
 "gesucht": ["nonce"]
}
Texte werden als UTF-8 ohne Zeilenumbruch gehasht: SHA256d(Text). Anzeigeform = wie im Block-Explorer; im Header liegen die
32 Bytes umgedreht. Aufruf zum Anschauen:  python aufgabe.py [AUFGABE.json]
"""
import sys, json, hashlib, pathlib, datetime
HERE = pathlib.Path(__file__).resolve().parent

def sha256d(b): return hashlib.sha256(hashlib.sha256(b).digest()).digest()
def _hex32(s, name):
    s = ''.join(str(s).split()).lower()
    if len(s) != 64 or any(c not in '0123456789abcdef' for c in s): raise ValueError('%s: 64 Hex-Zeichen erwartet' % name)
    return s
def _hex4(s, name):
    s = ''.join(str(s).split()).lower().removeprefix('0x')
    if len(s) != 8 or any(c not in '0123456789abcdef' for c in s): raise ValueError('%s: 8 Hex-Zeichen erwartet' % name)
    return int(s, 16)

def target_from_nbits(n):
    size = n >> 24; mant = n & 0x7fffff
    if (n & 0x800000) or not (3 <= size <= 32) or not mant: raise ValueError('nBits ungueltig: %08x' % n)
    return mant << (8 * (size - 3))

def laden(pfad):
    a = json.loads(pathlib.Path(pfad).read_text(encoding='utf-8'))
    if a.get('modus') != 'nbits': raise ValueError('modus muss "nbits" sein (Schritt 1); gefunden: %r' % a.get('modus'))
    g = a['gegeben']; herk = {}
    def feld32(text_key, hash_key, name):
        if (text_key in g) == (hash_key in g): raise ValueError('%s: genau eines von %s / %s angeben' % (name, text_key, hash_key))
        if text_key in g:
            t = g[text_key]; d = sha256d(t.encode('utf-8')); herk[name] = dict(text=t, kodierung='UTF-8, ohne Zeilenumbruch', anzeige=d[::-1].hex())
            return d[::-1]            # Anzeigeform als Bytes (big-endian-Darstellung)
        herk[name] = dict(anzeige=_hex32(g[hash_key], name)); return bytes.fromhex(herk[name]['anzeige'])
    version = _hex4(g['version'], 'version'); zeit = int(g['zeit']); nbits = _hex4(g['nbits'], 'nbits')
    if not (0 <= zeit < 2 ** 32): raise ValueError('zeit ausserhalb 32 Bit')
    vorg = feld32('vorgaenger_text', 'vorgaenger_hash', 'vorgaenger'); merk = feld32('merkle_text', 'merkle_wurzel', 'merkle')
    if list(a.get('gesucht', [])) != ['nonce']: raise ValueError('gesucht muss in Stufe A genau ["nonce"] sein')
    prefix = version.to_bytes(4, 'little') + vorg[::-1] + merk[::-1] + zeit.to_bytes(4, 'little') + nbits.to_bytes(4, 'little')
    assert len(prefix) == 76
    ziel = target_from_nbits(nbits)
    norm = json.dumps(dict(modus='nbits', prefix_hex=prefix.hex(), gesucht=['nonce']), sort_keys=True, separators=(',', ':'))
    aid = hashlib.sha256(norm.encode()).hexdigest()
    return dict(prefix=prefix, prefix_hex=prefix.hex(), ziel=ziel, ziel_hex=hex(ziel), ziel_anzeige=ziel.to_bytes(32, 'big').hex(),
                version=version, zeit=zeit, nbits=nbits, herkunft=herk, aufgabe_id=aid, quelle=str(pfad), roh=a)

def anzeige(A):
    h = A['herkunft']; z = datetime.datetime.fromtimestamp(A['zeit'], datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    def zeile_hash(name, info):
        s = '  %-14s %s' % (name, info['anzeige'])
        if 'text' in info: s += '\n  %-14s aus Text %r (%s)' % ('', info['text'], info['kodierung'])
        return s
    nz = 0; zb = A['ziel']
    while nz < 256 and not (zb >> (255 - nz)) & 1: nz += 1
    return '\n'.join([
        'AUFGABE (aufgabe_id %s)' % A['aufgabe_id'][:16],
        'GEGEBEN  - fester 76-Byte-Header-Vorsatz, selbst erzeugt:',
        '  %-14s 0x%08x' % ('Version', A['version']),
        zeile_hash('Vorgaenger', h['vorgaenger']), zeile_hash('Merkle-Wurzel', h['merkle']),
        '  %-14s %d (%s)' % ('Zeit', A['zeit'], z),
        '  %-14s 0x%08x' % ('nBits', A['nbits']),
        '  %-14s %s' % ('Vorsatz-Hex', A['prefix_hex']),
        'GESUCHT  - Nonce (32 Bit, Header-Byte 76..79) und dazu passende innere Werte aller 64 Arbeiter (1168 Bedingungen).',
        'ERFUELLT WENN - alle Arbeiterbedingungen gelten und SHA256d(Header) als little-endian-Zahl <= Ziel aus nBits.',
        '  %-14s %s' % ('Ziel (Anzeige)', A['ziel_anzeige']),
        '  %-14s %d fuehrende Nullbits noetig; rechnerisch ~2^(32-%d) = %s passende Nonces (Zaehlung, keine Garantie)' % (
            'in Worten', nz, nz, ('%.0f' % 2 ** (32 - nz)) if nz <= 32 else '< 1'),
        ('  Vollständiger Blockentwurf: Coinbase und Transaktionen vorhanden; Regelprüfung des Nodes ohne Proof of Work bestanden. PoW bleibt die Aufgabe.' if A['roh'].get('blockentwurf') else '  Eigener Testentwurf: Nur Header-PoW. Merkle-Wurzel aus Text, keine echte Coinbase.'),
    ])

if __name__ == '__main__':
    A = laden(sys.argv[1] if len(sys.argv) > 1 else HERE / 'AUFGABE.json'); print(anzeige(A))
