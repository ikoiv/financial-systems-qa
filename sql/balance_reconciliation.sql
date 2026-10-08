-- Each persisted balance must equal opening balance plus its signed postings.
SELECT a.id, a.balance_cents,
       a.opening_cents + COALESCE(SUM(p.delta_cents), 0) AS expected_cents
FROM accounts a
LEFT JOIN postings p ON p.account_id = a.id
GROUP BY a.id, a.balance_cents, a.opening_cents
HAVING a.balance_cents <> a.opening_cents + COALESCE(SUM(p.delta_cents), 0);
