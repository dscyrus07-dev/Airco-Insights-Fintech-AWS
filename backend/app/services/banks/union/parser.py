from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pdfplumber

from app.services.banks._shared.generic_bank import GenericParseError


UnionParseError = GenericParseError


@dataclass
class UnionTransaction:
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
class UnionParseResult:
    transactions: List[UnionTransaction]
    total_count: int
    parse_method: str
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    total_credits: float = 0.0
    total_debits: float = 0.0


class UnionParser:
    FULL_ROW_RE = re.compile(
        r"^(?P<serial>\d+)\s+"
        r"(?P<date>\d{2}/\d{2}/\d{4})\s+"
        r"(?P<rest>.+?)\s+"
        r"(?P<amount>[\d,]+\.\d{2})\s+\((?P<amount_marker>Dr|Cr)\)\s+"
        r"(?P<balance>[\d,]+\.\d{2})\s+\((?P<balance_marker>Dr|Cr)\)$"
    )
    HISTORY_ROW_RE = re.compile(
        r"^(?P<date>\d{2}-\d{2}-\d{4})\s+"
        r"(?P<rest>.+?)\s+"
        r"(?P<amount>[\d,]+\.\d{2})\s+"
        r"(?P<balance>[\d,]+\.\d{2})$"
    )

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def parse(self, file_path: str, text_content: str = "") -> UnionParseResult:
        transactions: List[UnionTransaction] = []
        prev_balance: Optional[float] = None

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                lines = [line.strip() for line in (page.extract_text() or "").splitlines() if line and line.strip()]
                page_transactions, prev_balance = self._parse_lines(lines, prev_balance)
                transactions.extend(page_transactions)

        if not transactions:
            raise GenericParseError(
                "Could not extract transactions from this Union Bank PDF.",
                error_code="NO_TRANSACTIONS",
                details={"file": file_path},
            )

        transactions = self._normalize_order(transactions)
        opening_balance = self._infer_opening(transactions[0])
        closing_balance = transactions[-1].balance if transactions else None
        total_credits = sum(txn.credit or 0 for txn in transactions)
        total_debits = sum(txn.debit or 0 for txn in transactions)

        return UnionParseResult(
            transactions=transactions,
            total_count=len(transactions),
            parse_method="text",
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            total_credits=total_credits,
            total_debits=total_debits,
        )

    def _parse_lines(self, lines: List[str], prev_balance: Optional[float]) -> Tuple[List[UnionTransaction], Optional[float]]:
        transactions: List[UnionTransaction] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if self._is_skip_line(line):
                i += 1
                continue

            row_match = self.FULL_ROW_RE.match(line)
            mode = "full"
            if not row_match:
                row_match = self.HISTORY_ROW_RE.match(line)
                mode = "history"

            if row_match:
                suffix_lines: List[str] = []
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    if self.FULL_ROW_RE.match(next_line) or self.HISTORY_ROW_RE.match(next_line) or self._is_skip_line(next_line):
                        break
                    suffix_lines.append(next_line)
                    j += 1

                txn, prev_balance = self._build_transaction(row_match, suffix_lines, prev_balance, mode)
                if txn:
                    transactions.append(txn)
                i = j
                continue
            i += 1

        return transactions, prev_balance

    def _build_transaction(
        self,
        row_match: re.Match[str],
        suffix_lines: List[str],
        prev_balance: Optional[float],
        mode: str,
    ) -> Tuple[Optional[UnionTransaction], Optional[float]]:
        amount = self._parse_amount(row_match.group("amount"))
        balance = self._parse_amount(row_match.group("balance"))
        if amount is None or balance is None:
            return None, prev_balance

        balance_marker = row_match.groupdict().get("balance_marker")
        if balance_marker and balance_marker.upper() == "DR":
            balance = -abs(balance)

        raw_rest = row_match.group("rest")
        description = self._build_description(raw_rest, suffix_lines, mode)
        ref_no = self._extract_reference(description, raw_rest)
        debit, credit = self._infer_direction(
            description=description,
            amount=amount,
            prev_balance=prev_balance,
            current_balance=balance,
            amount_marker=row_match.groupdict().get("amount_marker"),
            raw_rest=raw_rest,
        )

        txn = UnionTransaction(
            date=self._normalize_date(row_match.group("date")),
            description=description,
            ref_no=ref_no,
            debit=debit,
            credit=credit,
            balance=balance,
        )
        return txn, balance

    def _build_description(self, raw_rest: str, suffix_lines: List[str], mode: str) -> str:
        text = raw_rest.strip()
        if mode == "full":
            text = re.sub(r"^S\d+\s+", "", text)
        else:
            text = re.sub(r"\s+S\d+\s+(?:-|\w+)?\s*$", "", text)
            text = re.sub(r"\s+S\d+\s+", " ", text)
        text = re.sub(r"\s+-\s*$", "", text).strip()
        suffix = " ".join(line.strip() for line in suffix_lines if line.strip())
        combined = " ".join(part for part in [text, suffix] if part).strip()
        combined = re.sub(r"\s+", " ", combined)
        return self._clean_multiline(combined)

    def _infer_direction(
        self,
        description: str,
        amount: float,
        prev_balance: Optional[float],
        current_balance: float,
        amount_marker: Optional[str],
        raw_rest: str,
    ) -> Tuple[Optional[float], Optional[float]]:
        amount_abs = abs(amount)
        desc_upper = description.upper()
        raw_upper = raw_rest.upper()

        if amount_marker:
            return (amount_abs, None) if amount_marker.upper() == "DR" else (None, amount_abs)

        if prev_balance is not None:
            delta = round(current_balance - prev_balance, 2)
            if abs(delta - amount_abs) <= 1.0:
                return None, amount_abs
            if abs(delta + amount_abs) <= 1.0:
                return amount_abs, None

        credit_markers = ("UPIAB/", "IMPSAB/", "MOBFT FROM:", "NEFT:", "/CR/", "INT.", "POSITIVE PAY")
        debit_markers = ("UPIAR/", "NACH/", "EMANCH/", "MOBFT TO:", "/DR/", "POS:", "RTNCHG", "SMS CHARGES")
        if any(marker in raw_upper or marker in desc_upper for marker in credit_markers):
            return None, amount_abs
        if any(marker in raw_upper or marker in desc_upper for marker in debit_markers):
            return amount_abs, None

        return amount_abs, None

    def _extract_reference(self, description: str, raw_rest: str) -> str:
        txn_match = re.search(r"\b(S\d{6,10})\b", raw_rest)
        if txn_match:
            return txn_match.group(1)
        patterns = [
            r"\b(UPI[ABR]{1,2}/[0-9/]+)",
            r"\b(IMPSAB/[0-9]+)",
            r"\b(NACH/[0-9/]+)",
            r"\b(EMANCH/[0-9/\-A-Z]+)",
            r"\b(MOBFT (?:to|from): [^/]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(1)[:120]
        return ""

    def _clean_multiline(self, text: str) -> str:
        cleaned = text
        replacements = [
            (r"gundojisravant", "gundojisravant"),
            (r"cf\.\s*trillionloa", "cf.trillionloa"),
            (r"paytm-\s*(\d+)", r"paytm-\1"),
            (r"BHARATPE\.\s*(\d+)", r"BHARATPE.\1"),
            (r"/CR/\s*", "/CR/"),
            (r"/DR/\s*", "/DR/"),
            (r"\s+@\s*", "@"),
            (r"\s+/\s*", "/"),
            (r"\s+-\s+", "-"),
        ]
        for pattern, target in replacements:
            cleaned = re.sub(pattern, target, cleaned, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", cleaned).strip()

    def _infer_opening(self, txn: UnionTransaction) -> Optional[float]:
        if txn.credit:
            return round(txn.balance - txn.credit, 2)
        if txn.debit:
            return round(txn.balance + txn.debit, 2)
        return None

    def _normalize_order(self, transactions: List[UnionTransaction]) -> List[UnionTransaction]:
        if len(transactions) < 2:
            return transactions
        return list(reversed(transactions)) if transactions[0].date > transactions[-1].date else transactions

    def _normalize_date(self, date_text: str) -> str:
        fmt = "%d/%m/%Y" if "/" in date_text else "%d-%m-%Y"
        return datetime.strptime(date_text, fmt).strftime("%Y-%m-%d")

    def _parse_amount(self, value: str) -> Optional[float]:
        try:
            return float(value.replace(",", "").strip())
        except Exception:
            return None

    def _is_skip_line(self, line: str) -> bool:
        upper = line.upper().strip()
        if not upper:
            return True
        exact_or_contains_tokens = (
            "SCAN THE QR CODE", "DETAILS OF STATEMENT", "TO DOWNLOAD VYOM ON", "STATEMENT OF ACCOUNT",
            "UNION BANK OF INDIA", "E-MAIL", "EMAIL ID", "STATEMENT DATE", "STATEMENT PERIOD",
            "RECORDS FROM ", "S.NO DATE TRANSACTION ID REMARKS AMOUNT(RS.) BALANCE(RS.)",
            "DATE REMARKS TRAN ID-1 UTR NUMBER INSTR. ID WITHDRAWALS DEPOSITS BALANCE",
            "NNEEFFTT", "RRTTGGSS", "BBBBPPSS", "HTTP", "FOR ANY QUERIES",
            "THIS IS A SYSTEM GENERATED OUTPUT", "TO AVAIL OUR LOAN PRODUCTS", "PAGE NO",
        )
        if any(token in upper for token in exact_or_contains_tokens):
            return True

        metadata_prefixes = ("NAME ", "ADDRESS ", "CITY ", "STATE ", "COUNTRY ", "ZIP ", "MOBILE NO", "HOME BRANCH")
        return upper.startswith(metadata_prefixes)

