"""miner_cpu.py - Die Hashschleife. Ehrlich und sichtbar: hashlib fuer die Geschwindigkeit, jede Nonce wird komplett gerechnet,
keine wird uebersprungen (das geht nicht - siehe unsere Messungen). Meldet Hashrate, bestes Ergebnis, Treffer.
Einzeilige, ueberschreibende Ausgabe. Stoppt bei Treffer, am Ende des Bereichs oder nach --sekunden."""
import hashlib, time

def mine(header76: bytes, target: int, start: int = 0, anzahl: int = 1 << 32, sekunden: float = None, melden=None, schritt: int = 20000):
    """Liefert dict(status, geprueft, sekunden, hashrate, bester_nonce, bester_hash_zahl, treffer_nonce, treffer_digest)."""
    sha = hashlib.sha256; t0 = time.perf_counter(); n = start; ende = start + anzahl; beste = (1 << 256, None); treffer = None
    while n < ende:
        block_ende = min(ende, n + schritt)
        for x in range(n, block_ende):
            d = sha(sha(header76 + x.to_bytes(4, 'little')).digest()).digest(); z = int.from_bytes(d, 'little')
            if z < beste[0]: beste = (z, x)
            if z <= target: treffer = (x, d); n = x + 1; break
        else:
            n = block_ende
        dt = time.perf_counter() - t0
        if melden: melden(dict(geprueft=n - start, sekunden=dt, hashrate=(n - start) / dt if dt else 0, bester_nonce=beste[1], bester_hash_zahl=beste[0], treffer=treffer is not None))
        if treffer or (sekunden and dt >= sekunden): break
    dt = time.perf_counter() - t0
    return dict(status='TREFFER' if treffer else ('ZEIT' if sekunden and dt >= sekunden else 'BEREICH_ENDE'), geprueft=n - start, sekunden=dt,
                hashrate=(n - start) / dt if dt else 0, bester_nonce=beste[1], bester_hash_zahl=beste[0],
                treffer_nonce=treffer[0] if treffer else None, treffer_digest=treffer[1].hex() if treffer else None)

def zeile(m):
    b = m['bester_hash_zahl']; return f"\r{m['geprueft']:>12,} Nonces  {m['hashrate']:>10,.0f} H/s  bestes Ergebnis: {b.bit_length():3d} Bit (Nonce {m['bester_nonce']:08x})  {'TREFFER' if m['treffer'] else ''}   "
