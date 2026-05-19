"""
Airco Insights - Bank of Baroda Parser
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
class BankOfBarodaTransaction:
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
class BankOfBarodaParseResult:
    transactions: List[BankOfBarodaTransaction]
    total_count: int
    parse_method: str
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    total_credits: float = 0.0
    total_debits: float = 0.0


class BankOfBarodaParser:
    ROW_RE = re.compile(
        r"^(?P<serial>\d+)\s+(?P<txn_date>\d{2}-\d{2}-\d{4})\s+(?P<value_date>\d{2}-\d{2}-\d{4})\s+(?P<rest>.*)$"
    )
    OPENING_RE = re.compile(
        r"^(?P<serial>\d+)\s+(?P<date>\d{2}-\d{2}-\d{4})\s+Opening\s+Balance\s+-\s+-\s+(?P<balance>[\d,]+\.\d{2})$",
        re.IGNORECASE,
    )

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def parse(self, file_path: str, text_content: str = "") -> BankOfBarodaParseResult:
        transactions: List[BankOfBarodaTransaction] = []
        opening_balance: Optional[float] = None

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                page_transactions, page_opening = self._parse_page(page_text)
                if opening_balance is None and page_opening is not None:
                    opening_balance = page_opening
                transactions.extend(page_transactions)

        if not transactions:
            raise GenericParseError(
                "Could not extract transactions from this Bank of Baroda PDF.",
                error_code="NO_TRANSACTIONS",
                details={"file": file_path},
            )

        total_credits = sum(txn.credit or 0 for txn in transactions)
        total_debits = sum(txn.debit or 0 for txn in transactions)
        return BankOfBarodaParseResult(
            transactions=transactions,
            total_count=len(transactions),
            parse_method="text",
            opening_balance=opening_balance,
            closing_balance=transactions[-1].balance if transactions else None,
            total_credits=total_credits,
            total_debits=total_debits,
        )

    def _parse_page(self, page_text: str) -> Tuple[List[BankOfBarodaTransaction], Optional[float]]:
        lines = [line.strip() for line in page_text.splitlines() if line and line.strip()]
        transactions: List[BankOfBarodaTransaction] = []
        opening_balance: Optional[float] = None
        in_table = False
        prefix_lines: List[str] = []

        i = 0
        while i < len(lines):
            line = lines[i]
            if self._is_table_header(line):
                in_table = True
                prefix_lines = []
                i += 1
                continue

            if not in_table:
                i += 1
                continue

            if self._is_skip_line(line):
                prefix_lines = []
                i += 1
                continue

            opening_match = self.OPENING_RE.match(line)
            if opening_match:
                opening_balance = self._parse_amount(opening_match.group("balance"))
                prefix_lines = []
                i += 1
                continue

            row_match = self.ROW_RE.match(line)
            if row_match:
                suffix_lines: List[str] = []
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    if self._is_table_header(next_line) or self._is_skip_line(next_line):
                        break
                    if self.OPENING_RE.match(next_line) or self.ROW_RE.match(next_line):
                        break
                    if self._looks_like_new_description_start(next_line):
                        break
                    suffix_lines.append(next_line)
                    j += 1

                transaction = self._build_transaction(row_match, prefix_lines, suffix_lines)
                prefix_lines = []
                if transaction:
                    transactions.append(transaction)
                i = j
                continue

            prefix_lines.append(line)
            i += 1

        return transactions, opening_balance

    def _build_transaction(
        self,
        row_match: re.Match[str],
        prefix_lines: List[str],
        suffix_lines: List[str],
    ) -> Optional[BankOfBarodaTransaction]:
        rest = re.sub(r"\s+", " ", row_match.group("rest")).strip()
        parsed = self._parse_amount_columns(rest)
        if not parsed:
            return None

        lead_text, debit, credit, balance = parsed
        description = self._combine_description(prefix_lines, lead_text, suffix_lines)
        if not description:
            description = lead_text or f"Transaction {row_match.group('serial')}"

        ref_no = self._extract_reference(description)
        date_value = self._normalize_date(row_match.group("txn_date"))

        return BankOfBarodaTransaction(
            date=date_value,
            description=description,
            ref_no=ref_no,
            debit=debit,
            credit=credit,
            balance=balance,
        )

    def _parse_amount_columns(self, rest: str) -> Optional[Tuple[str, Optional[float], Optional[float], float]]:
        credit_match = re.search(
            r"^(?P<lead>.*?)\s*-\s*(?P<credit>\d[\d,]*\.\d{2})\s+(?P<balance>\d[\d,]*\.\d{2})$",
            rest,
        )
        if credit_match:
            return (
                credit_match.group("lead").strip(" -"),
                None,
                self._parse_amount(credit_match.group("credit")),
                self._parse_amount(credit_match.group("balance")) or 0.0,
            )

        debit_match = re.search(
            r"^(?P<lead>.*?)(?P<debit>\d[\d,]*\.\d{2})\s*-\s*(?P<balance>\d[\d,]*\.\d{2})$",
            rest,
        )
        if debit_match:
            return (
                debit_match.group("lead").strip(" -"),
                self._parse_amount(debit_match.group("debit")),
                None,
                self._parse_amount(debit_match.group("balance")) or 0.0,
            )

        return None

    def _combine_description(self, prefix_lines: List[str], lead_text: str, suffix_lines: List[str]) -> str:
        prefix = "".join(part.strip() for part in prefix_lines if part).strip()
        suffix = "".join(part.strip() for part in suffix_lines if part).strip()
        description = " ".join(part for part in [prefix, lead_text.strip(), suffix] if part).strip()
        description = re.sub(r"\s+", " ", description)
        return description.strip(" -")

    def _looks_like_new_description_start(self, line: str) -> bool:
        upper = line.upper().strip()
        starters = (
            "UPI/",
            "IMPS/",
            "ATM/CASH/",
            "MBK/",
            "CHARGES FOR",
            "BY CASH",
            "NEFT/",
            "RTGS/",
            "REVERSAL",
        )
        return any(upper.startswith(token) for token in starters)

    def _extract_reference(self, description: str) -> str:
        patterns = [
            r"\b(IMPS/[A-Z0-9/.-]+)",
            r"\b(UPI/\d+/\d{2}:\d{2}:\d{2}/UPI/[^\s]+)",
            r"\b(MBK/\d+/\d{2}:\d{2}:\d{2}/[^\s]+)",
            r"\b(ATM/CASH/\d+/[^\s]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(1)[:120]
        return ""

    def _is_table_header(self, line: str) -> bool:
        return (
            "Serial Transaction Value Description Cheque Debit Credit Balance" in line
            or line == "No Date Date Number"
        )

    def _is_skip_line(self, line: str) -> bool:
        upper = line.upper()
        skip_tokens = (
            "ACCOUNT STATEMENT FROM",
            "ACCOUNT DETAILS",
            "ACCOUNT NAME BRANCH NAME",
            "ACCOUNT NUMBER IFSC CODE",
            "ACCOUNT TYPE MICR CODE",
            "CUSTOMER ADDRESS",
            "BRANCH ADDRESS",
            "NOTE:IN CASE YOU FIND ANY DISCREPANCY",
            "THIS IS A COMPUTER-GENERATED STATEMENT",
            "MAINTAINED IN THE BANK CONTAINING TRANSACTIONS",
            "PAGE ",
        )
        if any(token in upper for token in skip_tokens):
            return True
        if upper.startswith("SO CHANDRA") or upper.startswith("MYSORE") or upper.startswith("KARNATAKA"):
            return True
        return False

    def _normalize_date(self, date_text: str) -> str:
        return datetime.strptime(date_text, "%d-%m-%Y").strftime("%Y-%m-%d")

    def _parse_amount(self, value: str) -> Optional[float]:
        try:
            return float(value.replace(",", "").strip())
        except Exception:
            return None




# Re-export for compatibility
BankOfBarodaParseError = GenericParseError
