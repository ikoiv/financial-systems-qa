import random
import sqlite3
import tempfile
import unittest
from pathlib import Path
from ledger import Ledger

class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.ledger = Ledger()
        self.addCleanup(self.ledger.close)
        self.ledger.account('checking', 10000)
        self.ledger.account('savings', 5000)

    def snapshot(self):
        return {table: self.ledger.db.execute('SELECT * FROM '+table+' ORDER BY id').fetchall()
                for table in ['accounts','transfers','postings']}

    def assert_clean(self):
        self.assertEqual(self.ledger.check('balance_reconciliation'), [])
        self.assertEqual(self.ledger.check('transfer_reconciliation'), [])
        self.assertEqual(self.ledger.db.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_transfer_conserves_money_and_posts_both_sides(self):
        transfer = self.ledger.transfer('checking','savings',1250,'move-1')
        self.assertEqual(self.ledger.balance('checking'),8750)
        self.assertEqual(self.ledger.balance('savings'),6250)
        self.assertEqual(self.ledger.db.execute('SELECT account_id,delta_cents FROM postings WHERE transfer_id=? ORDER BY delta_cents',(transfer,)).fetchall(), [('checking',-1250),('savings',1250)])
        self.assert_clean()

    def test_one_cent_and_exact_balance_boundaries(self):
        self.ledger.transfer('checking','savings',1,'cent')
        self.ledger.transfer('checking','savings',9999,'all')
        self.assertEqual(self.ledger.balance('checking'),0)
        self.assertEqual(self.ledger.balance('savings'),15000)
        self.assert_clean()

    def test_insufficient_funds_does_not_change_any_table(self):
        before=self.snapshot()
        with self.assertRaisesRegex(ValueError,'Insufficient'):
            self.ledger.transfer('checking','savings',10001,'too-much')
        self.assertEqual(self.snapshot(),before)

    def test_injected_failure_rolls_back_and_retry_succeeds(self):
        before=self.snapshot()
        with self.assertRaises(RuntimeError):
            self.ledger.transfer('checking','savings',500,'retry',fail_after_debit=True)
        self.assertEqual(self.snapshot(),before)
        self.ledger.transfer('checking','savings',500,'retry')
        self.assertEqual(self.ledger.balance('checking'),9500)
        self.assert_clean()

    def test_repeated_request_returns_same_id_without_duplicate_effect(self):
        first=self.ledger.transfer('checking','savings',500,'same')
        before=self.snapshot()
        self.assertEqual(self.ledger.transfer('checking','savings',500,'same'),first)
        self.assertEqual(self.snapshot(),before)

    def test_key_reuse_with_different_payload_is_rejected(self):
        self.ledger.transfer('checking','savings',500,'same')
        before=self.snapshot()
        with self.assertRaisesRegex(ValueError,'different request'):
            self.ledger.transfer('checking','savings',600,'same')
        self.assertEqual(self.snapshot(),before)

    def test_reject_invalid_amounts(self):
        before=self.snapshot()
        for amount in [0,-1,0.01,True,'100',None]:
            with self.subTest(amount=amount),self.assertRaises(ValueError):
                self.ledger.transfer('checking','savings',amount,'bad')
            self.assertEqual(self.snapshot(),before)

    def test_unknown_accounts_do_not_change_state(self):
        before=self.snapshot()
        for source,destination in [('missing','savings'),('checking','missing')]:
            with self.subTest(source=source,destination=destination),self.assertRaises(ValueError):
                self.ledger.transfer(source,destination,100,'bad')
            self.assertEqual(self.snapshot(),before)

    def test_same_account_and_blank_keys_are_rejected(self):
        before=self.snapshot()
        with self.assertRaises(ValueError):
            self.ledger.transfer('checking','checking',100,'self')
        for key in ['', ' ', None]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                self.ledger.transfer('checking','savings',100,key)
        self.assertEqual(self.snapshot(),before)

    def test_reconciliation_detects_corrupted_balance(self):
        self.ledger.db.execute("UPDATE accounts SET balance_cents=9999 WHERE id='checking'")
        self.assertEqual(self.ledger.check('balance_reconciliation'), [('checking',9999,10000)])

    def test_reconciliation_detects_missing_posting(self):
        transfer=self.ledger.transfer('checking','savings',100,'missing-post')
        self.ledger.db.execute('DELETE FROM postings WHERE transfer_id=? AND delta_cents>0',(transfer,))
        self.assertEqual(self.ledger.check('transfer_reconciliation'), [(transfer,)])
        self.assertTrue(self.ledger.check('balance_reconciliation'))

    def test_reconciliation_detects_wrong_account_even_if_total_is_zero(self):
        transfer=self.ledger.transfer('checking','savings',100,'wrong-account')
        self.ledger.db.execute("UPDATE postings SET account_id='checking' WHERE transfer_id=? AND delta_cents>0",(transfer,))
        self.assertEqual(self.ledger.db.execute('SELECT SUM(delta_cents) FROM postings').fetchone()[0],0)
        self.assertEqual(self.ledger.check('transfer_reconciliation'), [(transfer,)])

    def test_deterministic_random_sequence_preserves_invariants(self):
        rng=random.Random(2026)
        for i in range(200):
            source,destination=rng.choice([('checking','savings'),('savings','checking')])
            available=self.ledger.balance(source)
            if not available: continue
            self.ledger.transfer(source,destination,rng.randint(1,available),f'random-{i}')
            self.assertEqual(self.ledger.balance('checking')+self.ledger.balance('savings'),15000)
            self.assert_clean()

    def test_persistence_and_idempotency_survive_reopen(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'lab.db'
            first=Ledger(path)
            first.account('a',1000);first.account('b',0)
            transfer=first.transfer('a','b',100,'persist')
            first.close()
            second=Ledger(path)
            try:
                self.assertEqual(second.balance('a'),900)
                self.assertEqual(second.transfer('a','b',100,'persist'),transfer)
                self.assertEqual(second.balance('b'),100)
            finally: second.close()

    def test_database_rejects_negative_balance(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.ledger.db.execute("UPDATE accounts SET balance_cents=-1 WHERE id='checking'")
        self.ledger.db.rollback()
        self.assertEqual(self.ledger.balance('checking'),10000)

if __name__ == '__main__': unittest.main()
