# Phase 2 Plan - File Ingestion Service Extraction

## Objective
Extract file upload, validation, and storage into a dedicated microservice while implementing RabbitMQ message queuing for async processing.

## What Will Be Accomplished

### 1. File Ingestion Service
- Dedicated service for file uploads
- File validation and virus scanning
- Storage to S3/MinIO
- Metadata management
- Job creation and event emission

### 2. RabbitMQ Message Queuing
- Replace in-memory task processor with RabbitMQ
- Event-driven architecture
- Message durability and retry logic
- Dead letter queue for failed jobs

### 3. Event-Driven Processing
- File uploaded → PDF processing event
- PDF processed → AI analysis event
- AI analyzed → Report generation event
- Report generated → Notification event

### 4. Storage Service
- S3/MinIO integration for file storage
- File metadata tracking
- Cleanup policies
- Access control

## Service Architecture

```
Frontend (3000)
    ↓
API Gateway (future)
    ↓
File Ingestion Service (8002) → RabbitMQ → PDF Service (8003) → AI Service (8004) → Report Service (8005)
    ↓
Redis (6379) ← S3/MinIO (9000)
```

## Files to Create

### File Ingestion Service
- `services/file-service/app/main.py` - Service entry point
- `services/file-service/app/routes/upload.py` - Upload endpoints
- `services/file-service/app/services/file_service.py` - File processing logic
- `services/file-service/app/services/storage_service.py` - S3/MinIO integration
- `services/file-service/app/models/file.py` - File models
- `services/file-service/Dockerfile` - Container config

### Message Queue Integration
- `backend/app/services/message_queue.py` - RabbitMQ client
- `backend/app/services/event_publisher.py` - Event publishing
- `backend/app/services/event_consumer.py` - Event consumption
- `backend/app/events/file_events.py` - File event definitions

### Storage Service
- `backend/app/services/storage_service.py` - S3/MinIO wrapper
- `backend/app/utils/file_utils.py` - File utilities

## Implementation Steps

### Step 1: Create File Ingestion Service
- Set up FastAPI service structure
- Implement file upload endpoints
- Add file validation logic
- Integrate with S3/MinIO storage

### Step 2: Implement RabbitMQ Integration
- Create message queue client
- Define event schemas
- Implement publisher/consumer pattern
- Add retry and dead letter logic

### Step 3: Update Monolith
- Remove direct file handling from upload routes
- Add event publishing for file uploads
- Update job creation to use events
- Maintain backward compatibility

### Step 4: Update Docker Compose
- Add file service to docker-compose
- Add S3/MinIO service
- Configure RabbitMQ properly
- Update networking

### Step 5: Testing and Validation
- Test file upload flow
- Verify message queuing
- Test event processing
- Validate storage integration

## Migration Strategy

### Phase 2A: File Service Creation
- Create File Ingestion Service
- Keep existing upload endpoints in monolith
- Add new async upload endpoints

### Phase 2B: RabbitMQ Integration
- Implement message queuing
- Add event-driven processing
- Update task processor to use RabbitMQ

### Phase 2C: Storage Service
- Add S3/MinIO integration
- Update file storage logic
- Implement cleanup policies

### Phase 2D: Cutover
- Route traffic to File Service
- Remove old upload logic
- Update documentation

## Benefits

1. **Scalability**: File processing can scale independently
2. **Reliability**: Message queuing provides durability
3. **Performance**: Async processing improves response times
4. **Storage**: Dedicated storage service with cleanup
5. **Architecture**: Event-driven design for future services

## Rollback Plan

If issues arise:
1. Keep monolith upload endpoints active
2. Route traffic back to monolith
3. Disable RabbitMQ consumers
4. No data loss due to event sourcing

## Success Criteria

- [ ] File Service accepts uploads
- [ ] Files stored in S3/MinIO
- [ ] Events published to RabbitMQ
- [ ] PDF processing consumes events
- [ ] End-to-end flow works
- [ ] Backward compatibility maintained
