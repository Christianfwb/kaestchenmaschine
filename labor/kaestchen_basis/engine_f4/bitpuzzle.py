"""Belegter, lokaler Bitanschluss. Eingaben der Vorführung sind TEST-Annahmen.
Die vorhandene Arbeitsliste weckt Gleichungen; dieser Aufsatz zeigt den Bedarf.
"""
from rueckweg import KernRueckweg
import bitkern32 as bk


class KernPuzzle(KernRueckweg):
    def __init__(self, *args, **kwargs):
        self.ereignisse = []
        self.gesperrt = False
        super().__init__(*args, **kwargs)

    def setze(self, name, wert, regel, eltern):
        if self.gesperrt:
            raise ValueError('Widerspruch: keine weiteren Einträge erlaubt')
        try:
            neu = super().setze(name, wert, regel, eltern)
        except bk.Widerspruch:
            self.gesperrt = True
            self.arbeit.clear()
            raise
        if neu:
            self.ereignisse.append({'bit': name, 'wert': wert,
                'beleg': self.her[name], 'geweckt': list(self.x_index.get(name, ()))})
        return neu

    def fixpunkt(self):
        if self.gesperrt:
            raise ValueError('Widerspruch: Rechnung gesperrt')
        try:
            return super().fixpunkt()
        except bk.Widerspruch:
            self.gesperrt = True
            self.arbeit.clear()
            raise

    def bedarf(self, bit):
        """Alternativen: je Gleichung fehlen die übrigen unbekannten Bits.
        Dies ist lokaler Regelbedarf, keine Behauptung globaler Unlösbarkeit.
        """
        if bit in self.wert:
            return {'bit': bit, 'status': 'BEKANNT', 'wert': self.wert[bit],
                    'beleg': self.her[bit], 'alternativen': []}
        alternativen = []
        for gid in self.x_index.get(bit, ()):
            vs, par, nr = self.xor[gid]
            fehlt = sorted(v for v in vs if v != bit and v not in self.wert)
            alternativen.append({'gleichung': nr, 'fehlt': fehlt})
        alternativen.sort(key=lambda a: (len(a['fehlt']), a['gleichung']))
        return {'bit': bit, 'status': 'KONFLIKT' if self.gesperrt else 'WARTET',
                'alternativen': alternativen}

    def verbinde(self, start, definitionen, budget=256):
        """Eliminiere Zwischenbits anhand ausgewählter, bereits gebuchter GLs.
        Definitionsgrenze ist explizit: keine willkürlichen Zwischenwerte.
        """
        vs, parity = self.buch[start][3]
        names, parents, benutzt = set(vs), {start}, set()
        for _ in range(budget):
            choices = sorted(n for n in names if n in definitionen and n not in benutzt)
            if not choices:
                break
            name = choices[0]; benutzt.add(name)
            p = definitionen[name]
            if self.buch[p][2] != 'GL' or name not in self.buch[p][3][0]:
                raise ValueError('Ungültige Definition')
            terms, par = self.buch[p][3]
            names.symmetric_difference_update(terms); parity ^= par
            parents.symmetric_difference_update({p})
        else:
            raise bk.Budget('Verbindungsbudget: OFFEN')
        if not names or not parents:
            raise ValueError('Leere Verbindung')
        return self.xor_gl(sorted(names), parity, 'RB-R1 XOR-Elimination', sorted(parents))


def aufbau(gekoppelt=True):
    k = KernPuzzle(32)
    defs = {}
    def erfasse(out, f):
        start = len(k.buch); f()
        for nr in range(start, len(k.buch)):
            rule, _, art, info = k.buch[nr]
            if art == 'GL' and not rule.startswith('RB-'):
                for name in info[0]:
                    if name.startswith(out + '.'):
                        defs[name] = nr
    erfasse('L1', lambda: k.sigma('L1', 'W18', (17,19), (10,), 'B-R4 sigma1'))
    erfasse('W20', lambda: k.addition_konst('W20', 'L1', 0x80000000, 'AUFGABE'))
    erfasse('L2', lambda: k.sigma('L2', 'W20', (17,19), (10,), 'B-R4 sigma2'))
    erfasse('W22', lambda: k.addition_konst('W22', 'L2', 640, 'AUFGABE'))
    if gekoppelt:
        start = defs.pop('W22.0')
        k.puzzle_zeile = k.verbinde(start, defs)
    k.fixpunkt()
    return k


def vertrag(eingaben):
    # Unabhängiger Aufgabenaufbau ohne die abgeleitete Puzzle-Gleichung.
    k = aufbau(False)
    for bit, value in eingaben.items(): k.start(bit, value, 'TEST')
    return bk.vertrag_aus(k)


def fenster(parent):
    import tkinter as tk
    from tkinter import ttk
    from pruefer_rueckweg import herleitung_pruefen
    win = tk.Toplevel(parent); win.title('Bitpuzzle – Warten, Wecken, Belegen')
    win.geometry('850x540')
    ttk.Label(win, text='Lokale Kontrolle: drei bekannte Bits bestimmen das vierte.',
              padding=12).pack(anchor='w')
    ttk.Label(win, text='W22.0 = W18.2 XOR W18.6 XOR W18.20\n'
              'Die vorgegebenen Bits sind Testbedingungen, keine Herleitung aus dem Mining-Ziel.',
              padding=12).pack(anchor='w')
    view = tk.Text(win, wrap='word', font=('Consolas', 11)); view.pack(fill='both', expand=True)
    state = {}
    inputs = {'W18.2': 0, 'W18.6': 0, 'W22.0': 1}
    def anzeigen():
        k = state['kern']; d = k.bedarf('W18.20')
        errors = herleitung_pruefen(k, vertrag(inputs))
        view.delete('1.0', 'end')
        if d['status'] == 'BEKANNT':
            text = f"W18.20 = {d['wert']}\nBeleg: Buchzeile {d['beleg']}\n"
        else:
            text = 'W18.20 wartet. Kürzeste verfügbare Verbindung benötigt:\n'
            text += ', '.join(d['alternativen'][0]['fehlt']) + '\n'
        text += f'Prüffehler: {len(errors)}\n\nLetzte Einträge (Bit → Wert → Beleg):\n'
        text += '\n'.join(f"{e['bit']} → {e['wert']} → {e['beleg']}" for e in k.ereignisse[-12:])
        view.insert('end', text)
    def reset():
        state['kern'] = aufbau()
        for n in ('W18.2', 'W18.6'): state['kern'].start(n, 0, 'TEST')
        state['kern'].fixpunkt(); anzeigen()
    def liefern():
        state['kern'].start('W22.0', 1, 'TEST'); state['kern'].fixpunkt(); anzeigen()
    row = ttk.Frame(win, padding=12); row.pack(fill='x')
    ttk.Button(row, text='Fehlendes Testbit W22.0 = 1 liefern', command=liefern).pack(side='left')
    ttk.Button(row, text='Zurück auf WARTET', command=reset).pack(side='left', padx=10)
    reset()
