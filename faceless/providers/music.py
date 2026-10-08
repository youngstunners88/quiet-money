"""Music provider: Google Lyria RealTime through the Gemini API (experimental, instrumental, free-tier accessible).

Not called per video. `faceless.musiclib` builds a small library once and every video picks from it, so music costs nothing per
video. The stream is 48 kHz stereo and always carries Google's SynthID watermark. Needs the optional `google-genai` package
(a build-time tool, not a runtime dependency: `pip install google-genai`) and GEMINI_API_KEY from the environment.
The paid non-streaming models (Lyria 3 / 3.5) have no free tier (checked 2026-10-08: HTTP 429 on this key), so they are not used.
"""

from __future__ import annotations

import asyncio
import wave
from pathlib import Path

from faceless import config
from faceless.providers import ProviderError, ProviderUnavailable

RATE, CHANNELS, WIDTH = 48000, 2, 2


async def _stream(prompt: str, negative: str, seconds: float, bpm: int, scale: str, brightness: float, density: float) -> bytes:
    from google import genai
    from google.genai import types
    key = config.env("GEMINI_API_KEY", "GOOGLE_API_KEY")
    client = genai.Client(api_key=key, http_options={"api_version": "v1alpha"})
    cfg = {"bpm": bpm, "temperature": 1.0, "density": density, "brightness": brightness}
    if scale and getattr(types.Scale, scale, None):
        cfg["scale"] = getattr(types.Scale, scale)
    prompts = [types.WeightedPrompt(text=prompt, weight=1.0)]
    if negative:
        prompts.append(types.WeightedPrompt(text=negative, weight=-1.0))
    want = int(seconds * RATE * CHANNELS * WIDTH)
    buf = bytearray()
    async with client.aio.live.music.connect(model="models/lyria-realtime-exp") as session:
        await session.set_weighted_prompts(prompts=prompts)
        await session.set_music_generation_config(config=types.LiveMusicGenerationConfig(**cfg))
        await session.play()

        async def collect():
            while len(buf) < want:
                async for msg in session.receive():
                    sc = msg.server_content
                    if sc and sc.audio_chunks:
                        for chunk in sc.audio_chunks:
                            buf.extend(chunk.data)
                            if len(buf) >= want:
                                return
                await asyncio.sleep(1e-6)
        await asyncio.wait_for(collect(), timeout=seconds + 30)
    return bytes(buf[:want])


def generate(prompt: str, out: Path, seconds: float = 80, bpm: int = 90, scale: str = "", brightness: float = 0.5,
             density: float = 0.4, negative: str = "vocals, singing, lyrics, spoken words, loud drums") -> dict:
    """Stream `seconds` of music into a 48 kHz stereo WAV at `out`."""
    if not config.env("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        raise ProviderUnavailable("GEMINI_API_KEY not set")
    try:
        import google.genai  # noqa: F401
    except ImportError as e:
        raise ProviderUnavailable("pip install google-genai (build-time tool for the music library)") from e
    try:
        data = asyncio.run(_stream(prompt, negative, seconds, bpm, scale, brightness, density))
    except Exception as e:  # noqa: BLE001 - any stream failure is one failed track, never a crash
        raise ProviderError(f"lyria realtime: {type(e).__name__}: {str(e)[:160]}") from e
    if len(data) < RATE * CHANNELS * WIDTH * seconds * 0.9:
        raise ProviderError(f"lyria realtime: short stream ({len(data)} bytes)")
    with wave.open(str(out), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(WIDTH)
        wf.setframerate(RATE)
        wf.writeframes(data)
    return {"model": "lyria-realtime-exp", "seconds": seconds, "usd": 0.0}
