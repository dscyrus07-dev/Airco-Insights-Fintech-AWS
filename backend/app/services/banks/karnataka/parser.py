from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pdfplumber

from app.services.banks._shared.generic_bank import GenericParseError


KarnatakaParseError = GenericParseError


@dataclass
class KarnatakaTransaction:
    date: str
    description: str
    ref_no: str
    debit: Optional[float]
    credit: Optional[float]
    balance: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "description": self.description,
            "ref_no": self.ref_no,
            "debit": self.debit,
            "credit": self.credit,
            "balance": self.balance,
        }


@dataclass
class KarnatakaParseResult:
    transactions: List[KarnatakaTransaction]
    total_count: int
    parse_method: str
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    total_credits: float = 0.0
    total_debits: float = 0.0


class KarnatakaParser:
    ROW_RE = re.compile(r"^(?P<date>\d{2}-\d{2}-\d{4})\s+(?P<rest>.+?)\s+(?P<amount>[\d,]+\.\d{2})\s+(?P<balance>[\d,]+\.\d{2})$")

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def parse(self, file_path: str, text_content: str = "") -> KarnatakaParseResult:
        transactions: List[KarnatakaTransaction] = []
        opening_balance: Optional[float] = None
        closing_balance: Optional[float] = None
        prev_balance: Optional[float] = None

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                lines = [line.strip() for line in (page.extract_text() or "").splitlines() if line and line.strip()]
                page_transactions, page_opening, prev_balance = self._parse_lines(lines, prev_balance)
                if opening_balance is None and page_opening is not None:
                    opening_balance = page_opening
                    if prev_balance is None:
                        prev_balance = page_opening
                if page_transactions:
                    closing_balance = page_transactions[-1].balance
                transactions.extend(page_transactions)

        if not transactions:
            raise GenericParseError(
                "Could not extract transactions from this Karnataka Bank PDF.",
                error_code="NO_TRANSACTIONS",
                details={"file": file_path},
            )

        total_credits = sum(txn.credit or 0 for txn in transactions)
        total_debits = sum(txn.debit or 0 for txn in transactions)
        return KarnatakaParseResult(
            transactions=transactions,
            total_count=len(transactions),
            parse_method="text",
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            total_credits=total_credits,
            total_debits=total_debits,
        )

    def _parse_lines(self, lines: List[str], prev_balance: Optional[float]) -> Tuple[List[KarnatakaTransaction], Optional[float], Optional[float]]:
        transactions: List[KarnatakaTransaction] = []
        opening_balance: Optional[float] = None

        for line in lines:
            if self._is_skip_line(line):
                continue

            opening_match = re.search(r"^Opening\s+Balance\s+([-\d,]+\.\d{2})$", line, re.IGNORECASE)
            if opening_match and opening_balance is None:
                opening_balance = self._parse_amount(opening_match.group(1))
                if prev_balance is None:
                    prev_balance = opening_balance
                continue

            row_match = self.ROW_RE.match(line)
            if not row_match:
                continue

            amount = self._parse_amount(row_match.group("amount"))
            balance = self._parse_amount(row_match.group("balance"))
            if amount is None or balance is None:
                continue

            description = self._clean_description(row_match.group("rest"))
            debit, credit = self._infer_direction(description, amount, balance, prev_balance)
            ref_no = self._extract_reference(description)
            txn = KarnatakaTransaction(
                date=datetime.strptime(row_match.group("date"), "%d-%m-%Y").strftime("%Y-%m-%d"),
                description=description,
                ref_no=ref_no,
                debit=debit,
                credit=credit,
                balance=balance,
            )
            transactions.append(txn)
            prev_balance = balance

        return transactions, opening_balance, prev_balance

    def _infer_direction(self, description: str, amount: float, balance: float, prev_balance: Optional[float]) -> Tuple[Optional[float], Optional[float]]:
        desc_upper = description.upper()
        amount_abs = abs(amount)

        credit_markers = (
            "DEBITREVERSAL", "BY CASH", "PAYOUTS@PAYTM", "CF.PAYOUT@ICICI", "CASHFREEPAYOUT@IDFCBANK",
            "WALLETMONEYTOBANK@PAYTM", "NEFT-", "IMPS/P2A-",
        )
        debit_markers = (
            "TRANSFER TO ", "SENT", "PAYMENT", "PAYME", "REQUEST", "AMAZONPAY", "ONECARD@IDFCBANK",
            "CHRGS", "CHRGS FOR", "SMS CHRGS", "NA-K",
        )

        if prev_balance is not None:
            delta = round(balance - prev_balance, 2)
            if abs(delta - amount_abs) <= 1.0:
                return None, amount_abs
            if abs(delta + amount_abs) <= 1.0:
                return amount_abs, None

        if any(marker in desc_upper for marker in credit_markers):
            return None, amount_abs
        if any(marker in desc_upper for marker in debit_markers):
            return amount_abs, None

        return amount_abs, None

    def _clean_description(self, text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text).strip()
        fixes = [
            (r":Paym$", ":Payment"),
            (r":Payme$", ":Payment"),
            (r":Paymen$", ":Payment"),
            (r":Sent fr$", ":Sent from"),
            (r":Payment f$", ":Payment from"),
            (r"\(Cashfree Payment$", "(Cashfree Payment)"),
            (r"\(Paytm$", "(Paytm)"),
            (r"\(AMAZONPAY\):Request$", "(AMAZONPAY):Request"),
        ]
        for pattern, target in fixes:
            cleaned = re.sub(pattern, target, cleaned, flags=re.IGNORECASE)
        return cleaned

    def _extract_reference(self, description: str) -> str:
        patterns = [
            r"\b(UPI:\d+:[^\s]+)",
            r"\b(IMPS/[A-Z0-9-]+)",
            r"\b(NEFT-[A-Z0-9 /.-]+)",
            r"\b(KBNA\d+/\d+/\d{2}-\d{2}-\d{4})",
        ]
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(1)[:120]
        return ""

    def _is_skip_line(self, line: str) -> bool:
        upper = line.upper().strip()
        skip_tokens = (
            "STATEMENT FOR A/C", "CUSTOMER ID", "NAME ", "ADDRESS ", "INDIA PHONE NUMBER", "IFSC CODE",
            "PHONE ", "EMAIL ID", "VPA", "DATE PARTICULARS INSTRUMENT NO WITHDRAWALS DEPOSITS BALANCE", "PAGE ",
        )
        return any(token in upper for token in skip_tokens)

    def _parse_amount(self, value: str) -> Optional[float]:
        try:
            return float(value.replace(",", "").strip())
        except Exception:
            return None

