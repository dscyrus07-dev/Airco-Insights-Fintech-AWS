from datetime import datetime
from typing import Any, Dict

from ..database.models import UserFileRecord
from ..database.session import SessionLocal


class FileHistoryService:
    def upsert_upload(self, *, job_id: str, user_id: str, user_email: str | None, user_name: str | None,
                      full_name: str | None, account_type: str | None, bank_name: str | None,
                      batch_id: str | None, statement_label: str | None,
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
            record.batch_id = batch_id
            record.statement_label = statement_label
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
            batch_groups: dict[str, dict] = {}

            for record in records:
                created_at = record.created_at.isoformat() if record.created_at else None
                if record.status == "completed":
                    processed_count += 1

                batch_key = record.batch_id or record.job_id
                batch_group = batch_groups.setdefault(
                    batch_key,
                    {
                        "batch_id": record.batch_id or record.job_id,
                        "created_at": created_at,
                        "updated_at": created_at,
                        "bank_names": [],
                        "statement_count": 0,
                        "processed_count": 0,
                        "failed_count": 0,
                        "uploads": [],
                        "reports": [],
                        "bank_groups": {},
                    },
                )

                if created_at and (batch_group["created_at"] is None or created_at < batch_group["created_at"]):
                    batch_group["created_at"] = created_at
                if created_at and (batch_group["updated_at"] is None or created_at > batch_group["updated_at"]):
                    batch_group["updated_at"] = created_at

                if record.bank_name and record.bank_name not in batch_group["bank_names"]:
                    batch_group["bank_names"].append(record.bank_name)

                batch_group["statement_count"] += 1
                if record.status == "completed":
                    batch_group["processed_count"] += 1
                elif record.status == "failed":
                    batch_group["failed_count"] += 1

                upload_entry = {
                    "job_id": record.job_id,
                    "name": record.original_filename,
                    "bank_name": record.bank_name,
                    "account_type": record.account_type,
                    "mode": record.mode,
                    "batch_id": record.batch_id,
                    "statement_label": record.statement_label,
                    "status": record.status,
                    "created_at": created_at,
                    "upload_object_key": record.upload_object_key,
                    "total_transactions": record.total_transactions,
                }
                uploads.append(upload_entry)
                batch_group["uploads"].append(upload_entry)

                bank_key = record.bank_name or "Unknown"
                bank_group = batch_group["bank_groups"].setdefault(
                    bank_key,
                    {
                        "bank_name": bank_key,
                        "statement_count": 0,
                        "processed_count": 0,
                        "failed_count": 0,
                        "uploads": [],
                        "reports": [],
                    },
                )
                bank_group["statement_count"] += 1
                if record.status == "completed":
                    bank_group["processed_count"] += 1
                elif record.status == "failed":
                    bank_group["failed_count"] += 1
                bank_group["uploads"].append(upload_entry)

                if record.status == "completed":
                    report_entry = {
                        "job_id": record.job_id,
                        "name": record.report_filename or record.original_filename,
                        "bank_name": record.bank_name,
                        "batch_id": record.batch_id,
                        "statement_label": record.statement_label,
                        "created_at": created_at,
                        "report_object_key": record.report_object_key,
                    }
                    reports.append(report_entry)
                    batch_group["reports"].append(report_entry)
                    bank_group["reports"].append(report_entry)

            latest = records[0] if records else None
            return {
                "summary": {
                    "total_uploads": len(records),
                    "processed_files": processed_count,
                    "generated_reports": len(reports),
                    "total_batches": len(batch_groups),
                    "latest_account_type": latest.account_type if latest else None,
                },
                "uploads": uploads,
                "reports": reports,
                "batches": [
                    {
                        **batch,
                        "bank_groups": list(batch["bank_groups"].values()),
                    }
                    for batch in batch_groups.values()
                ],
            }
        finally:
            db.close()

    def delete_file(self, user_id: str, job_id: str) -> bool:
        """Delete a file record for a user.
        
        Args:
            user_id: The user ID
            job_id: The job ID (file identifier)
            
        Returns:
            True if deleted successfully, False if not found
        """
        db = SessionLocal()
        try:
            record = db.query(UserFileRecord).filter(
                UserFileRecord.user_id == user_id,
                UserFileRecord.job_id == job_id
            ).first()
            
            if record is None:
                return False
            
            # TODO: Also delete files from storage (MinIO) if needed
            # For now, just delete the database record
            
            db.delete(record)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()


file_history_service = FileHistoryService()
