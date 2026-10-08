-- Store amounts in cents so rounding is not part of the exercise.
CREATE TABLE IF NOT EXISTS accounts (
  id TEXT PRIMARY KEY,
  opening_cents INTEGER NOT NULL CHECK(typeof(opening_cents) = 'integer' AND opening_cents >= 0),
  balance_cents INTEGER NOT NULL CHECK(typeof(balance_cents) = 'integer' AND balance_cents >= 0)
);
CREATE TABLE IF NOT EXISTS transfers (
  id INTEGER PRIMARY KEY,
  request_key TEXT NOT NULL UNIQUE,
  source_id TEXT NOT NULL REFERENCES accounts(id),
  destination_id TEXT NOT NULL REFERENCES accounts(id),
  amount_cents INTEGER NOT NULL CHECK(typeof(amount_cents) = 'integer' AND amount_cents > 0),
  CHECK(source_id <> destination_id)
);
CREATE TABLE IF NOT EXISTS postings (
  id INTEGER PRIMARY KEY,
  transfer_id INTEGER NOT NULL REFERENCES transfers(id),
  account_id TEXT NOT NULL REFERENCES accounts(id),
  delta_cents INTEGER NOT NULL CHECK(typeof(delta_cents) = 'integer' AND delta_cents <> 0)
);
