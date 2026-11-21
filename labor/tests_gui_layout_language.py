"""No mining: test reachability and language changes with existing results."""
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import oberflaeche as U

def prohibited(*a, **k):
    raise AssertionError('Unexpected mining or measurement')
U.MC.mine = prohibited
U.App._start = prohibited
app = U.App(pathlib.Path(__file__).parent / 'headers/H970000.json')
try:
    for w, h in [(640, 480), (1024, 700), (1366, 768)]:
        app.geometry(f'{w}x{h}'); app.update()
        assert 640 <= app.winfo_width() <= w
        assert app.viewport.xview()[1] - app.viewport.xview()[0] < 1, app.viewport.xview()
        app.viewport.xview_moveto(1); app.viewport.yview_moveto(1); app.update()
        assert app.viewport.xview()[1] == 1
        assert app.viewport.yview()[1] == 1
        # The rightmost controls lie inside the visible viewport after scrolling.
        right = app.buch.winfo_rootx() + app.buch.winfo_width()
        edge = app.viewport.winfo_rootx() + app.viewport.winfo_width()
        assert right <= edge, (right, edge)
        assert app.scroll_x.winfo_ismapped() and app.scroll_y.winfo_ismapped()
        print(f'LAYOUT requested {w}x{h}, actual {app.winfo_width()}x{app.winfo_height()}: right/bottom reachable')
    app.av_bit.set(32); app._av_kippen()
    assert 'Bitte' in app.av_l.cget('text')
    app.sprache.set('English'); app._sprache_wechseln()
    assert 'Please' in app.av_l.cget('text')
    assert app.title() == 'The Glass Miner'
    assert app.nb.tab(0, 'text') == 'Glass wall'
    app.av_bit.set(0); app._av_kippen()
    assert app.av['hash_abstand'] == 124
    assert 'Different schedule words' in app.av_l.cget('text')
    assert 'Fahrplan' not in app.av_l.cget('text')
    result = app.av
    text_en = app.av_text.get('1.0','end-1c')
    app.sprache.set('Deutsch'); app._sprache_wechseln()
    assert app.av is result
    assert 'Hash-Abstand' in app.av_l.cget('text')
    app.sprache.set('English'); app._sprache_wechseln()
    assert app.av_text.get('1.0','end-1c') == text_en
    app._av_statistik(); assert 'mean 127.7' in app.av_l.cget('text')
    app._av_karte(); assert 'union of 32' in app.av_l.cget('text')
    assert 'Runden sind' not in app.av_text.get('1.0','end')
    app.zeitlupe.set(True); app._zl_zeige()
    assert 'round index' in app.zl_text.get('1.0','end')
    assert app.zl_text.cget('xscrollcommand') and app.zl_text.cget('yscrollcommand')
    assert app.buch.cget('xscrollcommand') and app.buch.cget('yscrollcommand')
    assert not app.laeuft and app.hashrate_ohne_zeichnen is None and app.geprueft == 0
    print('LANGUAGE: DE/EN roundtrip, existing results, new results, slow motion PASS')
    print('NO MINING / NO RATE MEASUREMENT: PASS')
finally:
    app.destroy()
