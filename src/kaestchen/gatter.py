"""Structurally shared Boolean DAG, Tseitin clauses, bounded SAT search."""
import hashlib
import json
import struct
import sys
import time
from pathlib import Path
import pruefung as P


class GraphLimit(Exception):
    pass


def inv(x):
    return 1-x if x in (0,1) else -x


class Graph:
    def __init__(self):
        self.nodes = [None,None]
        self.shared = {}

    def input(self,index):
        self.nodes.append(('input',index,0))
        return len(self.nodes)-1

    def gate(self,op,a,b):
        if op == 'and':
            if a == 0 or b == 0 or a == inv(b): return 0
            if a == 1: return b
            if b == 1 or a == b: return a
        elif op == 'xor':
            if a == 0: return b
            if b == 0: return a
            if a == 1: return inv(b)
            if b == 1: return inv(a)
            if a == b: return 0
            if a == inv(b): return 1
            negative = (a < 0) ^ (b < 0)
            a,b = abs(a),abs(b)
            if negative: return inv(self.gate(op,a,b))
        else:
            raise ValueError(op)
        a,b = sorted((a,b))
        key = (op,a,b)
        if key not in self.shared:
            if len(self.nodes) >= 300000:
                raise GraphLimit('300000 graph node limit')
            self.shared[key] = len(self.nodes)
            self.nodes.append(key)
        return self.shared[key]

    def values(self,assignment):
        values = [False,True]
        def read(x):
            return not values[-x] if x < 0 else values[x]
        for op,a,b in self.nodes[2:]:
            if op == 'input':
                values.append(bool(assignment >> a & 1))
            elif op == 'and':
                values.append(read(a) and read(b))
            else:
                values.append(read(a) != read(b))
        return values


class Ops:
    def __init__(self,graph):
        self.g = graph.gate
    const = staticmethod(lambda x:tuple((x >> i)&1 for i in range(32)))
    rot = staticmethod(lambda x,n:x[n:]+x[:n])
    shr = staticmethod(lambda x,n:x[n:]+(0,)*n)
    def xor(self,a,b,c):
        return tuple(self.g('xor',self.g('xor',x,y),z) for x,y,z in zip(a,b,c))
    def ch(self,a,b,c):
        return tuple(self.g('xor',z,self.g('and',x,self.g('xor',y,z))) for x,y,z in zip(a,b,c))
    def maj(self,a,b,c):
        return tuple(self.g('xor',self.g('and',x,y),self.g('and',z,self.g('xor',x,y))) for x,y,z in zip(a,b,c))
    def add(self,*words):
        result = words[0]
        for word in words[1:]:
            carry = 0
            output = []
            for a,b in zip(result,word):
                axb = self.g('xor',a,b)
                output.append(self.g('xor',axb,carry))
                carry = self.g('xor',self.g('and',a,b),self.g('and',axb,carry))
            result = tuple(output)
        return result


