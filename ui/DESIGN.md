# Control Room design

**Idea:** a production office at night. Dark slate desk; the plan itself is **paper**. Every visual rule comes from real film craft, so a filmmaker recognises it and a developer finds it crisp.

## Film-craft rules we use
| Craft rule | Where it shows up |
|---|---|
| **Script revision colours:** White, Blue, Pink, Yellow, Green, Goldenrod, Buff, Salmon, Cherry ([StudioBinder](https://www.studiobinder.com/blog/what-are-script-revision-colors)) | Release *n* is printed on the *n*th colour. Release 1 is white paper, release 2 blue, and so on. Old releases sit behind the current one in the stack |
| **Stripboard colours:** INT/DAY white, EXT/DAY yellow, INT/NIGHT blue, EXT/NIGHT green; black day breaks; banners for breaks ([StudioBinder](https://www.studiobinder.com/blog/shooting-schedule-stripboard/)) | The left column is a real stripboard. A **HOLD banner** is stamped across a held strip |
| **Call sheet** blocks: general call, sunset, schedule, cast call times ([StudioBinder](https://www.studiobinder.com/blog/film-call-sheet-template/)) | The release page layout and the rendered call-sheet PNG |
| **SetHero** crew confirmation: who has viewed, who has confirmed ([SetHero](https://help.sethero.com/en/articles/1523933-publishing-overview)) | Per-person confirmation of *the current release*; "still on r1" shown in amber |
| **Frame.io** version compare: A/B side by side, version chip ([Frame.io](https://support.frame.io/en/articles/4431-version-stacking-and-comparison)) | The two preview candidates |
| **Vercel Geist status dot:** only in-flight states animate, every state has a label, change on state change only ([Geist](https://vercel.com/geist/status-dot)) | Agent jobs, renders, publications |
| **Slate:** hinged stick, scene and take fields | The logo: a slate reading TAKE 2. The take number is the current release |

## Tokens
- Desk `#0E0E10`, panel `#151518`, raised `#1C1C20`, hairline `#26262C`, ink `#ECEAE3`, muted `#8E8C86`, faint `#5E5D59`.
- Status: pass `#4FBF7F`, fail `#E5534B`, hold/amber `#E8B04A`, verify `#D9C26A`, running `#6FA8DC`.
- Revision paper: White `#F7F5EE`, Blue `#CFE3F3`, Pink `#F6CFD8`, Yellow `#F5EAA8`, Green `#D3E9C9`, Goldenrod `#E8C46A`, Buff `#EBDDB8`, Salmon `#F3BBA4`, Cherry `#E58A8F`. Paper text is ink `#1A1916`.
- Strips: INT/DAY `#F4F1E8`, EXT/DAY `#F2E27A`, INT/NIGHT `#9DC3E6`, EXT/NIGHT `#A8D5A2`, day break `#08080A`.
- No purple. No emoji. Icons: Phosphor (regular, 16/20 px).

## Type
- **Instrument Serif** for display moments: the production title and big state headlines ("Scene 3 is on hold").
- **Geist** for UI text.
- **Courier Prime** for anything from the script: beats, story costs, the director's note. It's the screenplay font.
- **Geist Mono** for times, IDs and revision numbers, with tabular figures.

## Layout (1440 to 1920 wide; the video is recorded at 1920×1080)
```
┌ slate logo · title · day ─────────── script r1 · constraints r3 · clock · live ┐
│ STRIPBOARD   │ CHANGE DESK                               │ RELEASES (paper)    │
│ scene strips │ headline + pipeline (7 steps, dots)       │ current page on top │
│ HOLD banner  │ decision: A | B previews, check chips     │ crew confirmations  │
│ day break    │ ruled-out options (collapsed)             │ publications        │
├──────────────┴───────────────────────────────────────────┴─────────────────────┤
│ timeline (one line per event, newest left)                                       │
└──────────────────────────────────────────────────────────────────────────────────┘
```

## Motion (motion/react; all under 400 ms except the release drop; respects prefers-reduced-motion)
1. **Hold stamp:** a banner slides across the strip, scale 1.15 → 1 with rotate -3° → -1.5° (spring, stiffness 500, damping 30), and the strip desaturates.
2. **Pipeline:** queued = slow pulse; running = rotating ring; done = static check. A dot changes only when its state does.
3. **Release drop:** the new paper page drops in (y -28 → 0, rotate -2° → 0°, 520 ms ease-out-quint); the old page slides back 10 px and gets a SUPERSEDED stamp.
4. **Outdated:** decision cards dim to 45 % and an OUTDATED stamp lands diagonally.
5. **Confirmation tick:** the check path draws in 240 ms; the counter rolls.
6. **Numbers and clock:** tabular, never jump in width.
