"""odds.py - Ehrliche Zahlen. Aus nBits (Schwierigkeitsangabe im Header) folgen Target, Difficulty, erwartete Hashes je Block
und eine Schaetzung der Netz-Hashrate (Blockzeit 600 s). Mit der eigenen Hashrate: Chance auf einen Block je Stunde/Tag/Jahr.
Nichts hier ist Marketing: die Zahlen sind das, was jeder Miner verschweigt, wenn er 'Hashrate' anzeigt."""
import math

MAX_TARGET = 0xffff * 2 ** (8 * (0x1d - 3))   # Difficulty 1

def nbits_zu_target(nbits: int) -> int:
    exp = nbits >> 24; mant = nbits & 0x7fffff
    if nbits & 0x800000: mant = -mant
    return mant * 256 ** (exp - 3) if exp >= 3 else mant >> (8 * (3 - exp))

def nbits_aus_header(header76: bytes) -> int:
    return int.from_bytes(header76[72:76], 'little')

def zahlen(target: int, eigene_hashrate: float):
    p = (target + 1) / 2 ** 256                    # Trefferwahrscheinlichkeit je Hash
    erwartet = 1 / p                               # erwartete Hashes bis zum Treffer
    difficulty = MAX_TARGET / target
    netz = erwartet / 600                          # geschaetzte Netz-Hashrate, wenn alle 600 s ein Block kommt
    def chance(sek):
        # 1 - (1-p)^n, numerisch stabil fuer winzige p (sonst wird aus einer positiven Chance eine 0): -expm1(n*log1p(-p))
        n = eigene_hashrate * sek
        return -math.expm1(n * math.log1p(-p))
    def eins_zu(sek):
        c = chance(sek); return round(1 / c) if c > 0 else float('inf')
    return dict(target=target, nullbits=256 - target.bit_length(), difficulty=difficulty, p_je_hash=p, erwartete_hashes=erwartet,
                netz_hashrate_geschaetzt=netz, eigene_hashrate=eigene_hashrate, anteil_am_netz=eigene_hashrate / netz if netz else 0,
                chance_stunde=chance(3600), chance_tag=chance(86400), chance_jahr=chance(86400 * 365.25),
                eins_zu_stunde=eins_zu(3600), eins_zu_tag=eins_zu(86400), eins_zu_jahr=eins_zu(86400 * 365.25),
                erwartete_wartezeit_jahre=(erwartet / eigene_hashrate) / (86400 * 365.25) if eigene_hashrate else float('inf'))

def si(x, einheit='H/s'):
    for f, n in ((1e18, 'E'), (1e15, 'P'), (1e12, 'T'), (1e9, 'G'), (1e6, 'M'), (1e3, 'k')):
        if x >= f: return f'{x / f:.2f} {n}{einheit}'
    return f'{x:.0f} {einheit}'

def text(z):
    return '\n'.join([
        f"Target: {z['nullbits']} fuehrende Nullbits, Difficulty {z['difficulty']:.3e}",
        f"Chance je Hash: 1 zu {z['erwartete_hashes']:.3e}",
        f"Netz-Hashrate (aus nBits geschaetzt, 600 s je Block): {si(z['netz_hashrate_geschaetzt'])}",
        f"Eigene Hashrate: {si(z['eigene_hashrate'])} = Anteil {z['anteil_am_netz']:.3e} des Netzes",
        f"Chance auf einen Block:  je Stunde 1 zu {z['eins_zu_stunde']:.3e}   je Tag 1 zu {z['eins_zu_tag']:.3e}   je Jahr 1 zu {z['eins_zu_jahr']:.3e}",
        f"Erwartete Wartezeit bis zum eigenen Block: {z['erwartete_wartezeit_jahre']:.3e} Jahre",
    ])
