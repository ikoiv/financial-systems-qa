"""A small SQLite ledger to practice with. Amounts are in cents."""
import sqlite3
from pathlib import Path

class Ledger:
    def __init__(self, path=':memory:'):
        self.db = sqlite3.connect(path)
        self.db.execute('PRAGMA foreign_keys = ON')
        self.db.executescript(Path(__file__).with_name('sql').joinpath('schema.sql').read_text())

    def account(self, account_id, opening_cents):
        if type(opening_cents) is not int or opening_cents < 0:
            raise ValueError('Opening balance must be nonnegative integer cents')
        with self.db:
            self.db.execute('INSERT INTO accounts VALUES (?, ?, ?)', (account_id, opening_cents, opening_cents))

    def balance(self, account_id):
        row = self.db.execute('SELECT balance_cents FROM accounts WHERE id=?', (account_id,)).fetchone()
        if row is None:
            raise ValueError('Unknown account')
        return row[0]

    def transfer(self, source, destination, amount_cents, key, *, fail_after_debit=False):
        # Reject booleans too: Python treats True as an integer.
        if type(amount_cents) is not int or amount_cents <= 0:
            raise ValueError('Amount must be positive integer cents')
        if not isinstance(key, str) or not key.strip():
            raise ValueError('An idempotency key is required')
        if source == destination:
            raise ValueError('Source and destination must differ')
        # Both balances and the postings need to save together.
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            prior = self.db.execute('SELECT id, source_id, destination_id, amount_cents FROM transfers WHERE request_key=?', (key,)).fetchone()
            if prior:
                if prior[1:] != (source, destination, amount_cents):
                    raise ValueError('Idempotency key was used for a different request')
                return prior[0]
            self.balance(source)
            self.balance(destination)
            debit = self.db.execute('UPDATE accounts SET balance_cents=balance_cents-? WHERE id=? AND balance_cents>=?', (amount_cents, source, amount_cents))
            if debit.rowcount != 1:
                raise ValueError('Insufficient funds')
            # Leave this switch for trying a failure halfway through a transfer.
            if fail_after_debit:
                raise RuntimeError('Injected failure after debit')
            self.db.execute('UPDATE accounts SET balance_cents=balance_cents+? WHERE id=?', (amount_cents, destination))
            cursor = self.db.execute('INSERT INTO transfers(request_key,source_id,destination_id,amount_cents) VALUES (?,?,?,?)', (key,source,destination,amount_cents))
            transfer_id = cursor.lastrowid
            self.db.executemany('INSERT INTO postings(transfer_id,account_id,delta_cents) VALUES (?,?,?)', [(transfer_id,source,-amount_cents),(transfer_id,destination,amount_cents)])
            return transfer_id

    def close(self):
        self.db.close()
