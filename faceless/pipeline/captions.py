"""Caption track (ASS/libass): word-by-word highlighted captions, a hook headline, and pop-in callouts.

Layout respects platform UI safe zones: nothing in the bottom ~22% (TikTok/Shorts description and
buttons) or hugging the right edge (like/comment rail).
"""

from __future__ import annotations

import re
import textwrap

from faceless import config


def ass_color(hex_rgb: str, alpha: int = 0) -> str:
    h = hex_rgb.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def ts(t: float) -> str:
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def esc(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")")


WEAK_ENDS = {"a", "an", "the", "of", "to", "in", "on", "at", "for", "and", "but", "or", "his", "her", "my",
             "your", "their", "its", "with", "from", "by", "as", "is", "was", "be", "that", "this", "then", "so"}


def _label(w: dict) -> str:
    return (w.get("display") or w["w"]).strip()


def chunk_words(words: list[dict], max_words: int, max_chars: int) -> list[list[dict]]:
    """Group words into 1-3 word caption chunks that end at punctuation and never on a weak word."""
    chunks, cur = [], []
    for w in words:
        token = _label(w)
        if not token:
            continue
        candidate = " ".join(_label(x) for x in cur + [w])
        if cur and (len(cur) >= max_words or len(candidate) > max_chars):
            chunks.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[.!?;:,]$", token):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    # carry a dangling weak word ("a", "the", "his"...) into the next chunk
    def weak_tail(ch):
        return len(ch) > 1 and re.sub(r"\W", "", _label(ch[-1]).lower()) in WEAK_ENDS \
            and not re.search(r"[.!?;:,]$", _label(ch[-1]))

    for i in range(len(chunks) - 1):
        while weak_tail(chunks[i]):
            chunks[i + 1].insert(0, chunks[i].pop())
    chunks = [c for c in chunks if c]
    # fold a lone short word ("Not", "up") into its neighbour instead of flashing it alone
    merged: list[list[dict]] = []
    for ch in chunks:
        if merged and len(merged[-1]) == 1 and len(_label(merged[-1][0])) <= 4 \
                and not re.search(r"[.!?;:,]$", _label(merged[-1][0])) \
                and len(" ".join(_label(x) for x in merged[-1] + ch)) <= max_chars + 3:
            merged[-1] = merged[-1] + ch
        else:
            merged.append(ch)
    return merged


def wrap_hook(text: str, width: int = 15) -> list[str]:
    return textwrap.wrap(text.upper(), width=width)[:3]


def callout_text(text: str) -> tuple[str, int]:
    """Big single-line callouts; long ones wrap to two lines at a smaller size so nothing overflows."""
    text = text.upper()
    if len(text) <= 11:
        return esc(text), 150
    lines = textwrap.wrap(text, width=max(11, (len(text) + 1) // 2 + 2))[:2]
    return r"\N".join(esc(l) for l in lines), 118


def build(script: dict, voice: dict, out_path) -> int:
    cfg = config.load()["production"]
    W, H = cfg["width"], cfg["height"]
    accent = ass_color(cfg["accent"])
    white, black = "&H00FFFFFF", "&H00000000"
    cap_y = cfg["caption_y"]
    words = voice["words"]
    total = voice["duration"]

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Montserrat Black,88,{white},{white},{black},&H96000000,-1,0,0,0,100,100,1,0,1,8,4,5,60,60,0,1
Style: Hook,Montserrat Black,74,&H00101010,&H00101010,{accent},&H00000000,-1,0,0,0,100,100,0,0,3,22,0,8,90,90,300,1
Style: Callout,Anton,150,{accent},{accent},{black},&H96000000,0,0,0,0,100,100,2,0,1,9,5,8,80,80,520,1
Style: Brand,Montserrat ExtraBold,34,&H40FFFFFF,&H40FFFFFF,&H80000000,&H00000000,-1,0,0,0,100,100,4,0,1,2,0,8,40,40,70,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    # Hook headline: pops in on frame 1, holds through the first beat (max 3.2s)
    hook_end = min(voice["beats"][0][1] if voice["beats"] else 3.0, 3.2)
    if script.get("hook_text"):
        lines.append(f"Dialogue: 3,{ts(0)},{ts(hook_end)},Hook,,0,0,0,,"
                     r"{\fscx70\fscy70\t(0,120,\fscx104\fscy104)\t(120,200,\fscx100\fscy100)\fad(0,150)}"
                     + r"\N".join(esc(l) for l in wrap_hook(script["hook_text"])))
    # Callouts: big number/phrase for beats that have one
    for (start, end), beat in zip(voice["beats"], script["beats"]):
        if not beat.get("callout"):
            continue
        s, e = start + 0.12, min(end - 0.05, start + 2.8)
        if e - s < 0.6:
            continue
        text, size = callout_text(beat["callout"])
        lines.append(f"Dialogue: 2,{ts(s)},{ts(e)},Callout,,0,0,0,,"
                     r"{\fs" + str(size) + r"\fscx55\fscy55\t(0,140,\fscx108\fscy108)\t(140,240,\fscx100\fscy100)\fad(40,160)}"
                     + text)
    # Word-by-word captions: chunk of 1-3 words, active word in accent and slightly larger
    chunks = chunk_words(words, cfg["caption_words_max"], cfg["caption_chars_max"])
    for ci, ch in enumerate(chunks):
        chunk_end = chunks[ci + 1][0]["start"] if ci + 1 < len(chunks) else min(total, ch[-1]["end"] + 0.4)
        for wi, w in enumerate(ch):
            s = w["start"]
            e = ch[wi + 1]["start"] if wi + 1 < len(ch) else chunk_end
            if e <= s:
                continue
            parts = []
            for k, x in enumerate(ch):
                label = _label(x)
                if "." not in label.rstrip(".").strip("."):  # keep abbreviations like J.C.
                    label = re.sub(r"[.,;:]+$", "", label)
                word = esc(label.upper())
                if k == wi:
                    parts.append(r"{\c" + accent + r"\fscx108\fscy108}" + word + r"{\c" + white + r"\fscx100\fscy100}")
                else:
                    parts.append(word)
            pop = r"{\fscx85\fscy85\t(0,90,\fscx100\fscy100)}" if wi == 0 else ""
            lines.append(f"Dialogue: 1,{ts(s)},{ts(e)},Caption,,0,0,0,,{{\\pos({W // 2},{cap_y})}}{pop}{' '.join(parts)}")
    # quiet brand watermark at the top (helps with re-uploads and recognition)
    brand = config.load()["channel"]["name"].upper()
    lines.append(f"Dialogue: 0,{ts(0)},{ts(total)},Brand,,0,0,0,,{esc(brand)}")
    out_path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
    covered = sum(len(c) for c in chunks)
    return covered
