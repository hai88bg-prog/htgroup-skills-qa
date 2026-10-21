import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import bundle_private_skills as b

class BundleTest(unittest.TestCase):
    def test_private_skill_export_and_verify(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); skill=p/'stage3'; skill.mkdir()
            (skill/'SKILL.md').write_text('Synthetic skill')
            (skill/'scripts').mkdir()
            (skill/'scripts'/'test.py').write_text('print(42)')
            (skill/'.env').write_text('sensitive, excluded')
            out=p/'private.zip'
            count, result=b.build([skill],out)
            self.assertEqual(count,b.verify(out))
            self.assertEqual(result,out.resolve())
            with self.assertRaises(ValueError): b.build([skill],out)
    def test_reject_secret(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); skill=p/'stage3'; skill.mkdir()
            (skill/'SKILL.md').write_text('ghp_'+'X'*24)
            with self.assertRaises(ValueError): b.build([skill],p/'private.zip')
if __name__=='__main__':unittest.main()
