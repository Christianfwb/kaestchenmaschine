"""Small DE/EN catalogue of rendered UI strings, including live results."""
import re

language = 'de'
_pairs = {}
_fixed = {}

def keep_static():
    _fixed.update(_pairs)

def T(de, en):
    _pairs[de] = en
    if len(_pairs) > 1024:
        del _pairs[next(iter(_pairs))]
    return en if language == 'en' else de

def switch(root, new_language):
    global language
    if new_language == language:
        return
    catalogue = {**_fixed, **_pairs}
    mapping = catalogue if new_language == 'en' else {v: k for k, v in catalogue.items()}
    # One substitution pass: translated words must not be translated again.
    keys = sorted((k for k in mapping if k), key=len, reverse=True)
    pattern = re.compile('|'.join(re.escape(k) for k in keys)) if keys else None
    def translate(value):
        if value in mapping:
            return mapping[value]
        return pattern.sub(lambda m: mapping[m.group()], value) if pattern else value
    def visit(w):
        kind = w.winfo_class()
        if kind in ('Label', 'TLabel', 'Button', 'TButton', 'TCheckbutton', 'Checkbutton'):
            w.configure(text=translate(str(w.cget('text'))))
        elif kind == 'Text':
            value = w.get('1.0', 'end-1c')
            changed = translate(value)
            if changed != value:
                pos = w.yview()
                w.delete('1.0', 'end'); w.insert('1.0', changed)
                w.yview_moveto(pos[0])
        elif kind == 'Canvas':
            for item in w.find_all():
                if w.type(item) == 'text':
                    w.itemconfigure(item, text=translate(w.itemcget(item, 'text')))
        elif kind == 'TNotebook':
            for tab in w.tabs():
                w.tab(tab, text=translate(w.tab(tab, 'text')))
        for child in w.winfo_children():
            visit(child)
    visit(root)
    root.title(translate(root.title()))
    language = new_language
