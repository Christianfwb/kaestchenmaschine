"""Windows Tk smoke test. Withdrawn window; no candidate search. No visual QA."""
import pathlib,sys
P=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(P))
import oberflaeche as U
from glas import miner_cpu as M
def prohibited(*a,**k):raise AssertionError('Unexpected mining/meter call')
M.mine=prohibited
app=U.App(P/'headers/H970000.json');app.withdraw();app.update_idletasks()
assert not app.laeuft and app.hashrate_ohne_zeichnen is None
app.av_bit.set(32);app._av_kippen();assert 'Bitte' in app.av_l.cget('text')
app.av_bit.set(0);app._av_kippen();assert app.av['hash_abstand']==124
app._av_statistik();assert '127.7' in app.av_l.cget('text')
app._av_karte();assert 'Vereinigung' in app.av_l.cget('text')
assert not app.laeuft and app.hashrate_ohne_zeichnen is None
app.destroy();print('WINDOWS_TK_SMOKE_OK: start, invalid input, flip, statistics, map; no mining or rate measurement')
