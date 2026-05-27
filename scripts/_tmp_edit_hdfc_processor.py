from pathlib import Path

path = Path(r"x:\FinTech SAAS\Airco Insights Fintech\backend\app\services\banks\hdfc\processor.py")
lines = path.read_text(encoding="utf-8").splitlines()
lines = [line for line in lines if line.strip()]
path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
print("normalized")
