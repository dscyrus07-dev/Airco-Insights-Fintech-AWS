# Airco Insights FinTech - System Architecture

## System Design Overview

### Microservices Architecture Pattern
Airco Insights follows a **microservices architecture** with **event-driven processing** for scalable bank statement analysis. The system is designed for horizontal scaling, fault isolation, and independent service deployment.

### Core Architecture Principles
- **Service Isolation**: Each service has a single responsibility
- **Event-Driven Communication**: RabbitMQ for async service coordination
- **Stateless Services**: All services are stateless with external state management
- **Backward Compatibility**: Monolith remains functional during migration
- **Correlation Tracking**: End-to-end request tracing across services

## High-Level Architecture Diagram

```
                    Frontend Layer
                (Next.js + TypeScript)
                         |
                    API Gateway
                         |
                Backend Monolith
                 (FastAPI - Legacy)
                         |
            +-------------+-------------+
            |             |             |
      Auth Service   File Service   PDF Service
        (8001)         (8002)        (8003)
            |             |             |
            +-------------+-------------+
                         |
            +-------------+-------------+
            |             |             |
      AI Service    Report Service  Legacy APIs
        (8004)         (8005)        (8000)
            |             |
            +-------------+
                         |
                Infrastructure Layer
        Redis + RabbitMQ + MinIO + PostgreSQL
```

## Data Flow Architecture

### Primary Processing Pipeline
1. **File Upload** (Frontend) 
   - User uploads PDF bank statement
   - File validation and metadata extraction
   - Storage in MinIO with unique identifier

2. **PDF Processing** (PDF Service)
   - Bank-specific PDF parsing
   - Transaction extraction and validation
   - Structured data normalization

3. **AI Analysis** (AI Service)
   - Transaction categorization using ML models
   - Confidence scoring and fallback logic
   - Learning feedback collection

4. **Report Generation** (Report Service)
   - Bank-specific Excel report formatting
   - Multi-sheet report generation
   - Secure storage and download links

### Event-Driven Communication Flow
```
File Upload Event
    |
    v
PDF Processing Request
    |
    v
PDF Processed Event
    |
    v
AI Analysis Request
    |
    v
AI Analysis Complete Event
    |
    v
Report Generation Request
    |
    v
Report Generated Event
```

## Service Architecture Details

### Auth Service (Port 8001)
**Responsibility**: User authentication and authorization
- JWT token generation and validation
- User registration and profile management
- Role-based access control (user/admin)
- Token refresh mechanism
- Keycloak integration (optional)

**Key Components**:
- Authentication middleware
- JWT utilities
- User model and repository
- Keycloak client integration

### File Service (Port 8002)
**Responsibility**: File upload, validation, and storage
- Multi-format file validation
- MinIO S3-compatible storage
- File metadata management
- Presigned URL generation for downloads
- File status tracking

**Key Components**:
- File upload handlers
- Storage abstraction layer
- File validation engine
- Metadata repository

### PDF Service (Port 8003)
**Responsibility**: Bank-specific PDF parsing and transaction extraction
- HDFC processor (fully implemented)
- Axis, ICICI, Kotak, SBI processors (placeholders)
- Transaction validation and normalization
- PDF integrity checking
- Error handling and recovery

**Key Components**:
- Bank processor factory
- Transaction extraction engine
- Validation framework
- Error handling system

### AI Service (Port 8004)
**Responsibility**: Transaction categorization and analysis
- Multiple AI providers (Groq, Claude)
- Transaction categorization with confidence scores
- Batch processing capabilities
- Learning feedback system
- Fallback to rule-based categorization

**Key Components**:
- AI provider abstraction
- Categorization engine
- Confidence scoring
- Learning feedback loop

### Report Service (Port 8005)
**Responsibility**: Excel report generation and formatting
- Bank-specific report generators
- Multi-sheet Excel report creation
- Template-based report formatting
- Secure report storage
- Download link generation

**Key Components**:
- Report generator factory
- Excel template engine
- Storage integration
- Download management

## Infrastructure Architecture

### Data Storage Strategy
```
PostgreSQL (Primary Data)
    |
    +-- Users, Authentication
    +-- Job Tracking
    +-- Application Metadata
    |
Redis (Cache & Session)
    |
    +-- Job Status Cache
    +-- Session Storage
    +-- Analysis Results Cache
    |
MinIO (Object Storage)
    |
    +-- Uploaded Files (airco-files)
    +-- Generated Reports (airco-reports)
    +-- Temporary Processing Files
```

### Message Queue Architecture
```
RabbitMQ Event Bus
    |
    +-- file.uploaded (File Service)
    +-- pdf.processed (PDF Service)
    +-- ai.analyzed (AI Service)
    +-- report.generated (Report Service)
    |
    +-- Error Handling Queues
    +-- Retry Logic Queues
    +-- Dead Letter Queues
```

### Service Communication Patterns

#### Synchronous Communication
- Frontend to Backend APIs
- Health checks and status endpoints
- Configuration and metadata queries

#### Asynchronous Communication
- File processing pipeline events
- Service-to-service notifications
- Error handling and retry logic

