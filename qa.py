#!/usr/bin/env python3
"""Independent, portable STAGING QA for HT-Group stages 3..8.

This tool DOES NOT claim Native PASS or reviewer PASS. Input envelopes are
normalized metadata; original project adapters must be validated separately.
No network, API keys, image generation, or writes to a film project.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CRITERIA = ROOT / 'contracts' / 'review-31.json'
STAGES = (3, 4, 5, 6, 7, 8)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def stable_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def file_hash(path):
    return sha256(Path(path).read_bytes())


def all_codes():
    rules = read_json(CRITERIA)
    expected = ([f'DR{i:02d}' for i in range(1, 8)]
                + [f'A{i:02d}' for i in range(1, 15)]
                + [f'B{i:02d}' for i in range(1, 11)])
    actual = [code for group in ('DR', 'A', 'B') for code in rules[group]]
    if actual != expected or len(set(actual)) != 31:
        raise ValueError('INVALID_CONTRACT: criteria must be DR01-07, A01-14, B01-10')
    return expected


def valid_text(v):
    return isinstance(v, str) and bool(v.strip())


def numeric(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def near(a, b):
    return numeric(a) and numeric(b) and abs(a - b) < 1e-6


class Report:
    def __init__(self, stage):
        self.stage = stage
        self.issues = []
        self.machine_checks = []

    def fail(self, code, path, detail):
        self.issues.append({'code': code, 'path': str(path), 'message': detail})

    def checked(self, code):
        if code not in self.machine_checks:
            self.machine_checks.append(code)

    def result(self, data):
        status = 'FAIL' if self.issues else 'PASS_OFFLINE_STRUCTURE'
        machine = sorted(self.machine_checks)
        all31 = all_codes()
        return {
            'schema': 'htqa-offline-report-v1', 'stage': self.stage,
            'input_sha256': sha256(stable_bytes(data)),
            'rubric_sha256': file_hash(CRITERIA),
            'offline_status': status,
            'native_status': 'NOT_RUN',
            'independent_reviewer_status': 'NOT_RUN',
            'final_status': 'BLOCKED' if self.issues else 'NOT_VERIFIED',
            'machine_checks': machine,
            'criteria': {c: 'PARTIAL_MACHINE_CHECK' if c in machine else 'NOT_RUN'
                         for c in all31},
            'issues': self.issues,
            'warning': 'An offline structural check is not a semantic, native, reviewer, image-content, or production PASS.'
        }


def stage3(data, out):
    clips = data.get('clips')
    if not isinstance(clips, list) or not clips:
        out.fail('A02', 'clips', 'A nonempty clips list is required'); return
    seen = set(); prior = None; events = set()
    for i, clip in enumerate(clips):
        p = f'clips[{i}]'
        if not isinstance(clip, dict):
            out.fail('A02', p, 'Clip must be an object'); continue
        cid = clip.get('clip_id')
        if not valid_text(cid) or cid in seen:
            out.fail('A02', p+'.clip_id', 'Missing or repeated clip_id')
        seen.add(cid)
        start, end = clip.get('start_s'), clip.get('end_s')
        if not numeric(start) or not near(end, start + 15):
            out.fail('A08', p, 'Absolute clip duration must be exactly 15 seconds')
        if not valid_text(clip.get('script')):
            out.fail('A02', p+'.script', 'Script must be present')
        for field in ('start_state', 'end_state'):
            if not isinstance(clip.get(field), dict):
                out.fail('A02', p+'.'+field, 'A world-state object is required')
        ids = clip.get('event_ids')
        if not isinstance(ids, list) or not ids or any(not valid_text(x) for x in ids):
            out.fail('A08', p+'.event_ids', 'Expected nonempty event IDs')
        else:
            for eid in ids:
                if eid in events:
                    out.fail('DR02', p+'.event_ids', f'Event {eid} reused in multiple clips')
                events.add(eid)
        handoff = clip.get('handoff_out')
        if not isinstance(handoff, dict) or handoff.get('mode') not in ('continuous', 'cut', 'end'):
            out.fail('A12', p+'.handoff_out', 'Missing transition mode')
        if prior and isinstance(prior, dict):
            if not near(start, prior.get('end_s')):
                out.fail('A08', p+'.start_s', 'Timeline gap or overlap')
            mode = (prior.get('handoff_out') or {}).get('mode')
            if mode == 'continuous':
                if clip.get('transition_in') != 'continuous':
                    out.fail('A12', p+'.transition_in', 'Previous continuous handoff must match')
                if prior.get('end_state') != clip.get('start_state'):
                    out.fail('A07', p+'.start_state', 'Continuous world states differ')
            elif mode == 'cut' and clip.get('transition_in') != 'cut':
                out.fail('A12', p+'.transition_in', 'Previous cut must match')
            elif mode == 'end':
                out.fail('A12', p, 'Only film final clip can end')
        prior = clip
    out.checked('A02'); out.checked('A07'); out.checked('A08'); out.checked('A12')
    out.checked('DR02')


def stage4(data, out):
    clips = data.get('clips')
    if not isinstance(clips, list) or not clips:
        out.fail('B01', 'clips', 'A nonempty list of shot clips is required'); return
    seen = set()
    for ci, clip in enumerate(clips):
        p = f'clips[{ci}]'
        if not isinstance(clip, dict):
            out.fail('B01', p, 'Clip must be an object'); continue
        cid = clip.get('clip_id')
        if not valid_text(cid) or cid in seen:
            out.fail('B01', p+'.clip_id', 'Missing or duplicated ID')
        seen.add(cid)
        shots = clip.get('shots')
        if not isinstance(shots, list) or len(shots) != 4:
            out.fail('B01', p+'.shots', 'Exactly four shots are required'); continue
        last_end = 0
        for j, shot in enumerate(shots):
            q = f'{p}.shots[{j}]'
            if not isinstance(shot, dict):
                out.fail('B01', q, 'Shot must be an object'); continue
            a, b = shot.get('start_s'), shot.get('end_s')
            if not near(a, last_end) or not numeric(b) or b <= a:
                out.fail('B01', q, 'Shot windows must be positive and contiguous')
            if numeric(b):
                last_end = b
            if not valid_text(shot.get('image_prompt')):
                out.fail('B02', q+'.image_prompt', 'Prompt is required')
            refs = shot.get('source_refs')
            if not isinstance(refs, dict) or not all(
                isinstance(refs.get(k), list) and refs.get(k) for k in ('action', 'sound', 'image_prompt', 'purpose')):
                out.fail('B03', q+'.source_refs', 'All four source-ref tracks are required')
            if j:
                edit = shot.get('edit')
                if not isinstance(edit, dict) or not all(valid_text(edit.get(k)) for k in ('type', 'motivation', 'reason')):
                    out.fail('B07', q+'.edit', 'Cut type, motivation and reason required')
        if not near(last_end, 15):
            out.fail('B01', p+'.shots', 'The four shot windows must cover 0..15 seconds')
    out.checked('B01'); out.checked('B02'); out.checked('B03'); out.checked('B07')


def stage5(data, out):
    nodes, edges = data.get('nodes'), data.get('edges')
    if not isinstance(nodes, list) or not nodes:
        out.fail('S5_GRAPH', 'nodes', 'Graph nodes required'); return
    if not isinstance(edges, list):
        out.fail('S5_GRAPH', 'edges', 'Graph edges list required'); return
    ids = set()
    for i, n in enumerate(nodes):
        nid = n.get('id') if isinstance(n, dict) else None
        if not valid_text(nid) or nid in ids:
            out.fail('S5_NODE', f'nodes[{i}]', 'Node ID must be unique and nonempty')
        ids.add(nid)
    for i, e in enumerate(edges):
        a = e.get('source') if isinstance(e, dict) else None
        b = e.get('target') if isinstance(e, dict) else None
        if a not in ids or b not in ids or a == b:
            out.fail('S5_EDGE', f'edges[{i}]', 'Dangling or self-connected edge')
    out.checked('S5_NODE'); out.checked('S5_EDGE')


def stage6(data, out):
    checks = data.get('checks')
    if not isinstance(checks, dict) or not checks:
        out.fail('S6_CONDITIONS', 'checks', 'Named prerequisite checks required'); return
    for name, v in checks.items():
        if v is not True:
            out.fail('S6_CONDITIONS', f'checks.{name}', 'Prerequisite not affirmed')
    if data.get('read_only') is not True:
        out.fail('S6_READ_ONLY', 'read_only', 'Inspection must remain read-only')
    if data.get('images_generated') is not False:
        out.fail('S6_NO_EARLY_IMAGES', 'images_generated', 'Step 6 must not generate images')
    out.checked('S6_CONDITIONS')


def stage7(data, out):
    plan = data.get('plan')
    approval = data.get('approval')
    if not isinstance(plan, dict) or not plan:
        out.fail('S7_PLAN', 'plan', 'A nonempty image-production plan required'); return
    expected_hash = sha256(stable_bytes(plan))
    if not isinstance(approval, dict) or approval.get('approved') is not True:
        out.fail('S7_APPROVAL', 'approval', 'Explicit approval required'); return
    if approval.get('plan_sha256') != expected_hash:
        out.fail('S7_PLAN_HASH', 'approval.plan_sha256', 'Approved plan does not match current plan')
    if not valid_text(approval.get('approved_by')) or not valid_text(approval.get('approved_at')):
        out.fail('S7_APPROVAL', 'approval', 'Reviewer identifier and timestamp required')
    out.checked('S7_PLAN_HASH')


def stage8(data, out, assets_root):
    items = data.get('artifacts')
    if not isinstance(items, list) or not items:
        out.fail('S8_ARTIFACTS', 'artifacts', 'Nonempty manifest required'); return
    root = Path(assets_root).resolve() if assets_root else None
    if root is None:
        out.fail('S8_FILES', 'assets_root', 'An explicit --assets-root is required')
        return
    used = set()
    for i, a in enumerate(items):
        p = f'artifacts[{i}]'
        if not isinstance(a, dict) or not valid_text(a.get('path')):
            out.fail('S8_ARTIFACTS', p, 'Relative file path required'); continue
        f = (root / a['path']).resolve()
        if not f.is_relative_to(root):
            out.fail('S8_PATH', p+'.path', 'Path escapes asset root'); continue
        if f in used:
            out.fail('S8_ARTIFACTS', p+'.path', 'Duplicate image'); continue
        used.add(f)
        if not f.is_file():
            out.fail('S8_FILES', p+'.path', 'Image file missing'); continue
        if not valid_text(a.get('sha256')) or a['sha256'].lower() != file_hash(f):
            out.fail('S8_HASH', p+'.sha256', 'Image file checksum mismatch')
        if not valid_text(a.get('clip_id')) or not isinstance(a.get('shot'), int) or a['shot'] not in (1, 2, 3, 4):
            out.fail('S8_METADATA', p, 'clip_id and shot 1..4 required')
    if numeric(data.get('expected_images')) and data['expected_images'] != len(items):
        out.fail('S8_COUNT', 'expected_images', 'Manifest image count mismatch')
    out.checked('S8_HASH'); out.checked('S8_COUNT')


def lock_data(stage, source):
    p = Path(source)
    if stage == 3:
        if not p.is_dir():
            raise ValueError('Stage 3 prewrite source must be a directory')
        names = ('README.md', 'concept_bible.md', 'reference_manifest.json')
        hashes = {n: file_hash(p / n) for n in names}
    else:
        if not p.is_file():
            raise ValueError('Stage 4 prewrite source must be a Stage 3 ZIP')
        hashes = {p.name: file_hash(p)}
    return {'schema': 'htqa-prewrite-v1', 'stage': stage,
            'rubric_sha256': file_hash(CRITERIA), 'required_ids': all_codes(),
            'sources': hashes, 'scope': 'read acknowledgment, not proof of model comprehension'}


def check_lock(stage, source, filename, out):
    try:
        expected = lock_data(stage, source)
        found = read_json(filename)
        if found != expected:
            out.fail('RUBRIC_LOCK', 'prewrite', 'Source/rubric/31-criterion acknowledgment mismatch')
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        out.fail('RUBRIC_LOCK', 'prewrite', 'Invalid prewrite lock: '+str(exc))


def validate(stage, data, assets_root=None, lock=None, source=None):
    out = Report(stage)
    if not isinstance(data, dict):
        out.fail('DATA', 'root', 'Input must be a JSON object'); return out.result({})
    if stage in (3, 4):
        if not lock or not source:
            out.fail('RUBRIC_LOCK', 'prewrite', 'Stage 3/4 requires --prewrite and --source')
        else:
            check_lock(stage, source, lock, out)
    {3: stage3, 4: stage4, 5: stage5, 6: stage6, 7: stage7}.get(stage, lambda d, o: stage8(d, o, assets_root))(data, out)
    return out.result(data)


def cli(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    commands = ap.add_subparsers(dest='action', required=True)
    rubric = commands.add_parser('rubric', help='Print 31 authoritative criteria')
    rubric.add_argument('--stage', type=int, choices=(3, 4), required=True)
    pre = commands.add_parser('prewrite', help='Seal source and all 31 rubric IDs before writing')
    pre.add_argument('--stage', type=int, choices=(3, 4), required=True)
    pre.add_argument('--source', required=True)
    pre.add_argument('--output', required=True)
    val = commands.add_parser('validate', help='Validate normalized local stage metadata')
    val.add_argument('--stage', type=int, choices=STAGES, required=True)
    val.add_argument('--data', required=True)
    val.add_argument('--source')
    val.add_argument('--prewrite')
    val.add_argument('--assets-root')
    val.add_argument('--output')
    val.add_argument('--require-final', action='store_true', help='Fail closed unless independent native/reviewer PASS exists (never produced by offline tool)')
    args = ap.parse_args(argv)
    try:
        if args.action == 'rubric':
            obj = read_json(CRITERIA)
            print('STAGE', args.stage, 'READ ALL 31 BEFORE WRITING')
            for group in ('DR', 'A', 'B'):
                print('\n'+group)
                for k, v in obj[group].items(): print(k, v)
            return 0
        if args.action == 'prewrite':
            payload = lock_data(args.stage, args.source)
            out = Path(args.output)
            if out.exists():
                if read_json(out) != payload:
                    raise ValueError('Existing prewrite lock disagrees; refuse overwrite')
                print('EXISTING_LOCK_VALID', str(out)); return 0
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
            print('PREWRITE_LOCK_CREATED', str(out), 'CRITERIA', len(payload['required_ids']))
            return 0
        data = read_json(args.data)
        result = validate(args.stage, data, args.assets_root, args.prewrite, args.source)
        rendered = json.dumps(result, ensure_ascii=False, indent=2)+'\n'
        if args.output:
            target = Path(args.output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(rendered, encoding='utf-8')
        print(rendered, end='')
        if result['offline_status'] == 'FAIL' or args.require_final:
            return 2
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print('ERROR:', str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(cli())
