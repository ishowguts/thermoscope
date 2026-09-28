# Prepared submission package

Current version: **6**, prepared 29 September 2026 from version 5 for **Git_Push_Pray**, team **144613**, PS **SIH26162**. It matches release `v0.8.0-demo`. Status: **ready for team review; no portal entry, upload, saved draft, final submission or video upload**.

Files are outside this repository, in the project folder at `sih 2026/output/submission/` on the owner's Mac. This private repository stores only the handoff and evidence, not presentation binaries or credentials. Earlier decks (v2–v5) are kept unchanged; the unversioned text files in that folder are version 5 and superseded by `v6/`.

| File | Purpose / verified size |
| --- | --- |
| `READ_FIRST_v6.md` | Which files are current |
| `ThermoScope_SIH26162_Git_Push_Pray_v6.pdf` | Upload candidate after review: six pages, 741,200 bytes, below the portal's 10 MB limit; selectable text, six working reference links |
| `ThermoScope_SIH26162_Git_Push_Pray_v6.pptx` | Editable six-slide source, 8,740,961 bytes |
| `v6/Idea_Title.txt` | 72 characters, limit 100 (unchanged since v2) |
| `v6/Abstract_Summary.txt` | 1,983 characters, limit 10,000 |
| `v6/Idea_Description.txt` | 7,451 characters, limit 50,000 |
| `v6/Portal_Fields.md` | Copy/paste mapping, technology bucket and YouTube guidance |
| `v6/Submission_Claims.md` | Team-only slide-to-evidence ledger, limitations and the changes from v5 |
| `v6/Team_Talk_Track_and_Video.md` | Three-minute talk track, the demo video and judge questions |
| `v6/SUBMISSION_PACKAGE.md` | Package notes, validation and hashes |
| `v6/ThermoScope_SIH26162_demo_offline.mp4` | Optional captioned recording of the real app, 2 min 4 s, 11,777,746 bytes; not uploaded |

Character counts exclude the final newline.

## What changed from version 5

Slide 4: tests `148 + 19` → `164 + 23` (the release's unit/API and PostGIS suites) and the outage response "Hashed 2-region offline replay; map-free mode demonstrated." Slide 5: the export step reads "CSV / GeoJSON export" and the P07 roadmap item "Built and demonstrated". Slide 2: "Evaluate AlphaEarth only after verified India holdout labels." (same meaning, fits one line). Speaker notes describe the release. The texts add the two-region offline replay package and the exports (one case as GeoJSON, a time window as CSV or GeoJSON) and update the test counts. Nothing else on the slides changed. The claims follow `RELEASE.md` §8.

## Verification

- 10 of 69 PPTX parts changed; the package validator passes against v5.
- PDF exported by LibreOffice; all six pages rendered and inspected. The slide 1 heading appears in a serif substitute for the specified Garamond (v5's image-based PDF showed a sans-serif substitute); reference links show in blue. Native PowerPoint rendering was not tested.
- The six slide 6 links resolve to the named pages (29 September).
- A separate read-only review pass found no blocker; its four should-fix items (single-case export format, two-region offline scope, "map extracts" wording, Mac re-check tense) were fixed before delivery.
- SHA-256 on the Mac match the sources.

| Artifact | SHA-256 |
| --- | --- |
| PDF v6 | `cc2b630d758cc2813426ce0bb9291721ef727a08acec7dc2660a15a99813f415` |
| PPTX v6 | `16d7a07e88e40e5aa3d74fdaa092e1aad8cb378504edc1bfdb25971ab8637a82` |
| Demo video | `ecbec20174ef751c7820a0916d44e26e42995492667dae743b1d453aba2e2dd4` |
| PDF v5 (superseded) | `0a61385ecebf21eb26468b3b366fb0ff49f64dbb58d04b7da104bd8820417024` |

## Next actions

1. Team reviews the exact v6 PDF and portal text. Recheck current PS capacity before saving/submitting; the 140/500 count from 27 September is a dated snapshot, not a reservation.
2. Optional video: upload from the team's own account as Unlisted, open the link signed out, then paste it. The private development repository is not a judge-accessible link.
3. Save the approved content as a draft, inspect that saved draft, then submit when the team leader authorizes it. The portal warns against post-submission changes. Retain the submitted file, acknowledgement and the verified final portal state.

Human validation is deferred (ADR-024); no accuracy claim is available. Do not delay an honest idea submission until the complete product exists.
