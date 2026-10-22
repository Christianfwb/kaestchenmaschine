"""Small offline checks of contradiction handling, soundness and reference paths."""
import sys
import unittest
import itertools
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'kaestchen'))
sys.path.insert(0, str(ROOT / 'experimente' / 'skripte'))
from e1_bit import e1_lauf
from gatter import Graph, inv, read
from referenz import referenz_datei

class Regression(unittest.TestCase):
    def test_empty_domains_before_first_gate(self):
        g = Graph(); g.input(0)
        for d in ([0,2,3], [1,0,3], [1,2,0], [2,2,3], [1,1,3]):
            with self.subTest(d=d):
                self.assertEqual(e1_lauf(g,list(d)), ('WIDERSPRUCH',0))

    def test_constant_false_target_after_simplification(self):
        g=Graph(); x=g.input(0); root=g.gate('xor',x,x)
        self.assertEqual(root,0)
        d=[1,2,3]; d[root] &= 2
        self.assertEqual(e1_lauf(g,d)[0], 'WIDERSPRUCH')

    def test_exact_local_gate_support_and_negation(self):
        for op, neg in itertools.product(('and','xor'), (False,True)):
            g=Graph(); a=g.input(0); b=g.input(1)
            z=g.gate(op,inv(a) if neg else a,b)
            for A,B,Z in itertools.product((1,2,3),repeat=3):
                domains=[1,2,A,B,Z]; before=domains[:]
                solutions=[g.values(n) for n in range(4)]
                solutions=[v for v in solutions if all(m & (1<<int(x)) for m,x in zip(before,v))]
                status,_=e1_lauf(g,domains,max_sweeps=20)
                if not solutions:
                    self.assertEqual(status,'WIDERSPRUCH')
                else:
                    self.assertEqual(status,'FIXPUNKT')
                    exact=[sum(1<<v for v in {int(s[i]) for s in solutions}) for i in range(len(domains))]
                    self.assertEqual(domains,exact)

    def test_exhaustive_small_shared_graph(self):
        g=Graph(); a,b,c=[g.input(i) for i in range(3)]
        q=g.gate('xor',a,b); r=g.gate('and',q,inv(c)); root=g.gate('xor',r,a)
        for masks in itertools.product((1,2,3),repeat=3):
            for target in (0,1):
                d=[3]*len(g.nodes); d[:2]=[1,2]
                for node,mask in zip((a,b,c),masks): d[node]=mask
                d[root] &= 1<<target
                valid=[g.values(n) for n in range(8)]
                valid=[v for v in valid if all(m & (1<<int(x)) for m,x in zip(d,v))]
                status,_=e1_lauf(g,d,max_sweeps=20)
                if valid:
                    self.assertNotEqual(status,'WIDERSPRUCH')
                    for v in valid: self.assertTrue(all(m & (1<<int(x)) for m,x in zip(d,v)))

    def test_invalid_inputs_rejected(self):
        g=Graph()
        for d in ([1], [1,4]):
            with self.assertRaises(ValueError): e1_lauf(g,d)
        with self.assertRaises(ValueError): e1_lauf(g,[1,2],max_sweeps=0)

    def test_archived_baselines_exist(self):
        for name in ('ERGEBNIS2_E4_F1.json','ERGEBNIS2_WURZEL.json','ERGEBNIS_ZIELHASH_B_E4.json','ERGEBNIS_ZIELHASH_B_E1.json'):
            p=referenz_datei(name)
            self.assertEqual(p.parent, ROOT/'experimente'/'ergebnisse')
            self.assertTrue(p.is_file())
        with self.assertRaises(ValueError): referenz_datei('../README.md')

if __name__=='__main__': unittest.main(verbosity=2)
