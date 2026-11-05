# ERP Finance — Manual Adjustment Validation Prototype

**Actual company-supplied mock inputs, unmodified.** Python standard library only; Python 3.10+ recommended. No API keys or paid services.

## Run
```bash
python validator.py --coa data/chart_of_accounts.csv --adjustments data/manual_adjustments.json --out outputs/validation_report.json
python analyze_inputs.py --data data --out outputs/input_diagnostics.json
python -m unittest discover -s tests -v
```
Run from the repository root. `validator.py` handles all ten supplied journal entries; `analyze_inputs.py` scans the five supplied files without changing them. Results are deterministic JSON.

## Results
`JE-001`, `003`, `004`, `006`, `007`, `009`, `010`: `ACCEPTED` (passed implemented journal-level rules only).
`JE-002`: `REJECTED` (debits $28,500 vs credits $25,000).
`JE-005`: `REJECTED` (account `6315` absent from approved COA).
`JE-008`: `REVIEW` (same-account offset, intercompany details unavailable).

Input scan also identifies orphan `9999`, repeated TB codes, missing GBP closing FX, prior account `6905`, `TBD` CF categories and COA hierarchy defects. Raw TB totals mix currencies and **must not** be treated as USD balances.

## File map
- `validator.py`: deterministic adjustment validation, entry-level explanations and hashes.
- `analyze_inputs.py`: read-only cross-file diagnostics and source-file hashes.
- `data/`: the five original files supplied by the company.
- `outputs/`: generated JSON evidence.
- `tests/`: unit tests, including actual company data.
- `ARCHITECTURE.md`: proposed production system and audit model.
- `REFLECTION.md`: scope, scale limitations, AI use and key insight.
- `PRE_START_QUESTIONS.md`: three clarification questions to email.

## Semantics and limitations
The validator does not post journals, calculate FX valuations, build financial statements, or verify source substantiation. `ACCEPTED` means *no implemented journal-level rule failed*, not approved for posting. Intercompany graph cycles cannot be established without legal-entity/counterparty metadata. Trace hashes are integrity aids, not complete audit lineage. See architecture for required release gates.

## GitHub publication
Create a new repository, copy this folder, then run `git init`, `git add .`, `git commit -m "Prototype: deterministic journal validation"`, add your remote and push. Avoid claiming the three clarifying questions were emailed until you actually send them.
