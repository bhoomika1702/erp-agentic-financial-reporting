"""Read-only diagnostic scan of original company data. Never modifies inputs."""
import csv,json,argparse,collections,hashlib
from decimal import Decimal
from pathlib import Path

def read_csv(path):
 with open(path,newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def money(x):return Decimal(str(x or '0'))
def scan(folder):
 folder=Path(folder); coa=read_csv(folder/'chart_of_accounts.csv');tb=read_csv(folder/'trial_balance.csv');prior=read_csv(folder/'prior_period_tb.csv');fx=read_csv(folder/'fx_rates.csv');journal=json.loads((folder/'manual_adjustments.json').read_text());entries=journal['entries']
 codes={r['account_code'] for r in coa}; lookup={r['account_code']:r for r in coa}; freq=collections.Counter(r['account_code'] for r in tb)
 def totals(rows):
  d=sum((money(r['debit']) for r in rows),Decimal(0));c=sum((money(r['credit']) for r in rows),Decimal(0));return {'debit':str(d),'credit':str(c),'debit_minus_credit':str(d-c)}
 missing_fx=sorted({r['currency'] for r in tb if r['currency']!='USD' and not any(f['currency']==r['currency'] and f['rate_type']=='period_end' and f['period']==journal['period'] for f in fx)})
 issues=[]
 def issue(code,severity,detail,refs):issues.append({'code':code,'severity':severity,'detail':detail,'source_rows':refs})
 for i,r in enumerate(tb,2):
  if r['account_code'] not in codes:issue('TB_ORPHAN','BLOCK',f"Account {r['account_code']} ({r['account_name']}) absent from COA",[f'trial_balance.csv:{i}'])
 for code,n in freq.items():
  if n>1:issue('TB_REPEATED_CODE','INFO',f'{code} appears {n} times; distinguish multi-currency from repeated same-currency rows',[f'trial_balance.csv:{i}' for i,r in enumerate(tb,2) if r['account_code']==code])
 for code in sorted({r['account_code'] for r in prior}-codes):issue('PRIOR_UNMAPPED','BLOCK',f'Prior-period account {code} missing in current COA',[f'prior_period_tb.csv:{i}' for i,r in enumerate(prior,2) if r['account_code']==code])
 for r in coa:
  if r['cf_category']=='TBD':issue('AMBIGUOUS_CF','REVIEW',f"Account {r['account_code']} needs cash-flow classification",[f'chart_of_accounts.csv:{coa.index(r)+2}'])
  if r['account_type']=='Header' and not any(x['parent_code']==r['account_code'] for x in coa):issue('EMPTY_COA_HEADER','REVIEW',f"Header {r['account_code']} has no children",[f'chart_of_accounts.csv:{coa.index(r)+2}'])
  if r['account_code']=='8000' and r['account_type']!='Header' and any(x['parent_code']=='8000' for x in coa):issue('COA_PARENT_TYPE','REVIEW','Account 8000 is a parent but typed Expense rather than Header',['chart_of_accounts.csv'])
 for currency in missing_fx:issue('FX_MISSING_END_RATE','BLOCK',f'No 2024-Q4 period_end rate for {currency}',['fx_rates.csv'])
 return {'period':journal['period'],'functional_currency':journal['functional_currency'],'source_file_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(folder.iterdir()) if f.is_file()},'counts':{'coa':len(coa),'tb':len(tb),'prior_tb':len(prior),'fx_rates':len(fx),'journal_entries':len(entries)},'raw_tb_totals_untranslated':totals(tb),'raw_prior_tb_totals_untranslated':totals(prior),'warning':'Raw TB totals mix USD/EUR/GBP and are diagnostic only, not functional-currency reconciliation. Prior TB may have different scope (balance sheet only).','issues':issues}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data',default='data');p.add_argument('--out',default='outputs/input_diagnostics.json');a=p.parse_args();r=scan(a.data);dest=Path(a.out);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(r,indent=2));print(f"{len(r['issues'])} input findings -> {dest}")
