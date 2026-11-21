"""Lower contiguous bit windows <-> checked modular word remainders.
TW-1 collect; TW-2 project a checked FR relation; TW-3 return bits or a
relation to an active MONOME form; TW-4 incompatible remainders.
No factor scaling, arbitrary masks, new free bits, SHA or search driver.
"""
from collections import deque, defaultdict
import bitkern32 as bk
from uebersetzer32 import KernUebersetzer, wiederaufnahme as restore_translator


class KernTeilwort(KernUebersetzer):
    def __init__(self, nb, verdeckt, budget=None, max_ereignisse=100000,
                 teilbudget=10000, teilaktiv=True):
        self.teil = {}             # proof nr -> (word, remainder, modulus)
        self.teil_index = {}       # immutable exact fact -> proof nr
        self.teil_wort = defaultdict(list)
        self.teil_watched = set()
        self.teil_queue = deque()
        self.teil_pending = set()
        self.teil_done = set()     # (relation proof, partial proof)
        self.teil_events = []
        self.teilbudget = teilbudget
        self.teilaktiv = teilaktiv
        self.teilschritte = 0
        super().__init__(nb, verdeckt, budget, max_ereignisse)

    def _stop(self):
        if getattr(self, 'status', None) == 'WIDERSPRUCH':
            self.teil_queue.clear(); self.teil_pending.clear()
        return super()._stop()

    def _wake(self, word, cause):
        if self.teilaktiv and word in self.teil_watched and word not in self.teil_pending:
            self.teil_pending.add(word); self.teil_queue.append((word, cause))

    def setze(self, name, wert, regel, eltern):
        try:new = super().setze(name, wert, regel, eltern)
        except bk.Widerspruch:
            self.status='WIDERSPRUCH';self._clear_work();raise
        if new and '.' in name: self._wake(name.rsplit('.',1)[0], self.her[name])
        return new

    def beziehung(self,V,k,regel,eltern):
        try:return super().beziehung(V,k,regel,eltern)
        except bk.Widerspruch:
            self.status='WIDERSPRUCH';self._clear_work();raise

    def start_spaet(self,name,wert):
        try:return super().start_spaet(name,wert)
        except bk.Widerspruch:
            self.status='WIDERSPRUCH';self._clear_work();raise

    def _world_value(self, u, value, wn):
        fresh=u not in self.u_wert
        result = super()._world_value(u, value, wn)
        if fresh and '.' in u: self._wake(u.rsplit('.',1)[0], wn)
        return result

    def _verb_buchen(self, links, rechts, k, regel, eltern, ausloeser=None):
        self._stop()
        vid = super()._verb_buchen(links, rechts, k, regel, eltern, ausloeser)
        for w in (links, rechts):
            if w is not None:
                self.teil_watched.add(w); self._wake(w, self.verb[vid][3])
        return vid

    def _save(self, fact, rule, parents):
        if fact in self.teil_index: return self.teil_index[fact]
        word, rem, mod = fact
        nr = self.buche(rule, parents, 'TEILWERT', fact)
        self.teil[nr] = fact; self.teil_index[fact] = nr
        for old in self.teil_wort[word]:
            _, r, m = self.teil[old]; common = min(m, mod)
            if r % common != rem % common:
                self.buche('TW-4 konflikt', (old,nr), 'WIDERSPRUCH',
                           (word,common,r%common,rem%common))
                self.status='WIDERSPRUCH'; self._clear_work()
                raise bk.Widerspruch('incompatible partial word values')
        self.teil_wort[word].append(nr)
        self.teil_watched.add(word); self._wake(word,nr)
        return nr

    def sammeln(self, word, k=None):
        self._stop()
        prefix=0
        while prefix<self.NB and f'{word}.{prefix}' in self.wert: prefix+=1
        if k is None: k=prefix
        if type(k) is not int or not 1<=k<=self.NB or k>prefix:
            return None                  # not applicable, never exclusion
        parents=[self.her[f'{word}.{i}'] for i in range(k)]
        rem=sum(self.wert[f'{word}.{i}']<<i for i in range(k))
        return self._save((word,rem,1<<k),'TW-1 sammeln',parents)

    def sicht(self, vid, teil_nr, mod=None):
        self._stop()
        left,right,c,rnr=self.verb[vid]
        source,rem,oldmod=self.teil[teil_nr]
        if mod is None:mod=oldmod
        if type(mod) is not int or mod<2 or mod>oldmod or mod&(mod-1):
            raise ValueError('invalid partial modulus')
        if source==right: target,value=left,(rem+c)%mod
        elif source==left and right is not None: target,value=right,(rem-c)%mod
        else:raise ValueError('partial source not in relation')
        return self._save((target,value,mod),'TW-2 sicht',(rnr,teil_nr))

    def zurueck(self, teil_nr):
        self._stop()
        word,rem,mod=self.teil[teil_nr]
        for i in range(mod.bit_length()-1):
            name=f'{word}.{i}'; value=(rem>>i)&1
            if name in self.wert:
                if self.wert[name] != value:
                    self.buche(f'TW-3 bit {word} {i}',(teil_nr,self.her[name]),
                               'WIDERSPRUCH',(name,self.wert[name],value))
                    self.status='WIDERSPRUCH';self._clear_work()
                    raise bk.Widerspruch('partial word conflicts with bit')
                continue
            if name in self.form:
                c,vs=self.form[name]
                self.beziehung(vs,c^value,f'TW-3 form {word} {i}',
                               (teil_nr,self.form_nr[name]))
            else:
                # Ordinary bit entry only when no active symbolic form exists.
                self.setze(name,value,f'TW-3 bit {word} {i}',(teil_nr,))

    def _clear_work(self):
        self.arbeit.clear();self.arbeit_f.clear()
        self.teil_queue.clear();self.teil_pending.clear()

    def _drain_partial(self):
        while self.teil_queue:
            if self.teilschritte>=self.teilbudget:
                self.status='OFFEN';raise bk.Budget('partial work budget')
            word,cause=self.teil_queue.popleft();self.teil_pending.remove(word)
            self.teilschritte+=1;before=len(self.buch)
            self.sammeln(word)
            for nr in list(self.teil_wort[word]):
                self.zurueck(nr)
                for vid in sorted(self.sym_verb.get(word,())):
                    key=(self.verb[vid][3],nr)
                    if key in self.teil_done:continue
                    self.sicht(vid,nr);self.teil_done.add(key)
            self.teil_events.append(dict(word=word,cause=cause,
                partial_parents=list(self.teil_wort[word]),new_entries=len(self.buch)-before))

    def fixpunkt(self):
        if self.status=='WIDERSPRUCH':self._clear_work();return self
        try:
            while True:
                if self.teilaktiv:self._drain_partial()
                super().fixpunkt()
                if not self.teilaktiv or not self.teil_queue:break
            return self
        except bk.Widerspruch:
            self.status='WIDERSPRUCH';self._clear_work();raise


