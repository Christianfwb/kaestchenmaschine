"""Sound overapproximation: each bit is {0}, {1}, or {0,1}.
Correlations are discarded, never assumed. Empty intersection is a conflict.
"""
from itertools import product
from functools import lru_cache

VALUES={1:(0,),2:(1,),3:(0,1)}
def constant(x,w): return tuple(1<<((x>>i)&1) for i in range(w))
def meet(word,pairs):
    result=list(word)
    for i,value in pairs:
        result[i] &= 1<<value
        if not result[i]: return None
    return tuple(result)
def boolean(words,fn):
    return tuple(sum(1<<v for v in {fn(*xs) for xs in product(*(VALUES[x] for x in bits))})
                 for bits in zip(*words))
def sigma(word,rotations):
    w=len(word)
    return boolean([tuple(word[(i+r)%w] for i in range(w)) for r in rotations],
                   lambda *xs: sum(xs)%2)
def add(*words):
    carries={0}; result=[]
    for bits in zip(*words):
        sums=set(carries)
        for bit in bits: sums={s+b for s in sums for b in VALUES[bit]}
        result.append(sum(1<<v for v in {s&1 for s in sums}))
        carries={s>>1 for s in sums}
    return tuple(result)
@lru_cache(maxsize=256)
def round_domains(registers,kword,wword,r0,r1):
    a,b,c,d,e,f,g,h=registers
    t1=add(h,sigma(e,r1),boolean((e,f,g),lambda e,f,g:f if e else g),kword,wword)
    t2=add(sigma(a,r0),boolean((a,b,c),lambda a,b,c:int(a+b+c>=2)))
    return (add(t1,t2),a,b,c,add(d,t1),e,f,g)
