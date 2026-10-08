# Financial systems QA

[![Ledger and SQL tests](https://github.com/ikoiv/financial-systems-qa/actions/workflows/tests.yml/badge.svg)](https://github.com/ikoiv/financial-systems-qa/actions/workflows/tests.yml)

A personal lab for the part of testing where a small discrepancy matters. I enjoy tracing money movement from a request to its balances and postings, so this experiment uses a tiny SQLite ledger and entirely synthetic accounts.

## Run it

Python 3.12 or newer. Standard library only.

```bash
python -m unittest discover -s tests -v
```

## What I'm checking

| Risk | Evidence |
| --- | --- |
| Lost or created money | Exact balance expectations and conservation through 200 seeded random transfers |
| Partial posting | Failure injected after debit; every table must return to its prior state |
| Duplicate request | Same key returns the prior transfer ID without changing balances or postings |
| Conflicting retry | Same key plus different payload is rejected |
| Incorrect amount | Integer cents only; zero, negative, float, boolean, string, and null rejected |
| Overdraft | Conditional debit and nonnegative balance constraint |
| Data discrepancy | SQL checks against balances and both sides of each transfer |
| Misleading reconciliation | Corruption tests prove checks find a missing credit and a wrong account even when totals balance |
| Restart | Persisted request key and balances checked after reopening the database |

## Explore the code

- `ledger.py`: transaction boundary, validation, idempotency, and transfer posting.
- `sql/schema.sql`: foreign keys, uniqueness, and integer/nonnegative checks.
- `sql/balance_reconciliation.sql`: exceptions where opening balance plus postings differs from the stored balance.
- `sql/transfer_reconciliation.sql`: exceptions for missing, extra, unbalanced, or incorrectly assigned postings.
- `tests/test_ledger.py`: expected outcomes, unchanged-state checks, fault injection, and corruption detection.

Healthy reconciliation returns no rows. Tests deliberately corrupt data to check that “no exceptions” is meaningful rather than a query that always returns nothing. CI executes the tests on Python 3.12 and 3.13.

## Design notes and limits

Money is represented as integer cents to avoid binary floating-point rounding. A database transaction wraps both balance updates and both postings. `BEGIN IMMEDIATE` serializes SQLite writers; this suite does not claim to verify multi-process contention or a production distributed ledger.

This is a single-currency internal-transfer model. It excludes fees, FX, external payment networks, settlement, real customer identity, and regulatory workflows. SQLite makes it easy to run; the SQL is not presented as validated SQL Server code. Fault injection is a lab hook. No real transactions occur.

Next experiments: concurrent clients, reversal workflows, batch reconciliation imports, and SQL Server-specific integration checks.

MIT licensed. All accounts, balances, and scenarios are fictional.