def pruefen(nr, rule, parents, art, info, nb, known, forms, relations,
            formula_state, partial, contradictions):
    """Independent checker: typed moduli and exact evidence, no solver helpers."""
    def fact(raw):
        if len(raw)!=3:raise ValueError('partial fact shape')
        w,r,m=raw
        if not isinstance(w,str) or not w or type(m) is not int or type(r) is not int:
            raise ValueError('partial fact type')
        if not 2<=m<=2**nb or m&(m-1) or not 0<=r<m:
            raise ValueError('partial modulus/remainder')
        return w,r,m
    if art=='TEILWERT':
        w,r,m=fact(info)
        if rule=='TW-1 sammeln':
            bits=m.bit_length()-1
            if len(parents)!=bits:raise ValueError('missing lower bits')
            want=0
            for i,p in enumerate(parents):
                item=known.get(f'{w}.{i}')
                if item is None or item[1]!=p:raise ValueError('wrong lower-bit evidence')
                want+=item[0]*2**i
            if r!=want:raise ValueError('wrong partial remainder')
        elif rule=='TW-2 sicht':
            if len(parents)!=2 or parents[1] not in partial:raise ValueError('missing partial parent')
            candidates=[v for v in formula_state.get('verb',{}).values() if v[3]==parents[0]]
            if len(candidates)!=1:raise ValueError('missing checked formula')
            l,s,c,_=candidates[0];source,value,oldm=partial[parents[1]]
            if m>oldm or oldm%m:raise ValueError('unproved stronger modulus')
            if source==s:expected=(l,(value+c)%m,m)
            elif source==l and s is not None:expected=(s,(value-c)%m,m)
            else:raise ValueError('source not in formula')
            if (w,r,m)!=expected:raise ValueError('wrong projected remainder')
        else:raise ValueError('unknown partial word rule')
        partial[nr]=(w,r,m);return
    if rule=='TW-4 konflikt':
        if art!='WIDERSPRUCH' or len(parents)!=2 or any(p not in partial for p in parents):
            raise ValueError('partial contradiction parents')
        w,a,m=partial[parents[0]];v,b,n=partial[parents[1]];d=min(m,n)
        if w!=v or a%d==b%d or tuple(info)!=(w,d,a%d,b%d):raise ValueError('unproved partial contradiction')
        contradictions.append(nr);return
    tokens=rule.split()
    if len(tokens)!=4 or tokens[:2] not in (['TW-3','bit'],['TW-3','form']):
        raise ValueError('unknown partial return rule')
    if not parents or parents[0] not in partial:raise ValueError('missing partial evidence')
    w,r,m=partial[parents[0]];i=int(tokens[3]);name=f'{w}.{i}'
    if tokens[2]!=w or i<0 or 2**i>=m:raise ValueError('bit outside proved window')
    value=(r//2**i)%2
    if tokens[1]=='form':
        f=forms.get(name)
        if art!='BEZIEHUNG' or len(parents)!=2 or f is None or parents[1]!=f[2]:
            raise ValueError('active form evidence absent')
        c,vs,_=f
        if tuple(info[0])!=tuple(sorted(vs)) or info[1]!=(c^value):raise ValueError('wrong form relation')
        relations[nr]=(frozenset(vs),c^value);return
    if art=='BIT':
        if len(parents)!=1 or tuple(info)!=(name,value) or name in forms or name in known:
            raise ValueError('invalid bit return / form overwritten')
        known[name]=(value,nr);return
    if art=='WIDERSPRUCH':
        old=known.get(name)
        if len(parents)!=2 or old is None or old[1]!=parents[1] or old[0]==value or tuple(info)!=(name,old[0],value):
            raise ValueError('unproved bit contradiction')
        contradictions.append(nr);return
    raise ValueError('partial return kind')


def wiederaufnahme(nb,buch,vertrag,checker,teilbudget=10000):
    base,errors=restore_translator(nb,buch,vertrag,checker)
    if errors:return None,errors
    k=KernTeilwort(nb,sorted(vertrag['verdeckt']),teilbudget=teilbudget)
    k.__dict__.update(base.__dict__)
    for nr,(_,_,art,info) in enumerate(buch):
        if art=='TEILWERT':
            key=tuple(info);k.teil[nr]=key;k.teil_index[key]=nr
            k.teil_wort[key[0]].append(nr);k.teil_watched.add(key[0])
    k.teil_watched.update(k.sym_verb)
    if k.status=='WIDERSPRUCH':k._clear_work()
    else:
        for w in sorted(k.teil_watched):k._wake(w,'checked replay')
    return k,[]
