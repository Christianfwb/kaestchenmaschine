#!/usr/bin/env python3
"""Mini-Netz-Generator und Zufallsdomaenen, Kopie aus komposition_kind.py (unveraendert) fuer Gleichheitsreihen."""
import random
from ziffern import Netz
import bausteine as BS
def mininetz(seed, w):
    r = random.Random(seed); N = Netz(w); x = N.wort('x'); y = N.wort('y'); ws = [x, y]; eing = list(x) + list(y)
    for i in range(r.randint(2, 5)):
        a = r.choice(ws); b = r.choice(ws); art = r.choice(['add', 'xor', 'rot', 'ch', 'maj', 'neg', 'addself', 'konst', 'alias'])
        if art == 'add': w_ = N.add(a, b, 'a%d' % i)
        elif art == 'addself': w_ = N.add(a, a, 's%d' % i)
        elif art == 'xor': w_ = N.xor(a, b, 'x%d' % i)
        elif art == 'rot': w_ = BS.rot(N, a, r.randrange(1, w), 'r%d' % i)
        elif art == 'ch': w_ = BS.ch(N, a, b, r.choice(ws), 'c%d' % i)
        elif art == 'maj': w_ = BS.maj(N, a, b, r.choice(ws), 'm%d' % i)
        elif art == 'neg': w_ = N.neg(a, 'n%d' % i)
        elif art == 'konst': w_ = N.add(a, N.konst(r.getrandbits(w), 'k%d' % i), 'k%d' % i)
        else: w_ = N.wort('al%d' % i); N.gleich(a, w_); w_ = [N.kanon(v) for v in w_]
        ws.append(w_)
    ws = [[N.kanon(v) for v in ww] for ww in ws]; eing = [N.kanon(v) for v in eing]
    return N, eing, ws
def zufallsdomaenen(N, r, loesung=None, p_frei=0.5):
    dom = list(N.dom)
    for v in range(len(dom)):
        g = N.groesse[v]
        if loesung is not None:
            m = 1 << loesung[v]
            if r.random() < p_frei: m |= r.getrandbits(g)
            dom[v] &= m
        else:
            if r.random() < 0.3: dom[v] &= r.getrandbits(g)       # auch leer moeglich
    return dom
