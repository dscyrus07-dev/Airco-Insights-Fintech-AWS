"""
Airco Insights - Paytm Bank Parser
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
class PaytmTransaction:
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
class PaytmParseResult:
    transactions: List[PaytmTransaction]
    total_count: int
    parse_method: str
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    total_credits: float = 0.0
    total_debits: float = 0.0


class PaytmParser:
    HEADER_RE = re.compile(
        r"^(?P<date>\d{2} [A-Za-z]{3} \d{4})\s+"
        r"(?P<title>.+?)\s+"
        r"(?P<sign>[+-])\s+Rs\.(?P<amount>[\d,]+\.\d{2})\s+Rs\.(?P<balance>[\d,]+\.\d{2})$"
    )

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def parse(self, file_path: str, text_content: str = "") -> PaytmParseResult:
        transactions: List[PaytmTransaction] = []
        opening_balance: Optional[float] = None
        closing_balance: Optional[float] = None

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                lines = [line.strip() for line in (page.extract_text() or "").splitlines() if line and line.strip()]
                page_transactions = self._parse_page(lines)
                transactions.extend(page_transactions)

        if text_content and opening_balance is None:
            summary_match = re.search(
                r"Rs\.\s*([-\d,]+\.\d{2})\s+Rs\.\s*([-\d,]+\.\d{2})\s+Rs\.\s*([-\d,]+\.\d{2})\s+Rs\.\s*([-\d,]+\.\d{2})\s+OPENING BALANCE TOTAL DEPOSIT TOTAL WITHDRAWAL CLOSING BALANCE",
                text_content,
                re.IGNORECASE | re.DOTALL,
            )
            if summary_match:
                opening_balance = self._parse_amount(summary_match.group(1))

        if not transactions:
            raise GenericParseError(
                "Could not extract transactions from this Paytm PDF.",
                error_code="NO_TRANSACTIONS",
                details={"file": file_path},
            )

        if opening_balance is None:
            opening_balance = self._infer_opening(transactions[0])
        closing_balance = transactions[-1].balance
        total_credits = sum(txn.credit or 0 for txn in transactions)
        total_debits = sum(txn.debit or 0 for txn in transactions)
        return PaytmParseResult(
            transactions=transactions,
            total_count=len(transactions),
            parse_method="block_text",
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            total_credits=total_credits,
            total_debits=total_debits,
        )

    def _parse_page(self, lines: List[str]) -> List[PaytmTransaction]:
        transactions: List[PaytmTransaction] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if self._is_skip_line(line):
                i += 1
                continue

            header = self.HEADER_RE.match(line)
            if not header:
                i += 1
                continue

            block = [line]
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                if self.HEADER_RE.match(next_line) or self._is_skip_line(next_line):
                    break
                block.append(next_line)
                j += 1

            txn = self._build_transaction(header, block[1:])
            if txn:
                transactions.append(txn)
            i = j

        return transactions

    def _build_transaction(self, header: re.Match[str], detail_lines: List[str]) -> Optional[PaytmTransaction]:
        amount = self._parse_amount(header.group("amount"))
        balance = self._parse_amount(header.group("balance"))
        if amount is None or balance is None:
            return None

        sign = header.group("sign")
        title = header.group("title").strip()
        cleaned_detail = [line.strip() for line in detail_lines if line.strip()]
        description = self._build_description(title, cleaned_detail)
        ref_no = self._extract_reference(cleaned_detail)

        debit = amount if sign == "-" else None
        credit = amount if sign == "+" else None

        return PaytmTransaction(
            date=datetime.strptime(header.group("date"), "%d %b %Y").strftime("%Y-%m-%d"),
            description=description,
            ref_no=ref_no,
            debit=debit,
            credit=credit,
            balance=balance,
        )

    def _build_description(self, title: str, detail_lines: List[str]) -> str:
        informative = []
        for line in detail_lines:
            if re.match(r"^\d{1,2}:\d{2} [AP]M$", line):
                continue
            if line.startswith("Transaction ID") or line.startswith("Reference Number") or line.startswith("Reference No") or line.startswith("UPI Reference No") or line.startswith("Mandate Ref. No"):
                continue
            if line.startswith("From Account Number"):
                continue
            informative.append(line)

        description = " | ".join([title, *informative]) if informative else title
        description = re.sub(r"\s+", " ", description).strip()
        return description

    def _extract_reference(self, detail_lines: List[str]) -> str:
        patterns = [
            r"Transaction ID\s*:?\s*([A-Z0-9]+)",
            r"Reference Number:\s*([A-Z0-9]+)",
            r"Reference No\s*:?\s*([A-Za-z0-9]+)",
            r"UPI Reference No\s*:?\s*([A-Za-z0-9]+)",
            r"Mandate Ref\. No\s+([A-Za-z0-9]+)",
        ]
        for line in detail_lines:
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    return match.group(1)[:120]
        return ""

    def _infer_opening(self, txn: PaytmTransaction) -> Optional[float]:
        if txn.credit:
            return round(txn.balance - txn.credit, 2)
        if txn.debit:
            return round(txn.balance + txn.debit, 2)
        return None

    def _is_skip_line(self, line: str) -> bool:
        upper = line.upper().strip()
        skip_tokens = (
            "ACCOUNT STATEMENT FOR:",
            "OPENING BALANCE TOTAL DEPOSIT TOTAL WITHDRAWAL CLOSING BALANCE",
            "ACCOUNT NUMBER ACCOUNT TYPE IFSC MICR NOMINEE",
            "NEVER SHARE",
            "DETAILS CAN LEAD",
            "DATE & TIME TRANSACTION DETAILS AMOUNT AVAILABLE BALANCE",
            "THIS STATEMENT CONTAINS TRANSACTIONS UPTO",
            "TO VIEW TERMS & CONDITIONS",
            "EACH DEPOSITOR IS INSURED",
            "HELD BY HIM/HER",
            "NEED HELP?",
            "**** THIS IS COMPUTER GENERATED",
            "GSTIN -",
            "PPBL NOIDA BRANCH",
        )
        return any(token in upper for token in skip_tokens)

    def _parse_amount(self, value: str) -> Optional[float]:
        try:
            return float(value.replace(",", "").strip())
        except Exception:
            return None


# Re-export for compatibility
PaytmParseError = GenericParseError
