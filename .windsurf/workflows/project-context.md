# Airco Insights FinTech - Project Context

## Purpose
Airco Insights is a FinTech SaaS platform that automates bank statement analysis and financial insights generation. The system processes PDF bank statements from multiple banks (HDFC, Axis, ICICI, Kotak, SBI), extracts transactions, categorizes them using AI, and generates comprehensive Excel reports.

## Tech Stack

### Backend (Python/FastAPI)
- **Framework**: FastAPI 0.109.0 with async support
- **Database**: PostgreSQL 15 with SQLAlchemy 2.0.25 ORM
- **Cache**: Redis 7 for job persistence and caching
- **Message Queue**: RabbitMQ for event-driven processing
- **Storage**: MinIO S3-compatible object storage
- **AI Services**: 
  - Groq (LLaMA models) for fast inference
  - Anthropic Claude for advanced analysis
- **PDF Processing**: pdfplumber, PyMuPDF, pikepdf
- **Authentication**: JWT with optional Keycloak integration
- **File Processing**: OpenPyXL, XlsxWriter for Excel generation

### Frontend (Next.js/TypeScript)
- **Framework**: Next.js 14 with App Router
- **UI**: TailwindCSS 3.4.1 with Lucide React icons
- **TypeScript**: Full type safety throughout
- **Authentication**: Keycloak SSO integration
- **State Management**: React Context API

### Microservices Architecture
- **Auth Service** (8001): User authentication and JWT management
- **File Service** (8002): File upload, validation, storage
- **PDF Service** (8003): Bank-specific PDF parsing and transaction extraction
- **AI Service** (8004): Transaction categorization and analysis
- **Report Service** (8005): Excel report generation with bank-specific formatting

### Infrastructure
- **Containerization**: Docker with Docker Compose orchestration
- **Database**: PostgreSQL (app + Keycloak)
- **Caching**: Redis for session and job management
- **Message Broker**: RabbitMQ for async processing
- **Storage**: MinIO S3-compatible storage
- **Authentication**: Keycloak for enterprise SSO

## Key Modules

### Core Processing Pipeline
1. **File Upload** (File Service) - PDF validation and storage
2. **PDF Processing** (PDF Service) - Bank-specific transaction extraction
3. **AI Analysis** (AI Service) - Transaction categorization with confidence scores
4. **Report Generation** (Report Service) - Multi-sheet Excel reports

### Bank-Specific Processors
- **HDFC**: Fully implemented with 6-sheet report format
- **Axis, ICICI, Kotak, SBI**: Placeholder implementations ready for development

### Data Models
- **Job**: Processing job tracking with status and results
- **Transaction**: Extracted financial transaction with metadata
- **User**: Authentication and profile management
- **File**: File metadata and processing status

### API Structure
- **RESTful APIs**: Clean endpoint design with proper HTTP methods
- **Async Processing**: Job-based architecture with status tracking
- **Event-Driven**: RabbitMQ events for service communication
- **Correlation IDs**: End-to-end request tracing

## Dependencies

### External Services
- **AI Providers**: Groq API, Anthropic Claude API
- **Storage**: MinIO S3-compatible storage
- **Authentication**: Keycloak SSO (optional)
- **Database**: PostgreSQL with connection pooling

### Key Libraries
- **FastAPI**: Modern async web framework
- **SQLAlchemy**: Advanced ORM with async support
- **Redis**: High-performance caching
- **RabbitMQ**: Reliable message queuing
- **PDF Libraries**: Multiple PDF processing engines for robustness

## Problem Areas

### Current Challenges
- **Bank-Specific Logic**: Each bank requires custom PDF parsing logic
- **AI Accuracy**: Transaction categorization confidence varies by bank format
- **Performance**: Large PDF processing can be resource-intensive
- **Data Consistency**: Ensuring transaction accuracy across different bank formats

### Technical Debt
- **Monolithic Legacy**: Some components still in main backend
- **Error Handling**: Need more robust error recovery mechanisms
- **Testing**: Limited automated test coverage for bank-specific logic
- **Documentation**: API documentation needs improvement

## Business Context
- **Target Market**: Small to medium businesses needing financial insights
- **Value Proposition**: Automated bank statement analysis with AI-powered categorization
- **Competitive Advantage**: Multi-bank support with customizable reporting
- **Scalability**: Microservices architecture for enterprise deployment

## Development Status
- **Phase 0**: Monolith stabilization with correlation IDs and async processing
- **Phase 1**: Authentication service extraction
- **Phase 2**: File processing and storage services
- **Phase 3**: Core processing services (PDF, AI, Report)
- **Current**: Production-ready microservices with backward compatibility
