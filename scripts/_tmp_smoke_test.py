import sys
from pathlib import Path
backend_root = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(backend_root))
from app.services.banks.hdfc.report_generator import generate_report

transactions = [
    {"date": "01/01/2024", "description": "SALARY CREDIT", "debit": 0, "credit": 50000, "balance": 50000, "category": "Salary", "confidence": 99, "recurring": "No"},
    {"date": "02/01/2024", "description": "ATM CASH WITHDRAWAL", "debit": 2000, "credit": 0, "balance": 48000, "category": "ATM Withdrawal", "confidence": 90, "recurring": "No"},
]
output = Path(r'x:\FinTech SAAS\Airco Insights Fintech\backend\_tmp_shared_report_test.xlsx')
result = generate_report(transactions=transactions, output_path=str(output), user_info={"name": "Test User", "account_no": "1234"})
print(f"transactions={result.get('total_transactions')} recurring={result.get('recurring_count')} file_exists={output.exists()}")
