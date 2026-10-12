# The host: character bible

The owner's front man for Quiet Money. He welcomes people, makes announcements and checks in with the community **once a week**. He is the
face of "a place to build a community, grow, practise, and eventually escape the rat race". Penny and the Fee Gremlin are the cartoon cast; he is
the human one. He is a virtual (AI-generated) host and says so in every description.

## Locks (never change these between videos)
- **Face:** `channel/host/reference.png`, the owner's picture. Pass it as `@image1` to every image-to-video model. Never describe a different face.
- **Look:** early thirties, short dark swept-up hair, light stubble, calm direct eyes; black tailored blazer over a charcoal roll-neck; a small round
  gold enamel pin with a black Q on the **left lapel** (it is the brand mark: keep it visible and unchanged); a plain wedding ring.
- **Room:** a warm, dimly lit hotel lounge with soft golden bokeh. Other rooms and other characters are allowed (the owner wants variety), but the
  face, the blazer and the pin are fixed, and the voice never changes.
- **Voice:** a custom profile made with `gemini-omni-audio` (id in `host.json`): low warm baritone, faint rasp, unhurried, quietly smiling,
  intimate, never salesy, neutral international English with a soft transatlantic polish. Plus the **voice anchor** (`voice-anchor.wav`): the first
  intro's own audio, passed as reference audio to later clips so the timbre carries over.
- **Manner:** calm, grounded, warm. Talks to one person. Short pauses before the key number. No hype, no income promises, no personal advice.

## What he says
Welcome, announcements, a weekly check-in, a community prompt ("comment your number"), a pointer to the week's videos. Ten seconds, 20 to 26 words,
complete sentences, ends on a clear next step. Never trails off.

## Schedule
One clip a week (`[host] weekday`, Monday). Off in `studio.toml` until the owner approves the intro (`[host] enabled = false`).

## Honesty
He is AI-generated. The description of every host video says so, and the upload carries YouTube's synthetic-media flag like every other video.
He never claims to be a real person, never invents credentials, and never gives personal financial advice.

## Recipe: new scene, same man
`python -m faceless host clip "<line>" --apply` builds the prompt from the locks above. To put him somewhere else, change the room sentence only; keep
`@image1`, the look sentence and the voice description. After the first intro run `python -m faceless host anchor <intro.mp4>` once.