#### Request-Response Pattern
- API calls with immediate responses
- Authentication token validation
- Configuration and status queries

#### Event-Driven Pattern
- File upload processing pipeline
- Service coordination events
- Error handling and recovery

## Folder Structure Architecture

```
Airco Insights Fintech/
|
+-- backend/                    # Legacy Monolith
|   +-- app/
|   |   +-- api/               # API Routes (HDFC-specific)
|   |   +-- core/              # Configuration & Security
|   |   +-- database/          # Database Models & Session
|   |   +-- services/          # Business Logic
|   |   |   +-- banks/         # Bank-specific processors
|   |   |   +-- intelligence/  # AI integration
|   |   |   +-- core/          # Core services
|   |   +-- utils/             # Utilities
|   +-- tests/                 # Test Suite
|   +-- scripts/               # Analysis & Debug Scripts
|
+-- services/                  # Microservices
|   +-- auth-service/          # Authentication Service
|   +-- file-service/          # File Management Service
|   +-- pdf-service/           # PDF Processing Service
|   +-- ai-service/            # AI Analysis Service
|   +-- report-service/        # Report Generation Service
|
+-- frontend/                   # Next.js Frontend
|   +-- app/                   # App Router Pages
|   +-- components/            # React Components
|   +-- lib/                   # Utilities & API Clients
|   +-- contexts/              # React Contexts
|   +-- types/                 # TypeScript Types
|
+-- database/                   # Database Configuration
|   +-- migrations/            # Database Migrations
|   +-- docker/                # PostgreSQL Config
|
+-- nginx/                      # Reverse Proxy Configuration
+-- scripts/                    # Deployment Scripts
+-- Docs/                       # Documentation
```

## Security Architecture

### Authentication Flow
```
Frontend Application
        |
        v
Keycloak SSO (Optional)
        |
        v
Auth Service (JWT)
        |
        v
Service-to-Service Auth
        |
        v
Resource Access
```

### Data Security
- **Encryption in Transit**: TLS for all service communication
- **Encryption at Rest**: MinIO and PostgreSQL encryption
- **API Security**: JWT-based authentication with role-based access
- **File Security**: Presigned URLs with expiration
- **Audit Logging**: Comprehensive access logging

### Access Control
- **User Roles**: user, admin with specific permissions
- **Service Authentication**: Internal service-to-service auth
- **API Rate Limiting**: Prevent abuse and ensure stability
- **Data Isolation**: Tenant-specific data separation

## Performance Architecture

### Caching Strategy
```
Application Layer
    |
    v
Redis Cache
    |
    +-- Job Status Cache
    +-- Analysis Results Cache
    +-- Session Cache
    +-- API Response Cache
```

### Scalability Design
- **Horizontal Scaling**: Each service can scale independently
- **Load Balancing**: Service-level load distribution
- **Resource Optimization**: Right-sized service containers
- **Async Processing**: Non-blocking request handling

### Performance Optimization
- **Connection Pooling**: Database and external API connections
- **Batch Processing**: Efficient handling of large datasets
- **Lazy Loading**: On-demand resource loading
- **Compression**: Response compression for API calls

## Monitoring & Observability

### Health Check Architecture
```
Service Health Checks
    |
    v
Infrastructure Monitoring
    |
    +-- Service Status
    +-- Resource Usage
    +-- Queue Depths
    +-- Storage Usage
```

### Logging Strategy
- **Structured Logging**: JSON format with correlation IDs
- **Log Aggregation**: Centralized log collection
- **Error Tracking**: Comprehensive error logging
- **Performance Metrics**: Request timing and throughput

### Distributed Tracing
- **Correlation IDs**: End-to-end request tracking
- **Service Dependencies**: Service interaction mapping
- **Performance Bottlenecks**: Identification of slow operations
- **Error Propagation**: Error flow across services

## Deployment Architecture

### Container Strategy
```
Docker Containers
    |
    +-- Service Containers (6 services)
    +-- Infrastructure Containers (Redis, RabbitMQ, MinIO, PostgreSQL)
    +-- Frontend Container (Next.js)
    +-- Reverse Proxy (Nginx)
```

### Environment Configuration
- **Development**: Local Docker Compose setup
- **Staging**: Pre-production environment
- **Production**: Multi-container orchestration
- **Configuration Management**: Environment-based configuration

### Deployment Pipeline
```
Code Repository
    |
    v
Build & Test
    |
    v
Docker Image Build
    |
    v
Container Deployment
    |
    v
Health Validation
    |
    v
Production Traffic
```

## Evolution Strategy

### Migration Path
1. **Phase 0**: Monolith stabilization with correlation IDs
2. **Phase 1**: Authentication service extraction
3. **Phase 2**: File processing services
4. **Phase 3**: Core processing services
5. **Phase 4**: API Gateway and advanced monitoring

### Future Enhancements
- **API Gateway**: Centralized routing and authentication
- **Service Discovery**: Dynamic service registration
- **Circuit Breakers**: Fault tolerance patterns
- **Advanced Monitoring**: Prometheus + Grafana
- **Auto-scaling**: Kubernetes integration
