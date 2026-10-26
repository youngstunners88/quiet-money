---
name: faceless-gig-gallery
description: Make the display images for a Fiverr gig (thumbnail plus gallery) that actually sell: 1280x769 hero with one promise, a "what you get" image, and a sample-proof image. Pictures from Flow (free) or the engine, type and layout drawn in code so the lettering is crisp. Use when the owner asks for better gig images, a gig thumbnail, gallery, mockups or sample pictures for Fiverr.
metadata:
  author: quiet-money
  version: 1.0.0
---

# Fiverr gig gallery

## Specs (verify against Fiverr's current gig editor before upload)
- Images **1280x769 px** (about 5:3), JPG or PNG, under 5 MB, up to 3 images (plus one video and PDFs). The first one is the thumbnail: it must read at about 300 px wide.
- Keep type inside the middle 90%; Fiverr crops thumbnails.

## The three images
1. **Hero (thumbnail).** One promise in 5-8 words, large, high contrast, over the best sample picture. A small line of proof ("6 directions in 24 hours", "avatar + banner + logo + brand sheet"). Brand colour only as accent.
2. **What you get.** A tidy grid of the actual deliverables (real renders from the engine, not icons), each captioned with its size or file type.
3. **Proof.** 3-4 different sample projects side by side showing range and consistency; every sample labelled "sample" and made-up.

## How to make them
- **Pictures:** the concept art comes from Flow in the browser pane (`faceless-flow-browser`, 0 credits): prompts ask for **no text, no letters** in the image. Anything readable is added in code afterwards, because AI lettering comes out garbled (the current Fern & Fold sheet shows it).
- **Layout:** Pillow in `faceless/gigart.py` (fonts Anton and Montserrat through `brand.font(name, size)`; brand colours from `faceless/brand.py`). Every output is 1280x769 and goes to `channel/services/<gig>/gallery/`.
- **Check:** open the contact sheet, shrink to 300 px wide, and ask: is the promise readable, is it different from the other thumbnails in search, is anything garbled or off-brand?

## Rules
- Samples are fictional brands; never a real client, person's face or other company's logo.
- No claim you cannot deliver in the picture (no "#1", no fake review stars, no price slashes).
- Do not write "AI-assisted" on any image (owner rule). Disclosure belongs in the gig's own fields.
- Gold/brand accents follow `faceless-visual-charge`: tension and clarity over noise.
