# Distribution: the shipping dock

Every gated video gets a **posting pack** in `queue/<day>/slot<N>-<pillar>/`:
`video.mp4`, `cover.jpg`, `POST.md` (title, description, caption, checklist), `meta.json`.

## Publish modes (`studio.toml [publish].mode`)
| Mode | What happens | Needs |
|---|---|---|
| `local` (default) | Packs only. Post from your phone using POST.md, or let CI attach them as downloadable artifacts. | nothing |
| `upload_post` | Packs + scheduled upload to TikTok, YouTube, Instagram through Upload-Post, with AI-disclosure flags set. | `UPLOAD_POST_API_KEY`, `UPLOAD_POST_USER` (profile with accounts connected) |

Why a posting API instead of direct platform APIs: YouTube locks every upload from an unaudited
API project to **private**, and TikTok's direct-post API requires an app audit. Upload-Post's apps
are already approved, so one call posts publicly to all three.

## Schedule
Five slots per day in `America/New_York` (largest high-RPM audience): 07:30, 11:30, 15:00, 18:30, 21:00.
Change `[publish].slots` / `timezone` to target your audience. Posts are never scheduled into the past.

## Platform settings
| | TikTok | YouTube Shorts | Instagram Reels |
|---|---|---|---|
| Length | 61-72 s (Creator Rewards needs > 60 s) | up to 3 min | up to 3 min |
| Caption | hook line + 4-5 hashtags | title <= 60 chars, description + #shorts | same as TikTok |
| AI label | ON | "altered or synthetic" ON | ON when prompted |
| Extra | add a trending sound at 5-10% volume in-app | pin first comment | share to story |

## Manual posting checklist (local mode)
1. Open the day's folder, upload `video.mp4`, paste the caption from `POST.md`.
2. Turn on the AI-generated label. Set the cover from `cover.jpg` where supported.
3. Pin the `first_comment` question. Reply to the first 10 comments within the first hour.
