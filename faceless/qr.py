"""A small QR encoder (byte mode, error level L, versions 1 to 6: up to 134 bytes), so `faceless serve` can show the phone its address
without a new dependency. Enough for a LAN or Tailscale URL with a token; a longer text returns None and the caller prints the URL alone.

`matrix(text)` gives rows of booleans (True = dark); `terminal(text)` gives the block-character picture for a dark terminal.
"""

from __future__ import annotations

# version: (data codewords per block, blocks, error codewords per block, alignment centre or None)
_VERSIONS = {1: (19, 1, 7, None), 2: (34, 1, 10, 18), 3: (55, 1, 15, 22), 4: (80, 1, 20, 26), 5: (108, 1, 26, 30), 6: (68, 2, 18, 34)}
_MASKS = (
    lambda x, y: (x + y) % 2 == 0, lambda x, y: y % 2 == 0, lambda x, y: x % 3 == 0, lambda x, y: (x + y) % 3 == 0,
    lambda x, y: (x // 3 + y // 2) % 2 == 0, lambda x, y: x * y % 2 + x * y % 3 == 0,
    lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0, lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0,
)

_EXP, _LOG = [0] * 512, [0] * 256
_v = 1
for _i in range(255):
    _EXP[_i], _LOG[_v] = _v, _i
    _v <<= 1
    if _v & 0x100:
        _v ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def _mul(a: int, b: int) -> int:
    return 0 if a == 0 or b == 0 else _EXP[_LOG[a] + _LOG[b]]


def _ecc(data: list[int], n: int) -> list[int]:
    gen = [1]
    for i in range(n):
        gen = [a ^ b for a, b in zip([_mul(g, 1) for g in gen] + [0], [0] + [_mul(g, _EXP[i]) for g in gen])]
    rem = [0] * n
    for byte in data:
        factor = byte ^ rem[0]
        rem = rem[1:] + [0]
        rem = [r ^ _mul(g, factor) for r, g in zip(rem, gen[1:])]
    return rem


def _codewords(payload: bytes, version: int) -> list[int]:
    per_block, blocks, ecn, _ = _VERSIONS[version]
    capacity = per_block * blocks
    bits = [0, 1, 0, 0] + [(len(payload) >> i) & 1 for i in range(7, -1, -1)]
    for byte in payload:
        bits += [(byte >> i) & 1 for i in range(7, -1, -1)]
    bits += [0] * min(4, capacity * 8 - len(bits))
    bits += [0] * (-len(bits) % 8)
    data = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    data += [(0xEC, 0x11)[i % 2] for i in range(capacity - len(data))]
    chunks = [data[i * per_block:(i + 1) * per_block] for i in range(blocks)]
    eccs = [_ecc(c, ecn) for c in chunks]
    return [c[i] for i in range(per_block) for c in chunks] + [e[i] for i in range(ecn) for e in eccs]


def _penalty(m: list[list[bool]]) -> int:
    n, score = len(m), 0
    lines = m + [list(col) for col in zip(*m)]
    for line in lines:
        run = 1
        for a, b in zip(line, line[1:]):
            run = run + 1 if a == b else 1
            score += 3 if run == 5 else 1 if run > 5 else 0
        s = "".join("1" if c else "0" for c in line)
        score += 40 * (s.count("10111010000") + s.count("00001011101"))
    for y in range(n - 1):
        for x in range(n - 1):
            if m[y][x] == m[y][x + 1] == m[y + 1][x] == m[y + 1][x + 1]:
                score += 3
    dark = sum(map(sum, m)) * 100 // (n * n)
    return score + 10 * (abs(dark - 50) // 5)


def matrix(text: str) -> list[list[bool]] | None:
    payload = text.encode("utf-8")
    version = next((v for v, (per, blocks, _, _) in _VERSIONS.items() if len(payload) + 2 <= per * blocks), None)
    if version is None:
        return None
    n = 17 + 4 * version
    m = [[False] * n for _ in range(n)]
    fn = [[False] * n for _ in range(n)]

    def put(x: int, y: int, dark: bool) -> None:
        if 0 <= x < n and 0 <= y < n:
            m[y][x], fn[y][x] = dark, True

    for cx, cy in ((3, 3), (n - 4, 3), (3, n - 4)):                      # finders with their separators
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                put(cx + dx, cy + dy, max(abs(dx), abs(dy)) in (0, 1, 3))
    for i in range(8, n - 8):                                              # timing
        put(i, 6, i % 2 == 0)
        put(6, i, i % 2 == 0)
    align = _VERSIONS[version][3]
    if align:
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                put(align + dx, align + dy, max(abs(dx), abs(dy)) != 1)

    def format_bits(mask: int) -> None:
        data = (1 << 3) | mask                                             # error level L
        rem = data
        for _ in range(10):
            rem = (rem << 1) ^ ((rem >> 9) * 0x537)
        bits = ((data << 10) | rem) ^ 0x5412
        bit = lambda i: (bits >> i) & 1 == 1   # noqa: E731
        for i in range(6):
            put(8, i, bit(i))
        put(8, 7, bit(6))
        put(8, 8, bit(7))
        put(7, 8, bit(8))
        for i in range(9, 15):
            put(14 - i, 8, bit(i))
        for i in range(8):
            put(n - 1 - i, 8, bit(i))
        for i in range(8, 15):
            put(8, n - 15 + i, bit(i))
        put(8, n - 8, True)

    format_bits(0)                                                         # reserves the format area before the data is laid
    words = _codewords(payload, version)
    stream = [(w >> i) & 1 == 1 for w in words for i in range(7, -1, -1)]
    k, right = 0, n - 1
    while right >= 1:
        if right == 6:
            right = 5
        for vert in range(n):
            for j in range(2):
                x = right - j
                y = n - 1 - vert if ((right + 1) & 2) == 0 else vert
                if not fn[y][x]:
                    m[y][x] = stream[k] if k < len(stream) else False
                    k += 1
        right -= 2

    best, best_score = None, None
    for mask, rule in enumerate(_MASKS):
        trial = [[m[y][x] ^ (rule(x, y) and not fn[y][x]) for x in range(n)] for y in range(n)]
        saved = m
        m = trial
        format_bits(mask)
        score = _penalty(m)
        if best_score is None or score < best_score:
            best, best_score = [row[:] for row in m], score
        m = saved
    return best


def terminal(text: str, quiet: int = 3, invert: bool = False) -> str | None:
    """Half-block picture for a terminal with light text on a dark background (pass invert=True for a light terminal)."""
    m = matrix(text)
    if m is None:
        return None
    n = len(m) + 2 * quiet
    grid = [[False] * n for _ in range(n)]
    for y, row in enumerate(m):
        for x, dark in enumerate(row):
            grid[y + quiet][x + quiet] = dark
    if n % 2:
        grid.append([False] * n)
    chars = {(False, False): "█", (False, True): "▀", (True, False): "▄", (True, True): " "}   # the light modules are drawn
    if invert:
        chars = {(a, b): chars[(not a, not b)] for a, b in chars}
    return "\n".join("".join(chars[(grid[y][x], grid[y + 1][x])] for x in range(n)) for y in range(0, len(grid), 2))
