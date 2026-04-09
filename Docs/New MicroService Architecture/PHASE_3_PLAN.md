# Phase 3 Plan - Core Processing Services Extraction

## Objective
Extract PDF Processing, AI Analysis, and Report Generation into dedicated microservices, completing the event-driven processing pipeline.

## What Will Be Accomplished

### 1. PDF Processing Service
- Dedicated service for PDF parsing and transaction extraction
- Bank-specific processor integration
- Transaction validation and normalization
- Event-driven processing from File Service

### 2. AI Intelligence Service
- Standalone AI analysis microservice
- Transaction categorization and enrichment
- Multiple AI provider support (Groq, Claude, etc.)
- Learning and feedback integration

### 3. Report Generation Service
- Dedicated report generation microservice
- Excel report creation with multiple sheets
- Bank-specific report formatting
- Template-based report generation

### 4. API Gateway
- Single entry point for all services
- Request routing and load balancing
- Authentication and rate limiting
- Request/response transformation

## Service Architecture

```
Frontend (3000)
    ↓
API Gateway (8080) → Auth Service (8001) → File Service (8002) → PDF Service (8003) → AI Service (8004) → Report Service (8005)
    ↓
Redis (6379) ← RabbitMQ (5672) ← MinIO (9000)
```

## Files to Create

### PDF Processing Service
- `services/pdf-service/app/main.py` - Service entry point
- `services/pdf-service/app/routes/processing.py` - PDF processing endpoints
- `services/pdf-service/app/services/pdf_processor.py` - PDF processing logic
- `services/pdf-service/app/services/bank_processors/` - Bank-specific processors
- `services/pdf-service/Dockerfile` - Container config

### AI Intelligence Service
- `services/ai-service/app/main.py` - Service entry point
- `services/ai-service/app/routes/analysis.py` - AI analysis endpoints
- `services/ai-service/app/services/ai_processor.py` - AI processing logic
- `services/ai-service/app/services/groq_client.py` - Groq integration
- `services/ai-service/app/services/claude_client.py` - Claude integration
- `services/ai-service/Dockerfile` - Container config

### Report Generation Service
- `services/report-service/app/main.py` - Service entry point
- `services/report-service/app/routes/reports.py` - Report generation endpoints
- `services/report-service/app/services/report_generator.py` - Report generation logic
- `services/report-service/app/templates/` - Report templates
- `services/report-service/Dockerfile` - Container config

### API Gateway
- `services/api-gateway/app/main.py` - Gateway entry point
- `services/api-gateway/app/routes/proxy.py` - Service routing
- `services/api-gateway/app/middleware/auth.py` - Gateway auth
- `services/api-gateway/app/middleware/rate_limit.py` - Rate limiting
- `services/api-gateway/Dockerfile` - Container config

## Implementation Steps

### Step 1: PDF Processing Service
- Extract PDF parsing logic from monolith
- Create bank-specific processor modules
- Implement event consumption from RabbitMQ
- Add PDF validation and error handling

### Step 2: AI Intelligence Service
- Extract AI logic from monolith
- Support multiple AI providers
- Implement learning and feedback
- Add analysis quality metrics

### Step 3: Report Generation Service
- Extract report generation logic
- Create template-based system
- Support multiple output formats
- Add report caching and storage

### Step 4: API Gateway
- Create routing logic for all services
- Implement authentication middleware
- Add rate limiting and monitoring
- Configure service discovery

### Step 5: Update Docker Compose
- Add all new services
- Configure service networking
- Update environment variables
- Add monitoring endpoints

### Step 6: Testing and Validation
- Test end-to-end processing pipeline
- Verify service communication
- Test error handling and recovery
- Validate performance improvements

## Migration Strategy

### Phase 3A: Service Extraction
- Create individual processing services
- Keep monolith endpoints for backward compatibility
- Add event-driven processing alongside sync

### Phase 3B: API Gateway Implementation
- Create gateway for routing
- Implement authentication and rate limiting
- Add service health checks

### Phase 3C: Cutover
- Route traffic through API Gateway
- Deprecate monolith processing endpoints
- Enable full event-driven pipeline

### Phase 3D: Optimization
- Add monitoring and metrics
- Implement caching strategies
- Optimize service performance

## Benefits

1. **Complete Microservices**: Full processing pipeline as services
2. **Independent Scaling**: Each service can scale based on load
3. **Fault Isolation**: Failure in one service doesn't affect others
4. **Technology Diversity**: Different services can use optimal tech stacks
5. **API Gateway**: Single entry point with unified auth and rate limiting

## Rollback Plan

If issues arise:
1. Keep monolith processing endpoints active
2. Route traffic directly to monolith
3. Disable new services individually
4. No data loss due to event sourcing

## Success Criteria

- [ ] PDF Service processes files correctly
- [ ] AI Service provides accurate analysis
- [ ] Report Service generates proper reports
- [ ] API Gateway routes requests correctly
- [ ] End-to-end pipeline works
- [ ] Performance improvements measurable
- [ ] Backward compatibility maintained
