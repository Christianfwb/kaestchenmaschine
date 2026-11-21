"""Bedienfenster. Rechnet nur nach Start; Stop beendet ausschließlich den eigenen Arbeiter."""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from maschine import beispiel

ROOT=Path(__file__).resolve().parent
MODES={
    'Erweiterter Stand → Zielregeln, Beziehungen und Tabellenschnitte': 'erweitert',
    'Rückweg: W22 vorgegeben → ganzes Noncewort (Kontrolle)': 'rueckweg',
    'Ziel vorgegeben → alle 32 Noncebits offen': 'offen',
    'Zwei freie Bits → bestehendes MONOME + Wortanschluss': 'zwei',
    'Bekannter Header → vollständige Rechenkontrolle': 'bekannt',
}


class Fenster:
    def __init__(self, root):
        self.root=root; self.proc=None; self.q=queue.Queue(); self.result=None; self.custom=None
        root.title('Ghost – Arbeitsmaschine | Kästchen, Bedingungen und Belege')
        root.geometry(f"{min(1230,root.winfo_screenwidth()-35)}x{min(850,root.winfo_screenheight()-90)}"); root.minsize(950,620)
        style=ttk.Style(); style.theme_use('clam')
        style.configure('.', font=('Segoe UI',10)); style.configure('Treeview',rowheight=25)
        top=ttk.Frame(root,padding=12); top.pack(fill='x')
        ttk.Label(top,text='Unsere Arbeitsmaschine – gemeinsamer Stand',font=('Segoe UI',20,'bold')).pack(anchor='w')
        ttk.Label(top,text='Vorwärts und rückwärts im selben Gleichungsnetz · lokale Einzelaufgabe · keine Übermittlung').pack(anchor='w',pady=(2,10))
        row=ttk.Frame(top); row.pack(fill='x')
        self.mode=tk.StringVar(value=next(iter(MODES)))
        self.combo=ttk.Combobox(row,textvariable=self.mode,values=list(MODES),state='readonly',width=68)
        self.combo.pack(side='left'); self.combo.bind('<<ComboboxSelected>>',self.changed)
        self.start=ttk.Button(row,text='Aufgabe prüfen und starten',command=self.run); self.start.pack(side='left',padx=8)
        self.stop=ttk.Button(row,text='Stopp',command=self.cancel,state='disabled'); self.stop.pack(side='left')
        self.load=ttk.Button(row,text='Aufgabe laden …',command=self.load_task); self.load.pack(side='left',padx=8)
        self.desc=tk.StringVar(); ttk.Label(top,textvariable=self.desc,wraplength=1150).pack(anchor='w',pady=8)
        self.status=tk.StringVar(value='Bereit. Noch kein Lauf gestartet.')
        ttk.Label(top,textvariable=self.status,font=('Segoe UI',12,'bold')).pack(anchor='w')
        tabs=ttk.Notebook(root); tabs.pack(fill='both',expand=True,padx=12)
        mapframe=ttk.Frame(tabs); tabs.add(mapframe,text='Kästchentopologie')
        self.canvas=tk.Canvas(mapframe,bg='#eef2f7',highlightthickness=0,height=320)
        self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda e:self.draw())
        ttk.Label(mapframe,text='Kästchen anklicken: zugehörige Wörter und offene Bits anzeigen. Pfeile sind Gleichungsabhängigkeiten, keine Erfolgsgarantie.',wraplength=1100).pack(pady=8)
        tableframe=ttk.Frame(tabs); tabs.add(tableframe,text='Alle Wörter und Herkunft')
        filterrow=ttk.Frame(tableframe); filterrow.pack(fill='x',pady=6)
        ttk.Label(filterrow,text='Filter:').pack(side='left')
        self.filter=tk.StringVar(); entry=ttk.Entry(filterrow,textvariable=self.filter,width=36); entry.pack(side='left',padx=8)
        entry.bind('<KeyRelease>',lambda e:self.refresh_table())
        ttk.Button(filterrow,text='Alle',command=lambda:self.set_filter('')).pack(side='left')
        self.tree=ttk.Treeview(tableframe,columns=('bits','wert','formen','bitbild'),selectmode='browse')
        self.tree.heading('#0',text='Wort / Kästchen'); self.tree.column('#0',width=180)
        for name,title,width in [('bits','Bekannt',80),('wert','Wert (hex)',100),('formen','Bitformen',80),('bitbild','Bits: ? heißt offen',340)]:
            self.tree.heading(name,text=title); self.tree.column(name,width=width)
        scroll=ttk.Scrollbar(tableframe,orient='vertical',command=self.tree.yview); self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y'); self.tree.pack(fill='both',expand=True)
        self.tree.bind('<<TreeviewSelect>>',self.details)
        self.detail=tk.Text(tableframe,height=7,wrap='word',font=('Consolas',10)); self.detail.pack(fill='x')
        logframe=ttk.Frame(tabs); tabs.add(logframe,text='Laufprotokoll')
        self.log=tk.Text(logframe,wrap='word',font=('Consolas',10)); self.log.pack(fill='both',expand=True)
        foot=ttk.Frame(root,padding=12); foot.pack(fill='x')
        from bitpuzzle import fenster as puzzle_fenster
        ttk.Button(foot,text='Bitpuzzle: Was fehlt?',command=lambda:puzzle_fenster(root)).pack(side='left',padx=6)
        ttk.Button(foot,text='Ergebnisordner öffnen',command=lambda:os.startfile(ROOT/'letzter_lauf')).pack(side='left')
        ttk.Label(foot,text='Ein Ergebnisplatz: Der nächste Lauf ersetzt nur den letzten Lauf dieser neuen Anwendung.').pack(side='left',padx=12)
        self.tabs=tabs; self.changed(); self.draw(); root.after(150,self.poll)
        root.protocol('WM_DELETE_WINDOW',self.close)

    def changed(self,event=None):
        self.custom=None
        self.result=None
        self.status.set('Bereit. Diese gewählte Aufgabe wurde noch nicht gerechnet.')
        self.refresh_table(); self.draw()
        a=beispiel(MODES[self.mode.get()])
        self.desc.set(a['beschreibung'] + (' | Alle Noncebits sind frei; fehlendes Wissen wird als OFFEN angezeigt.' if MODES[self.mode.get()]=='offen' else ''))

    def load_task(self):
        path=filedialog.askopenfilename(filetypes=[('Aufgabe','*.json')])
        if not path:return
        try:
            from maschine import validiere
            self.custom=validiere(json.loads(Path(path).read_text(encoding='utf-8-sig')))
            self.result=None; self.refresh_table(); self.draw()
            self.status.set('Bereit. Geladene Aufgabe wurde noch nicht gerechnet.')
            self.desc.set('Geladene Aufgabe: '+path+(' | MIT zusätzlicher W22-Testannahme' if self.custom.get('test_w22') is not None else ''))
        except Exception as e: messagebox.showerror('Aufgabe nicht gültig',str(e)); self.custom=None

    def run(self):
        if self.proc:return
        a=self.custom or beispiel(MODES[self.mode.get()])
        out=ROOT/'letzter_lauf'; out.mkdir(exist_ok=True)
        # Vorherige Ausgabe darf bei einem abgebrochenen neuen Lauf nicht als neu erscheinen.
        for name in ('ERGEBNIS.json','BEWEIS.jsonl.gz','KAESTCHEN.txt','PFADE.json.gz','PFADKARTE.txt'):
            (out/name).unlink(missing_ok=True)
        task=out/'AUFGABE.json'; task.write_text(json.dumps(a,indent=2),encoding='utf-8')
        self.result=None; self.refresh_table(); self.draw(); self.log.delete('1.0','end')
        self.start.configure(state='disabled'); self.load.configure(state='disabled'); self.combo.configure(state='disabled'); self.stop.configure(state='normal')
        self.status.set('Läuft …'); self.cancelled=False
        env=dict(os.environ,PYTHONHASHSEED='0',PYTHONUTF8='1')
        self.proc=subprocess.Popen([sys.executable,'-X','utf8','-B','-u',str(ROOT/'maschine.py'),'--aufgabe',str(task)],
            cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',env=env,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.hard_deadline=time.monotonic()+min(max(float(a.get('sekunden',90)),1),300)+60
        proc=self.proc
        def reader():
            for line in proc.stdout:self.q.put(('text',line))
            self.q.put(('exit',proc.wait()))
        threading.Thread(target=reader,daemon=True).start()

    def cancel(self):
        if self.proc and self.proc.poll() is None:
            self.cancelled=True; self.proc.terminate(); self.status.set('Abgebrochen – kein Urteil aus diesem Lauf.')

    def poll(self):
        if self.proc and self.proc.poll() is None and time.monotonic()>self.hard_deadline:
            self.cancel(); self.status.set('Zeitgrenze – abgebrochen, kein Urteil aus diesem Lauf.')
        while not self.q.empty():
            kind,data=self.q.get()
            if kind=='text':self.log.insert('end',data); self.log.see('end')
            else:
                self.proc=None; self.start.configure(state='normal'); self.load.configure(state='normal'); self.combo.configure(state='readonly'); self.stop.configure(state='disabled')
                path=ROOT/'letzter_lauf'/'ERGEBNIS.json'
                if not self.cancelled and data==0 and path.exists():
                    self.result=json.loads(path.read_text(encoding='utf-8'))
                    r=self.result
                    self.status.set(f"{r['status']} · {r['sekunden']:.1f} s · {len(r['prueffehler'])} Prüffehler" + (f" · Nonce {r['nonce']}" if r['nonce'] else ''))
                    self.log.insert('end',r['grund']+'\n')
                    rp=r.get('regelprofil',{})
                    self.log.insert('end','Aktive Regeln: '+', '.join(rp.get('aktive_regeln',[]))+'\n')
                    self.log.insert('end','Regelabschluss: '+rp.get('abschluss','nicht protokolliert')+'\n')
                    if rp.get('begrenzungen'): self.log.insert('end','Grenzen: '+'; '.join(rp['begrenzungen'])+'\n')
                    self.refresh_table(); self.draw()
                elif not self.cancelled:self.status.set('Lauf fehlgeschlagen – siehe Protokoll; kein bestätigtes Ergebnis.')
        self.root.after(150,self.poll)

    def set_filter(self,text):
        self.filter.set(text); self.refresh_table(); self.tabs.select(1)

    def refresh_table(self):
        self.tree.delete(*self.tree.get_children())
        self.detail.delete('1.0','end')
        if not self.result:return
        for n,b in enumerate(self.result['kaestchen']):
            if self.filter.get().lower() in b['wort'].lower():
                self.tree.insert('', 'end',iid=str(n),text=b['wort'],values=(f"{b['bekannte_bits']}/32",b['wert'] or 'offen',b['formen'],b['bitbild']))

    def details(self,event=None):
        sel=self.tree.selection()
        if not sel or not self.result:return
        b=self.result['kaestchen'][int(sel[0])]
        lines=[b['wort']+' – Herkunft der bekannten Bits:']
        lines += [f"Bit {p['bit']:2}: {p['wert']}  ← Buchzeile {p['buch']} · {p['regel']}" for p in b['belege']]
        if not b['belege']:lines+=['Noch kein fester Bitwert hergeleitet. Unbekannt wird nicht als null behandelt.']
        lines+=['Alle Eltern und Gleichungen stehen im komprimierten Beweisbuch im Ergebnisordner.']
        self.detail.delete('1.0','end'); self.detail.insert('end','\n'.join(lines))

    def draw(self):
        c=self.canvas; c.delete('all'); width=max(c.winfo_width(),950)
        bw=(width-100)/4; bh=85; gap=18
        boxes=[('Header / Mittelzustand','k0_',0,0),('Noncewort W3','k1_W3',1,0),('Fahrplan W18 / W20 / W22','k1_W22',2,0),('Runden im ersten Hash','k1_a',3,0),
               ('Zielgrenze H ≤ T','k2_H',0,1),('Endhash / Feedforward','k2_H',1,1),('Runden im zweiten Hash','k2_a',2,1),('Zwischenhash','k1_H',3,1)]
        coords=[]
        for title,prefix,col,row in boxes:
            x=20+col*(bw+gap); y=35+row*180; coords.append((x,y))
            found=[b for b in (self.result or {}).get('kaestchen',[]) if (b['wort']==prefix if prefix[-1].isdigit() else b['wort'].startswith(prefix))]
            total=32*len(found); known=sum(b['bekannte_bits'] for b in found)
            color='#d3efde' if total and known==total else '#fff0cb' if known else '#ffffff'
            tag=f'box{len(coords)}'
            c.create_rectangle(x,y,x+bw,y+bh,fill=color,outline='#475569',width=2,tags=tag)
            c.create_text(x+bw/2,y+24,text=title,font=('Segoe UI',11,'bold'),width=bw-12,tags=tag)
            text=f'{known}/{total} Bits bekannt' if total else 'Noch kein Messergebnis'
            if title.startswith('Zielgrenze'):
                text='Bedingung aus der Aufgabe'
            c.create_text(x+bw/2,y+61,text=text,font=('Segoe UI',10),tags=tag)
            if title.startswith('Zielgrenze'):
                c.tag_bind(tag,'<Button-1>',lambda e:self.zeige_ziel())
            else:
                c.tag_bind(tag,'<Button-1>',lambda e,p=prefix:self.set_filter(p))
        for a,b in [(0,1),(1,2),(2,3),(3,7),(7,6),(6,5),(5,4)]:
            x,y=coords[a]; X,Y=coords[b]
            if y==Y:
                right=X>x; sx=x+bw if right else x; tx=X if right else X+bw
                c.create_line(sx,y+bh/2,tx,Y+bh/2,arrow='both',width=2,fill='#2563eb')
            else:c.create_line(x+bw/2,y+bh,X+bw/2,Y,arrow='both',width=2,fill='#2563eb')
        c.create_text(width/2,158,text='W22 → W20 → W18 → W3 ist angeschlossen. Woher W22 kommt, bleibt Teil der Aufgabe.',font=('Segoe UI',11),fill='#334155')

    def zeige_ziel(self):
        a=(self.result or {}).get('aufgabe') or self.custom or beispiel(MODES[self.mode.get()])
        if a['arm']=='M': text=f"Vollständiger Vergleich H ≤ T\nT = {a['nbits_ziel']:064x}\nGleichheit zählt als Treffer."
        else:text='Exakter Wunschhash (Digest-Reihenfolge):\n'+a['ziel_hash_hex']
        if a.get('test_w22') is not None:text+=f"\n\nZusätzliche TEST-Annahme: W22 = {a['test_w22']:08x}. Sie wurde nicht aus dem Ziel hergeleitet."
        messagebox.showinfo('Bedingungen dieser Aufgabe',text)

    def close(self):
        self.cancel(); self.root.destroy()


if __name__=='__main__':
    root=tk.Tk(); Fenster(root); root.mainloop()
