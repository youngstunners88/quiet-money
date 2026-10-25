# 2026-10-25: the phone lane (OpenDeviceMCP on the owner's own phone)

**Owner's words:** "I recreated the phone use in a way that lets us operate for free. Therefore create a system in how this can be used on my phone so that we can run flow.google images so that we cut costs from Muapi and to perform the posts on YouTube and community page and TikTok and to run fivver."

**Decided**
- The owner's OpenDeviceMCP (MIT, local, adb) is vendored at `tools/open-device-mcp` and driven by Claude Code on the owner's computer. It is free, with no PhoneUse account or key. Its 19 tests pass.
- Posting through the phone is approved: comics on the YouTube Posts tab, Shorts the API quota refused, and every passed Short on TikTok, each with its AI label on (`[phone]` in studio.toml, rule 9).
- Google Flow pictures replace Muapi for planned premium sets (vibe stills: $1.26 a video on Muapi). Daily Short stills stay on the free Cloudflare tier, because Flow cannot answer inside the cloud run.
- Fiverr: the phone reads the inbox and drafts. A reply is sent only after `phone approve` (rule 16).

**Risks the owner accepts:** automating the YouTube, TikTok, Flow and Fiverr apps is allowed by none of their terms. A slow pace, one device, the owner's own accounts and no fake engagement keep the risk low, but not at zero. The earlier stance in `faceless/flow.py` (never script the Flow login) still holds: the owner signs in by hand, and the phone only taps what a person would tap.
