# Worked example: YouTube upload (2026-10-10 to 11)

| Step | What happened | What it taught |
|---|---|---|
| Symptom | Composio's YouTube connection acted as "Teacher Chris" (`UCxBalkIv0Z0rf_MwPNXMvIw`); the studio channel is Quiet Money (`UC9B1QBr3_8Eulok8IdQbCqQ`) | Check which identity a connection acts as before any write: `YOUTUBE_LIST_CHANNELS {"mine": true}` |
| Wrong turns | Three reconnects, changing the default channel in YouTube, moving a channel | Changing the default in YouTube did nothing for the API. The sign-in itself decides |
| Cause | Google had a standing grant for Composio and skipped the account/brand-account chooser. The old Composio links were removed with `revoke_on_delete=False`, so the grant survived | Remove the grant at myaccount.google.com/connections, then connect from a private window and pick the channel on the chooser |
| Upload 1 | `YOUTUBE_UPLOAD_VIDEO` returned `uploaded`, then the video showed "Deleted video" | Success responses lie. Read the end state back minutes later |
| Upload 2 | Same result. YouTube's help calls it "processing abandoned" (file shortened or invalid) | The local file was fine (`ffprobe`, a clean decode), so the fault was in transit |
| Fix | Open a resumable session through `Composio().tools.proxy(...)`, then PUT the whole file to Google ourselves | Bypass the wrapper through the vendor's documented path. The third upload stayed up past 20 minutes |
| Side issues | 403 and 429 quota errors that cleared at midnight Pacific | Wait for the reset instead of looping |
| Codified | `composio_tools.youtube_upload()` with a channel guard and the AI label; tests; skill notes | Every fix leaves a test and a note |

Time to cause: a long afternoon of reconnects. With this loop it should be: probe identity, probe end state, read the tool schema, go to the raw API.
