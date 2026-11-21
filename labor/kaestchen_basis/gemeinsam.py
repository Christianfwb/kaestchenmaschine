"""Gemeinsames fuer den SAT-Anschluss (Fable 2026-11-14). Nur Standardbibliothek + F4-Engine (reines Python).
Konventionen: Nonce = basis | low, im Header als 4 Byte Little Endian; Hash als Zahl = int.from_bytes(digest,'little');
Treffer = Hash <= Target (Gleichheit zaehlt). Diese Konventionen stehen auch in task_contract.json und werden dort geprueft."""
import sys, json, hashlib, itertools, time, os
from pathlib import Path
HIER = Path(__file__).resolve().parent
ENGINE = Path(os.environ.get('KAESTCHEN_ENGINE', HIER / 'engine_f4')).resolve()
sys.dont_write_bytecode = True
if str(ENGINE) not in sys.path: sys.path.insert(0, str(ENGINE))

def dh(x): return hashlib.sha256(hashlib.sha256(x).digest()).digest()
def hash_zahl(d): return int.from_bytes(d, 'little')
def nonce_bytes(n): return n.to_bytes(4, 'little')
def sha_datei(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def speichern(p, obj): Path(p).write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding='utf-8')
def laden(p): return json.loads(Path(p).read_text(encoding='utf-8'))

def operator(op, x):
    if op == 'Maj': return int(sum(x) >= 2)
    if op == 'Ch': return x[1] if x[0] else x[2]
    if op == 'Gleich': return int(x[0] and x[1] == x[2])
    if op == 'Kleiner': return int(x[0] or (x[1] and not x[2] and x[3]))
    if op == 'Oder': return int(any(x))
    raise ValueError('unbekannter Operator ' + repr(op))

# ---------- Vertrag ----------
PFLICHT = ('header76_hex', 'basis', 'maske', 'arm', 'nbits_ziel', 'profil', 'target_kind', 'target_hex', 'bitkonvention')
KONVENTION = {'nonce': 'little-endian 4 Byte an Headerposition 76..79, nonce = basis | low',
              'hash_zahl': "int.from_bytes(digest,'little')", 'treffer': 'hash_zahl <= target (Gleichheit zaehlt)'}
def vertrag_pruefen(t):
    import maschine
    for k in PFLICHT:
        if k not in t: raise ValueError('Vertrag: Feld fehlt: ' + k)
    if t.get('test_w22') is not None: raise ValueError('Vertrag: test_w22 ist fuer den SAT-Anschluss nicht erlaubt')
    if t['bitkonvention'] != KONVENTION: raise ValueError('Vertrag: bitkonvention weicht ab')
    if t['target_kind'] not in ('NBITS_ECHT', 'DIAGNOSE'): raise ValueError('Vertrag: target_kind')
    h = bytes.fromhex(t['header76_hex'])
    echt = maschine.ziel_nbits(int.from_bytes(h[72:76], 'little'))
    tgt = int(t['target_hex'], 16)
    if t['target_kind'] == 'NBITS_ECHT' and tgt != echt: raise ValueError('Vertrag: NBITS_ECHT, aber target_hex != nBits-Ziel des Headers')
    if t['target_kind'] == 'DIAGNOSE' and tgt == echt: raise ValueError('Vertrag: DIAGNOSE mit echtem Target - target_kind falsch')
    # Fuer den Aufbau braucht maschine.validiere nbits_ziel == echtes Ziel; die Maschine wird deshalb mit einer
    # Aufgabenkopie gebaut, in der nbits_ziel = target steht (Arm M vergleicht gegen nbits_ziel), und validiere nur
    # fuer die Headerfelder benutzt.
    a = dict(t); a['nbits_ziel'] = echt; maschine.validiere(a)
    return tgt

def aufgabe_fuer_maschine(t):
    """Kopie des Vertrags, wie maschine.aufbau sie erwartet: nbits_ziel = das zu pruefende Target (echt oder Diagnose)."""
    a = {k: t[k] for k in ('header76_hex', 'basis', 'maske', 'arm', 'profil')}
    a['nbits_ziel'] = int(t['target_hex'], 16); a['rueckweg'] = True; a['sekunden'] = t.get('sekunden', 60)
    return a

def freie_bits(t):
    import a4_basis32
    return [(j, f"k1_W3.{a4_basis32.w3_bit(j)}") for j in range(32) if (t['maske'] >> j) & 1]

def digest_aus_werten(get):
    """k2_H0..7 (je 32 Bit, Bit i = 2^i des Worts) -> Digest-Bytes (Woerter big-endian) wie hashlib."""
    return b''.join(sum(get(f'k2_H{j}.{i}') << i for i in range(32)).to_bytes(4, 'big') for j in range(8))


# ---------- Dispatch: Vollmodell (maschine/a4_basis32) oder rundenreduziert (runden_modell) ----------
def ist_reduziert(t): return 'runden' in t
def vertrag_pruefen_alle(t):
    if ist_reduziert(t):
        import runden_modell; runden_modell.pruefen_r(t); return int(t['target_hex'], 16) if t['arm'] == 'M' else None
    return vertrag_pruefen(t)
def bauen(kern, t):
    if ist_reduziert(t):
        import runden_modell; return runden_modell.aufbau_r(kern, t)
    import maschine; return maschine.aufbau(kern, aufgabe_fuer_maschine(t))
def vertrag_von(t):
    if ist_reduziert(t):
        import runden_modell; return runden_modell.vertrag_r(t)
    import maschine; return maschine.vertrag(aufgabe_fuer_maschine(t))
def referenz_digest(t, nonce):
    if ist_reduziert(t):
        import runden_modell; return runden_modell.referenz_digest(t, nonce)
    return dh(bytes.fromhex(t['header76_hex']) + nonce_bytes(nonce))
def loesung_ok(t, digest):
    if t['arm'] == 'W': return digest == bytes.fromhex(t['ziel_hash_hex'])
    return hash_zahl(digest) <= int(t['target_hex'], 16)
def ergebnis_name(t): return 'TREFFER_GEPRUEFT' if (not ist_reduziert(t) and t.get('target_kind') == 'NBITS_ECHT') else 'DIAGNOSE_LOESUNG'
