-- Every transfer must have exactly one matching debit and one matching credit.
-- A balanced total alone can hide postings to the wrong accounts.
SELECT t.id
FROM transfers t
LEFT JOIN postings p ON p.transfer_id = t.id
GROUP BY t.id, t.source_id, t.destination_id, t.amount_cents
HAVING COUNT(p.id) <> 2
   OR COALESCE(SUM(p.delta_cents), 0) <> 0
   OR SUM(CASE WHEN p.account_id = t.source_id AND p.delta_cents = -t.amount_cents THEN 1 ELSE 0 END) <> 1
   OR SUM(CASE WHEN p.account_id = t.destination_id AND p.delta_cents = t.amount_cents THEN 1 ELSE 0 END) <> 1;
