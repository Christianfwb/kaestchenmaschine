"""Offline SHA-256d bridge; no mining service or network submission.

The domain engine is conservative and drops correlations. It is not a solver.
Header data: Bitcoin Core src/kernel/chainparams.cpp (mainnet genesis).
Algorithm: SHA-256, FIPS 180-4; cross-checked against hashlib.
"""
import hashlib
import json
import platform
import random
import struct
import time
from pathlib import Path
import teilbits as D

MASK = 0xffffffff
IV = tuple(int(x, 16) for x in """
6a09e667 bb67ae85 3c6ef372 a54ff53a 510e527f 9b05688c 1f83d9ab 5be0cd19
""".split())
K = tuple(int(x, 16) for x in """
428a2f98 71374491 b5c0fbcf e9b5dba5 3956c25b 59f111f1 923f82a4 ab1c5ed5
d807aa98 12835b01 243185be 550c7dc3 72be5d74 80deb1fe 9bdc06a7 c19bf174
e49b69c1 efbe4786 0fc19dc6 240ca1cc 2de92c6f 4a7484aa 5cb0a9dc 76f988da
983e5152 a831c66d b00327c8 bf597fc7 c6e00bf3 d5a79147 06ca6351 14292967
27b70a85 2e1b2138 4d2c6dfc 53380d13 650a7354 766a0abb 81c2c92e 92722c85
a2bfe8a1 a81a664b c24b8b70 c76c51a3 d192e819 d6990624 f40e3585 106aa070
19a4c116 1e376c08 2748774c 34b0bcb5 391c0cb3 4ed8aa4a 5b9cca4f 682e6ff3
748f82ee 78a5636f 84c87814 8cc70208 90befffa a4506ceb bef9a3f7 c67178f2
""".split())


class IntegerOps:
    const = staticmethod(lambda x: x & MASK)
    add = staticmethod(lambda *xs: sum(xs) & MASK)
    xor = staticmethod(lambda a, b, c: a ^ b ^ c)
    ch = staticmethod(lambda a, b, c: (a & b) ^ (~a & c))
    maj = staticmethod(lambda a, b, c: (a & b) ^ (a & c) ^ (b & c))
    shr = staticmethod(lambda x, n: x >> n)
    rot = staticmethod(lambda x, n: ((x >> n) | (x << (32-n))) & MASK)


class DomainOps:
    const = staticmethod(lambda x: D.constant(x, 32))
    add = staticmethod(D.add)
    xor = staticmethod(lambda a, b, c: D.boolean((a,b,c), lambda x,y,z: x^y^z))
    ch = staticmethod(lambda a,b,c: D.boolean((a,b,c), lambda x,y,z: y if x else z))
    maj = staticmethod(lambda a,b,c: D.boolean((a,b,c), lambda x,y,z: int(x+y+z >= 2)))
    shr = staticmethod(lambda x,n: x[n:] + (1,)*n)
    rot = staticmethod(lambda x,n: x[n:] + x[:n])


def compress(state, words, op, trace=None):
    w = list(words)
    for i in range(16, 64):
        s0 = op.xor(op.rot(w[i-15],7),op.rot(w[i-15],18),op.shr(w[i-15],3))
        s1 = op.xor(op.rot(w[i-2],17),op.rot(w[i-2],19),op.shr(w[i-2],10))
        w.append(op.add(w[i-16],s0,w[i-7],s1))
    a,b,c,d,e,f,g,h = state
    for i in range(64):
        s1 = op.xor(op.rot(e,6),op.rot(e,11),op.rot(e,25))
        s0 = op.xor(op.rot(a,2),op.rot(a,13),op.rot(a,22))
        t1 = op.add(h,s1,op.ch(e,f,g),op.const(K[i]),w[i])
        t2 = op.add(s0,op.maj(a,b,c))
        a,b,c,d,e,f,g,h = op.add(t1,t2),a,b,c,op.add(d,t1),e,f,g
        if trace is not None:
            trace.append((a,b,c,d,e,f,g,h))
    return tuple(op.add(x,y) for x,y in zip(state,(a,b,c,d,e,f,g,h)))


def padded(data):
    return data + b'\x80' + b'\0'*((55-len(data)) % 64) + struct.pack('>Q',len(data)*8)


def sha(data):
    state = IV
    p = padded(data)
    for i in range(0,len(p),64):
        state = compress(state, struct.unpack('>16I',p[i:i+64]),IntegerOps)
    return struct.pack('>8I',*state)


def double_sha(data):
    return sha(sha(data))


MERKLE = '4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b'
GENESIS_HASH = '000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f'
NONCE = 2083236893
BITS = 0x1d00ffff


def header(nonce=NONCE):
    return (struct.pack('<I',1) + bytes(32) + bytes.fromhex(MERKLE)[::-1]
            + struct.pack('<III',1231006505,BITS,nonce))


def target(bits):
    exponent, coefficient = bits >> 24, bits & 0x7fffff
    value = coefficient >> (8*(3-exponent)) if exponent <= 3 else coefficient << (8*(exponent-3))
    if bits & 0x800000 or not 0 < value < 2**256:
        raise ValueError('invalid compact target')
    return value


