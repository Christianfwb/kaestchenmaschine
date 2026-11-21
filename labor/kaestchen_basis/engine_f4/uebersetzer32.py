"""FR-4: checked word relation -> existing constant adder -> two-input MONOME.
No SHA driver. Source modules remain unchanged. Whole-word writes into active
forms are deferred to the translated adder, never overwrite a form with a BIT.
"""
from collections import deque
import bitkern32 as bk
from formelnetz32 import KernFormel, aus_buch as formel_aus_buch


class KernUebersetzer(KernFormel, bk.KernMonome):
    def __init__(self, nb, verdeckt, budget=None, max_ereignisse=100000):
        if nb not in (4, 8, 32):
            raise ValueError('unsupported word width')
        bk.KernMonome.__init__(self, nb, budget, 'UEBERSETZER', verdeckt)
        # Only word/formula metadata, not the temporary object's base kernel.
        empty = KernFormel(nb, budget, max_ereignisse=max_ereignisse)
        for key in ('wrel', 'wortwert', 'ausdr', 'ausdr_nr', 'ausdr_index',
                    'verb', 'verb_index', 'sym_verb', 'version', 'zustand',
                    'erledigt', 'arbeit_f', 'ereignisse', 'max_ereignisse', 'status'):
            setattr(self, key, getattr(empty, key))
        for key, value in empty.zb.items():
            self.zb.setdefault(key, value)

    def _stop(self):
        if getattr(self, 'status', None) == 'WIDERSPRUCH':
            self.arbeit.clear()
            self.arbeit_f.clear()
            raise RuntimeError('terminal checked contradiction')

    def buche(self, regel, eltern, art, info):
        self._stop()
        return bk.Kern.buche(self, regel, eltern, art, info)

    def setze(self, name, wert, regel, eltern):
        self._stop()
        try:
            return bk.Kern.setze(self, name, wert, regel, eltern)
        except bk.Widerspruch:
            self.status = 'WIDERSPRUCH'
            self.arbeit.clear(); self.arbeit_f.clear()
            raise

    def setze_form(self, name, k, V, regel, eltern):
        self._stop()
        return bk.KernLF.setze_form(self, name, k, V, regel, eltern)

    def beziehung(self, V, k, regel, eltern):
        self._stop()
        return bk.KernMonome.beziehung(self, V, k, regel, eltern)

    def _kennung(self, schluessel, nr_quelle, regel):
        self._stop()
        if nr_quelle is not None and self.buch[nr_quelle][2] == 'VERB':
            # This label changes only ADD. All carry/sum lines use existing B-R5.
            if schluessel[0] != 'B-R5':
                raise ValueError('FR-4 only constant addition')
            regel = 'FR-4 addition'
        return bk.Kern._kennung(self, schluessel, nr_quelle, regel)

    def uebersetzen(self, vid):
        self._stop()
        left, right, c, nr = self.verb[vid]
        if right is None or left == right:
            raise ValueError('FR-4 requires two distinct word symbols')
        # Registry consistency is also independently checked from the book.
        if self.buch[nr][2] != 'VERB' or self.buch[nr][3][0] != vid:
            raise ValueError('missing relation source')
        return self.addition_konst(left, right, c, 'FR-4', nr)

    def wert_aus_verb(self, vid, ausloeser=None):
        self._stop()
        left, right, _, _ = self.verb[vid]
        if any(f'{s}.{i}' in self.form for s in (left, right) if s is not None
               for i in range(self.NB)):
            # Numeric FR-3 cannot legally erase an active MONOME form.
            # FR-4 + MONOME handles that dependency through its existing rules.
            return None
        return KernFormel.wert_aus_verb(self, vid, ausloeser)

    def start_spaet(self, name, wert):
        self._stop()
        try:
            return bk.KernMonome.start_spaet(self, name, wert)
        except bk.Widerspruch:
            self.status = 'WIDERSPRUCH'
            self.arbeit.clear(); self.arbeit_f.clear()
            raise

    def fixpunkt(self):
        if self.status == 'WIDERSPRUCH':
            self.arbeit.clear(); self.arbeit_f.clear()
            return self
        # A checkpoint may stop after WELTEN but before its derived values.
        try:
            if len(self.worlds) == 1 and self.world_history:
                x, y = self.worlds[0]
                for u, val in zip((*self.xy, self.z), (x, y, x & y)):
                    self._world_value(u, val, self.world_history[-1][0])
            return bk.KernMonome.fixpunkt(self)
        except bk.Widerspruch:
            self.status = 'WIDERSPRUCH'
            self.arbeit.clear(); self.arbeit_f.clear()
            raise

    def abarbeiten(self):
        if self.status == 'WIDERSPRUCH':
            self.arbeit.clear(); self.arbeit_f.clear()
            return self.status
        self.status = 'LAUFEND'
        try:
            return KernFormel.abarbeiten(self)
        except bk.Budget:
            self.status = 'OFFEN'
            return self.status
        except bk.Widerspruch:
            self.status = 'WIDERSPRUCH'
            self.arbeit.clear(); self.arbeit_f.clear()
            raise


