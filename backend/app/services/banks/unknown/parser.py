"""
Airco Insights - Unknown Bank Parser
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
class UnknownTransaction:
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
class UnknownParseResult:
    transactions: List[UnknownTransaction]
    total_count: int
    parse_method: str
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    total_credits: float = 0.0
    total_debits: float = 0.0


class UnknownParser:
    ROW_RE = re.compile(
        r"^(?P<date>\d{2}-[A-Za-z]{3}-\d{2})"
        r"(?P<rest>.+?)\s+"
        r"(?P<amount>[\d,]+\.\d{2})\s+"
        r"(?P<balance>[\d,]+\.\d{2})\((?P<marker>Cr|Dr)\)$"
    )

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def parse(self, file_path: str, text_content: str = "") -> UnknownParseResult:
        transactions: List[UnknownTransaction] = []
        in_account_section = False
        opening_balance: Optional[float] = None
        prev_balance: Optional[float] = None

        if text_content:
            opening_match = re.search(r"OpeningBalance\s+([-\d,]+\.\d{2})\([CD]r\)", text_content, re.IGNORECASE)
            if opening_match:
                opening_balance = self._parse_amount(opening_match.group(1))
                prev_balance = opening_balance

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                lines = [line.strip() for line in (page.extract_text() or "").splitlines() if line.strip()]
                for i, line in enumerate(lines):
                    if "StatementofBankingAccount" in line:
                        in_account_section = True
                    if not in_account_section:
                        continue
                    if "StatementSummary" in line or "Summary StatementofStandaloneTermDeposit" in line or "DetailedStatementofTermDeposit" in line:
                        in_account_section = False
                        continue
                    if self._is_skip_line(line):
                        continue

                    row = self.ROW_RE.match(line)
                    if row:
                        suffix_lines: List[str] = []
                        j = i + 1
                        while j < len(lines):
                            nxt = lines[j]
                            if self.ROW_RE.match(nxt) or self._is_skip_line(nxt) or "StatementSummary" in nxt or "Summary StatementofStandaloneTermDeposit" in nxt:
                                break
                            suffix_lines.append(nxt)
                            j += 1
                        txn, prev_balance = self._build_transaction(row, suffix_lines, prev_balance)
                        if txn:
                            transactions.append(txn)

        if not transactions:
            raise GenericParseError(
                "Could not extract transactions from this unknown-bank PDF.",
                error_code="NO_TRANSACTIONS",
                details={"file": file_path},
            )

        if opening_balance is None:
            opening_balance = self._infer_opening(transactions[0])
        closing_balance = transactions[-1].balance
        total_credits = sum(txn.credit or 0 for txn in transactions)
        total_debits = sum(txn.debit or 0 for txn in transactions)
        return UnknownParseResult(
            transactions=transactions,
            total_count=len(transactions),
            parse_method="targeted_text",
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            total_credits=total_credits,
            total_debits=total_debits,
        )

    def _build_transaction(
        self,
        row: re.Match[str],
        suffix_lines: List[str],
        prev_balance: Optional[float],
    ) -> Tuple[Optional[UnknownTransaction], Optional[float]]:
        date_text = row.group("date")
        rest = row.group("rest").strip()
        description = " ".join([rest, *suffix_lines]).strip()
        description = self._clean_description(description)

        amount = self._parse_amount(row.group("amount"))
        balance = self._parse_amount(row.group("balance"))
        if balance is None or amount is None:
            return None, prev_balance
        if row.group("marker").upper() == "DR":
            balance = -abs(balance)

        # Opening row stores amount in deposit slot; keep it out of transactions
        if description.upper().startswith("OPENINGBALANCE"):
            return None, prev_balance

        debit, credit = self._infer_direction(description, amount, prev_balance, balance)

        ref_match = re.search(r"\b((?:UPI|TBMS|IMPS)-[A-Z0-9-]+|UPI-[0-9]+|TBMS-[0-9]+|IMPS-[0-9]+)\b", description, re.IGNORECASE)
        ref_no = ref_match.group(1) if ref_match else ""

        txn = UnknownTransaction(
            date=datetime.strptime(date_text, "%d-%b-%y").strftime("%Y-%m-%d"),
            description=description,
            ref_no=ref_no,
            debit=debit,
            credit=credit,
            balance=balance,
        )
        return txn, balance

    def _clean_description(self, text: str) -> str:
        cleaned = text
        replacements = [
            (r"fromPh", "from PhonePe"),
            (r"StatementSummary.*$", ""),
            (r"\s+", " "),
        ]
        for pattern, target in replacements:
            cleaned = re.sub(pattern, target, cleaned, flags=re.IGNORECASE)
        return cleaned.strip()

    def _infer_opening(self, txn: UnknownTransaction) -> Optional[float]:
        if txn.credit:
            return round(txn.balance - txn.credit, 2)
        if txn.debit:
            return round(txn.balance + txn.debit, 2)
        return None

    def _infer_direction(
        self,
        description: str,
        amount: float,
        prev_balance: Optional[float],
        balance: float,
    ) -> Tuple[Optional[float], Optional[float]]:
        desc_upper = description.upper()
        amount_abs = abs(amount)

        if prev_balance is not None:
            delta = round(balance - prev_balance, 2)
            if delta >= 0 and abs(delta - amount_abs) <= 1.0:
                return None, amount_abs
            if delta <= 0 and abs(delta + amount_abs) <= 1.0:
                return amount_abs, None

        credit_markers = ("TDINT:", "RECD:IMPS/", "PAYMENT FROM PHONEPE", "FROMPH")
        debit_markers = ("CHRG:", "REMCHRGS:", "UPI/")
        if any(token in desc_upper for token in credit_markers):
            return None, amount_abs
        if any(token in desc_upper for token in debit_markers):
            return amount_abs, None
        return amount_abs, None

    def _parse_amount(self, value: Optional[str]) -> Optional[float]:
        if not value:
            return None
        try:
            return float(value.replace(",", "").strip())
        except Exception:
            return None

    def _is_skip_line(self, line: str) -> bool:
        upper = line.upper().strip()
        skip_tokens = (
            "STATEMENTOFBANKINGACCOUNT",
            "DATE NARRATION CHQ/REF NO. WITHDRAWAL(DR) DEPOSIT(CR) BALANCE",
            "STATEMENTSUMMARY",
            "OPENINGBALANCE",
            "TOTALWITHDRAWALAMOUNT",
            "TOTALDEPOSITAMOUNT",
            "CLOSINGBALANCE",
            "SWEEPTDBALANCE",
            "ENDOFSTATEMENT",
            "THISISSYSTEMGENERATEDREPORT",
            "A1",
        )
        return any(token in upper for token in skip_tokens)


# Re-export for compatibility
UnknownParseError = GenericParseError
