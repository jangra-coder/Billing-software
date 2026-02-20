"""Tests for services/number_generator.py."""

import sqlite3
import unittest
from datetime import date
from services.number_generator import generate_document_number, peek_next_number


def _create_test_db() -> sqlite3.Connection:
    """Create an in-memory DB with the invoice_counter table."""
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE invoice_counter (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            doc_type TEXT NOT NULL,
            last_number INTEGER NOT NULL DEFAULT 0,
            UNIQUE(year, doc_type)
        )
    """)
    conn.commit()
    return conn


class TestGenerateDocumentNumber(unittest.TestCase):
    def setUp(self):
        self.conn = _create_test_db()

    def tearDown(self):
        self.conn.close()

    def test_first_number(self):
        num = generate_document_number(
            self.conn, "IN", ref_date=date(2026, 3, 15)
        )
        self.assertEqual(num, "2026IN0001")

    def test_sequential(self):
        d = date(2026, 5, 1)
        n1 = generate_document_number(self.conn, "IN", ref_date=d)
        n2 = generate_document_number(self.conn, "IN", ref_date=d)
        n3 = generate_document_number(self.conn, "IN", ref_date=d)
        self.assertEqual(n1, "2026IN0001")
        self.assertEqual(n2, "2026IN0002")
        self.assertEqual(n3, "2026IN0003")

    def test_different_types_independent(self):
        d = date(2026, 5, 1)
        inv = generate_document_number(self.conn, "IN", ref_date=d)
        qt = generate_document_number(self.conn, "QT", ref_date=d)
        self.assertEqual(inv, "2026IN0001")
        self.assertEqual(qt, "2026QT0001")

    def test_custom_format(self):
        num = generate_document_number(
            self.conn, "IN",
            number_format="{PREFIX}/{YYYY}/{NNNN}",
            prefix="TAX",
            ref_date=date(2026, 3, 15),
        )
        self.assertEqual(num, "TAX/2026/0001")

    def test_custom_padding(self):
        num = generate_document_number(
            self.conn, "IN", padding_digits=6, ref_date=date(2026, 1, 1)
        )
        self.assertEqual(num, "2026IN000001")


class TestPeekNextNumber(unittest.TestCase):
    def setUp(self):
        self.conn = _create_test_db()

    def tearDown(self):
        self.conn.close()

    def test_peek_without_consuming(self):
        p1 = peek_next_number(self.conn, "IN", year=2026)
        p2 = peek_next_number(self.conn, "IN", year=2026)
        self.assertEqual(p1, "2026IN0001")
        self.assertEqual(p2, "2026IN0001")  # unchanged — not consumed

    def test_peek_after_generate(self):
        generate_document_number(self.conn, "IN", ref_date=date(2026, 1, 1))
        p = peek_next_number(self.conn, "IN", year=2026)
        self.assertEqual(p, "2026IN0002")


if __name__ == "__main__":
    unittest.main()