def fr4_pruefen(kern, vertrag, eltern, art, info, add, formel_zustand):
    """Independent rule: only an already checked VERB can authorize this ADD.
    The original task contract is read-only. The new instance is entered in
    the checker's local, proven ADD registry used by existing carry checks.
    """
    if art != 'ADD' or len(eltern) != 1 or len(info) != 2:
        raise ValueError('FR-4 requires ADD and exactly one VERB parent')
    kid, raw = info
    key = tuple(raw)
    if not isinstance(kid, str) or not kid or kid in add:
        raise ValueError('FR-4 invalid/duplicate instance')
    source = eltern[0]
    proven = [v for v in formel_zustand.get('verb', {}).values() if v[3] == source]
    if len(proven) != 1:
        raise ValueError('FR-4 parent not a checked relation')
    left, right, constant, _ = proven[0]
    nb = vertrag['nb']
    if nb not in (4, 8, 32) or right is None or left == right:
        raise ValueError('FR-4 invalid relation width/symbols')
    expected = ('B-R5', left, right, constant)
    if key != expected or type(constant) is not int or not 0 <= constant < 2**nb:
        raise ValueError('FR-4 structure differs from checked relation')
    if any(tuple(v[1]) == key for v in add.values()):
        raise ValueError('FR-4 duplicate addition')
    return kid, key


def wiederaufnahme(nb, buch, vertrag, pruefer):
    """Restore only from checked entries; stored runtime state is not accepted.
    Requeue equations/tables, not a saved scheduler. Partial ADD expansion is
    rejected: a checkpoint must be at a completed construction boundary.
    """
    if nb != vertrag.get('nb') or not vertrag.get('monome'):
        return None, ['restore width/mode differs from contract']
    old, errors = formel_aus_buch(nb, buch, vertrag, pruefer)
    if errors:
        return None, errors
    k = KernUebersetzer(nb, sorted(vertrag['verdeckt']))
    counters = dict(k.zb)
    for key, value in vars(old).items():
        setattr(k, key, value)
    counters.update(k.zb)
    k.zb = counters
    k.budget.setdefault('BF', 50_000)
    k.budget.setdefault('BG', 2_000_000)
    # These fields belong to MONOME, absent from KernFormel restored above.
    k.form.clear(); k.form_nr.clear(); k.u_index.clear()
    k.constraints.clear(); k.u_wert.clear(); k.world_history.clear()
    k.worlds = ((0, 0), (0, 1), (1, 0), (1, 1))
    for nr, (rule, parents, art, info) in enumerate(buch):
        if art == 'FORM':
            name, c, vs = info
            k.form[name] = (c, frozenset(vs)); k.form_nr[name] = nr
        elif art == 'BIT':
            k.form.pop(info[0], None)
            if rule == 'M-R2 wert': k.u_wert[info[0]] = (info[1], nr)
        elif rule == 'M-R0 produkt': k.product_nr = nr
        elif art == 'BEZIEHUNG': k.constraints[(tuple(info[0]), info[1])] = nr
        elif art == 'WELTEN':
            k.worlds = tuple(tuple(w) for w in info)
            k.world_history.append((nr, k.worlds))
        elif rule == 'START spaet': k.spaet[info[0]] = info[1]
    for name, (c, vs) in k.form.items():
        for u in vs: k.u_index[u].add(name)
    k.zb.update(formen=len(k.form), beziehungen=len(k.constraints),
                weltenpruefungen=len(k.world_history), additionen=len(k.additionen),
                xor=len(k.xor), tabellen=len(k.taf))
    # Every restored constant adder must have NB sum rows and NB-1 carry rows.
    for kid, (nr, key) in k.additionen.items():
        rows = [z for z in buch if nr in z[1]]
        if sum(z[2] == 'GL' for z in rows) != nb or sum(z[2] == 'TAF' for z in rows) != nb-1:
            return None, ['checkpoint inside unfinished addition']
    if k.status == 'WIDERSPRUCH':
        k.arbeit.clear(); k.arbeit_f.clear()
    else:
        k.arbeit = deque([('GL', i) for i in range(len(k.xor))] +
                         [('TAF', i) for i in range(len(k.taf))])
        k.status = 'LAUFEND'
    return k, []
