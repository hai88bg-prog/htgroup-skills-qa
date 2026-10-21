# Normalized QA envelopes (initial public integration contract)

This standalone tool expects generic metadata; **these are not HT-Group native schemas**. Implement and test adapters privately for real files. Never pass film text to GitHub Actions.

Stage 3: `{ "clips": [{ "clip_id": "C001", "start_s":0, "end_s":15, "script":"...", "event_ids":["E1"], "start_state":{}, "end_state":{}, "transition_in":"start", "handoff_out":{"mode":"continuous"} }] }`. A continuous handoff to the next clip requires matching state and its `transition_in`.

Stage 4: `{ "clips":[{"clip_id":"C001","shots":[{"start_s":0,"end_s":3.75,"image_prompt":"...","source_refs":{"action":["E1"],"sound":["E1"],"image_prompt":["E1"],"purpose":["E1"]}}, ...]}] }`. Exactly four contiguous shot windows, relative to each clip's 0..15 seconds. Shots 2–4 additionally require `{ "edit": {"type":"hard_cut", "motivation":"action", "reason":"..."} }`.

Stage 5: `{ "nodes":[{"id":"stage3"},{"id":"stage4"}], "edges":[{"source":"stage3","target":"stage4"}] }`.

Stage 6: `{ "checks": {"script_verified": true, "shotlist_verified": true}, "read_only": true, "images_generated": false }`. The booleans are just metadata and do not prove checks actually happened.

Stage 7: `{ "plan": {"clip_ids":["C001"]}, "approval": {"approved": true, "approved_by":"operator", "approved_at":"2026-10-22T12:00:00+07:00", "plan_sha256":"<SHA256 canonical sorted compact JSON of plan>"} }`. Identity of approver is not authenticated.

Stage 8: `{ "expected_images":1, "artifacts":[{"path":"C001_1.png", "sha256":"<file sha256>", "clip_id":"C001", "shot":1}] }`. For full page production, compare `expected_images` to planned count; this initial validator does not enforce a global 4-shots-per-clip image count or inspect image contents.
