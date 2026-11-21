"""kaestchen.py - Anschluss an die Kaestchenmaschine (Paket FABLE_SAT_KAESTCHEN_20261114 mit engine_f4, unveraendert).
Zwei Dinge, die kein Miner kann:
  beweis(header76, nonce)      Beweisbuch: Header + Nonce -> Hash, jede Folgerung als Zeile, vom unabhaengigen Pruefer gegengezeichnet.
                               Gebaut ohne Zielvorgabe (Target = 2^256-1), damit auch Nicht-Treffer ein Beweisbuch bekommen.
  kante(header76, nonce, r)    Die Kante: r Runden je Kompression, exaktes Ziel = reduzierter Hash dieser Nonce, untere 16 Noncebits frei.
                               r <= 16: die Maschine leitet die Nonce her. r >= 17: sie bleibt stehen (k2_W16 unbekannt).
Pfad zum Paket: Umgebungsvariable GLAS_KAESTCHEN oder mitgelieferte kaestchen_basis im Laborordner."""
import os, sys, time, threading
from pathlib import Path

def paket():
    p = Path(os.environ.get('GLAS_KAESTCHEN') or Path(__file__).resolve().parent.parent / 'kaestchen_basis')
    if not (p / 'engine_f4').is_dir(): raise FileNotFoundError(f'Kaestchenmaschine nicht gefunden: {p} (GLAS_KAESTCHEN setzen)')
    for q in (str(p), str(p / 'engine_f4')):
        if q not in sys.path: sys.path.insert(0, q)
    return p

def bewerte(k, header76: bytes, nonce: int, vertrag):
    """Bewertet das Buch k.buch (so wie es ist) - fuer Pruefungen mit leeren, gekuerzten oder manipulierten Buechern.
    Liefert dict(pruefer_fehler, hash_bits_belegt, digest_aus_buch, hashlib_gleich, vollstaendig)."""
    import pruefer_rueckweg, sha_verdrahtung32, hashlib
    fehler = pruefer_rueckweg.herleitung_pruefen(k, vertrag); n_fehler = len(fehler) if isinstance(fehler, (list, tuple)) else fehler
    hash_namen = sha_verdrahtung32.hash_zahl_bits([f'k2_H{j}' for j in range(8)])
    buchwerte = {z[3][0]: z[3][1] for z in k.buch if z[2] == 'BIT'}
    belegt = sum(1 for n in hash_namen if n in buchwerte)
    d = bytes(sum(buchwerte.get(hash_namen[8 * b + i], 0) << i for i in range(8)) for b in range(32)) if belegt == 256 else None
    ref = hashlib.sha256(hashlib.sha256(header76 + nonce.to_bytes(4, 'little')).digest()).digest()
    return dict(pruefer_fehler=n_fehler, hash_bits_belegt=belegt, digest_aus_buch=(d.hex() if d else None), hashlib_gleich=(d == ref),
                zeilen=len(k.buch), vollstaendig=(d == ref and belegt == 256 and len(k.buch) > 0 and n_fehler == 0))

def beweis(header76: bytes, nonce: int, sekunden: float = 120):
    paket()
    import gemeinsam, maschine, pruefer_rueckweg
    from rueckweg import KernRueckweg
    a = dict(header76_hex=header76.hex(), basis=nonce, maske=0, arm='M', profil='bits_erweitert', nbits_ziel=(1 << 256) - 1, rueckweg=True, sekunden=sekunden)
    k = KernRueckweg(32); k.stop_event = threading.Event(); k.deadline = time.monotonic() + sekunden; k.rueckweg_an = True
    t0 = time.perf_counter(); maschine.aufbau(k, a); k.fixpunkt(); t1 = time.perf_counter()
    digest = gemeinsam.digest_aus_werten(lambda n: k.wert[n])
    vertrag = maschine.vertrag(a)
    arten = {}
    for z in k.buch: arten[z[2]] = arten.get(z[2], 0) + 1
    t2 = time.perf_counter(); bw = bewerte(k, header76, nonce, vertrag); t3 = time.perf_counter()   # Pruefzeit = Pruefer + Rekonstruktion
    return dict(nonce=nonce, digest=digest.hex(), hashlib_gleich=bw['hashlib_gleich'], zeilen=len(k.buch), zeilenarten=arten, bits_fest=len(k.wert),
                pruefer_fehler=bw['pruefer_fehler'], hash_bits_belegt=bw['hash_bits_belegt'], digest_aus_buch=bw['digest_aus_buch'],
                pruefung_vollstaendig=bw['vollstaendig'],
                hinweis='Der Pruefer prueft Zeilen; ein leeres Buch haette 0 Fehler. "Vollstaendig" heisst: alle 256 Hash-Bits stehen als Buchzeilen, der daraus rekonstruierte Digest == hashlib, 0 Pruefer-Fehler, Buch nicht leer. Vertrag ohne Zielvorgabe (Target 2^256-1): bewiesen wird die Hashberechnung, nicht die Zielbedingung.', zeit_aufbau_herleitung=round(t1 - t0, 2), zeit_pruefung=round(t3 - t2, 2), buch=k.buch)

def kante(header76: bytes, nonce: int, r: int, sekunden: float = 300):
    paket()
    import gemeinsam, runden_modell
    basis = nonce & ~0xffff
    t = dict(header76_hex=header76.hex(), basis=basis, maske=0xffff, runden=r, arm='W', test_w22=None, profil='bits_erweitert',
             bitkonvention=gemeinsam.KONVENTION, beschreibung=f'Glas-Miner Kante: {r} Runden, exaktes Ziel')
    t['ziel_hash_hex'] = runden_modell.referenz_digest(t, nonce).hex(); runden_modell.pruefen_r(t)
    t0 = time.perf_counter(); k, prot, zeiten = runden_modell.herleiten_r(t, sekunden); dt = time.perf_counter() - t0
    from pruefer_rueckweg import herleitung_pruefen
    fehler = herleitung_pruefen(k, runden_modell.vertrag_r(t)); n_fehler = len(fehler) if isinstance(fehler, (list, tuple)) else fehler
    buchwerte = {z[3][0]: z[3][1] for z in k.buch if z[2] == 'BIT'}
    frei = gemeinsam.freie_bits(t); fest = {j: buchwerte[n] for j, n in frei if n in buchwerte}
    hergeleitet = None
    if len(fest) == 16 and n_fehler == 0:
        hergeleitet = basis | sum(b << j for j, b in fest.items())
    w16 = sum(1 for i in range(32) if f'k2_W16.{i}' in k.wert) if r >= 17 else None
    return dict(runden=r, noncebits_fest=len(fest), nonce_hergeleitet=(f'{hergeleitet:08x}' if hergeleitet is not None else None),
                stimmt=(hergeleitet == nonce) if hergeleitet is not None else None, k2_W16_feste_bits=w16, pruefer_fehler=n_fehler,
                hinweis='Ergebnis DIESES Versuchs (dieser Header, diese Nonce, dieses r); Nonce nur bei fehlerfreier Buchpruefung bestaetigt; kein Unmoeglichkeitsbeweis.', zeilen=len(k.buch), bits_fest=len(k.wert),
                sekunden=round(dt, 2), stop=prot.get('stop'))
