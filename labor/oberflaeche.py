#!/usr/bin/env python3
"""oberflaeche.py - Der glaeserne Miner, Stufe 2: Fenster mit Glaswand, Zeitlupe, Kante und Beweis. tkinter, keine Zusatzpakete.

Drei Zonen:
  oben    die Wahrheit: Block, Nullbits, Netz-Hashrate, eigene Hashrate, Chance heute als "1 zu ..." - immer sichtbar
  mitte   die Glaswand: k0 | k1 | k2 als Bitteppich (64 Runden x 256 Bits). grau = nonce-frei, blau = nonce-abhaengig, hell = Bit 1,
          rote Linie = Early Exit (Runde 61 in k2), unten der Hash mit den Nullbits. Beim Hashen wird alle paar tausend Nonces
          neu gezeichnet (kostet fast nichts). Zeitlupe: eine Nonce, eine Runde aufgeklappt, Rotationen und Uebertraege sichtbar.
  rechts  Instrumente: Rundenregler + "Herleiten" (Kante 16/17), "Beweis dieser Nonce" (Kaestchenmaschine, Pruefer), Buch zum Blaettern
Regeln: keine Nonce wird uebersprungen; kein Geschwindigkeitsvorteil; Chancen stehen immer oben. Miner/Node des Projekts unveraendert."""
import sys, json, threading, queue, time, hashlib
from pathlib import Path
import tkinter as tk
from tkinter import ttk
H = Path(__file__).resolve().parent; sys.path.insert(0, str(H))
import ui_sprache
from ui_sprache import T
from glas import lebenslauf as LB, odds as OD, miner_cpu as MC, avalanche as AV

BG, PANEL, GRID = '#0b0f14', '#121820', '#1a222c'
FG, DIM, ACC, WARN, ROT, GOLD = '#e6edf3', '#7d8b99', '#58a6ff', '#f0883e', '#ff4d4d', '#ffd166'
C_FREI0, C_FREI1 = '#2a3139', '#4a545e'        # nonce-frei: Bit 0 / Bit 1
C_NON0, C_NON1 = '#0f3b66', '#58a6ff'          # nonce-abhaengig: Bit 0 / Bit 1
C_NULL = '#1b5e20'

class Glaswand(tk.Canvas):
    """Bitteppich einer Kompression: 64 Zeilen (Runden) x 256 Spalten (8 Woerter x 32 Bit)."""
    def __init__(self, master, name, zelle=2, **kw):
        self.z = zelle; self.name = name; self.b = 256 * zelle; self.h = 65 * zelle + 18
        super().__init__(master, width=self.b + 2, height=self.h, bg=GRID, highlightthickness=0, **kw)
        self.create_text(2, 2, anchor='nw', text=name, fill=DIM, font=('Consolas', 9)); self.bilder = {}
    def zeichne(self, komp, hash_zeile=None, nullbits=0, markiere_runde=None):
        self.delete('bit')
        z = self.z; y0 = 14
        # PhotoImage waere schneller, aber Rechtecke reichen bei 2px bei ~16k Zellen -> wir zeichnen je Runde 8 Woerter als Streifen
        for r in komp['runden']:
            y = y0 + r['t'] * z; frei = r['zustand_nonce_frei']
            for w in range(8):
                v = r['zustand'][w]
                for i in range(32):
                    bit = (v >> (31 - i)) & 1; x = (w * 32 + i) * z
                    self.create_rectangle(x, y, x + z, y + z, outline='', fill=(C_FREI1 if bit else C_FREI0) if frei else (C_NON1 if bit else C_NON0), tags='bit')
        if hash_zeile is not None:
            # hash_zeile = die Hash-ZAHL (int.from_bytes(digest, 'little')), gezeichnet hoechste Stelle links - dieselbe Zahl wie im Targetvergleich
            y = y0 + 64 * z + 4
            for i in range(256):
                stelle = 255 - i; bit = (hash_zeile >> stelle) & 1; x = i * z
                if stelle >= 256 - nullbits: farbe = C_NULL if bit == 0 else ROT      # muss 0 sein: gruen wenn 0, rot wenn verletzt
                else: farbe = GOLD if bit else '#3a3a1a'
                self.create_rectangle(x, y, x + z, y + z, outline='', fill=farbe, tags='bit')
        if markiere_runde is not None:
            y = y0 + markiere_runde * z; self.create_line(0, y, self.b, y, fill=ROT, width=1, tags='bit')
            self.create_text(self.b - 2, y - 1, anchor='se', text=T(f'Early Exit nach der {markiere_runde}. Runde (t={markiere_runde - 1})', f'Early exit after round {markiere_runde} (t={markiere_runde - 1})'), fill=ROT, font=('Consolas', 8), tags='bit')

