"""Tests for services/gst_engine.py."""

import unittest
from decimal import Decimal
from services.gst_engine import (
    determine_supply_type,
    calculate_tax,
    extract_state_code_from_gstin,
    TaxBreakdown,
)


class TestDetermineSupplyType(unittest.TestCase):
    def test_same_state_is_intra(self):
        self.assertTrue(determine_supply_type("06", "06"))

    def test_different_state_is_inter(self):
        self.assertFalse(determine_supply_type("06", "07"))

    def test_empty_seller_is_inter(self):
        self.assertFalse(determine_supply_type("", "06"))

    def test_empty_buyer_is_inter(self):
        self.assertFalse(determine_supply_type("06", ""))

    def test_both_empty_is_inter(self):
        self.assertFalse(determine_supply_type("", ""))

    def test_whitespace_trimmed(self):
        self.assertTrue(determine_supply_type(" 06 ", "06"))


class TestCalculateTax(unittest.TestCase):
    def test_intra_state_18_pct(self):
        tb = calculate_tax(Decimal("1000"), 18.0, is_intra_state=True)
        self.assertTrue(tb.is_intra_state)
        self.assertEqual(tb.cgst_rate, Decimal("9.00"))
        self.assertEqual(tb.sgst_rate, Decimal("9.00"))
        self.assertEqual(tb.cgst_amount, Decimal("90.00"))
        self.assertEqual(tb.sgst_amount, Decimal("90.00"))
        self.assertEqual(tb.igst_amount, Decimal("0"))
        self.assertEqual(tb.total_tax, Decimal("180.00"))

    def test_inter_state_18_pct(self):
        tb = calculate_tax(Decimal("1000"), 18.0, is_intra_state=False)
        self.assertFalse(tb.is_intra_state)
        self.assertEqual(tb.igst_rate, Decimal("18"))
        self.assertEqual(tb.igst_amount, Decimal("180.00"))
        self.assertEqual(tb.cgst_amount, Decimal("0"))
        self.assertEqual(tb.total_tax, Decimal("180.00"))

    def test_5_pct_gst(self):
        tb = calculate_tax(Decimal("2000"), 5.0, is_intra_state=True)
        self.assertEqual(tb.cgst_rate, Decimal("2.50"))
        self.assertEqual(tb.cgst_amount, Decimal("50.00"))
        self.assertEqual(tb.sgst_amount, Decimal("50.00"))
        self.assertEqual(tb.total_tax, Decimal("100.00"))

    def test_zero_gst(self):
        tb = calculate_tax(Decimal("5000"), 0.0, is_intra_state=True)
        self.assertEqual(tb.total_tax, Decimal("0.00"))

    def test_fractional_amount(self):
        tb = calculate_tax(Decimal("999.99"), 18.0, is_intra_state=False)
        self.assertEqual(tb.igst_amount, Decimal("180.00"))  # 999.99 * 0.18 = 179.9982 → 180.00


class TestExtractStateCode(unittest.TestCase):
    def test_valid_gstin(self):
        self.assertEqual(extract_state_code_from_gstin("06AALFA1234B1Z5"), "06")

    def test_short_gstin(self):
        self.assertEqual(extract_state_code_from_gstin("0"), "")

    def test_empty_gstin(self):
        self.assertEqual(extract_state_code_from_gstin(""), "")

    def test_none_gstin(self):
        self.assertEqual(extract_state_code_from_gstin(None), "")

    def test_alpha_start(self):
        self.assertEqual(extract_state_code_from_gstin("ABCDEFGHIJ12345"), "")


if __name__ == "__main__":
    unittest.main()
