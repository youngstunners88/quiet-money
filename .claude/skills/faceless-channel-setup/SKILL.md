---
name: faceless-channel-setup
description: Stand up or rebrand Quiet Money's YouTube, TikTok, and Instagram accounts. Verify the handle, regenerate the brand kit, walk the owner through the account-creation steps only they can do, then connect each account through Composio and apply profile, playlists, and branding via API. Use when creating channels, renaming the brand, or connecting a new platform.
---

# Channel setup

What only the owner can do: create the accounts. Platforms tie accounts to a person (phone/email
verification, age, terms of service), and the YouTube API has no "create channel" endpoint. Never automate
signup or enter the owner's credentials; prepare everything so their part takes 5 minutes.

## 1. Pick and verify the handle (read-only)
```bash

python - <<'EOF'
from faceless.providers import composio_tools as ct
for h in ["@quietmoneyrules", "@itsquietmoney"]:
    items = ct.execute("YOUTUBE_GET_CHANNEL_ID_BY_HANDLE", {"channel_handle": h})["data"].get("items") or []
    print(h, "TAKEN" if items else "available")
EOF
curl -sL -A "Mozilla/5.0 (iPhone)" https://www.tiktok.com/@quietmoneyrules | grep -c "Couldn't find this account"   # 1 = free
```
Record the result in `channel/profiles.md` and `studio.toml [channel].handle`. Use one handle everywhere.

## 2. Brand kit
`python -m faceless brand` regenerates `channel/brand-kit/` (avatar, YouTube banner with mobile-safe text,
watermark, OG card, favicons, logo.svg) from `studio.toml`. Review the banner's safe area before shipping.

## 3. Owner checklist (send this, with the files)
**YouTube** (2 min, on the Google account that should own the channel):
1. youtube.com → profile picture → Settings → **Add or manage your channel(s)** → **Create a channel**.
2. Name `Quiet Money` → Create. (This makes a separate Brand Account channel; the personal channel is untouched.)
3. youtube.com/handle → set the handle from `profiles.md`.
4. YouTube Studio → Customization: upload `avatar.png`, `banner-youtube.png`, `watermark.png`; paste the description, links, keywords from `profiles.md`.
5. Studio → Settings → Upload defaults: category Education, language English.

**TikTok** (3 min, in the app): Sign up → username from `profiles.md` → profile photo `avatar.png` → bio → switch to a **Business account** (enables the link in bio before 1k followers) → turn on the AI-generated content label when posting.

**Instagram** (2 min): new account with the same username → photo → bio → Professional account (Creator).

## 4. Connect through Composio (owner clicks the links)
```bash
python -m faceless composio connect youtube    # choose the Quiet Money brand channel on Google's screen
python -m faceless composio connect tiktok
python -m faceless composio connect instagram
```
If YouTube was connected before to another channel, the new link must select the **Quiet Money** channel.

## 5. Apply branding via API (safety-checked)
Before any write, list the connected channel (`YOUTUBE_LIST_CHANNELS` with `mine=true`) and **stop unless its
title is the brand name**. Then: update description/keywords (`YOUTUBE_UPDATE_CHANNEL`), create one playlist
per series (`YOUTUBE_CREATE_PLAYLIST`), and a channel section for them. Discover exact arguments with the
`faceless-composio` skill (never guess slugs). Banner and avatar uploads stay manual (no API tool).

## 6. Wire the engine
Set `[publish].mode` (Composio YouTube uploads or Upload-Post), confirm `[site.socials]` URLs, run
`python -m faceless doctor`, then a one-video dry run with `--no-publish`.
