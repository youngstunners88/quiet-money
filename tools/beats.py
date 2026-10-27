"""Beat and onset detection with numpy only (no librosa): spectral flux, tempo by autocorrelation, beat grid by phase search."""
import subprocess, numpy as np

SR, WIN, HOP = 22050, 1024, 512

def decode(path, seconds=75, start=0.0):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{start}", "-t", f"{seconds}", "-i", str(path), "-ac", "1", "-ar", str(SR),
                          "-f", "s16le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768

def flux(x):
    w = np.hanning(WIN).astype(np.float32)
    n = 1 + (len(x) - WIN) // HOP
    frames = np.lib.stride_tricks.as_strided(x, (n, WIN), (x.strides[0] * HOP, x.strides[0])) * w
    mag = np.abs(np.fft.rfft(frames, axis=1))
    mag = np.log1p(mag * 20)
    d = np.maximum(0, np.diff(mag, axis=0)).sum(axis=1)
    d = np.concatenate([[0], d])
    d = d - np.convolve(d, np.ones(17) / 17, mode="same")
    return np.maximum(d, 0) / (d.std() + 1e-9)

def analyse(path, seconds=75, bpm_range=(70, 150)):
    x = decode(path, seconds)
    env = flux(x)
    fps = SR / HOP
    ac = np.correlate(env, env, mode="full")[len(env) - 1:]
    lo, hi = int(fps * 60 / bpm_range[1]), int(fps * 60 / bpm_range[0])
    seg = ac[lo:hi]
    lag = lo + int(seg.argmax())
    strength = float(seg.max() / (ac[0] + 1e-9))
    period = lag / fps
    best, phase = -1, 0.0
    for p in np.arange(0, period, 1 / fps):
        ts = np.arange(p, len(env) / fps, period)
        s = env[np.clip((ts * fps).astype(int), 0, len(env) - 1)].sum() / max(1, len(ts))
        if s > best: best, phase = s, p
    beats = np.arange(phase, len(env) / fps, period)
    return {"bpm": round(60 / period, 1), "period": period, "phase": phase, "strength": round(strength, 3), "beats": beats, "env": env, "fps": fps}

if __name__ == "__main__":
    import sys, glob
    for p in sorted(glob.glob("assets/music/*.mp3")):
        a = analyse(p)
        print(f"{p.split('/')[-1]:18s} bpm {a['bpm']:6.1f} pulse {a['strength']:.3f} first beat {a['phase']:.2f}s")
