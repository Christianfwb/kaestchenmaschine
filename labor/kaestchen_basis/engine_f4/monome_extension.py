"""Two-input ANF extension. Imported by bitkern32 after its original definitions.

The world evaluator does not execute SHA: it evaluates a local relation on
the four Boolean inputs. Original LF files remain available for regression.
"""
from collections import deque


def install(b):
    class KernMonome(b.KernLF):
        def __init__(self, nb, budget=None, name='MONOME', verdeckt=()):
            if len(set(verdeckt)) != 2:
                raise ValueError('MONOME requires exactly two hidden input bits')
            super().__init__(nb, budget, name, verdeckt)
            self.monome = True
            self.xy = tuple(sorted(self.verdeckt))
            self.z = '*'.join(self.xy)
            if any('*' in n for n in self.xy):
                raise ValueError('ambiguous product name')
            self.unbekannte.add(self.z)
            self.product_nr = self.buche('M-R0 produkt', [], 'BINDUNG', (self.z, *self.xy))
            self.constraints = {}  # immutable original relations; at most 32 signatures
            self.worlds = ((0, 0), (0, 1), (1, 0), (1, 1))
            self.world_history = []
            self.zb.update(weltenpruefungen=0)

        def _evaluate(self, form, x, y):
            values = {self.xy[0]: x, self.xy[1]: y, self.z: x & y}
            ans = form[0]
            for n in form[1]:
                ans ^= values[n]
            return ans

        def start_spaet(self, name, wert):
            if name in self.verdeckt or name == self.z:
                raise ValueError('hidden/product as late input')
            self.spaet[name] = wert
            if name in self.wert:
                if self.wert[name] != wert:
                    self.beziehung((), 1, 'M-R1 spaet ' + name, [self.her[name]])
                return True
            return super().start_spaet(name, wert)

        def _table_form(self, tname, inputs):
            values = [b.FUNKTIONEN[tname][1](*[self._evaluate(f, x, y) for f in inputs])
                      for x, y in ((0, 0), (0, 1), (1, 0), (1, 1))]
            w00, w01, w10, w11 = values
            coeff = (w00 ^ w10, w00 ^ w01, w00 ^ w01 ^ w10 ^ w11)
            return w00, frozenset(n for n, a in zip((*self.xy, self.z), coeff) if a)

        def beziehung(self, V, k, regel, eltern):
            sig = (tuple(sorted(V)), k)
            if k not in (0, 1) or not set(V) <= self.unbekannte:
                raise ValueError('invalid relation')
            if sig in self.constraints or (not V and not k):
                return
            nr = self.buche(regel, eltern, 'BEZIEHUNG', sig)
            self.constraints[sig] = nr
            self.zb['beziehungen'] += 1
            self._world_check()

        def _world_check(self):
            parents = [self.product_nr] + list(self.constraints.values())
            parents += [nr for value, nr in self.u_wert.values()]
            worlds = tuple((x, y) for x, y in ((0, 0), (0, 1), (1, 0), (1, 1))
                           if all(self._evaluate((k, V), x, y) == 0 for V, k in self.constraints)
                           and all(self._evaluate((0, (n,)), x, y) == value
                                   for n, (value, _) in self.u_wert.items()))
            if not set(worlds) <= set(self.worlds):
                raise ValueError('world set grew')
            self.worlds = worlds
            self.zb['weltenpruefungen'] += 1
            wn = self.buche('M-R2 welten', parents, 'WELTEN', worlds)
            self.world_history.append((wn, worlds))
            if not worlds:
                self.buche('M-R2 widerspruch', [wn], 'WIDERSPRUCH', ())
                self.zb['widersprueche'] += 1
                raise b.Widerspruch('no admissible world')
            if len(worlds) == 1:
                x, y = worlds[0]
                for n, value in zip((*self.xy, self.z), (x, y, x & y)):
                    self._world_value(n, value, wn)

        def _world_value(self, u, value, wn):
            if u in self.u_wert:
                if self.u_wert[u][0] != value:
                    raise ValueError('world/value disagreement')
                return
            self.zb['bits'] += 1
            self.wert[u] = value
            self.her[u] = self.buche('M-R2 wert', [wn], 'BIT', (u, value))
            self.u_wert[u] = (value, self.her[u])
            self.form.pop(u, None)
            self.arbeit.append(u)
            for name in list(self.u_index.get(u, ())):
                if name == u:
                    continue
                old = self.form.get(name)
                if old is None or u not in old[1]:
                    continue
                k, V = old[0] ^ value, old[1] - {u}
                parents = [self.form_nr[name], self.her[u]]
                if V:
                    self.setze_form(name, k, V, 'L-R5 einsetzen', parents)
                else:
                    self.form.pop(name, None)
                    self.setze(name, k, 'L-R5 einsetzen', parents)
            self.u_index.pop(u, None)

        def _gleichung(self, idx):
            vs, par, nr = self.xor[idx]
            les = [self.lesart(v) for v in vs]
            if any(f is None for f in les):
                return super()._gleichung(idx)
            k, V = par, frozenset()
            for f in les:
                k ^= f[0]
                V ^= f[1]
            if V or k:
                self.beziehung(V, k, f'L-R1 beziehung [{nr}]', [nr] + [self.beleg_nr(v) for v in vs])

        def _tabelle(self, idx):
            tname, names, nr = self.taf[idx]
            inputs = [self.lesart(n) for n in names[:-1]]
            if any(f is None for f in inputs):
                return super()._tabelle(idx)
            self.zb['tabellenpruefungen'] += 1
            if self.zb['tabellenpruefungen'] > self.budget['BT']:
                raise b.Budget('BT')
            new = self._table_form(tname, inputs)
            parents = [self.product_nr, nr] + [self.beleg_nr(n) for n in names[:-1]]
            old = self.lesart(names[-1])
            if old is None:
                self.setze_form(names[-1], *new, f'M-R1 form [{nr}]', parents)
            elif old != new:
                self.beziehung(old[1] ^ new[1], old[0] ^ new[0], f'M-R1 abgleich [{nr}]',
                               parents + [self.beleg_nr(names[-1])])

    return KernMonome
