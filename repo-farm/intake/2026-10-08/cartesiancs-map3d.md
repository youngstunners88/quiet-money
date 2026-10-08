# Intake: cartesiancs/map3d

- **Source:** https://github.com/cartesiancs/map3d
- **Looked at:** 2026-10-08 14:35 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | MIT (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
<p align='center'>
<h1 align='center'>🗺️ map3d</h1>
<p align='center'>Generate a real world 3D map</p>
</p>

<p align='center'>
<a href="https://map.fleet.im/">Visit Website</a> · <a href="https://github.com/cartesiancs/map3d/issues">Report Bugs</a>
</p>

![img](./.github/screenshot.png)

## About The Project

This is a 3D building mapping service implemented with [React-Three-Fiber](https://github.com/pmndrs/react-three-fiber). It allows exporting as a GLB file, and all features are free to use. Based on this project, various functionalities such as **digital twin**, **drone surveying**, and **GPS markers** can be implemented.

The map files are based on OpenStreetMap data.

> [!IMPORTANT]
> 📢 <strong>This project cannot guarantee the accuracy of the data.</strong> Since it uses OpenStreetMap data, some height values may be missing or incorrectly recorded. To address this issue, an option will be added in the future to allow users to manually correct the data.

## Roadmap

- [x] Create 3D Buildings
- [x] Create Roads
- [x] Export GLB
- [ ] Building Texture
- [ ] Height Customization
- [ ] Material
- [ ] Heightmap

## Demo

https://github.com/user-attachments/assets/1b61c2f8-dcf9-40bb-9804-59f6a74594dc

## Contributors

Hyeong Jun Huh [(GitHub)](https://github.com/DipokalLab)

## License

MIT License
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [x] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-08)

**KILL**, pipeline stage: visuals.

MIT. Builds 3D building maps from OpenStreetMap data and exports GLB. Nothing in money education needs it, and the data accuracy is disclaimed by its authors.
