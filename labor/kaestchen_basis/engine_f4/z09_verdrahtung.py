#!/usr/bin/env python3
"""Z-09 Verdrahtung (gemeinsam fuer Loeser und Vertrag der Pruefstelle; beide kennen die verdeckten Bits nicht).

D1 (headerabhaengige Linie): Block0 vollstaendig, Block1 vollstaendig (Fahrplan + 64 Runden), KEIN Durchgang 2, kein Ziel.
   Verdeckte Noncebits wie in A4 (a4_basis32.w3_bit). Messstellen: Runde 3 (e4, a4), Runde 4 (e5, a5), W18, W19.
D1_VOLL: das aktuelle Programm (a4_basis32.aufbau, Arm M, drei Kompressionen, voller Vergleich H <= T).
D2 (universelle Linie): nur Durchgang 2 ab IV mit acht Zwischenhash-Woertern Z0..Z7 (Herkunft AUFGABE); Z0 traegt
   zwei verdeckte Bits (maske_z0, Bitnummer = Stellenwert im Wort). Messstelle: Runde 0 (e1, a1).

Formelnetz-Anschluss (FR-1/FR-1b) ist ein Treiberschritt ("manuell" in der Karte); FR-2/FR-3 laufen im Kern (erzeugt);
FR-4 wird fuer jede gebuchte Verbindung versucht ("manuell"); identische und umgestellte Dubletten (dieselbe Addition) werden
nicht erneut instanziiert, sondern gezaehlt."""
import bitkern32 as bk
import sha_verdrahtung32 as sv
import a4_basis32 as a4


def wort_mit_verdeckten(kern, name, wert, maske, herkunft):
    """Wort mit verdeckten Bits: START WORT mit maskiertem Wert, bekannte Bits per B-R1, verdeckte ohne Wert (wie a4_basis32)."""
    w = wert & ~maske & 0xffffffff
    nr = kern.buche(f'START {herkunft}', [], 'WORT', (name, w, 32)); kern.worte[name] = nr
    verdeckt = []
    for i in range(32):
        if (maske >> i) & 1: verdeckt.append(f'{name}.{i}')
        else: kern.setze(f'{name}.{i}', (w >> i) & 1, f'B-R1 {name} bit {i}', [nr])
    return verdeckt


def aufbau_d1(kern, aufgabe):
    header76 = bytes.fromhex(aufgabe['header76_hex']); basis = aufgabe['basis']; maske = aufgabe['maske']
    iv = sv.konstanten_woerter(kern, 'k0', 'IV', sv.IV, 'IV')
    W0 = sv.konstanten_woerter(kern, 'k0', 'W', sv.woerter_aus_bytes(header76[:64]), 'HEADER')
    H0, _, _ = sv.kompression(kern, 'k0', iv, W0, start_konst=sv.IV)
    W1 = sv.konstanten_woerter(kern, 'k1', 'W', sv.woerter_aus_bytes(header76[64:76]), 'HEADER')
    w3 = int.from_bytes((basis & 0xffffffff).to_bytes(4, 'little'), 'big')
    maske_w3 = sum(1 << a4.w3_bit(j) for j in range(32) if (maske >> j) & 1)
    verdeckt = wort_mit_verdeckten(kern, 'k1_W3', w3, maske_w3, 'AUFGABE')
    kern.verdeckt = set(verdeckt)
    W1.append('k1_W3'); W1 += sv.konstanten_woerter(kern, 'k1', 'P', sv.PAD1, 'PAD')
    H1, st, W = sv.kompression(kern, 'k1', H0, W1)
    return dict(verdeckt=verdeckt, H1=H1, W=W)


def aufbau_d1_voll(kern, aufgabe):
    H2, verdeckt, zielbit = a4.aufbau(kern, aufgabe)
    return dict(verdeckt=verdeckt, H2=H2, zielbit=zielbit)


def aufbau_d2(kern, aufgabe):
    Z = aufgabe['zwischenhash']; maske = aufgabe['maske_z0']
    iv2 = sv.konstanten_woerter(kern, 'k2', 'IV', sv.IV, 'IV')
    verdeckt = wort_mit_verdeckten(kern, 'k2_Z0', Z[0], maske, 'AUFGABE')
    kern.verdeckt = set(verdeckt)
    Zn = ['k2_Z0']
    for j in range(1, 8):
        n = f'k2_Z{j}'; kern.wort_start(n, Z[j], 'AUFGABE'); Zn.append(n)
    W2 = Zn + sv.konstanten_woerter(kern, 'k2', 'P', sv.PAD2, 'PAD')
    H2, st, W = sv.kompression(kern, 'k2', iv2, W2, start_konst=sv.IV)
    return dict(verdeckt=verdeckt, H2=H2, W=W)


AUFBAU = dict(D1=aufbau_d1, D1_VOLL=aufbau_d1_voll, D2=aufbau_d2)


def verdeckte_vorab(aufgabe):
    if aufgabe['art'] == 'D2': return [f'k2_Z0.{i}' for i in range(32) if (aufgabe['maske_z0'] >> i) & 1]
    return [f'k1_W3.{a4.w3_bit(j)}' for j in range(32) if (aufgabe['maske'] >> j) & 1]


def volle(kern, w): return all(f'{w}.{i}' in kern.wert for i in range(kern.NB))


def formelnetz_anschliessen(kern):
    """FR-1 fuer jede Konstantenaddition mit mindestens einem nicht voll bekannten Wort; FR-1b fuer jede Zweiwortaddition mit
    genau einem voll bekannten Summanden und nicht voll bekannter Summe. Reihenfolge = Verdrahtungsreihenfolge. Liefert Protokoll."""
    prot = []
    for kid, (nr, s) in list(kern.additionen.items()):
        if s[0] == 'B-R5':
            _, w, p, K = s
            if volle(kern, w) and volle(kern, p): continue
            vid = kern.verb_aus_addition(kid); prot.append(dict(kid=kid, regel='FR-1', vid=vid))
        else:
            _, w, p, q = s
            bekannt = [x for x in (p, q) if volle(kern, x)]
            if len(bekannt) != 1 or volle(kern, w): continue
            kern.wortwert_aus_bits(bekannt[0])
            vid = kern.verb_aus_addition(kid); prot.append(dict(kid=kid, regel='FR-1b', vid=vid))
    return prot


def uebersetzen_alle(kern):
    """FR-4 fuer jede Verbindung zwischen zwei Woertern; Dubletten (Schluessel schon als Addierinstanz vorhanden) werden gezaehlt."""
    prot = dict(uebersetzt=[], dubletten=[], umkehr_dubletten=[], abgewiesen=[])
    M = 1 << kern.NB
    for vid in sorted(kern.verb, key=lambda x: int(x[1:])):
        links, rechts, c, nr = kern.verb[vid]
        if rechts is None: continue
        if ('B-R5', links, rechts, c) in kern.entfaltet: prot['dubletten'].append(vid); continue
        if ('B-R5', rechts, links, (-c) % M) in kern.entfaltet: prot['umkehr_dubletten'].append(vid); continue   # gleiche Addition, nur umgestellt
        try:
            kid = kern.uebersetzen(vid); prot['uebersetzt'].append(dict(vid=vid, kid=kid))
        except ValueError as e:
            prot['abgewiesen'].append(dict(vid=vid, grund=str(e)))
    return prot
