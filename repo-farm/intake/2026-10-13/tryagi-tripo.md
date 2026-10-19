# Intake: tryAGI/Tripo

- **Source:** https://github.com/tryAGI/Tripo
- **Looked at:** 2026-10-13 04:26 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | MIT (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only
- **INFO `needs-keys`:** mentions keys: TRIPO_API_KEY

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# Tripo

[![Nuget package](https://img.shields.io/nuget/vpre/Tripo)](https://www.nuget.org/packages/Tripo/)
[![dotnet](https://github.com/tryAGI/Tripo/actions/workflows/dotnet.yml/badge.svg?branch=main)](https://github.com/tryAGI/Tripo/actions/workflows/dotnet.yml)
[![License: MIT](https://img.shields.io/github/license/tryAGI/Tripo)](https://github.com/tryAGI/Tripo/blob/main/LICENSE.txt)
[![Discord](https://img.shields.io/discord/1115206893015662663?label=Discord&logo=discord&logoColor=white&color=d82679)](https://discord.gg/Ca2xhfBf3v)

## Features 🔥
- Fully generated C# SDK for [Tripo API V3](https://developers.tripo3d.ai/en/docs/quick-start) using [AutoSDK](https://github.com/HavenDV/AutoSDK)
- Same day update to support new features
- Updated and supported automatically if there are no breaking changes
- All modern .NET features - nullability, trimming, NativeAOT, etc.
- Targets .NET 10

### Usage
'''csharp
using Tripo;

using var api = new TripoClient(apiKey);

TaskCreatedResponse response = await api.ThreeDGeneration.TextToModelAsync(new TextToModelRequest
{
    Prompt = "Generate a stylized explorer character",
    Model = "v3.1-20260211",
    Texture = true,
});

Console.WriteLine($"Code: {response.Code}");
Console.WriteLine($"TaskId: {response.Data.TaskId}");

await System.Threading.Tasks.Task.Delay(TimeSpan.FromMinutes(1));

TaskResponse taskResponse = await api.Tasks
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-13)

**PARK**, pipeline stage: visuals.

MIT, wrong language, and the studio's `TRIPO_API` key is rejected (code 1002). No 3D in the money-education look.

**Only the owner can:** Replace the Tripo key if 3D is wanted later.
