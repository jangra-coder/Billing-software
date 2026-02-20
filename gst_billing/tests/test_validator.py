"""Tests for services/validator.py."""

import unittest
from services.validator import (
    validate_gstin,
    validate_pan,
    validate_mobile,
    validate_email,
    validate_hsn,
    validate_date,
    validate_amount,
    validate_quantity,
    validate_rate,
    validate_discount,
    validate_ifsc,
    validate_state_code,
    validate_required,
    extract_pan_from_gstin,
)


class TestGSTIN(unittest.TestCase):
    def test_valid(self):
        ok, msg = validate_gstin("06AALFA1234B1Z5")
        self.assertTrue(ok)

    def test_empty_is_ok(self):
        ok, _ = validate_gstin("")
        self.assertTrue(ok)

    def test_wrong_length(self):
        ok, msg = validate_gstin("06AALF")
        self.assertFalse(ok)
        self.assertIn("15", msg)

    def test_bad_format(self):
        ok, msg = validate_gstin("00AAAAA0000A0A0")
        self.assertFalse(ok)


class TestPAN(unittest.TestCase):
    def test_valid(self):
        ok, _ = validate_pan("ABCDE1234F")
        self.assertTrue(ok)

    def test_empty_ok(self):
        ok, _ = validate_pan("")
        self.assertTrue(ok)

    def test_invalid(self):
        ok, msg = validate_pan("12345ABCDE")
        self.assertFalse(ok)


class TestMobile(unittest.TestCase):
    def test_valid(self):
        ok, _ = validate_mobile("9876543210")
        self.assertTrue(ok)

    def test_starts_with_5(self):
        ok, msg = validate_mobile("5876543210")
        self.assertFalse(ok)

    def test_too_short(self):
        ok, msg = validate_mobile("98765")
        self.assertFalse(ok)


class TestEmail(unittest.TestCase):
    def test_valid(self):
        ok, _ = validate_email("user@example.com")
        self.assertTrue(ok)

    def test_invalid(self):
        ok, _ = validate_email("user@")
        self.assertFalse(ok)


class TestHSN(unittest.TestCase):
    def test_4_digits(self):
        ok, _ = validate_hsn("8456")
        self.assertTrue(ok)

    def test_6_digits(self):
        ok, _ = validate_hsn("845610")
        self.assertTrue(ok)

    def test_8_digits(self):
        ok, _ = validate_hsn("84561010")
        self.assertTrue(ok)

    def test_5_digits_invalid(self):
        ok, _ = validate_hsn("84561")
        self.assertFalse(ok)

    def test_empty_required(self):
        ok, msg = validate_hsn("")
        self.assertFalse(ok)
        self.assertIn("required", msg)


class TestDate(unittest.TestCase):
    def test_valid_date(self):
        ok, _ = validate_date("2026-01-15")
        self.assertTrue(ok)

    def test_invalid_format(self):
        ok, msg = validate_date("15-01-2026")
        self.assertFalse(ok)

    def test_empty_required(self):
        ok, msg = validate_date("", required=True)
        self.assertFalse(ok)

    def test_empty_optional(self):
        ok, _ = validate_date("", required=False)
        self.assertTrue(ok)


class TestAmount(unittest.TestCase):
    def test_valid(self):
        ok, _ = validate_amount(100.50)
        self.assertTrue(ok)

    def test_negative(self):
        ok, msg = validate_amount(-10)
        self.assertFalse(ok)

    def test_zero_allowed(self):
        ok, _ = validate_amount(0, allow_zero=True)
        self.assertTrue(ok)

    def test_zero_disallowed(self):
        ok, _ = validate_amount(0, allow_zero=False)
        self.assertFalse(ok)

    def test_non_numeric(self):
        ok, _ = validate_amount("abc")
        self.assertFalse(ok)


class TestQuantity(unittest.TestCase):
    def test_positive(self):
        ok, _ = validate_quantity(5)
        self.assertTrue(ok)

    def test_zero(self):
        ok, _ = validate_quantity(0)
        self.assertFalse(ok)


class TestDiscount(unittest.TestCase):
    def test_valid(self):
        ok, _ = validate_discount(0.10)
        self.assertTrue(ok)

    def test_over_one(self):
        ok, _ = validate_discount(1.5)
        self.assertFalse(ok)


class TestIFSC(unittest.TestCase):
    def test_valid(self):
        ok, _ = validate_ifsc("UTIB0001081")
        self.assertTrue(ok)

    def test_invalid(self):
        ok, _ = validate_ifsc("INVALID")
        self.assertFalse(ok)


class TestStateCode(unittest.TestCase):
    def test_valid(self):
        ok, _ = validate_state_code("06")
        self.assertTrue(ok)

    def test_known_set(self):
        ok, _ = validate_state_code("06", valid_codes={"06", "07"})
        self.assertTrue(ok)

    def test_unknown_code(self):
        ok, msg = validate_state_code("99", valid_codes={"06", "07"})
        self.assertFalse(ok)


class TestRequired(unittest.TestCase):
    def test_filled(self):
        ok, _ = validate_required("Hello", "Name")
        self.assertTrue(ok)

    def test_empty(self):
        ok, msg = validate_required("", "Name")
        self.assertFalse(ok)
        self.assertIn("Name", msg)


class TestExtractPAN(unittest.TestCase):
    def test_from_gstin(self):
        self.assertEqual(extract_pan_from_gstin("06AALFA1234B1Z5"), "AALFA1234B")

    def test_short_input(self):
        self.assertEqual(extract_pan_from_gstin("06A"), "")


if __name__ == "__main__":
    unittest.main()
