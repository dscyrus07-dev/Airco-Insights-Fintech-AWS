---
description: Comprehensive workflow of the Airco Insights FinTech SaaS system
---

# Airco Insights System Workflow

## Overview
Airco Insights is a bank statement processing SaaS platform that transforms raw bank PDFs into structured, categorized Excel reports with financial intelligence.

## Architecture Components

### Frontend (Next.js)
- **Login/Authentication**: Keycloak-based authentication with secure access requests
- **Dashboard**: Multi-step form interface for statement processing
- **File Management**: Upload tracking, report generation history
- **Real-time Processing**: WebSocket-based job status updates

### Backend (FastAPI)
- **API Layer**: RESTful endpoints with async job processing
- **Bank Processors**: Modular, bank-specific processing engines
- **Pipeline Orchestrator**: Routes requests to appropriate bank processors
- **Task Queue**: Redis + RabbitMQ for background processing
- **Storage**: MinIO for file persistence (PDFs and Excel reports)

### Bank Processing Engines
Production-grade parsers for 4 major banks:
- **HDFC**: DD/MM/YY format, 7-sheet Excel reports
- **Axis**: DD-MM-YYYY format, auto-scaling column boundaries  
- **ICICI**: DD-MM-YYYY format, page-aware Y filtering
- **Kotak**: DD Mon YYYY format, row number handling

## Data Flow Pipeline

### 1. User Upload Flow
```
User Login
    |
User Details (Name, Account Type, Bank Selection)
    |
PDF Upload (with optional password)
    |
Mode Selection (Free/Hybrid)
    |
Async Processing Start
```

### 2. Backend Processing Pipeline
```
File Upload Validation
    |
Bank Router (pipeline_orchestrator.py)
    |
Bank-Specific Processor (HDFC/Axis/ICICI/Kotak)
    |
PDF Integrity Check
    |
Structure Validation
    |
Transaction Parsing (coordinate-based)
    |
Transaction Validation
    |
Balance Reconciliation
    |
Rule Engine Classification (500+ deterministic rules)
    |
AI Fallback (if hybrid mode)
    |
Recurring Detection
    |
Aggregation Engine
    |
Excel Generation (5-8 sheets)
    |
MinIO Storage
    |
Download URL Generation
```

### 3. Frontend Response Flow
```
Job ID Received
    |
Polling Status Updates
    |
Processing Complete
    |
Excel Download Available
    |
Report Preview (sheet-wise)
    |
File Management Dashboard
```

## Bank Processor Architecture

### HDFC Processor (Complete)
- **Parser**: Coordinate-based extraction with table/text fallback
- **Structure Validator**: HDFC-specific format detection
- **Transaction Validator**: Field validation and normalization
- **Reconciliation**: Balance verification with auto-correction
- **Rule Engine**: 500+ deterministic classification rules
- **AI Fallback**: Claude API integration for unclassified transactions
- **Recurring Engine**: Subscription/EMI/salary detection
- **Aggregation**: Financial analytics and summaries
- **Excel Generator**: 8-sheet professional reports

### Axis/ICICI/Kotak Processors
Similar modular architecture with bank-specific:
- Date format handling
- Column boundary detection
- Page filtering logic
- Opening balance extraction
- Transaction parsing methods

## API Endpoints

### Upload & Processing
- `POST /api/upload/bank-statement-async` - Main upload endpoint (returns job ID)
- `GET /api/jobs/{job_id}` - Job status polling
- `GET /api/upload/download/{job_id}` - Excel file download

### Supporting Endpoints
- `POST /api/upload/check-pdf` - Check if PDF is password-protected
- `POST /api/upload/unlock-pdf` - Unlock password-protected PDFs
- `GET /process/supported-banks` - List of supported banks
- `POST /process` - Legacy synchronous endpoint

### Frontend Routes
- `/` - Login/access request page
- `/dashboard` - Main processing interface
- `/api/upload` - Backend proxy for uploads

## Processing Modes

### Free Mode
- Coordinate-based parser only
- Deterministic rule engine classification
- 5-sheet Excel reports
- No AI, no API costs
- ~2-3 seconds processing time

### Hybrid Mode
- All Free Mode features
- Claude AI for unclassified transactions
- Higher classification coverage (85%+ vs 60%+)
- Additional API costs
- ~5-10 seconds processing time

## Storage Architecture

### MinIO Buckets
- `airco-files`: User-uploaded PDFs (scoped by user ID)
- `airco-reports`: Generated Excel reports (scoped by user ID)

### File Naming Convention
```
PDFs: users/{user_id}/uploads/{original_name}_{temp_id}
Reports: users/{user_id}/reports/{bank}_report_{uuid}.xlsx
```

## Error Handling

### Pipeline Errors
- **Validation Errors**: Invalid file format, missing required fields
- **Parsing Errors**: Scanned PDFs, corrupted files, unsupported formats
- **Bank Errors**: Unsupported bank, statement format mismatches
- **Processing Errors**: Balance reconciliation failures, system errors

### User-Friendly Messages
- SCANNED_PDF: "Please upload a text-based PDF from internet banking"
- NO_TRANSACTIONS: "Could not extract transactions from this statement"
- UNSUPPORTED_BANK: "Bank not yet supported"
- PASSWORD_PROTECTED: "PDF is password-protected"

## Performance Metrics

### Processing Benchmarks
- **HDFC**: 182 txns, 12 categories, ~7 seconds
- **ICICI**: 731 txns, 16 categories, ~8 seconds  
- **Kotak**: 675 txns, 9 categories, ~6 seconds
- **Axis**: Similar performance characteristics

### Classification Coverage
- **Rule Engine Only**: 60-70% coverage
- **Rule Engine + AI**: 85-95% coverage
- **Recurring Detection**: Salaries, EMIs, subscriptions
- **Balance Reconciliation**: 100% verification

## Security & Privacy

### Authentication
- Keycloak OAuth2 integration
- JWT token-based session management
- User-scoped file storage

### Data Protection
- No sensitive data logging
- Temporary file cleanup
- Encryption in transit (HTTPS)
- User data isolation

### Access Control
- Login request workflow (email/WhatsApp)
- Role-based access (future enhancement)
- Audit logging (future enhancement)

## Deployment Architecture

### Docker Containers
- `thearico/fintech-backend:latest` - FastAPI backend
- `thearico/fintech-frontend:latest` - Next.js frontend
- Production: `insights.theairco.ai` (Cloudflare proxy)

### Environment Configuration
- Development: `docker-compose.yml`
- Production: `docker-compose.prod.yml`
- Environment variables for API keys, database URLs

## Monitoring & Observability

### Logging
- Structured logging with correlation IDs
- Performance metrics at each pipeline step
- Error tracking with detailed context

### Health Checks
- `/health` endpoint for service status
- Database connectivity checks
- External service monitoring

## Future Enhancements

### Planned Features
- Additional bank processors (PNB, Bank of Baroda, SBI)
- Multi-statement batch processing
- Machine learning model training
- Advanced analytics dashboard
- API rate limiting and quotas

### Scalability Improvements
- Horizontal scaling with load balancers
- Distributed processing clusters
- Database sharding for user data
- CDN integration for file downloads

## Quality Assurance

### Testing Strategy
- Unit tests for individual modules
- Integration tests for bank processors
- End-to-end workflow testing
- Performance benchmarking

### Code Standards
- Type hints throughout
- Comprehensive error handling
- Modular architecture
- Clean separation of concerns

---

**Last Updated**: April 2026  
**Version**: 2.0.0  
**Maintainer**: Airco Insights Team
