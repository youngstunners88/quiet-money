# Blender clips (2026-10-31), 9:16 1080x1920, 8 s, 24 fps, H.264, no text/faces/logos
1. stake-to-vault.blend -> flow/inbox/story-20261031-4.mp4: one gold coin becomes a spiral of coin stacks, then a vault door slams into place (LeBron: equity over wages, a small early stake). Render 47 min.
2. vinyl-reclaimed.blend -> flow/inbox/escape-20261031-5.mp4: a vinyl locked in a cage of bars rattles, the bars burst outward, the record rises gold-rimmed (Jay-Z: owning the master). Render 40 min.
3. half-sold-fortress.blend -> flow/inbox/myth-20261031-6.mp4: a half-gold, half-grey sphere; the grey "sold" half shatters, is replaced by gold, and a gold fortress rises (Taylor Swift: buying the masters back). Render 33 min.
Approach: pure bpy (clipN_*.py build the scene from primitives, keyframes, bevel/bisect), shared helpers in common.py (Eevee, AgX, dark world, emissive softboxes for gold reflections, DOF camera with track-to target, shake). Impact at frame 144 (last third).
Render: `./render.sh <file.blend> <frames_dir> <out.mp4>` (headless Blender PNG frames, then ffmpeg libx264 crf 17). About 12-15 s per frame on the 920MX laptop, 24 Eevee samples.
Reuse: `blender -b -P clip1_stake.py` regenerates the .blend; change colors/timings in the script (IMPACT, FRAMES in common.py). Inbox files are gitignored; the engine claims them as hook shots.