def domain_hash(unknown_nonce_bits, base_nonce=NONCE):
    """Full 80-byte SHA256d, with selected numerical nonce bits unknown."""
    op = DomainOps
    p = padded(header(base_nonce))
    state = tuple(op.const(x) for x in IV)
    traces = []
    for offset in (0,64):
        words = [op.const(x) for x in struct.unpack('>16I',p[offset:offset+64])]
        for bit in unknown_nonce_bits:
            byte_index = 76 + bit//8
            if offset <= byte_index < offset+64:
                wi = (byte_index-offset)//4
                bi = 8*(3-(byte_index % 4)) + bit % 8
                word = list(words[wi])
                word[bi] = 3
                words[wi] = tuple(word)
        trace = []
        state = compress(state,words,op,trace)
        traces.append(trace)
    # The first digest is 32 bytes big endian, followed by SHA padding.
    words = list(state) + [op.const(0x80000000)] + [op.const(0)]*6 + [op.const(256)]
    trace = []
    result = compress(tuple(op.const(x) for x in IV),words,op,trace)
    traces.append(trace)
    return result,traces


def contains(domains, digest):
    return all(domain & (1 << ((word >> i)&1))
               for ds,word in zip(domains,struct.unpack('>8I',digest))
               for i,domain in enumerate(ds))


def lower_bound(domains):
    # Minimum permitted hash, using Bitcoin's little-endian uint256 convention.
    minimum = [sum((d == 2) << i for i,d in enumerate(word)) for word in domains]
    return int.from_bytes(struct.pack('>8I',*minimum),'little')


def main():
    start = time.perf_counter()
    rng = random.Random(20261020)
    vectors = [b'',b'abc',header()] + [rng.randbytes(n) for n in (1,31,32,55,56,63,64,65,80,119,120,127,128,129,1024)]
    vectors += [rng.randbytes(rng.randrange(0,257)) for _ in range(64)]
    for data in vectors:
        assert sha(data) == hashlib.sha256(data).digest()
        assert double_sha(data) == hashlib.sha256(hashlib.sha256(data).digest()).digest()
    assert len(header()) == 80
    assert double_sha(header())[::-1].hex() == GENESIS_HASH
    assert int.from_bytes(double_sha(header()),'little') <= target(BITS)
    # A changed header must be recomputed, not inherit acceptance.
    altered = double_sha(header(NONCE ^ 1))
    assert int.from_bytes(altered,'little') > target(BITS)
    assert target(0x03012345) == 0x12345
    assert target(0x02012345) == 0x123
    for bad in (0,0x1d80ffff,0x23000001):
        try:
            target(bad)
        except ValueError:
            pass
        else:
            raise AssertionError('invalid target accepted')
    experiments = []
    for base_nonce,unknown in ((NONCE,[]),(NONCE,[0]),(NONCE,[31]),(NONCE,[0,1,2,3]),(NONCE ^ 256,[0])):
        then = time.perf_counter()
        domains,traces = domain_hash(unknown,base_nonce)
        valid_completions = 0
        for assignment in range(1 << len(unknown)):
            nonce = base_nonce
            for j,bit in enumerate(unknown):
                nonce = (nonce & ~(1<<bit)) | (((assignment>>j)&1)<<bit)
            digest = hashlib.sha256(hashlib.sha256(header(nonce)).digest()).digest()
            assert contains(domains,digest)
            valid_completions += int.from_bytes(digest,'little') <= target(BITS)
        fixed = sum(d != 3 for word in domains for d in word)
        if not unknown:
            assert fixed == 256
        experiments.append({
            'base_nonce':base_nonce,
            'unknown_nonce_bits':unknown,
            'all_concrete_completions_checked':1 << len(unknown),
            'concrete_valid_completions':valid_completions,
            'fixed_output_bits':fixed,
            'minimum_possible_hash':f'{lower_bound(domains):064x}',
            'safe_rejection_by_target':lower_bound(domains)>target(BITS),
            'fixed_register_bits_after_each_round':[
                [sum(d != 3 for word in state for d in word) for state in trace]
                for trace in traces],
            'seconds':time.perf_counter()-then,
        })
    result = {
        'status':'OK','platform':platform.platform(),'python':platform.python_version(),
        'hashlib_comparison_messages':len(vectors),
        'genesis_header_hex':header().hex(),'genesis_hash':GENESIS_HASH,
        'historical_header_pow_valid':True,
        'changed_nonce_rejected':True,
        'target_hex':f'{target(BITS):064x}',
        'experiments':experiments,
        'seconds':time.perf_counter()-start,
        'scope':'Historical header PoW only; no current block, no full block consensus validation, no accelerated search claim.',
    }
    Path(__file__).with_name('ERGEBNIS.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k != 'experiments'}))
    for e in experiments:
        print(json.dumps({k:v for k,v in e.items() if k != 'fixed_register_bits_after_each_round'}))


if __name__ == '__main__':
    main()
