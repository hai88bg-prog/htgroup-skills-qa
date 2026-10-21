# HT-Group Skills QA — Stages 3–8

**Public, portable, read-only verification core** for the six-step film workflow.

> Status: **Initial portable offline validators, not the original native reviewer**. This repository is deliberately separate from HT-Group source, film scripts, images, user accounts and API integrations. It cannot certify Native PASS or Reviewer PASS. Raw Stage 3/4 outputs need adapters to the normalized QA schema before the checks reflect the real pipeline. Do not treat `PASS_OFFLINE_STRUCTURE` as production-ready.

## The six gates

| Stage | Vietnamese UI | Current public checks | Limits |
|---|---|---|---|
| 3 | Viết kịch bản | Immutable 31-criteria reference, prewrite source seal, 15-second clips, uniqueness, basic continuity/handoff | No semantic plot verification, no native reviewer |
| 4 | Chia cảnh quay | Exactly four shots / 15 seconds, contiguous shot windows, required source-reference tracks and edit fields | No camera-axis geometry or native storyboard verification |
| 5 | Xem đồ thị | Unique node IDs, valid connected edges, no self-loop | Does not verify actual HT-Group Canvas wiring |
| 6 | Kiểm điều kiện | Named preflight booleans, read-only, no premature generation | Does not trust booleans as verified external evidence |
| 7 | Duyệt vẽ ảnh | Explicit approval metadata and exact plan hash | Does not authenticate the human approving |
| 8 | Chạy | Confirms generated files, paths, manifest IDs and SHA-256 values | Does not create images, inspect artwork or OCR panels |

Machine-checkable criteria are **PARTIAL_MACHINE_CHECK**; everything else is **NOT_RUN**. The final status remains **NOT_VERIFIED** even when all offline structural checks succeed. Actual Native PASS and independent Reviewer PASS need their own authenticated native integrations and evidence.

## Install on another machine

Python 3.9+ is required. No external packages or API keys.

```bash
git clone https://github.com/hai88bg-prog/htgroup-skills-qa.git
cd htgroup-skills-qa
python3 -m unittest discover -s tests -v
python3 qa.py rubric --stage 3
```

To move *your own private skills*, copy the skill folders separately onto the second machine (for example `htgroup-stage3-screenplay` and `htgroup-stage4-shotlist`). **Do not put the film, API keys, `.env`, internal adapters or private skill data into this public repository.** Consult `docs/MOVE_TO_NEW_MACHINE.md`.

## Before authoring Stage 3 or 4

Stage 3 must read DR01–DR07, A01–A14 and B01–B10 before writing. Stage 4 must read the relevant original rubric and the upstream Stage 3 lock. A generated prewrite file records the rubric/source hashes but **cannot prove an LLM actually read or understood them**. It is a tamper-evident preparation record, not approval evidence.

```bash
python3 qa.py rubric --stage 3
python3 qa.py prewrite --stage 3 --source /path/to/three-input-files --output /path/to/prewrite-stage3.json
python3 qa.py validate --stage 3 --source /path/to/three-input-files --prewrite /path/to/prewrite-stage3.json --data /path/to/normalized-stage3.json

python3 qa.py rubric --stage 4
python3 qa.py prewrite --stage 4 --source /path/to/stage3-output.zip --output /path/to/prewrite-stage4.json
python3 qa.py validate --stage 4 --source /path/to/stage3-output.zip --prewrite /path/to/prewrite-stage4.json --data /path/to/normalized-stage4.json
```

`--source` for stage 3 contains exactly the named files `README.md`, `concept_bible.md`, `reference_manifest.json`. For stage 4 it is the real stage-3 ZIP. `--data` accepts a **normalized QA envelope**; raw film files cannot be passed in unmodified. See `docs/NORMALIZED_SCHEMAS.md`.

Stages 5–8:

```bash
python3 qa.py validate --stage 5 --data graph.json
python3 qa.py validate --stage 6 --data preflight.json
python3 qa.py validate --stage 7 --data image-approval.json
python3 qa.py validate --stage 8 --data generated-images.json --assets-root /path/to/output-images
```

Use `--output report.json` to save the report and `--require-final` in strict automation. The latter intentionally exits with a nonzero code while independent/native confirmations are unavailable.

**Key behavior**: fail closed, never silently pass, isolate repairs to reported paths and rerun affected checks. Automatic retries, agent reassignment and crash recovery belong to the external orchestrator (not ChatGPT or this library); no infinite loop is promised.

## Public release safety

Only the reviewed criteria snapshot, generic validators, synthetic tests and docs are committed. The original project remains private. No generated film data, `.env`, accounts, model access keys, asset images, exported ZIPs or native HT-Group code is included.

MIT license applies to the code in this repository only; it does not change the license or confidentiality of the original HT-Group project.

## Local private portable ZIP export

`tools/bundle_private_skills.py` can copy designated private skill folders together with this public QA library **into a local ZIP only**, and `--verify` checks all SHA-256 checksums. It never uploads that ZIP. Example commands are in `docs/MOVE_TO_NEW_MACHINE.md`. It excludes typical credential/config files, caches, film data and media, but you must inspect any archive before distributing it.
