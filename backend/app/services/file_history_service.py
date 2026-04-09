from datetime import datetime
from typing import Any, Dict

from ..database.models import UserFileRecord
from ..database.session import SessionLocal


class FileHistoryService:
    def upsert_upload(self, *, job_id: str, user_id: str, user_email: str | None, user_name: str | None,
                      full_name: str | None, account_type: str | None, bank_name: str | None,
                      mode: str | None, original_filename: str, upload_object_key: str | None) -> None:
        db = SessionLocal()
        try:
            record = db.query(UserFileRecord).filter(UserFileRecord.job_id == job_id).first()
            if record is None:
                record = UserFileRecord(job_id=job_id, user_id=user_id, original_filename=original_filename)
                db.add(record)

            record.user_email = user_email
            record.user_name = user_name
            record.full_name = full_name
            record.account_type = account_type
            record.bank_name = bank_name
            record.mode = mode
            record.original_filename = original_filename
            record.upload_object_key = upload_object_key
            record.status = "uploaded"
            db.commit()
        finally:
            db.close()

    def mark_running(self, job_id: str) -> None:
        db = SessionLocal()
        try:
            record = db.query(UserFileRecord).filter(UserFileRecord.job_id == job_id).first()
            if record:
                record.status = "running"
                db.commit()
        finally:
            db.close()

    def mark_completed(self, job_id: str, result_data: Dict[str, Any]) -> None:
        db = SessionLocal()
        try:
            record = db.query(UserFileRecord).filter(UserFileRecord.job_id == job_id).first()
            if not record:
                return

            record.status = "completed"
            record.completed_at = datetime.utcnow()
            record.report_object_key = result_data.get("excel_object_key")
            record.report_filename = result_data.get("excel_path", "").split("/")[-1] or None
            stats = result_data.get("stats") or {}
            total_transactions = stats.get("total_transactions")
            record.total_transactions = int(total_transactions) if total_transactions is not None else None
            record.error_message = None
            db.commit()
        finally:
            db.close()

    def mark_failed(self, job_id: str, error_message: str | None) -> None:
        db = SessionLocal()
        try:
            record = db.query(UserFileRecord).filter(UserFileRecord.job_id == job_id).first()
            if record:
                record.status = "failed"
                record.error_message = error_message
                db.commit()
        finally:
            db.close()

    def list_for_user(self, user_id: str) -> dict:
        db = SessionLocal()
        try:
            records = (
                db.query(UserFileRecord)
                .filter(UserFileRecord.user_id == user_id)
                .order_by(UserFileRecord.created_at.desc())
                .all()
            )

            uploads = []
            reports = []
            processed_count = 0

            for record in records:
                created_at = record.created_at.isoformat() if record.created_at else None
                if record.status == "completed":
                    processed_count += 1

                uploads.append({
                    "job_id": record.job_id,
                    "name": record.original_filename,
                    "bank_name": record.bank_name,
                    "account_type": record.account_type,
                    "mode": record.mode,
                    "status": record.status,
                    "created_at": created_at,
                    "upload_object_key": record.upload_object_key,
                    "total_transactions": record.total_transactions,
                })

                if record.status == "completed":
                    reports.append({
                        "job_id": record.job_id,
                        "name": record.report_filename or record.original_filename,
                        "bank_name": record.bank_name,
                        "created_at": created_at,
                        "report_object_key": record.report_object_key,
                    })

            latest = records[0] if records else None
            return {
                "summary": {
                    "total_uploads": len(records),
                    "processed_files": processed_count,
                    "generated_reports": len(reports),
                    "latest_account_type": latest.account_type if latest else None,
                },
                "uploads": uploads,
                "reports": reports,
            }
        finally:
            db.close()


file_history_service = FileHistoryService()
