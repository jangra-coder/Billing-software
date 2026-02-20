"""
Indian Number-to-Words — exact replication of VBA Module5.

Converts a rupee amount (Decimal or float) to Indian English words.
Grouping: Crore → Lakh → Thousand → Hundred → Tens/Ones.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

_ONES = [
    "", "One", "Two", "Three", "Four", "Five", "Six", "Seven",
    "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen",
    "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen",
]

_TENS = [
    "", "", "Twenty", "Thirty", "Forty", "Fifty",
    "Sixty", "Seventy", "Eighty", "Ninety",
]


def _two_digits(n: int) -> str:
    """Convert a number 0-99 to words."""
    if n < 20:
        return _ONES[n]
    ten, unit = divmod(n, 10)
    return (_TENS[ten] + " " + _ONES[unit]).strip()


def _chunk_to_words(n: int) -> str:
    """Convert a number 0-999 to words."""
    if n == 0:
        return ""
    hundreds, remainder = divmod(n, 100)
    parts: list[str] = []
    if hundreds:
        parts.append(f"{_ONES[hundreds]} Hundred")
    if remainder:
        parts.append(_two_digits(remainder))
    return " ".join(parts)


def num_to_words(amount: float | Decimal | int, currency: str = "Rupees") -> str:
    """Convert a numeric amount to Indian English words.

    Args:
        amount: The amount in *rupees* (NOT paise).
                e.g. 15743.56 or Decimal('15743.56')
        currency: Currency word (default 'Rupees').

    Returns:
        e.g. 'Fifteen Thousand Seven Hundred Forty Three Rupees and Fifty Six Paise Only'
        Returns 'Zero Rupees Only' for 0.
    """
    # Normalise to Decimal for precision
    d = Decimal(str(amount)).quantize(Decimal("0.01"), ROUND_HALF_UP)
    is_negative = d < 0
    d = abs(d)

    rupees = int(d)
    paise = int((d - rupees) * 100)

    if rupees == 0 and paise == 0:
        return f"Zero {currency} Only"

    # Indian grouping: Crore, Lakh, Thousand, Hundred
    parts: list[str] = []

    crore, remainder = divmod(rupees, 10_000_000)
    if crore:
        parts.append(f"{_chunk_to_words(crore)} Crore")

    lakh, remainder = divmod(remainder, 100_000)
    if lakh:
        parts.append(f"{_two_digits(lakh)} Lakh")

    thousand, remainder = divmod(remainder, 1_000)
    if thousand:
        parts.append(f"{_two_digits(thousand)} Thousand")

    if remainder:
        parts.append(_chunk_to_words(remainder))

    rupee_words = " ".join(parts).strip()
    if not rupee_words:
        rupee_words = "Zero"
    prefix = "Minus " if is_negative else ""

    if paise:
        paise_words = _two_digits(paise)
        return f"{prefix}{rupee_words} {currency} and {paise_words} Paise Only"
    else:
        return f"{prefix}{rupee_words} {currency} Only"


def paise_to_words(paise_amount: int, currency: str = "Rupees") -> str:
    """Convenience: convert integer paise to words.

    Args:
        paise_amount: Amount in paise (e.g. 1574356 for ₹15,743.56).
        currency: Currency word.
    """
    rupees = Decimal(paise_amount) / Decimal("100")
    return num_to_words(rupees, currency)
