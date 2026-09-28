# What needs Bittu's attention

Updated 29 September 2026 01:45 IST. Release `v0.8.0-demo` is integrated in `main` (CI green) and submission package v6 is on your Mac.

## Needed now

1. **Mac check and tag (Terminal).** In the ThermoScope folder run `bash local/p08-verify/verify_release_mac.sh`. When it ends, run `bash local/p08-verify/finish_release_mac.sh`: it refuses unless every step passed, then updates your `main` and publishes the tag `v0.8.0-demo`. If anything fails, send `local/p08-verify/report.txt`.
2. **Team review of v6.** Open `output/submission/READ_FIRST_v6.md`, then the v6 PDF and the texts in `output/submission/v6/`. Check team details, the idea and what the team is comfortable presenting. This does not require a technical expert or labels.
3. **Final submission.** Recheck the live PS count, paste the v6 text, upload the v6 PDF, save a draft, inspect it, then submit. Keep the acknowledgement and final PDF. Nothing is submitted yet.

## Optional before submission

- Upload `v6/ThermoScope_SIH26162_demo_offline.mp4` (2 min, captioned, no audio) from the team's account as Unlisted, check it plays signed out, then paste the link. A team voice-over is possible using the talk track. Not uploaded yet.
- Run the offline demo on the Mac with Wi-Fi off (`docs/DEMO_RUNBOOK.md` §4) as a rehearsal.

## Decisions that stay yours

- A code licence and the public-file allowlist (`docs/inventory/public-release-review.csv`) before anything is made public. Nothing is public now.
- Hosting, only with a provider, billing owner and budget cap. Not needed for the submission.

## Not needed from you for this checkpoint

- Finding a faculty/domain expert or completing manual labels before submission: **deferred** at your request.
- A new FIRMS key, Earthdata account, GPU, cloud account or paid service: the existing local setup and saved data cover the P05 engineering checks.
- Manually installing libraries, merging branches or preparing evidence files: handled separately (the two Mac scripts above are the exception because only your Terminal can run them).
- More historical backfill: the 252 saved files were verified and integrated. Cases near region edges can still lack enough spatial coverage; keep those exclusions explicit.

## What the team can honestly say

Genuine satellite observations drive the map, context and computed rules. These are not hardcoded case answers. The labelling and XGBoost training/evaluation software can be completed and tested without claiming a validated classifier. Human validation is deferred; there is no reportable learned-model accuracy. Rule-trained runs test execution only and cannot replace independent test labels. The demonstrated release does not serve learned predictions or confirm industrial accidents.

No software output will stand in for a human reviewer or turn guesses into independent truth. P05 engineering acceptance and scientific model acceptance are separate statuses.

## Next-phase choice

P05 local acceptance, the bounded P07 demo and the local P08 release checks are complete. The next scientific step is independent labels (deferred, ADR-024); defer P06 experiments until they exist. A recording plus reliable local replay avoids waiting for hosting; a public hosted demo needs a provider, billing owner, budget cap and a reviewed deployment plan first.
