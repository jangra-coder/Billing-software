"""Tests for services/num_to_words.py."""

import unittest
from services.num_to_words import num_to_words, paise_to_words


class TestNumToWords(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(num_to_words(0), "Zero Rupees Only")

    def test_ones(self):
        self.assertEqual(num_to_words(5), "Five Rupees Only")

    def test_teens(self):
        self.assertEqual(num_to_words(15), "Fifteen Rupees Only")

    def test_tens(self):
        self.assertEqual(num_to_words(50), "Fifty Rupees Only")

    def test_hundred(self):
        self.assertEqual(num_to_words(100), "One Hundred Rupees Only")

    def test_thousand(self):
        self.assertEqual(num_to_words(1000), "One Thousand Rupees Only")

    def test_lakh(self):
        self.assertEqual(num_to_words(100000), "One Lakh Rupees Only")

    def test_crore(self):
        self.assertEqual(num_to_words(10000000), "One Crore Rupees Only")

    def test_complex_number(self):
        result = num_to_words(15743.56)
        self.assertEqual(
            result,
            "Fifteen Thousand Seven Hundred Forty Three Rupees and Fifty Six Paise Only",
        )

    def test_paise_only_via_decimal(self):
        result = num_to_words(0.50)
        self.assertEqual(result, "Zero Rupees and Fifty Paise Only")

        result2 = paise_to_words(50)
        self.assertIn("Fifty Paise", result2)

    def test_negative(self):
        result = num_to_words(-500)
        self.assertIn("Minus", result)

    def test_two_crore(self):
        result = num_to_words(25_43_217.89)
        self.assertIn("Twenty Five Lakh", result)
        self.assertIn("Eighty Nine Paise", result)


class TestPaiseToWords(unittest.TestCase):
    def test_basic(self):
        result = paise_to_words(1574356)
        self.assertEqual(
            result,
            "Fifteen Thousand Seven Hundred Forty Three Rupees and Fifty Six Paise Only",
        )

    def test_exact_rupees(self):
        result = paise_to_words(500000)
        self.assertEqual(result, "Five Thousand Rupees Only")


if __name__ == "__main__":
    unittest.main()
