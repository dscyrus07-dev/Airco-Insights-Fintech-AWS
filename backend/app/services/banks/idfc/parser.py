"""
Airco Insights - IDFC Bank Parser
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import pdfplumber

from app.services.banks._shared.generic_bank import GenericParseError

logger = logging.getLogger(__name__)


@dataclass
class IDFCTransaction:
    date: str
    description: str
    ref_no: str
    debit: Optional[float]
    credit: Optional[float]
    balance: float

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "description": self.description,
            "ref_no": self.ref_no,
            "debit": self.debit,
            "credit": self.credit,
            "balance": self.balance,
        }


@dataclass
class IDFCParseResult:
    transactions: List[IDFCTransaction]
    total_count: int
    parse_method: str
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    total_credits: float = 0.0
    total_debits: float = 0.0


class IDFCParser:
    ROW_RE = re.compile(
        r"^(?P<txn_date>\d{2}-[A-Za-z]{3}-\d{4})\s+"
        r"(?P<value_date>\d{2}-[A-Za-z]{3}-\d{4})\s+"
        r"(?P<rest>.*)$"
    )

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def parse(self, file_path: str, text_content: str = "") -> IDFCParseResult:
        transactions: List[IDFCTransaction] = []
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
                "Could not extract transactions from this IDFC PDF.",
                error_code="NO_TRANSACTIONS",
                details={"file": file_path},
            )

        total_credits = sum(txn.credit or 0 for txn in transactions)
        total_debits = sum(txn.debit or 0 for txn in transactions)
        return IDFCParseResult(
            transactions=transactions,
            total_count=len(transactions),
            parse_method="text",
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            total_credits=total_credits,
            total_debits=total_debits,
        )

    def _parse_lines(
        self,
        lines: List[str],
        prev_balance: Optional[float],
    ) -> Tuple[List[IDFCTransaction], Optional[float], Optional[float]]:
        transactions: List[IDFCTransaction] = []
        opening_balance: Optional[float] = None

        i = 0
        while i < len(lines):
            line = lines[i]

            if self._is_skip_line(line):
                i += 1
                continue

            opening_match = re.search(r"^Opening\s+Balance\s+([-\d,]+\.\d{2})$", line, re.IGNORECASE)
            if opening_match and opening_balance is None:
                opening_balance = self._parse_amount(opening_match.group(1))
                if prev_balance is None:
                    prev_balance = opening_balance
                i += 1
                continue

            row_match = self.ROW_RE.match(line)
            if row_match:
                suffix_lines: List[str] = []
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    if self.ROW_RE.match(next_line) or self._is_skip_line(next_line):
                        break
                    suffix_lines.append(next_line)
                    j += 1

                txn, prev_balance = self._build_transaction(row_match, suffix_lines, prev_balance)
                if txn:
                    transactions.append(txn)
                i = j
                continue

            i += 1

        return transactions, opening_balance, prev_balance

    def _build_transaction(
        self,
        row_match: re.Match[str],
        suffix_lines: List[str],
        prev_balance: Optional[float],
    ) -> Tuple[Optional[IDFCTransaction], Optional[float]]:
        full_text = " ".join(part.strip() for part in [row_match.group("rest"), *suffix_lines] if part).strip()
        full_text = re.sub(r"\s+", " ", full_text)
        full_text = self._clean_multiline_text(full_text)

        parsed = self._extract_amount_and_balance(full_text)
        if not parsed:
            return None, prev_balance

        description, amount, balance = parsed
        if amount is None or balance is None:
            return None, prev_balance

        debit, credit = self._infer_direction(description, amount, balance, prev_balance)
        description = description or "IDFC Transaction"
        ref_no = self._extract_reference(description)

        txn = IDFCTransaction(
            date=datetime.strptime(row_match.group("txn_date"), "%d-%b-%Y").strftime("%Y-%m-%d"),
            description=description,
            ref_no=ref_no,
            debit=debit,
            credit=credit,
            balance=balance,
        )
        return txn, balance

    def _extract_amount_and_balance(self, text: str) -> Optional[Tuple[str, Optional[float], Optional[float]]]:
        matches = list(re.finditer(r"-?[\d,]+\.\d{2}", text))
        if len(matches) < 2:
            return None

        amount_match = matches[-2]
        balance_match = matches[-1]
        lead = text[:amount_match.start()].strip(" /-")
        tail = text[balance_match.end():].strip(" /-")
        amount = self._parse_amount(amount_match.group(0))
        balance = self._parse_amount(balance_match.group(0))
        description = " ".join(part for part in [lead, tail] if part).strip()
        description = re.sub(r"\s+", " ", description)
        return description, amount, balance

    def _infer_direction(
        self,
        description: str,
        amount: float,
        balance: float,
        prev_balance: Optional[float],
    ) -> Tuple[Optional[float], Optional[float]]:
        desc_upper = description.upper()
        amount_abs = abs(amount)

        credit_markers = (
            "IMPS-MOB/FUND TRF",
            "IMPS-INET/FUND TRF",
            "NEFT/",
            "CREDIT ADJUSTMENT",
            "INTEREST CREDIT",
            "REFUND",
            "REVERSAL",
        )
        debit_markers = (
            "NACH/",
            "UPI/MOB/",
            "CHARGE:",
            "CGST ON CHARGE",
            "SGST ON CHARGE",
            "MANDATE REQUEST",
            "PAY TO BHARATPE",
            "PAY BY WHATSAPP",
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

        if amount < 0:
            return amount_abs, None
        return amount_abs, None

    def _extract_reference(self, description: str) -> str:
        patterns = [
            r"\b(UPI/[A-Z0-9/-]+)",
            r"\b(IMPS-[A-Z]+/Fund Trf/\d+)",
            r"\b(NEFT/[A-Z0-9/.-]+)",
            r"\b(NACH/[A-Z0-9 /.-]+/\w+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(1)[:120]
        return ""

    def _clean_multiline_text(self, text: str) -> str:
        cleaned = text
        regex_replacements = [
            (r"Payment\s+f\s+rom", "Payment from"),
            (r"UPI\s+Trans\s+action", "UPI Transaction"),
            (r"MandateRe\s+quest", "Mandate Request"),
            (r"Pay\s+to\s+Bh\s+aratPe", "Pay to BharatPe"),
            (r"PAY\s+BY\s+WH\s+ATSAPP", "PAY BY WHATSAPP"),
            (r"INTEREST\s+CREDI\s+T", "INTEREST CREDIT"),
            (r"Non-Mainten\s+ance", "Non-Maintenance"),
            (r"31-DE\s+C-2022", "31-DEC-2022"),
            (r"TVS\s+CRED\s+IT\s+SERVICES", "TVS CREDIT SERVICES"),
        ]
        for pattern, target in regex_replacements:
            cleaned = re.sub(pattern, target, cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*/\s*", "/", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip(" /")

    def _is_skip_line(self, line: str) -> bool:
        upper = line.upper().strip()
        skip_tokens = (
            "STATEMENT OF ACCOUNT",
            "CUSTOMER ID :",
            "ACCOUNT NO :",
            "STATEMENT PERIOD :",
            "CUSTOMER NAME :",
            "COMMUNICATION :",
            "ADDRESS",
            "EMAIL ID :",
            "PHONE NO :",
            "NOMINATION :",
            "IFSC :",
            "MICR :",
            "ACCOUNT OPENING DATE :",
            "ACCOUNT STATUS :",
            "ACCOUNT TYPE :",
            "CURRENCY :",
            "OPENING BALANCE TOTAL DEBIT TOTAL CREDIT CLOSING BALANCE",
            "TRANSACTION DATE VALUE DATE PARTICULARS CHEQUE DEBIT CREDIT BALANCE",
            "REGISTERED OFFICE:",
            "PAGE ",
        )
        if upper == "NO":
            return True
        return any(token in upper for token in skip_tokens)

    def _parse_amount(self, value: str) -> Optional[float]:
        try:
            return float(value.replace(",", "").strip())
        except Exception:
            return None


# Re-export for compatibility
IDFCParseError = GenericParseError
