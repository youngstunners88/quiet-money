# Intake: VAST-AI-Research/tripo-python-sdk

- **Source:** https://github.com/VAST-AI-Research/tripo-python-sdk
- **Looked at:** 2026-10-13 04:26 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | MIT (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only
- **INFO `needs-keys`:** mentions keys: TRIPO_API_KEY

## Commands its docs tell you to run (read, do not run)

```
pip install tripo3d
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# Tripo3d Python SDK

The Tripo3d Python SDK is the official Python client library for the [Tripo 3D Generation API](https://tripo3d.ai/). With this SDK, you can easily generate high-quality 3D models.

## Features

- Text-to-3D model generation
- Image-to-3D model generation
- Multi-view to 3D model generation
- **Text-to-image and advanced image generation** (multi-model, multi-reference, templates)
- **Multiview image generation and editing**
- **One-shot model animation** (auto rig + retarget)
- **External model import** (GLB / OBJ / FBX / STL)
- Mesh editing including mesh segmentation, mesh completion and smart lowpoly
- Model conversion and stylization
- Rigging and retarget
- Asynchronous API support
- Complete type hints

## Installation

'''bash
pip install tripo3d
'''

## Quick Start

### Initialization

'''python
import asyncio
from tripo3d import TripoClient

async def main():
    # Initialize client with API key
    client = TripoClient(api_key="your_api_key")

    # Or read from environment variable
    # export TRIPO_API_KEY=your_api_key
    # client = TripoClient()

    # Use the client
    # ...

    # Close client connection
    await client.close()

# Run async function
asyncio.run(main())
'''

### Text to 3D Model

'''python
import asyncio
from tripo3d import TripoClient

async def text_to_model_example():
    async with TripoClient() as client:
        # C
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-13)

**PARK**, pipeline stage: visuals.

MIT, official. Parked with the Tripo MCP: key `TRIPO_API` fails authentication and no pillar needs 3D assets.

**Only the owner can:** Replace the Tripo key if 3D is wanted later.