def build(base,bits,header=None,target=None):
    graph = Graph()
    op = Ops(graph)
    masked = base & ~sum(1<<b for b in bits)
    if header is None:
        header = P.header(masked)
    assert len(header) == 80
    target = P.target(P.BITS) if target is None else target
    assert 0 < target < 2**256
    padded = P.padded(header[:76]+masked.to_bytes(4,'little'))
    mid = P.compress(P.IV,struct.unpack('>16I',padded[:64]),P.IntegerOps)
    words = [op.const(x) for x in struct.unpack('>16I',padded[64:])]
    inputs = []
    for index,bit in enumerate(bits):
        node = graph.input(index)
        inputs.append(node)
        word = list(words[3])
        word[8*(3-bit//8)+bit%8] = node
        words[3] = tuple(word)
    first = P.compress(tuple(op.const(x) for x in mid),words,op)
    words = list(first)+[op.const(0x80000000)]+[op.const(0)]*6+[op.const(256)]
    digest = P.compress(tuple(op.const(x) for x in P.IV),words,op)
    numeric = [digest[byte//4][8*(3-byte%4)+bit] for byte in range(32) for bit in range(8)]
    le = 1
    for i,x in enumerate(numeric):
        if target >> i & 1:
            le = inv(graph.gate('and',x,inv(le)))
        else:
            le = graph.gate('and',inv(x),le)
    return graph,inputs,digest,le


def read(values,x):
    return not values[-x] if x < 0 else values[x]


def nonce(base,bits,assignment):
    for i,b in enumerate(bits):
        base = (base & ~(1<<b)) | (((assignment >> i)&1)<<b)
    return base


def clauses(graph,root):
    # Only target ancestors are required. Every retained gate has one named output.
    reachable = set()
    stack = [abs(root)]
    while stack:
        v = stack.pop()
        if v < 2 or v in reachable: continue
        reachable.add(v)
        op,a,b = graph.nodes[v]
        if op != 'input': stack.extend((abs(a),abs(b)))
    rows = []
    for v in sorted(reachable):
        op,a,b = graph.nodes[v]
        if op == 'and':
            rows.extend(((-v,a),(-v,b),(v,inv(a),inv(b))))
        elif op == 'xor':
            rows.extend(((a,b,-v),(inv(a),inv(b),-v),(a,inv(b),v),(inv(a),b,v)))
    rows.append((root,))
    return rows,reachable


def reference(n):
    raw = hashlib.sha256(hashlib.sha256(P.header(n)).digest()).digest()
    return raw,int.from_bytes(raw,'little') <= P.target(P.BITS)


def encoding_checks():
    checked = 0
    for op in ('and','xor'):
        for sign_a in (False,True):
            for sign_b in (False,True):
                graph = Graph()
                a,b = graph.input(0),graph.input(1)
                root = graph.gate(op,inv(a) if sign_a else a,inv(b) if sign_b else b)
                rows,_ = clauses(graph,root)
                for assignment in range(4):
                    values = graph.values(assignment)
                    x,y = bool(assignment&1)^sign_a,bool(assignment&2)^sign_b
                    correct = x and y if op == 'and' else x != y
                    assert read(values,root) == correct
                    assert all(any(read(values,v) for v in row) for row in rows[:-1])
                    # An incorrect gate value must violate its defining clauses.
                    values[abs(root)] = not values[abs(root)]
                    assert not all(any(read(values,v) for v in row) for row in rows[:-1])
                    checked += 1
    return checked


def experiment(base,bits,emit):
    start = time.perf_counter()
    graph,inputs,digest,root = build(base,bits)
    build_s = time.perf_counter()-start
    emit('build',nodes=len(graph.nodes),root=root,seconds=build_s)
    start = time.perf_counter()
    rows,reachable = clauses(graph,root)
    expected = []
    for assignment in range(1<<len(bits)):
        values = graph.values(assignment)
        raw = struct.pack('>8I',*(sum(read(values,x)<<i for i,x in enumerate(word)) for word in digest))
        n = nonce(base,bits,assignment)
        ref,valid = reference(n)
        assert raw == ref and read(values,root) == valid
        # Verify clause encoding on every concrete gate valuation.
        assert all(any(read(values,x) for x in row) for row in rows[:-1])
        assert any(read(values,x) for x in rows[-1]) == valid
        corrupted = bytearray(raw)
        corrupted[0] ^= 1
        assert bytes(corrupted) != ref
        if valid: expected.append(n)
    validation_s = time.perf_counter()-start
    emit('verified',candidates=1<<len(bits),clauses=len(rows),seconds=validation_s)
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'work'/'z3_deps'))
    import z3
    z3.set_param('memory_max_size',320)
    start = time.perf_counter()
    solver = z3.Tactic('sat').solver()
    solver.set(timeout=8000)
    variables = {v:z3.Bool(f'g{v}') for v in reachable}
    def literal(x):
        if x < 0: return z3.Not(variables[-x])
        if x < 2: return z3.BoolVal(bool(x))
        return variables[x]
    for offset in range(0,len(rows),1024):
        solver.add(*(z3.Or(*(literal(x) for x in row)) for row in rows[offset:offset+1024]))
    translation_s = time.perf_counter()-start
    emit('translated',seconds=translation_s,variables=len(variables))
    start = time.perf_counter()
    status = solver.check()
    search_s = time.perf_counter()-start
    result = dict(status='OK',base=base,bits=bits,nodes=len(graph.nodes),
                  target_nodes=len(reachable),clauses=len(rows),build_s=build_s,
                  validation_s=validation_s,translation_s=translation_s,search_s=search_s,
                  solver_status=str(status),z3=z3.get_version_string(),
                  all_hashes_target_and_clauses_verified=True,expected_hits=len(expected))
    if status == z3.sat:
        model = solver.model()
        assignment = sum(int(z3.is_true(model.eval(variables[v],model_completion=True)))<<i
                         for i,v in enumerate(inputs) if v in variables)
        found = nonce(base,bits,assignment)
        raw,valid = reference(found)
        assert valid and found in expected
        result.update(found_nonce=found,found_hash=raw[::-1].hex(),independently_verified=True)
    elif status == z3.unsat:
        assert not expected
        result['group_rejected'] = True
    else:
        result.update(status='OPEN',reason=solver.reason_unknown())
    return result
