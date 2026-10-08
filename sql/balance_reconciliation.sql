-- Each persisted balance must equal opening balance plus its signed postings.
SELECT a.id, a.balance_cents,
       a.opening_cents + COALESCE(SUM(p.delta_cents), 0) AS expected_cents
FROM accounts a
-- LEFT JOIN keeps untouched accounts in scope; COALESCE treats no postings as zero.
LEFT JOIN postings p ON p.account_id = a.id
GROUP BY a.id, a.balance_cents, a.opening_cents
-- Return only mismatches: each output row is an exception needing investigation.
HAVING a.balance_cents <> a.opening_cents + COALESCE(SUM(p.delta_cents), 0);
