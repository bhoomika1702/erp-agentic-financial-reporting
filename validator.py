"""Deterministic journal validation. No AI can override a hard failure."""
import csv, json, hashlib, argparse
from decimal import Decimal, InvalidOperation
from pathlib import Path

def load_accounts(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        rows=list(csv.DictReader(f))
    accounts={}; duplicates=[]
    for row in rows:
        code=str(row.get('account_code','')).strip()
        if not code: continue
        if code in accounts: duplicates.append(code)
        accounts[code]=row
    return accounts, sorted(set(duplicates))

def amount(v):
    try:
        x=Decimal(str(v))
        if not x.is_finite(): raise ValueError('non-finite amount')
        return x
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f'invalid amount: {v!r}')

def normalize(payload):
    if isinstance(payload,dict):
        for key in ('adjustments','journal_entries','entries'):
            if isinstance(payload.get(key),list): return payload[key]
        raise ValueError('JSON object must contain adjustments, journal_entries, or entries list')
    if isinstance(payload,list): return payload
    raise ValueError('Expected JSON array or object containing entries')

def validate(entries, accounts, duplicate_coa=None):
    duplicate_coa=duplicate_coa or []
    seen_ids=set(); results=[]
    for idx, entry in enumerate(entries):
        issues=[]; warnings=[]
        entry_id=str(entry.get('id',entry.get('entry_id',f'row-{idx+1}')))
        if entry_id in seen_ids: issues.append('DUPLICATE_ENTRY_ID')
        seen_ids.add(entry_id)
        lines=entry.get('lines',[])
        if not isinstance(lines,list) or len(lines)<2:
            issues.append('INSUFFICIENT_LINES'); lines=[]
        debits=Decimal('0'); credits=Decimal('0'); parsed=[]
        for n,line in enumerate(lines,1):
            code=str(line.get('account_code',line.get('account',''))).strip()
            if code not in accounts: issues.append(f'UNKNOWN_ACCOUNT:{n}:{code}')
            elif accounts[code].get('account_type')=='Header': issues.append(f'NON_POSTABLE_HEADER:{n}:{code}')
            if code in duplicate_coa: issues.append(f'AMBIGUOUS_COA_DUPLICATE:{n}:{code}')
            try:
                debit=amount(line.get('debit',0)); credit=amount(line.get('credit',0))
                if debit<0 or credit<0: issues.append(f'NEGATIVE_AMOUNT:{n}')
                if (debit>0 and credit>0) or (debit==0 and credit==0): issues.append(f'INVALID_LINE_SIDES:{n}')
                debits+=debit; credits+=credit
            except ValueError:
                issues.append(f'INVALID_AMOUNT:{n}'); debit=credit=Decimal('0')
            parsed.append((code,str(debit),str(credit)))
        if debits!=credits: issues.append('UNBALANCED_ENTRY')
        if debits==0 and credits==0: issues.append('ZERO_VALUE_ENTRY')
        # An intercompany flag triggers review, not automatic graph-cycle assertions.
        if entry.get('intercompany') or 'intercompany' in (str(entry.get('type',''))+' '+str(entry.get('description',''))).lower() or any(str(line.get('account',''))=='2170' for line in lines):
            warnings.append('INTERCOMPANY_REVIEW_REQUIRED: verify entity/counterparty and elimination graph')
            if len(set(code for code,_,_ in parsed))==1 and debits==credits and debits>0:
                warnings.append('SAME_ACCOUNT_OFFSET: debit and credit cancel on the same account; verify intent')
        if not entry.get('date'): warnings.append('MISSING_DATE')
        elif not str(entry['date']).startswith('2024-'): warnings.append('PERIOD_DATE_REVIEW')
        if not entry.get('description'): warnings.append('MISSING_DESCRIPTION')
        issues=list(dict.fromkeys(issues))
        result={'entry_id':entry_id,'status':'REJECTED' if issues else ('REVIEW' if warnings else 'ACCEPTED'),
                'debits':str(debits),'credits':str(credits),'difference':str(debits-credits),
                'issues':issues,'warnings':warnings,
                'explanation':explain(issues,warnings)}
        result['trace_hash']=hashlib.sha256(json.dumps({'entry':entry,'result':{k:v for k,v in result.items() if k!='trace_hash'}},sort_keys=True,default=str).encode()).hexdigest()
        results.append(result)
    return results

def explain(issues,warnings):
    notes=[]
    for issue in issues:
        if issue=='UNBALANCED_ENTRY': notes.append('Total debits do not equal total credits; correct the source journal before posting.')
        elif issue.startswith('UNKNOWN_ACCOUNT'): notes.append(f'Account on line {issue.split(":")[1]} is absent from the COA; request an approved mapping.')
        elif issue.startswith('AMBIGUOUS_COA_DUPLICATE'): notes.append('Account code occurs more than once in the COA; a finance owner must resolve it.')
        elif issue=='DUPLICATE_ENTRY_ID': notes.append('Entry ID was already used in this batch; check for duplicate submission.')
        else: notes.append(issue.replace('_',' ').capitalize()+'.')
    if warnings: notes.append('Manual review needed: '+ '; '.join(warnings))
    return ' '.join(notes) if notes else 'All implemented journal-level checks passed; this is not approval to post.'

def main():
    p=argparse.ArgumentParser(); p.add_argument('--coa',required=True); p.add_argument('--adjustments',required=True); p.add_argument('--out',default='outputs/validation_report.json'); args=p.parse_args()
    accounts,duplicates=load_accounts(args.coa)
    with open(args.adjustments,encoding='utf-8-sig') as f: entries=normalize(json.load(f))
    report={'schema_version':'1.0','coa_duplicate_codes':duplicates,'results':validate(entries,accounts,duplicates)}
    target=Path(args.out); target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(f'Wrote {target} | '+', '.join(f'{s}={sum(r["status"]==s for r in report["results"])}' for s in ('ACCEPTED','REVIEW','REJECTED')))
if __name__=='__main__': main()