class App(tk.Tk):
    def __init__(self, header_datei):
        super().__init__(); self.title(T('Der glaeserne Miner', 'The Glass Miner')); self.configure(bg=BG); self.minsize(640, 420)
        self.geometry(f'{min(1280, self.winfo_screenwidth()-80)}x{min(820, self.winfo_screenheight()-100)}')
        st = ttk.Style(self); st.theme_use('clam')
        st.configure('.', background=BG, foreground=FG, fieldbackground=PANEL, font=('Segoe UI', 10))
        st.configure('Kopf.TLabel', font=('Segoe UI', 16, 'bold')); st.configure('Wert.TLabel', font=('Consolas', 11), foreground=ACC)
        st.configure('Warn.TLabel', font=('Segoe UI', 11, 'bold'), foreground=WARN); st.configure('Dim.TLabel', foreground=DIM)
        st.configure('TButton', background=PANEL, foreground=FG, padding=6); st.map('TButton', background=[('active', '#1f2a36')])
        st.configure('TScale', background=BG, troughcolor=PANEL); st.configure('TCheckbutton', background=BG, foreground=FG)
        st.map('TCombobox', fieldbackground=[('readonly', PANEL)], foreground=[('readonly', FG)], selectbackground=[('readonly', PANEL)], selectforeground=[('readonly', FG)])
        st.configure('TScrollbar', background='#344355', troughcolor=PANEL, arrowcolor=FG)
        st.map('TScrollbar', background=[('active', ACC)])
        d = json.load(open(header_datei)); self.header = bytes.fromhex(d['header76_hex']); self.quelle = d.get('quelle', str(header_datei))
        self.target = OD.nbits_zu_target(OD.nbits_aus_header(self.header)); self.nullbits = 256 - self.target.bit_length()
        self.bekannter_treffer = int(d['nonce_hex'], 16) if d.get('nonce_hex') else None
        self.q = queue.Queue(); self.laeuft = False; self.hashrate = 0.0; self.geprueft = 0; self.beste = (1 << 256, None); self.aktuelle_nonce = 0
        self.zeitlupe = tk.BooleanVar(value=False); self.zl_runde = 0; self.zl_komp = 'k2'
        self.hashrate_ohne_zeichnen = None   # erst nach Klick auf 'Vergleichsmessung' (hasht 100.000 Nonces) - kein Hashen ohne Klick
        self._viewport_bauen(); self._bauen(); ui_sprache.keep_static(); self.after(200, self._tick)
    def _viewport_bauen(self):
        """Keep navigation visible even when the bit grids exceed the screen."""
        bar = ttk.Frame(self, padding=(10, 5)); bar.pack(fill='x')
        ttk.Label(bar, text='Sprache / Language:').pack(side='left')
        self.sprache = ttk.Combobox(bar, values=['Deutsch', 'English'], state='readonly', width=10)
        self.sprache.set('English' if ui_sprache.language == 'en' else 'Deutsch')
        self.sprache.pack(side='left', padx=6)
        self.sprache.bind('<<ComboboxSelected>>', self._sprache_wechseln)
        ttk.Label(bar, text=T('Unten seitlich scrollen; Umschalt + Mausrad = links/rechts.',
                             'Scroll sideways at the bottom; Shift + mouse wheel = left/right.'),
                  style='Dim.TLabel', wraplength=470).pack(side='left', padx=8)
        frame = ttk.Frame(self); frame.pack(fill='both', expand=True)
        frame.rowconfigure(0, weight=1); frame.columnconfigure(0, weight=1)
        self.viewport = tk.Canvas(frame, bg=BG, highlightthickness=0)
        self.viewport.grid(row=0, column=0, sticky='nsew')
        self.scroll_x = ttk.Scrollbar(frame, orient='horizontal', command=self.viewport.xview)
        self.scroll_y = ttk.Scrollbar(frame, orient='vertical', command=self.viewport.yview)
        self.scroll_x.grid(row=1, column=0, sticky='ew')
        self.scroll_y.grid(row=0, column=1, sticky='ns')
        self.viewport.configure(xscrollcommand=self.scroll_x.set, yscrollcommand=self.scroll_y.set)
        self.inhalt = ttk.Frame(self.viewport)
        self._content_id = self.viewport.create_window(0, 0, anchor='nw', window=self.inhalt)
        self.inhalt.bind('<Configure>', self._viewport_groesse)
        self.viewport.bind('<Configure>', self._viewport_groesse)
        self.bind('<MouseWheel>', self._mausrad)
        self.bind('<Button-4>', self._mausrad)
        self.bind('<Button-5>', self._mausrad)

    def _viewport_groesse(self, event=None):
        self.viewport.itemconfigure(self._content_id,
            width=max(self.inhalt.winfo_reqwidth(), self.viewport.winfo_width()),
            height=max(self.inhalt.winfo_reqheight(), self.viewport.winfo_height()))
        self.viewport.configure(scrollregion=self.viewport.bbox('all'))

    def _mausrad(self, event):
        # Text panes and editable controls retain their normal wheel behaviour.
        if event.widget.winfo_class() in ('Text', 'TCombobox', 'TSpinbox', 'TScale'):
            return
        delta = (-1 if event.delta > 0 else 1) if getattr(event, 'delta', 0) else (-1 if event.num == 4 else 1)
        if event.state & 1:
            self.viewport.xview_scroll(delta * 3, 'units')
        else:
            self.viewport.yview_scroll(delta * 3, 'units')
        return 'break'

    def _sprache_wechseln(self, event=None):
        ui_sprache.switch(self, 'en' if self.sprache.get() == 'English' else 'de')
        self.update_idletasks()
        self._viewport_groesse()

    def _text_box(self, parent):
        frame = ttk.Frame(parent); frame.pack(fill='both', expand=True, pady=(4, 0))
        frame.rowconfigure(0, weight=1); frame.columnconfigure(0, weight=1)
        return frame

    def _text_scrollbars(self, frame, text):
        text.grid(row=0, column=0, sticky='nsew')
        sx = ttk.Scrollbar(frame, orient='horizontal', command=text.xview)
        sy = ttk.Scrollbar(frame, orient='vertical', command=text.yview)
        sx.grid(row=1, column=0, sticky='ew'); sy.grid(row=0, column=1, sticky='ns')
        text.configure(xscrollcommand=sx.set, yscrollcommand=sy.set)

    # ---- Aufbau ----
    def _bauen(self):
        kopf = ttk.Frame(self.inhalt, padding=(14, 10)); kopf.pack(fill='x')
        ttk.Label(kopf, text=T('Der glaeserne Miner', 'The Glass Miner'), style='Kopf.TLabel').grid(row=0, column=0, sticky='w', columnspan=3)
        ttk.Label(kopf, text=T('Ein Miner, der zeigt, was er tut. Nicht schneller. Durchsichtig.', 'A miner that shows its work. Transparent, with no speed advantage.'), style='Dim.TLabel').grid(row=1, column=0, sticky='w', columnspan=3)
        self.l_block = ttk.Label(kopf, text='', style='Wert.TLabel'); self.l_block.grid(row=2, column=0, sticky='w', pady=(8, 0))
        self.l_netz = ttk.Label(kopf, text='', style='Wert.TLabel'); self.l_netz.grid(row=3, column=0, sticky='w')
        self.l_eigen = ttk.Label(kopf, text='', style='Wert.TLabel'); self.l_eigen.grid(row=4, column=0, sticky='w')
        self.l_chance = ttk.Label(kopf, text='', style='Warn.TLabel'); self.l_chance.grid(row=5, column=0, sticky='w', columnspan=3, pady=(4, 0))
        kopf.columnconfigure(2, weight=1)
        mitte = ttk.Frame(self.inhalt, padding=(14, 4)); mitte.pack(fill='both', expand=True)
        st = ttk.Style(self); st.configure('TNotebook', background=BG, borderwidth=0); st.configure('TNotebook.Tab', background=PANEL, foreground=FG, padding=(12, 4)); st.map('TNotebook.Tab', background=[('selected', '#1f2a36')])
        self.nb = ttk.Notebook(mitte, width=1320); self.nb.pack(side='left', fill='y'); self.nb.pack_propagate(False)
        links = ttk.Frame(self.nb); self.nb.add(links, text=T('Glaswand', 'Glass wall'))
        labor = ttk.Frame(self.nb); self.nb.add(labor, text=T('Avalanche-Labor', 'Avalanche lab')); self._labor_bauen(labor)
        reihe = ttk.Frame(links); reihe.pack(fill='x')
        self.w = {}
        for name, titel in (('k0', T('k0  erster Block (Midstate, nonce-frei)', 'k0  first block (midstate, nonce-independent)')), ('k1', T('k1  zweiter Block (Nonce = W3)', 'k1  second block (nonce = W3)')), ('k2', T('k2  zweite SHA -> Hash', 'k2  second SHA -> hash'))):
            f = ttk.Frame(reihe); f.pack(side='left', padx=(0, 10), anchor='n')
            ttk.Label(f, text=titel, style='Dim.TLabel').pack(anchor='w'); self.w[name] = Glaswand(f, name, zelle=(1 if name == 'k0' else 2)); self.w[name].pack(anchor='n')
        leg = ttk.Frame(links); leg.pack(fill='x', pady=(6, 0))
        for farbe, text in ((C_FREI1, T('nonce-frei (fuer alle 2^32 Nonces gleich)', 'nonce-independent (same for all 2^32 nonces)')), (C_NON1, T('haengt von der Nonce ab', 'depends on the nonce')), (C_NULL, T('Nullbits, die das Ziel verlangt (gruen = ist 0, rot = verletzt)', 'Required zero bits (green = zero, red = violated)')), (GOLD, T('Hash-Bits als Zahl, hoechste Stelle links', 'Hash as a number, most significant bit on the left'))):
            tk.Label(leg, text='  ', bg=farbe).pack(side='left'); ttk.Label(leg, text=text, style='Dim.TLabel', wraplength=270).pack(side='left', padx=(4, 14))
        self.l_nonce = ttk.Label(links, text='', style='Wert.TLabel', wraplength=1250, justify='left'); self.l_nonce.pack(anchor='w', pady=(8, 0))
        self.l_tricks = ttk.Label(links, text='', style='Dim.TLabel', wraplength=820, justify='left'); self.l_tricks.pack(anchor='w')
        # Zeitlupe
        zl = ttk.Frame(links); zl.pack(fill='x', pady=(8, 0))
        ttk.Checkbutton(zl, text=T('Zeitlupe (eine Nonce, eine Runde aufgeklappt - kostet Rechenzeit, nur wenn man will)', 'Slow motion (one nonce, one round in detail; calculates only when enabled)'), variable=self.zeitlupe, command=self._zeitlupe_umschalten).pack(anchor='w')
        zl_box = self._text_box(links)
        self.zl_text = tk.Text(zl_box, height=12, bg=PANEL, fg=FG, insertbackground=FG, font=('Consolas', 9), relief='flat', wrap='none'); self._text_scrollbars(zl_box, self.zl_text)
        zlk = ttk.Frame(links); zlk.pack(fill='x')
        ttk.Button(zlk, text=T('< Runde', '< Round'), command=lambda: self._zl_schritt(-1)).pack(side='left'); ttk.Button(zlk, text=T('Runde >', 'Round >'), command=lambda: self._zl_schritt(1)).pack(side='left', padx=4)
        self.zl_wahl = ttk.Combobox(zlk, values=['k0', 'k1', 'k2'], width=4, state='readonly'); self.zl_wahl.set('k2'); self.zl_wahl.pack(side='left', padx=8); self.zl_wahl.bind('<<ComboboxSelected>>', lambda e: self._zl_zeige())
        rechts = ttk.Frame(mitte, padding=(10, 0)); rechts.pack(side='right', fill='y')
        ttk.Label(rechts, text='Mining', style='Kopf.TLabel').pack(anchor='w')
        kn = ttk.Frame(rechts); kn.pack(anchor='w', pady=4)
        self.b_start = ttk.Button(kn, text='Start', command=self._start); self.b_start.pack(side='left'); ttk.Button(kn, text=T('Stopp', 'Stop'), command=self._stopp).pack(side='left', padx=4)
        sf = ttk.Frame(rechts); sf.pack(anchor='w'); ttk.Label(sf, text=T('ab Nonce (hex):', 'start nonce (hex):'), style='Dim.TLabel').pack(side='left'); self.e_start = ttk.Entry(sf, width=10); self.e_start.insert(0, '00000000'); self.e_start.pack(side='left', padx=4)
        ttk.Button(rechts, text='Messung: 100.000 Nonces hashen', command=self._messung).pack(anchor='w', pady=(2, 4))
        self.l_stat = ttk.Label(rechts, text=T('bereit - keine Nonce-Suche, bevor du Start oder Vergleichsmessung drueckst (der Lebenslauf der angezeigten Nonce wird berechnet)', 'Ready. No nonce search until Start or Measure is clicked. The displayed nonce is traced once.'), style='Dim.TLabel', wraplength=300, justify='left'); self.l_stat.pack(anchor='w')
        ttk.Separator(rechts).pack(fill='x', pady=10)
        ttk.Label(rechts, text=T('Die Kante', 'The boundary'), style='Kopf.TLabel').pack(anchor='w')
        ttk.Label(rechts, text=T('Runden je Kompression (Modell mit exaktem Ziel):', 'Rounds per compression (exact-target model):'), style='Dim.TLabel').pack(anchor='w')
        self.r_var = tk.IntVar(value=16); sk = ttk.Scale(rechts, from_=8, to=64, variable=self.r_var, command=lambda v: self.l_r.configure(text=f'r = {int(float(v))}')); sk.pack(fill='x')
        self.l_r = ttk.Label(rechts, text='r = 16', style='Wert.TLabel'); self.l_r.pack(anchor='w')
        ttk.Button(rechts, text=T('Herleiten (Kaestchenmaschine)', 'Derive (Kaestchenmaschine)'), command=self._kante).pack(anchor='w', pady=4)
        self.l_kante = ttk.Label(rechts, text=T('Gemessen fuer diesen Header und diese Nonce: bis 16 Runden\nleitet die Maschine die Nonce aus dem Ziel her; ab 17 bleibt\nsie stehen (k2_W16 unbekannt). Kein Unmoeglichkeitsbeweis.', 'For this header and nonce, the machine derives the nonce up to 16 rounds; at 17 it stalls (k2_W16 unknown). This does not prove impossibility.'), style='Dim.TLabel', wraplength=300, justify='left'); self.l_kante.pack(anchor='w')
        ttk.Separator(rechts).pack(fill='x', pady=10)
        ttk.Label(rechts, text=T('Beweis', 'Proof'), style='Kopf.TLabel').pack(anchor='w')
        ttk.Button(rechts, text=T('Beweisbuch dieser Nonce', 'Proof book for this nonce'), command=self._beweis).pack(anchor='w', pady=4)
        self.l_beweis = ttk.Label(rechts, text=T('Header + Nonce -> Hash, jede Folgerung eine Zeile,\nvom unabhaengigen Pruefer gegengezeichnet.', 'Header + nonce -> hash. Each inference is recorded and checked by a separate verifier.'), style='Dim.TLabel', wraplength=300, justify='left'); self.l_beweis.pack(anchor='w')
        buch_box = self._text_box(rechts)
        self.buch = tk.Text(buch_box, height=14, width=44, bg=PANEL, fg=FG, font=('Consolas', 8), relief='flat', wrap='none'); self._text_scrollbars(buch_box, self.buch)
        fuss = ttk.Frame(self.inhalt, padding=(14, 6)); fuss.pack(fill='x')
        self.l_fuss = ttk.Label(fuss, text=T('Keine Nonce wird uebersprungen  ·  kein Geschwindigkeitsvorteil  ·  die Chancen stehen oben  ·  Miner und Node des Projekts unveraendert', 'No nonces skipped  ·  no speed advantage  ·  odds shown above  ·  project miner and node unchanged'), style='Dim.TLabel'); self.l_fuss.pack(anchor='w')
        self._kopf_aktualisieren(); self.zeige_nonce(self.bekannter_treffer if self.bekannter_treffer is not None else 0)
    # ---- Avalanche-Labor ----
    def _labor_bauen(self, f):
        ttk.Label(f, text='Ein Nonce-Bit kippen und zusehen, wie sich der Unterschied ausbreitet. Laborrechnung: hasht, aber sucht keine Nonce und verwendet keinen Zielvergleich zur Auswahl.', style='Dim.TLabel', wraplength=1000, justify='left').pack(anchor='w', pady=(4, 2))
        k = ttk.Frame(f); k.pack(anchor='w')
        ttk.Label(k, text=T('Nonce-Bit (Stellenwert 0..31):', 'Nonce bit (position 0..31):'), style='Dim.TLabel').pack(side='left'); self.av_bit = tk.IntVar(value=0)
        ttk.Spinbox(k, from_=0, to=31, textvariable=self.av_bit, width=4).pack(side='left', padx=4)
        ttk.Button(k, text=T('Kippen', 'Flip bit'), command=self._av_kippen).pack(side='left', padx=4)
        ttk.Button(k, text=T('Statistik: 300 zufaellige Nonces x Bit', 'Statistics: 300 random nonce/bit pairs'), command=self._av_statistik).pack(side='left', padx=4)
        ttk.Button(k, text=T('Abhaengigkeitskarte: alle 32 Nonce-Bits', 'Influence map: all 32 nonce bits'), command=self._av_karte).pack(side='left', padx=4)
        self.av_l = ttk.Label(f, text='', style='Wert.TLabel', wraplength=1000, justify='left'); self.av_l.pack(anchor='w', pady=(6, 2))
        reihe = ttk.Frame(f); reihe.pack(fill='x'); self.av_w = {}
        for name, titel in (('k1', T('k1  Unterschied je Runde (rot = Bit verschieden)', 'k1  differences per round (red = different bit)')), ('k2', T('k2  Unterschied je Runde', 'k2  differences per round'))):
            fr = ttk.Frame(reihe); fr.pack(side='left', padx=(0, 10), anchor='n'); ttk.Label(fr, text=titel, style='Dim.TLabel').pack(anchor='w')
            self.av_w[name] = Glaswand(fr, name, zelle=2); self.av_w[name].pack()
        self.av_kurve = tk.Canvas(f, height=150, bg=GRID, highlightthickness=0); self.av_kurve.pack(fill='x', pady=(8, 0))
        av_box = self._text_box(f)
        self.av_text = tk.Text(av_box, height=9, bg=PANEL, fg=FG, font=('Consolas', 9), relief='flat', wrap='word'); self._text_scrollbars(av_box, self.av_text)
        self.av_text.insert('1.0', T('Noch nichts gekippt. Waehle ein Bit und druecke Kippen.', 'No bit flipped yet. Choose a bit and click Flip bit.'))
    def _av_wand(self, name, av):
        c = self.av_w[name]; c.delete('bit'); z = c.z; y0 = 14
        for r in av['komp'][name]['runden']:
            y = y0 + r['t'] * z
            for w in range(8):
                v = r['xor'][w]
                if v == 0: continue
                for i in range(32):
                    if (v >> (31 - i)) & 1: x = (w * 32 + i) * z; c.create_rectangle(x, y, x + z, y + z, outline='', fill=ROT, tags='bit')
    def _av_kurve_zeichnen(self, kurven, titel):
        c = self.av_kurve; c.delete('all'); W = max(c.winfo_width(), 600); H = 150; c.create_text(6, 4, anchor='nw', text=titel, fill=DIM, font=('Consolas', 9))
        c.create_line(40, H - 20, W - 10, H - 20, fill=DIM); c.create_line(40, 10, 40, H - 20, fill=DIM)
        for yv, lab in ((0, '0'), (128, '128'), (256, '256')): y = H - 20 - yv / 256 * (H - 35); c.create_line(40, y, W - 10, y, fill='#263040'); c.create_text(36, y, anchor='e', text=lab, fill=DIM, font=('Consolas', 8))
        for (name, werte, farbe) in kurven:
            pts = []
            for t, v in enumerate(werte): pts += [40 + t * (W - 60) / 63, H - 20 - v / 256 * (H - 35)]
            c.create_line(*pts, fill=farbe, width=2); c.create_text(W - 12, 14 + 12 * len(c.find_withtag('leg')), anchor='ne', text=name, fill=farbe, font=('Consolas', 9), tags='leg')
        for t in (0, 8, 16, 32, 48, 63): c.create_text(40 + t * (W - 60) / 63, H - 16, anchor='n', text=str(t), fill=DIM, font=('Consolas', 8))
    def _av_kippen(self):
        try:
            bit = int(self.av_bit.get())
            if not 0 <= bit <= 31:
                raise ValueError('nonce bit outside 0..31')
            av = AV.kippen(self.header, self.aktuelle_nonce, bit)
        except (ValueError, tk.TclError) as ex:
            self.av_l.configure(text=T('Bitte ein Nonce-Bit von 0 bis 31 eingeben.', 'Please enter a nonce bit from 0 to 31.')); return
        self.av = av
        for n in ('k1', 'k2'): self._av_wand(n, av)
        k1 = av['komp']['k1']; k2 = av['komp']['k2']
        self.av_l.configure(text=T(f"Nonce {av['nonce']:08x} -> {av['nonce2']:08x} (Bit {bit} gekippt).  k0: kein Unterschied (nonce-frei).  k1: erster Unterschied in Runde {k1['erste_runde_mit_unterschied']}, Fahrplanwoerter verschieden: W3 und W18..W63 (W16/W17 nicht).  Hash-Abstand: {av['hash_abstand']} von 256 Bits (Erwartungswert bei Zufall 128, Streuung 8 - kein Maximum).", f"Nonce {av['nonce']:08x} -> {av['nonce2']:08x} (bit {bit} flipped).  k0: no differences (nonce-independent).  k1: first difference at round index {k1['erste_runde_mit_unterschied']}, Different schedule words: W3 and W18..W63 (not W16/W17).  Hash distance: {av['hash_abstand']} of 256 bits (random expectation 128, standard deviation 8; not a maximum)."))
        self._av_kurve_zeichnen([(T('k1 verschiedene Zustandsbits', 'k1 differing state bits'), AV.kurve(av, 'k1'), ACC), ('k2', AV.kurve(av, 'k2'), GOLD)], T('verschiedene Bits im 256-Bit-Zustand je Runde', 'Different bits in the 256-bit state, per round'))
        self.av_text.delete('1.0', 'end')
        self.av_text.insert('1.0', T('k1 je Runde: ', 'k1 per round: ') + ' '.join(f'{v}' for v in AV.kurve(av, 'k1')) + T('\nk2 je Runde: ', '\nk2 per round: ') + ' '.join(f'{v}' for v in AV.kurve(av, 'k2')) +
                            T('\nLesart: Runde 3 nimmt die Nonce als W3 auf - zunaechst nur wenige Bits verschieden (a und e, je nach Uebertrag). Jede weitere Runde mischt Sigma, Ch, Maj und Uebertraege; nach etwa 8 Runden schwankt die Zahl um 128 - das ist der Erwartungswert einer Zufallsfunktion (Streuung etwa 8), KEINE Obergrenze: einzelne Runden zeigen 105 oder 150. Die rote Wand ist nicht die Nonce-Abhaengigkeit (die zeigt die Glaswand), sondern der konkrete Unterschied zwischen zwei Nonces.', '\nReading the chart: round index 3 introduces the nonce as W3. Initially only a few bits differ (in a and e, depending on carries). Further rounds mix Sigma, Ch, Maj and carries. After about 8 rounds, the count fluctuates around 128: the random-function expectation (standard deviation about 8), NOT an upper bound. Individual rounds may show 105 or 150. The red wall shows observed differences between two nonces, not a structural dependency proof.'))
    def _av_statistik(self):
        self.av_l.configure(text=T('rechne 300 Paare ...', 'Calculating 300 pairs ...')); self.update_idletasks()
        st = AV.statistik(self.header, 300); ha = st['hash_abstand']
        self._av_kurve_zeichnen([(T('k1 Mittel ueber 300 Paare', 'k1 average over 300 pairs'), st['mittel']['k1'], ACC), (T('k2 Mittel', 'k2 average'), st['mittel']['k2'], GOLD)], T('mittlere Zahl verschiedener Zustandsbits je Runde (300 zufaellige Nonces, je ein zufaelliges Bit)', 'Average differing state bits per round (300 random nonces, one random bit each)'))
        self.av_l.configure(text=T(f"Hash-Abstand ueber {st['n']} Paare: Mittel {ha['mittel']:.1f}, Streuung {ha['std']:.1f}, min {ha['min']}, max {ha['max']}  |  Erwartungswert bei Zufall 128, Streuung 8  |  Abweichung des Mittels: {ha['abweichung_in_std']:+.1f} Standardfehler (|z| < 3 unauffaellig)", f"Hash distance over {st['n']} pairs: mean {ha['mittel']:.1f}, standard deviation {ha['std']:.1f}, min {ha['min']}, max {ha['max']}  |  Random expectation 128, standard deviation 8  |  Mean deviation: {ha['abweichung_in_std']:+.1f} standard errors (|z| < 3: no conspicuous deviation)"))
        self.av_text.delete('1.0', 'end'); self.av_text.insert('1.0', T('k1 Mittel je Runde: ', 'k1 average per round: ') + ' '.join(f'{v:.0f}' for v in st['mittel']['k1']) + '\n' + T(st['hinweis'], 'Reproducible sample, not a proof of randomness or security. Ideal independent 256-bit outputs have mean distance 128 and standard deviation 8. The displayed deviation uses the standard error of the sample mean.'))
    def _av_karte(self):
        self.av_l.configure(text=T('kippe alle 32 Nonce-Bits ...', 'Flipping all 32 nonce bits ...')); self.update_idletasks()
        ak = AV.abhaengigkeitskarte(self.header, self.aktuelle_nonce); e = ak['erreichte_zustandsbits']
        self._av_kurve_zeichnen([(T('k1 Zustandsbits, die irgendein Nonce-Bit erreicht', 'k1 state bits changed by at least one nonce-bit flip'), e['k1'], WARN), ('k2', e['k2'], GOLD)], T('Abhaengigkeitskarte: wie viele Zustandsbits sich bei mindestens einem der 32 Flips aendern', 'Influence map: state bits changed by at least one of the 32 flips'))
        self.av_l.configure(text=T(f"k1: Runde 3: {e['k1'][3]} Bits, Runde 4: {e['k1'][4]}, Runde 5: {e['k1'][5]}, Runde 6: {e['k1'][6]} - Vereinigung der 32 einzelnen Flips an dieser Nonce; alle 256 beobachtet ab t= {ak['erste_runde_alle_256']['k1']}. k2: alle 256 ab Runde {ak['erste_runde_alle_256']['k2']}.", f"k1: round index 3: {e['k1'][3]} bits, round index 4: {e['k1'][4]}, round index 5: {e['k1'][5]}, round index 6: {e['k1'][6]} - union of 32 individual flips at this nonce; all 256 observed from t= {ak['erste_runde_alle_256']['k1']}. k2: all 256 from round index {ak['erste_runde_alle_256']['k2']}."))
        self.av_text.delete('1.0', 'end'); self.av_text.insert('1.0', T('k1 erreichte Bits je Runde: ', 'k1 reached bits per round: ') + ' '.join(str(v) for v in e['k1']) + '\n' + T(ak['hinweis'], 'Empirical union of single-bit flips at this nonce, not a structural proof of influence for every possible input.') + T('\nRunden sind 0-basierte Indizes t. 256 erreichte Bits bedeutet: jedes Zustandsbit aendert sich bei mindestens einem der 32 Flips. Das ist kein Nachweis, dass jedes Eingabebit jedes Zustandsbit beeinflusst. Die Matrix ist ueber den CLI-JSON-Export verfuegbar.', '\nRounds use zero-based indices t. Reaching 256 bits means that each state bit changes for at least one of the 32 flips. This does not show that every input bit influences every state bit. The matrix is available through the CLI JSON export.'))
    # ---- Anzeige ----
    def _kopf_aktualisieren(self):
        z = OD.zahlen(self.target, max(self.hashrate, 1e-9))
        self.l_block.configure(text=T(f"{self.quelle}   nBits {OD.nbits_aus_header(self.header):08x}   Ziel: {self.nullbits} fuehrende Nullbits   Difficulty {z['difficulty']:.3e}", f"{self.quelle}   nBits {OD.nbits_aus_header(self.header):08x}   Target: {self.nullbits} leading zero bits   Difficulty {z['difficulty']:.3e}"))
        self.l_netz.configure(text=T(f"Netz-Hashrate (aus nBits geschaetzt): {OD.si(z['netz_hashrate_geschaetzt'])}   Chance je Hash 1 zu {z['erwartete_hashes']:.2e}", f"Network hash rate (estimated from nBits): {OD.si(z['netz_hashrate_geschaetzt'])}   Odds per hash: 1 in {z['erwartete_hashes']:.2e}"))
        self.l_eigen.configure(text=T(f"Eigene Hashrate: {OD.si(self.hashrate)} mit Zeichnen  |  ohne Zeichnen: {(OD.si(self.hashrate_ohne_zeichnen) + ' (100.000 Nonces)' if self.hashrate_ohne_zeichnen else 'nicht gemessen')}   geprueft: {self.geprueft:,}   bestes Ergebnis: {(self.beste[0].bit_length() if self.beste[1] is not None else '-')} Bit", f"Own hash rate: {OD.si(self.hashrate)} with drawing  |  without drawing: {(OD.si(self.hashrate_ohne_zeichnen) + ' (100,000 nonces)' if self.hashrate_ohne_zeichnen else 'not measured')}   checked: {self.geprueft:,}   best result: {(self.beste[0].bit_length() if self.beste[1] is not None else '-')} Bit") + (f' (Nonce {self.beste[1]:08x})' if self.beste[1] is not None else ''))
        if self.hashrate > 0:
            self.l_chance.configure(text=T(f"Chance auf einen Block:  heute 1 zu {z['eins_zu_tag']:.2e}   ·   dieses Jahr 1 zu {z['eins_zu_jahr']:.2e}   ·   erwartete Wartezeit {z['erwartete_wartezeit_jahre']:.1e} Jahre", f"Block probability:  per day 1 in {z['eins_zu_tag']:.2e}   ·   per year 1 in {z['eins_zu_jahr']:.2e}   ·   expected wait {z['erwartete_wartezeit_jahre']:.1e} years"))
        else: self.l_chance.configure(text=T('Chance auf einen Block: wird gemessen, sobald gehasht wird', 'Block probability: available once a hash rate has been measured'))
    def zeige_nonce(self, nonce):
        self.aktuelle_nonce = nonce; lb = LB.lebenslauf(self.header, nonce, self.target); self.lb = lb
        for name in ('k0', 'k1'): self.w[name].zeichne(lb[name])
        self.w['k2'].zeichne(lb['k2'], hash_zeile=lb['zahl'], nullbits=self.nullbits, markiere_runde=61)
        self.l_nonce.configure(text=T(f"Nonce {nonce:08x}   Hash {lb['digest'][::-1].hex()}   {('TREFFER' if lb['treffer'] else 'kein Treffer')}   Hash-Zahl {lb['zahl'].bit_length()} Bit, Target {self.target.bit_length()} Bit (Treffer: Zahl <= Target, exakt verglichen)", f"Nonce {nonce:08x}   Hash {lb['digest'][::-1].hex()}   {('MATCH' if lb['treffer'] else 'no match')}   Hash number {lb['zahl'].bit_length()} Bit, Target {self.target.bit_length()} bits (match: number <= target, exact comparison)"))
        tr = lb['tricks']; ee = lb['early_exit']
        self.l_tricks.configure(text=T(f"Tricks dieser Nonce: naiv {tr['naiv_runden']} Runden; Midstate spart {tr['midstate']['gespart']}, Vorrunden {tr['vorrunden_k1']['gespart']}, Early Exit {tr['early_exit']['gespart']} (H2_7 nach der 61. Runde, t=60: {ee['H2_7_aus_e61']:08x}{(', Abbruch' if ee['abbruch_moeglich'] else ', weiterrechnen')}) -> {tr['verbleibend']} Runden. Keine Nonce uebersprungen.", f"This nonce: naive {tr['naiv_runden']} rounds; midstate saves {tr['midstate']['gespart']}, initial rounds {tr['vorrunden_k1']['gespart']}, Early Exit {tr['early_exit']['gespart']} (H2_7 after the 61st round, t=60: {ee['H2_7_aus_e61']:08x}{(', could stop' if ee['abbruch_moeglich'] else ', continue')}) -> {tr['verbleibend']} rounds. No nonce skipped."))
        if self.zeitlupe.get(): self._zl_zeige()
    # ---- Mining ----
    def _start(self):
        if self.laeuft: return
        self.laeuft = True; self.stop_ev = threading.Event()
        try: start = int(self.e_start.get(), 16) & 0xffffffff
        except ValueError: start = 0
        def lauf():
            sha = hashlib.sha256; n = start; t0 = time.perf_counter(); schritt = 20000; beste = self.beste
            while not self.stop_ev.is_set() and n < (1 << 32):
                ende = min(1 << 32, n + schritt); treffer = None
                for x in range(n, ende):
                    d = sha(sha(self.header + x.to_bytes(4, 'little')).digest()).digest(); z = int.from_bytes(d, 'little')
                    if z < beste[0]: beste = (z, x)
                    if z <= self.target: treffer = x; break
                n = ende if treffer is None else treffer + 1
                self.q.put(dict(n=n, start=start, t=time.perf_counter() - t0, beste=beste, treffer=treffer, letzte=n - 1))
                if treffer is not None: break
            self.q.put(dict(ende=True))
        def sicher():
            try: lauf()
            except Exception as ex: self.q.put(dict(fehler=repr(ex))); self.q.put(dict(ende=True))
        threading.Thread(target=sicher, daemon=True).start(); self.l_stat.configure(text=T('hasht ...', 'Hashing ...'))
    def _messung(self):
        if self.laeuft: return
        self.hashrate_ohne_zeichnen = MC.mine(self.header, 0, start=0, anzahl=100000)['hashrate']; self._kopf_aktualisieren()
        self.l_stat.configure(text=T(f'Vergleichsmessung: {OD.si(self.hashrate_ohne_zeichnen)} ohne Zeichnen (bis zu 100.000 Nonces, Target 0; Vergleichsmessung, kein Benchmark)', f'Comparison measurement: {OD.si(self.hashrate_ohne_zeichnen)} without drawing (up to 100,000 nonces, target 0; comparison measurement, not a benchmark)'))
    def _stopp(self):
        if self.laeuft: self.stop_ev.set()
    def _tick(self):
        neu = None; ende = False
        try:
            while True:
                m = self.q.get_nowait()
                if m.get('fehler'): self.l_stat.configure(text=T('Fehler im Mining: ', 'Mining error: ') + m['fehler'])
                elif m.get('ende'): ende = True
                else: neu = m
        except queue.Empty: pass
        if neu is not None:
            if True:
                self.geprueft = neu['n'] - neu['start']; self.hashrate = self.geprueft / neu['t'] if neu['t'] else 0; self.beste = neu['beste']
                if neu['treffer'] is not None:
                    self.l_stat.configure(text=T(f"TREFFER bei Nonce {neu['treffer']:08x} - mit hashlib geprueft. Hash erfuellt das Target; Netzwerkannahme nicht geprueft.", f"MATCH at nonce {neu['treffer']:08x} - verified with hashlib. The hash meets the target; network acceptance has not been checked.")); self.zeige_nonce(neu['treffer'])
                elif not self.zeitlupe.get(): self.zeige_nonce(neu['letzte'])
                self._kopf_aktualisieren()
        if ende: self.laeuft = False; self.l_stat.configure(text=T(f'gestoppt. {self.geprueft:,} Nonces, {OD.si(self.hashrate)}', f'Stopped. {self.geprueft:,} nonces, {OD.si(self.hashrate)}'))
        self.after(250, self._tick)
    # ---- Zeitlupe ----
    def _zeitlupe_umschalten(self):
        if self.zeitlupe.get(): self._zl_zeige()
        else: self.zl_text.delete('1.0', 'end')
    def _zl_schritt(self, d): self.zl_runde = max(0, min(63, self.zl_runde + d)); self._zl_zeige()
    def _zl_zeige(self):
        lb = self.lb; komp = self.zl_wahl.get(); t = self.zl_runde; r = lb[komp]['runden'][t]; W = r['W']
        vor = lb[komp]['runden'][t - 1]['zustand'] if t > 0 else ([LB.IV if komp != 'k1' else None][0] or lb['k0']['H'])
        a, b, c, d, e, f, g, h = vor
        rot = lambda x, n: ((x >> n) | (x << (32 - n))) & 0xffffffff
        bits = lambda v: format(v, '032b')
        S1 = rot(e, 6) ^ rot(e, 11) ^ rot(e, 25); ch = (e & f) ^ (~e & g & 0xffffffff); S0 = rot(a, 2) ^ rot(a, 13) ^ rot(a, 22); maj = (a & b) ^ (a & c) ^ (b & c)
        x1 = (h + S1) & 0xffffffff; x2 = (x1 + ch) & 0xffffffff; x3 = (x2 + W) & 0xffffffff; T1 = (x3 + LB.K[t]) & 0xffffffff; T2 = (S0 + maj) & 0xffffffff
        carry = lambda u, v: bits(((u & v) | ((u ^ v) & ~((u + v) & 0xffffffff))) & 0xffffffff).replace('0', '.').replace('1', '^')
        zeilen = [T(f"{komp} Runde {t}   W_t = {W:08x} {('(nonce-frei)' if r['W_nonce_frei'] else '(haengt von der Nonce ab)')}   K_t = {LB.K[t]:08x}", f"{komp} round index {t}   W_t = {W:08x} {('(nonce-independent)' if r['W_nonce_frei'] else '(depends on the nonce)')}   K_t = {LB.K[t]:08x}"), '',
                  f'e            {bits(e)}', f'ROTR 6       {bits(rot(e,6))}', f'ROTR 11      {bits(rot(e,11))}', f'ROTR 25      {bits(rot(e,25))}', T(f'Sigma1(e) =  {bits(S1)}  (XOR der drei Drehungen)', f'Sigma1(e) =  {bits(S1)}  (XOR of the three rotations)'), '',
                  T(f'Ch(e,f,g) =  {bits(ch)}  (e waehlt: 1 -> f, 0 -> g)', f'Ch(e,f,g) =  {bits(ch)}  (e selects: 1 -> f, 0 -> g)'), f'Maj(a,b,c) = {bits(maj)}   Sigma0(a) = {bits(S0)}', '',
                  f'h + Sigma1   {bits(x1)}', T(f'  Uebertraege {carry(h, S1)}', f'  Carries    {carry(h, S1)}'), f'+ Ch         {bits(x2)}', f'+ W_t        {bits(x3)}', f'+ K_t = T1   {bits(T1)}', f'T2 = S0+Maj  {bits(T2)}', '',
                  T(f"neu: a = T1+T2 = {T1 + T2 & 4294967295:08x}   e = d+T1 = {d + T1 & 4294967295:08x}   (b,c,d,f,g,h) ruecken nach   -> Zustand {' '.join((f'{v:08x}' for v in r['zustand']))}", f"new: a = T1+T2 = {T1 + T2 & 4294967295:08x}   e = d+T1 = {d + T1 & 4294967295:08x}   (b,c,d,f,g,h) shift along   -> state {' '.join((f'{v:08x}' for v in r['zustand']))}")]
        self.zl_text.delete('1.0', 'end'); self.zl_text.insert('1.0', '\n'.join(zeilen))
    # ---- Kaestchenmaschine ----
    def _kante(self):
        r = int(self.r_var.get()); nonce = self.aktuelle_nonce; self.l_kante.configure(text=T(f'rechne r = {r} ...', f'Calculating r = {r} ...'))
        def lauf():
            try:
                from glas import kaestchen as KM; e = KM.kante(self.header, nonce, r)
                if e['nonce_hergeleitet']: txt = T(f"r = {r}: Die Maschine leitet die Nonce HER: {e['nonce_hergeleitet']} (stimmt: {e['stimmt']}). {e['zeilen']:,} Beweiszeilen, Pruefer {e['pruefer_fehler']} Fehler, {e['sekunden']} s.", f"r = {r}: The machine DERIVES the nonce: {e['nonce_hergeleitet']} (matches: {e['stimmt']}). {e['zeilen']:,} proof lines, checker {e['pruefer_fehler']} errors, {e['sekunden']} s.")
                else: txt = T(f"r = {r}: Die Maschine bleibt stehen (dieser Versuch). {e['noncebits_fest']}/16 Noncebits, k2_W16 feste Bits: {e['k2_W16_feste_bits']}. {e['zeilen']:,} Zeilen, Pruefer {e['pruefer_fehler']} Fehler, {e['sekunden']} s.", f"r = {r}: The machine stalls (this experiment). {e['noncebits_fest']}/16 nonce bits, k2_W16 fixed bits: {e['k2_W16_feste_bits']}. {e['zeilen']:,} lines, checker {e['pruefer_fehler']} errors, {e['sekunden']} s.")
            except Exception as ex: txt = T(f'Fehler: {ex}', f'Error: {ex}')
            self.after(0, lambda: self.l_kante.configure(text=txt))
        threading.Thread(target=lauf, daemon=True).start()
    def _beweis(self):
        nonce = self.aktuelle_nonce; self.l_beweis.configure(text=T(f'baue Beweisbuch fuer {nonce:08x} (volle 64 Runden) ...', f'Building proof book for {nonce:08x} (all 64 rounds) ...'))
        def lauf():
            try:
                from glas import kaestchen as KM; b = KM.beweis(self.header, nonce)
                txt = T(f"{b['zeilen']:,} Zeilen. Digest aus den geprueften Buchzeilen == hashlib: {b['digest_aus_buch'] is not None and b['pruefung_vollstaendig']}. Pruefer: {b['pruefer_fehler']} Fehler, Hash-Bits als Buchzeilen {b['hash_bits_belegt']}/256, Beweis vollstaendig: {b['pruefung_vollstaendig']}. {b['zeit_aufbau_herleitung']} s + {b['zeit_pruefung']} s. (Vertrag ohne Zielvorgabe: bewiesen ist die Hashberechnung.)", f"{b['zeilen']:,} lines. Digest reconstructed from checked book lines == hashlib: {b['digest_aus_buch'] is not None and b['pruefung_vollstaendig']}. Checker: {b['pruefer_fehler']} errors, hash bits recorded as book lines {b['hash_bits_belegt']}/256, proof complete: {b['pruefung_vollstaendig']}. {b['zeit_aufbau_herleitung']} s + {b['zeit_pruefung']} s. (No target constraint: this proves the hash computation.)")
                auszug = '\n'.join(f'{i:6d} {z[2]:<5} {z[0][:60]}' for i, z in enumerate(b['buch']) if i < 400 or i % 1000 == 0)
            except Exception as ex: txt = T(f'Fehler: {ex}', f'Error: {ex}'); auszug = ''
            def zeig(): self.l_beweis.configure(text=txt); self.buch.delete('1.0', 'end'); self.buch.insert('1.0', auszug)
            self.after(0, zeig)
        threading.Thread(target=lauf, daemon=True).start()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Glass Miner / Glaeserner Miner')
    parser.add_argument('header', nargs='?', default=H / 'headers' / 'H970000.json')
    parser.add_argument('--lang', choices=['de', 'en'], default='de')
    args = parser.parse_args()
    ui_sprache.language = args.lang
    App(args.header).mainloop()
