import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import qa


class QATest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.inputs = self.root/'inputs'
        self.inputs.mkdir()
        for name in ('README.md', 'concept_bible.md', 'reference_manifest.json'):
            (self.inputs/name).write_text('fixture data\n')
        self.pre3 = self.root/'stage3_lock.json'
        self.pre3.write_text(json.dumps(qa.lock_data(3, self.inputs)))
        self.zfile = self.root/'stage3.zip'
        with zipfile.ZipFile(self.zfile, 'w') as z:
            z.writestr('manifest.json', '{}')
        self.pre4 = self.root/'stage4_lock.json'
        self.pre4.write_text(json.dumps(qa.lock_data(4, self.zfile)))

    def clip3(self, clip_id='C001', start=0, end=15, state=None):
        state = {'position': 'A1'} if state is None else state
        return {'clip_id': clip_id, 'start_s': start, 'end_s': end,
                'script': 'Actor opens a gate', 'event_ids': [clip_id+'_EV'],
                'start_state': state, 'end_state': state,
                'transition_in': 'start' if start == 0 else 'continuous',
                'handoff_out': {'mode': 'continuous'}}

    def shot4(self, a, b, index):
        out = {'start_s': a, 'end_s': b,
               'image_prompt': 'An empty wooden gate',
               'source_refs': {'action': ['E1'], 'sound': ['E1'],
                               'image_prompt': ['E1'], 'purpose': ['E1']}}
        if index:
            out['edit'] = {'type': 'hard_cut', 'motivation': 'action', 'reason': 'change focus'}
        return out

    def validate3(self, data):
        return qa.validate(3, data, lock=str(self.pre3), source=str(self.inputs))

    def validate4(self, data):
        return qa.validate(4, data, lock=str(self.pre4), source=str(self.zfile))

    def test_31_exact_codes(self):
        self.assertEqual(len(qa.all_codes()), 31)
        self.assertEqual(qa.all_codes()[0], 'DR01')
        self.assertEqual(qa.all_codes()[-1], 'B10')

    def test_stage3_offline_only(self):
        result = self.validate3({'clips': [self.clip3()]})
        self.assertEqual(result['offline_status'], 'PASS_OFFLINE_STRUCTURE')
        self.assertEqual(result['final_status'], 'NOT_VERIFIED')
        self.assertEqual(result['native_status'], 'NOT_RUN')
        self.assertEqual(result['independent_reviewer_status'], 'NOT_RUN')
        self.assertIn('NOT_RUN', result['criteria'].values())

    def test_stage3_lock_required(self):
        self.assertEqual(qa.validate(3, {'clips':[self.clip3()]})['offline_status'], 'FAIL')

    def test_stage3_continuity_bad(self):
        clips = [self.clip3(), self.clip3('C002', 15, 30, {'position': 'far-away'})]
        result = self.validate3({'clips': clips})
        self.assertIn('A07', [x['code'] for x in result['issues']])

    def test_stage3_cannot_retroactively_fake_different_source(self):
        (self.inputs/'README.md').write_text('changed')
        self.assertEqual(self.validate3({'clips': [self.clip3()]})['offline_status'], 'FAIL')

    def test_stage4_four_shots(self):
        shots = [self.shot4(i*3.75, (i+1)*3.75, i) for i in range(4)]
        good = self.validate4({'clips': [{'clip_id': 'C001', 'shots': shots}]})
        self.assertEqual(good['offline_status'], 'PASS_OFFLINE_STRUCTURE')
        self.assertEqual(good['final_status'], 'NOT_VERIFIED')
        bad = self.validate4({'clips': [{'clip_id': 'C001', 'shots': shots[:-1]}]})
        self.assertEqual(bad['offline_status'], 'FAIL')
        self.assertIn('B01', [x['code'] for x in bad['issues']])

    def test_stage5_graph(self):
        good = {'nodes': [{'id': 'a'}, {'id': 'b'}], 'edges': [{'source': 'a', 'target': 'b'}]}
        self.assertEqual(qa.validate(5, good)['offline_status'], 'PASS_OFFLINE_STRUCTURE')
        good['edges'].append({'source': 'c', 'target': 'a'})
        self.assertEqual(qa.validate(5, good)['offline_status'], 'FAIL')

    def test_stage6_read_only(self):
        checks = {'checks': {'script': True, 'storyboard': True},
                  'read_only': True, 'images_generated': False}
        self.assertEqual(qa.validate(6, checks)['offline_status'], 'PASS_OFFLINE_STRUCTURE')
        checks['images_generated'] = True
        self.assertEqual(qa.validate(6, checks)['offline_status'], 'FAIL')

    def test_stage7_plan_hash(self):
        plan = {'clips': ['C001'], 'image_model': 'testing-only'}
        approval = {'approved': True, 'approved_at': '2026-10-22',
                    'approved_by': 'fixture-operator', 'plan_sha256': qa.sha256(qa.stable_bytes(plan))}
        self.assertEqual(qa.validate(7, {'plan': plan, 'approval': approval})['offline_status'], 'PASS_OFFLINE_STRUCTURE')
        plan['clips'].append('C002')
        self.assertEqual(qa.validate(7, {'plan': plan, 'approval': approval})['offline_status'], 'FAIL')

    def test_stage8_hash_and_path_escape(self):
        (self.root/'C001_1.png').write_bytes(b'fake-image-bytes')
        entry = {'path': 'C001_1.png', 'clip_id': 'C001', 'shot': 1,
                 'sha256': hashlib.sha256(b'fake-image-bytes').hexdigest()}
        ok = qa.validate(8, {'artifacts': [entry], 'expected_images': 1}, assets_root=str(self.root))
        self.assertEqual(ok['offline_status'], 'PASS_OFFLINE_STRUCTURE')
        entry['path'] = '../different.png'
        fail = qa.validate(8, {'artifacts': [entry], 'expected_images': 1}, assets_root=str(self.root))
        self.assertEqual(fail['offline_status'], 'FAIL')

    def test_require_final_does_not_pass(self):
        data = self.root/'graph.json'
        data.write_text(json.dumps({'nodes':[{'id':'a'}], 'edges':[]}))
        self.assertEqual(qa.cli(['validate', '--stage', '5', '--data', str(data), '--require-final']), 2)


if __name__ == '__main__':
    unittest.main()
