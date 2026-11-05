import unittest,json
from pathlib import Path
from validator import load_accounts,validate,normalize
from analyze_inputs import scan
ROOT=Path(__file__).resolve().parents[1]
class CompanyDataTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  accounts,duplicates=load_accounts(ROOT/'data/chart_of_accounts.csv')
  cls.results={r['entry_id']:r for r in validate(normalize(json.loads((ROOT/'data/manual_adjustments.json').read_text())),accounts,duplicates)}
  cls.diag=scan(ROOT/'data')
 def test_counts(self):self.assertEqual({s:sum(r['status']==s for r in self.results.values()) for s in ['ACCEPTED','REVIEW','REJECTED']},{'ACCEPTED':7,'REVIEW':1,'REJECTED':2})
 def test_unbalanced(self):self.assertEqual(self.results['JE-002']['difference'],'3500.0')
 def test_unknown_account(self):self.assertIn('UNKNOWN_ACCOUNT:1:6315',self.results['JE-005']['issues'])
 def test_intercompany(self):self.assertEqual(self.results['JE-008']['status'],'REVIEW')
 def test_fx_and_orphan(self):
  codes={x['code'] for x in self.diag['issues']};self.assertIn('FX_MISSING_END_RATE',codes);self.assertIn('TB_ORPHAN',codes)
 def test_raw_inputs_untouched(self):self.assertEqual(len(self.diag['source_file_sha256']),5)
if __name__=='__main__':unittest.main()
