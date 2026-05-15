from __future__ import annotations

import json
import os
from typing import Optional

# ── Load canonical map from words.json once at import ──────────

def _find_words_json() -> str:
    """Walk up from this file to find words.json"""
    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        candidate = os.path.join(current, "words.json")
        if os.path.isfile(candidate):
            return candidate
        current = os.path.dirname(current)
    raise FileNotFoundError("words.json not found in parent directories")


def _load_data() -> tuple[dict, list]:
    try:
        path = _find_words_json()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        canonical_map = (
            data
            .get("category_normalization", {})
            .get("canonical_map", {})
        )
        all_categories = (
            data
            .get("metadata", {})
            .get("extended_categories", [])
        )
        return canonical_map, all_categories
    except Exception:
        return {}, []


_CANONICAL_MAP, _ALL_CATEGORIES = _load_data()

_DISPLAY_ALIASES = {
    "Loan Payment / EMI": "Loan Payment",
    "Loan Disbursal": "Loan Disbursed",
    "Bank Transfer": "Transfer",
    "Transfer Out": "Transfer",
    "Transfer In": "Transfer",
    "UPI Transfer": "Transfer",
    "Salary Credits": "Salary",
    "Interest Credit": "Interest Income",
    "Interest Debit": "Interest Income",
    "Bank Transfer In": "Transfer",
    "Cheque Deposit": "Cash Deposit",
}

# ── Public API ──────────────────────────────────────────────────

def normalize_category(
    category: Optional[str],
    is_debit: bool = True
) -> str:
    """
    Convert any category string to canonical form.
    Call this at every point a category is assigned.

    Handles:
    - SCREAMING_SNAKE from words.json (FOOD_EXPENSE → Food)
    - Title Case from rule engines (Loan Payments → Loan Payment)
    - Legacy/inconsistent names (Others → Others Debit)
    - None / empty string → safe fallback
    """
    if not category or not str(category).strip():
        return "Others Debit" if is_debit else "Others Credit"

    c = str(category).strip()

    # Already canonical
    if c in _ALL_CATEGORIES:
        return c

    # Lookup in canonical map (covers both words.json codes
    # and rule engine legacy names)
    if c in _DISPLAY_ALIASES:
        return _DISPLAY_ALIASES[c]

    if c in _CANONICAL_MAP:
        return _CANONICAL_MAP[c]

    # Unknown — safe fallback
    return "Others Debit" if is_debit else "Others Credit"


def get_allowed_categories() -> list[str]:
    """
    Single source of truth for AI allowed_categories.
    Use this everywhere — do not hardcode category lists.
    """
    if _ALL_CATEGORIES:
        return list(_ALL_CATEGORIES)
    # Hardcoded fallback if words.json unavailable
    return [
        "Food", "Transport", "Shopping", "Groceries", "Medical",
        "Entertainment", "Loan Payment", "Bill Payment",
        "Credit Card Payment", "ATM Withdrawal", "Bank Charges",
        "Investment", "Insurance", "Insurance Claim", "Fuel",
        "Travel", "Fitness", "Education", "Subscription",
        "Business Expense", "Tax Payment", "Transfer",
        "Others Debit", "Salary", "Business Income",
        "Freelance Income", "Interest Income", "Refund",
        "Cashback", "Dividend", "Loan Disbursed",
        "Investment Returns", "Rental Income", "Others Credit",
    ]


def is_valid_category(category: str) -> bool:
    return category in _ALL_CATEGORIES
