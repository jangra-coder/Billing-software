"""Tests for services/calculator.py."""

import unittest
from services.calculator import (
    compute_line_item,
    compute_doc_totals,
    format_currency,
    rupees_to_paise,
    paise_to_rupees,
    LineResult,
)


class TestComputeLineItem(unittest.TestCase):
    def test_basic_intra_state(self):
        lr = compute_line_item(
            quantity=10,
            rate_paise=100_00,   # ₹100 per unit
            discount_pct=0.0,
            gst_rate=18.0,
            is_intra_state=True,
        )
        # taxable = 10 × 100 = ₹1000 = 100000 paise
        self.assertEqual(lr.taxable_amount, 100_000)
        self.assertEqual(lr.cgst_rate, 9.0)
        self.assertEqual(lr.cgst_amount, 9_000)   # ₹90
        self.assertEqual(lr.sgst_amount, 9_000)
        self.assertEqual(lr.igst_amount, 0)
        self.assertEqual(lr.line_total, 118_000)   # ₹1180

    def test_with_discount(self):
        lr = compute_line_item(
            quantity=5,
            rate_paise=200_00,   # ₹200
            discount_pct=0.10,   # 10%
            gst_rate=18.0,
            is_intra_state=True,
        )
        # taxable = 5 × 200 × 0.90 = ₹900 = 90000 paise
        self.assertEqual(lr.taxable_amount, 90_000)
        self.assertEqual(lr.cgst_amount, 8_100)    # ₹81
        self.assertEqual(lr.sgst_amount, 8_100)

    def test_inter_state(self):
        lr = compute_line_item(
            quantity=1,
            rate_paise=500_00,
            discount_pct=0.0,
            gst_rate=18.0,
            is_intra_state=False,
        )
        self.assertEqual(lr.taxable_amount, 50_000)
        self.assertEqual(lr.cgst_amount, 0)
        self.assertEqual(lr.sgst_amount, 0)
        self.assertEqual(lr.igst_amount, 9_000)
        self.assertEqual(lr.line_total, 59_000)

    def test_zero_quantity(self):
        lr = compute_line_item(
            quantity=0,
            rate_paise=100_00,
            discount_pct=0.0,
            gst_rate=18.0,
            is_intra_state=True,
        )
        self.assertEqual(lr.taxable_amount, 0)
        self.assertEqual(lr.line_total, 0)


class TestComputeDocTotals(unittest.TestCase):
    def test_multiple_items(self):
        items = [
            compute_line_item(10, 100_00, 0.0, 18.0, True),
            compute_line_item(5, 200_00, 0.0, 18.0, True),
        ]
        totals = compute_doc_totals(items)
        # Item 1: taxable=100000, cgst=9000, sgst=9000
        # Item 2: taxable=100000, cgst=9000, sgst=9000
        self.assertEqual(totals.total_taxable, 200_000)
        self.assertEqual(totals.total_cgst, 18_000)
        self.assertEqual(totals.total_sgst, 18_000)
        self.assertEqual(totals.grand_total, 236_000)

    def test_empty_items(self):
        totals = compute_doc_totals([])
        self.assertEqual(totals.grand_total, 0)


class TestFormatCurrency(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(format_currency(1234567), "₹12,345.67")

    def test_small(self):
        self.assertEqual(format_currency(500), "₹5.00")

    def test_zero(self):
        self.assertEqual(format_currency(0), "₹0.00")

    def test_negative(self):
        self.assertEqual(format_currency(-1234567), "-₹12,345.67")

    def test_large_indian_grouping(self):
        # ₹1,23,45,678.90 = 12345678 rupees 90 paise = 1234567890 paise
        result = format_currency(1234567890)
        self.assertEqual(result, "₹1,23,45,678.90")

    def test_custom_symbol(self):
        self.assertEqual(format_currency(10000, "$"), "$100.00")


class TestConversions(unittest.TestCase):
    def test_rupees_to_paise(self):
        self.assertEqual(rupees_to_paise(123.45), 12345)
        self.assertEqual(rupees_to_paise("999.99"), 99999)

    def test_paise_to_rupees(self):
        from decimal import Decimal
        self.assertEqual(paise_to_rupees(12345), Decimal("123.45"))


if __name__ == "__main__":
    unittest.main()
