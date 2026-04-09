# API Contracts - Phase 0 Baseline

This document captures the current API contracts before microservices migration.

## Upload Endpoints

### POST /api/upload/bank-statement (Legacy)
**Description**: Synchronous PDF processing (will be deprecated)
**Request**:
- file: UploadFile (PDF)
- bank_name: str (required)
- full_name: str (optional)
- account_type: str (optional)

**Response**: FileResponse (Excel download)

### POST /api/upload/bank-statement-async (New)
**Description**: Asynchronous PDF processing
**Request**:
- file: UploadFile (PDF)
- bank_name: str (required)
- full_name: str (optional)
- account_type: str (optional)
- mode: str (default: "free")
- api_key: str (optional, for hybrid mode)
- user_id: str (optional)

**Response**:
```json
{
  "job_id": "uuid",
  "status": "submitted",
  "message": "Processing started. Check job status with /api/jobs/{job_id}"
}
```

## Job Management

### GET /api/jobs/{job_id}
**Response**: Job object with status, results, and metadata

### GET /api/jobs/
**Query Parameters**:
- user_id: str (optional)
- status: str (optional: pending, running, completed, failed, cancelled)

**Response**: List of Job objects

### DELETE /api/jobs/{job_id}
**Response**: {"message": "Job cancelled successfully"}

### GET /api/upload/download/{job_id}
**Response**: FileResponse (Excel download when job is complete)

## Sync Endpoint

### POST /api/sync
**Request**:
```json
{
  "sheets": {...},
  "learning_events": [...]
}
```

**Response**:
```json
{
  "status": "ok",
  "message": "Sync completed successfully",
  "learned_events": 0,
  "promoted_rules": []
}
```

## Feedback Endpoints

### POST /api/feedback/transaction
**Request**:
```json
{
  "transaction_id": "str",
  "corrected_category": "str",
  "user_id": "str",
  "method": "ui"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Correction saved. Learning features temporarily disabled.",
  "learning_stats": {...}
}
```

## Health Endpoint

### GET /health
**Response**:
```json
{
  "status": "ok",
  "engine": "airco-insights",
  "version": "1.0.0"
}
```

## Supported Banks

- HDFC
- Axis
- ICICI
- Kotak
- SBI

## File Constraints

- Type: PDF only
- Size: Max 20MB
- Processing modes: "free" or "hybrid"

## Correlation IDs

All requests support:
- Header: X-Correlation-ID
- Response header: X-Correlation-ID

## Error Format

```json
{
  "detail": "Error message"
}
```
