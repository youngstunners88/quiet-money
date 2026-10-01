"""Original procedural audio: an ambient pad + pulse bed (never a copyright claim) and transition SFX."""

from __future__ import annotations

import wave

import numpy as np

SR = 44100
NOTE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def _freq(semitone_from_a4: float) -> float:
    return 440.0 * 2 ** (semitone_from_a4 / 12)


def _lowpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    spec *= 1 / (1 + (f / cutoff) ** 4)
    return np.fft.irfft(spec, n=len(x))


def _bandpass(x: np.ndarray, lo: float, hi: float) -> np.ndarray:
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    spec *= (1 / (1 + (lo / np.maximum(f, 1)) ** 4)) * (1 / (1 + (f / hi) ** 4))
    return np.fft.irfft(spec, n=len(x))


def write_wav(path, x: np.ndarray) -> None:
    x = np.clip(x, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def ambient_bed(seconds: float, key: str = "A", bpm: float = 88, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    root = NOTE.get(key, 9) - 9 - 24          # semitones from A4, two octaves down (A2 region)
    # minor-key progression i - VI - III - VII, two bars per chord
    progression = [[0, 3, 7, 12], [-4, 0, 3, 8], [3, 7, 10, 15], [-2, 2, 5, 10]]
    bar = 4 * 60 / bpm
    chord_len = 2 * bar
    pad = np.zeros(n)
    fade = int(0.9 * SR)
    for ci in range(int(np.ceil(seconds / chord_len)) + 1):
        a = int(ci * chord_len * SR)
        b = min(n, int((ci + 1) * chord_len * SR) + fade)
        if a >= n:
            break
        seg_t = t[a:b]
        seg = np.zeros(b - a)
        for semis in progression[ci % 4]:
            f0 = _freq(root + 12 + semis)
            for det in (-0.12, 0.0, 0.11):
                f = f0 * 2 ** (det / 12)
                ph = rng.uniform(0, 2 * np.pi)
                for k in range(1, 6):
                    seg += np.sin(2 * np.pi * f * k * seg_t + ph * k) / (k * 1.4)
        env = np.ones(b - a)
        ramp = min(fade, (b - a) // 2)
        env[:ramp] = np.linspace(0, 1, ramp)
        env[-ramp:] = np.linspace(1, 0, ramp)
        pad[a:b] += seg * env
    pad = _lowpass(pad, 1400)
    pad *= 1 + 0.08 * np.sin(2 * np.pi * 0.25 * t)                 # slow swell
    # soft heartbeat pulse on beats 1 and 3 (felt more than heard)
    pulse = np.zeros(n)
    beat = 60 / bpm
    kick_len = int(0.35 * SR)
    kt = np.arange(kick_len) / SR
    kick = np.sin(2 * np.pi * (48 + 60 * np.exp(-kt * 22)) * kt) * np.exp(-kt * 9)
    for bi in range(int(seconds / beat)):
        if bi % 2:
            continue
        a = int(bi * beat * SR)
        b = min(n, a + kick_len)
        pulse[a:b] += kick[: b - a] * (0.9 if bi % 4 == 0 else 0.6)
    # airy shaker on 8ths
    shaker = np.zeros(n)
    tick_len = int(0.05 * SR)
    for bi in range(int(seconds / (beat / 2))):
        a = int(bi * beat / 2 * SR)
        b = min(n, a + tick_len)
        shaker[a:b] += rng.normal(0, 1, b - a) * np.exp(-np.arange(b - a) / (0.012 * SR)) * (0.5 if bi % 2 else 0.25)
    shaker = _bandpass(shaker, 6000, 12000)
    mix = pad / (np.abs(pad).max() + 1e-9) * 0.55 + pulse * 0.35 + shaker * 0.06
    mix[: int(0.4 * SR)] *= np.linspace(0, 1, int(0.4 * SR))
    mix[-int(1.0 * SR):] *= np.linspace(1, 0.3, int(1.0 * SR))
    return mix / (np.abs(mix).max() + 1e-9) * 0.8


def sfx_track(seconds: float, cuts: list[float], seed: int = 0) -> np.ndarray:
    """Whoosh into every cut plus a low impact under the hook."""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    out = np.zeros(n)
    wl = int(0.42 * SR)
    for c in cuts:
        noise = rng.normal(0, 1, wl)
        whoosh = _bandpass(noise, 500, 5000)
        env = np.sin(np.linspace(0, np.pi, wl)) ** 2
        env *= np.linspace(0.4, 1.0, wl)
        whoosh = whoosh * env
        whoosh /= np.abs(whoosh).max() + 1e-9
        a = int(max(0, c - 0.28) * SR)
        b = min(n, a + wl)
        out[a:b] += whoosh[: b - a] * 0.55
    il = int(0.9 * SR)
    it = np.arange(il) / SR
    impact = np.sin(2 * np.pi * (40 + 70 * np.exp(-it * 18)) * it) * np.exp(-it * 4.5)
    out[:il] += impact[: min(il, n)] * 0.9
    return out
