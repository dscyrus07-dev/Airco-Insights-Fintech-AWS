"""
Airco Insights - Canara Bank Parser
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

import pdfplumber

from app.services.banks._shared.generic_bank import GenericParseError

logger = logging.getLogger(__name__)


@dataclass
class CanaraTransaction:
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


# Re-export for compatibility
CanaraParseError = GenericParseError


@dataclass
class CanaraParseResult:
    transactions: List[CanaraTransaction]
    total_count: int
    parse_method: str
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    total_credits: float = 0.0
    total_debits: float = 0.0


class CanaraParser:
    ROW_RE = re.compile(
        r"^(?P<txn_date>\d{2}-\d{2}-\d{4})\s+"
        r"(?P<txn_time>\d{2}:\d{2}:\d{2})\s+"
        r"(?P<value_date>\d{2}\s+[A-Za-z]{3}\s+\d{4})\s+"
        r"(?P<rest>.*)$"
    )
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def parse(self, file_path: str, text_content: str = "") -> CanaraParseResult:
        transactions: List[CanaraTransaction] = []
        opening_balance: Optional[float] = None
        closing_balance: Optional[float] = None
        prev_balance: Optional[float] = None

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                lines = [line.strip() for line in (page.extract_text() or "").splitlines() if line and line.strip()]
                page_transactions, page_opening, prev_balance = self._parse_lines(lines, prev_balance)
                if opening_balance is None and page_opening is not None:
                    opening_balance = page_opening
                if page_transactions:
                    closing_balance = page_transactions[-1].balance
                transactions.extend(page_transactions)

        if not transactions:
            raise GenericParseError(
                "Could not extract transactions from this Canara PDF.",
                error_code="NO_TRANSACTIONS",
                details={"file": file_path},
            )

        total_credits = sum(txn.credit or 0 for txn in transactions)
        total_debits = sum(txn.debit or 0 for txn in transactions)
        return CanaraParseResult(
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
    ) -> Tuple[List[CanaraTransaction], Optional[float], Optional[float]]:
        transactions: List[CanaraTransaction] = []
        pending_lines: List[str] = []
        opening_balance: Optional[float] = None

        i = 0
        while i < len(lines):
            line = lines[i]

            opening_match = re.search(r"Opening\s*Balance\s*Rs\.\s*([-\d,]+\.\d{2})", line, re.IGNORECASE)
            if opening_match and opening_balance is None:
                opening_balance = self._parse_amount(opening_match.group(1))
                i += 1
                continue

            if self._is_skip_line(line):
                pending_lines = []
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

                txn, prev_balance = self._build_transaction(row_match, pending_lines, suffix_lines, prev_balance)
                pending_lines = []
                if txn:
                    transactions.append(txn)
                i = j
                continue

            pending_lines.append(line)
            i += 1

        return transactions, opening_balance, prev_balance

    def _build_transaction(
        self,
        row_match: re.Match[str],
        pending_lines: List[str],
        suffix_lines: List[str],
        prev_balance: Optional[float],
    ) -> Tuple[Optional[CanaraTransaction], Optional[float]]:
        full_rest = " ".join(part.strip() for part in [row_match.group("rest"), *suffix_lines] if part).strip()
        full_rest = re.sub(r"\s+", " ", full_rest)
        full_rest = self._strip_footer_noise(full_rest)
        parsed_tail = self._extract_amount_and_balance(full_rest)
        if not parsed_tail:
            return None, prev_balance

        lead, amount, balance = parsed_tail
        if amount is None or balance is None:
            return None, prev_balance

        amount_abs = abs(amount)
        combined_description = " ".join(part for part in [*pending_lines, lead] if part).strip()
        combined_description = re.sub(r"\s+", " ", combined_description)

        debit, credit = self._infer_direction(combined_description, amount, balance, prev_balance)
        ref_no = self._extract_reference(combined_description)

        txn = CanaraTransaction(
            date=datetime.strptime(row_match.group("txn_date"), "%d-%m-%Y").strftime("%Y-%m-%d"),
            description=combined_description,
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
        lead = text[:amount_match.start()].strip()
        amount = self._parse_amount(amount_match.group(0))
        balance = self._parse_amount(balance_match.group(0))
        lead = re.sub(r"\b[0-9A-Z]{2,14}\b\s*$", "", lead).strip()
        return lead, amount, balance

    def _infer_direction(
        self,
        description: str,
        amount: float,
        balance: float,
        prev_balance: Optional[float],
    ) -> Tuple[Optional[float], Optional[float]]:
        desc_upper = description.upper()
        amount_abs = abs(amount)

        credit_markers = (" CR", "CREDIT", "GROSS INT CR", "NEFT CR", "IMPS-CR", "UPI/CR/", "FD REDEEM", "GST REV")
        debit_markers = (" DR", "DEBIT", "ECS ", "ATM CASH", "SMS CHARGES", "CHARGES", "DRAWDOWN", "IB OAT", "INSTL PAY")

        if prev_balance is not None:
            delta = round(balance - prev_balance, 2)
            if abs(delta - amount_abs) <= 1.0:
                return None, amount_abs
            if abs(delta + amount_abs) <= 1.0:
                return amount_abs, None

        if amount < 0:
            return amount_abs, None
        if any(marker in desc_upper for marker in credit_markers):
            return None, amount_abs
        if any(marker in desc_upper for marker in debit_markers):
            return amount_abs, None

        return amount_abs, None

    def _extract_reference(self, description: str) -> str:
        patterns = [
            r"\b(\d{12})\b",
            r"\b(IMPS/[A-Z0-9/.-]+)",
            r"\b(UPI/[A-Z0-9/.*@_-]+)",
            r"\b(NEFT\s+Cr-[A-Z0-9-]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(1)[:120]
        return ""

    def _strip_footer_noise(self, text: str) -> str:
        cut_tokens = [
            "Disclaimer:",
            "UNLESS THE CONSTITUENT BRINGS",
            "END OF STATEMENT",
            "Page ",
        ]
        result = text
        for token in cut_tokens:
            pos = result.find(token)
            if pos >= 0:
                result = result[:pos].strip()
        return result

    def _is_skip_line(self, line: str) -> bool:
        upper = line.upper().strip()
        skip_tokens = (
            "CURRENT & SAVING ACCOUNT STATEMENT",
            "ACCOUNT STATEMENT AS OF",
            "ACCOUNT HOLDERS",
            "ACCOUNT HOLDERS NAME",
            "CUSTOMER ID",
            "BRANCH NAME",
            "MICR CODE",
            "IFSC CODE",
            "SEARCHED BY FROM",
            "ACCOUNT NUMBER",
            "ACCOUNT CURRENCY",
            "PRODUCT NAME",
            "OPENING BALANCE RS.",
            "CLOSING BALANCE RS.",
            "TXN DATE VALUE DATE CHEQUE NO. DESCRIPTION BRANCH DEBIT CREDIT BALANCE",
            "CODE",
            "PAGE ",
            "DISCLAIMER:",
            "END OF STATEMENT",
            "ONLINE COMPLAINT REGISTRATION PORTAL",
            "TOLL FREE NO",
        )
        return any(token in upper for token in skip_tokens)

    def _parse_amount(self, value: str) -> Optional[float]:
        try:
            return float(value.replace(",", "").strip())
        except Exception:
            return None


# Re-export for compatibility
GenericParseError = GenericParseError
