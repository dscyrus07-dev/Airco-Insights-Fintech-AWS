# Airco Insights FinTech - Project Rules & Guidelines

## Coding Rules

### Python/FastAPI Backend Rules

#### Code Style
- **Python Version**: Python 3.11+ required
- **Code Formatting**: Use `black` with 88-character line length
- **Import Style**: Follow PEP 8, group imports (stdlib, third-party, local)
- **Type Hints**: Mandatory for all function signatures and return types
- **Docstrings**: Use Google-style docstrings for all public functions

#### FastAPI Specific Rules
- **Async/Await**: Use async/await for all I/O operations
- **Dependency Injection**: Use FastAPI's dependency system for services
- **Response Models**: Define Pydantic models for all API responses
- **Error Handling**: Use HTTPException with proper status codes
- **Validation**: Use Pydantic models for request validation

#### Database Rules
- **SQLAlchemy**: Use async SQLAlchemy with proper session management
- **Models**: All database models must inherit from Base with proper relationships
- **Migrations**: Use Alembic for all database schema changes
- **Queries**: Use async session methods for all database operations

#### Service Architecture Rules
- **Single Responsibility**: Each service must have one clear purpose
- **Interface Design**: Define abstract interfaces for all service contracts
- **Error Handling**: Implement proper error handling with logging and retry logic
- **Configuration**: Use environment variables for all configuration

### TypeScript/Next.js Frontend Rules

#### Code Style
- **TypeScript**: Strict mode enabled, no `any` types allowed
- **Component Structure**: Use functional components with hooks
- **File Naming**: PascalCase for components, camelCase for utilities
- **Imports**: Use absolute imports with path aliases

#### React/Next.js Specific Rules
- **App Router**: Use Next.js 14 App Router exclusively
- **Server Components**: Use server components by default, client components only when needed
- **State Management**: Use React Context for global state, local state for component state
- **API Routes**: Follow RESTful conventions with proper HTTP methods

#### Styling Rules
- **TailwindCSS**: Use utility classes, avoid custom CSS when possible
- **Responsive Design**: Mobile-first approach with proper breakpoints
- **Component Design**: Design for reusability and composability
- **Accessibility**: Follow WCAG 2.1 guidelines, include proper ARIA labels

### Microservices Rules

#### Service Design
- **Stateless**: All services must be stateless
- **Health Checks**: Every service must implement `/health` endpoint
- **Configuration**: Use environment variables, no hardcoded values
- **Logging**: Structured logging with correlation IDs

#### Communication Rules
- **Async Communication**: Use RabbitMQ for service-to-service communication
- **Synchronous Communication**: Use HTTP/REST for external APIs
- **Error Handling**: Implement circuit breaker pattern for external dependencies
- **Retry Logic**: Implement exponential backoff for transient failures

#### Data Management
- **Database Ownership**: Each service owns its database schema
- **Data Consistency**: Use eventual consistency for cross-service data
- **File Storage**: Use MinIO for all file storage operations
- **Caching**: Use Redis for caching and session management

## Constraints

### Technical Constraints
- **Database**: PostgreSQL only, no other databases supported
- **Message Queue**: RabbitMQ only for async communication
- **Storage**: MinIO only for object storage
- **Authentication**: JWT-based with optional Keycloak integration
- **AI Services**: Groq and Anthropic Claude only

### Performance Constraints
- **File Size**: Maximum 20MB per PDF file
- **Processing Time**: Maximum 5 minutes per PDF processing
- **Concurrent Jobs**: Maximum 10 concurrent processing jobs per service
- **Memory Usage**: Maximum 512MB per service container
- **API Response Time**: Maximum 2 seconds for API responses

### Security Constraints
- **Authentication**: All endpoints except health checks require authentication
- **Authorization**: Role-based access control (user/admin roles)
- **Data Privacy**: No sensitive data in logs, use structured logging
- **File Security**: Files must be encrypted at rest and in transit
- **API Security**: Rate limiting and input validation required

### Business Constraints
- **Bank Support**: HDFC fully implemented, other banks as placeholders
- **Report Format**: Excel only, specific formats per bank
- **AI Categorization**: Must provide confidence scores
- **Data Retention**: Files and reports retained for 30 days
- **User Limits**: Maximum 100 users per tenant in basic plan

## Do's and Don'ts

### Do's

#### Development Practices
- **DO** write comprehensive tests for all business logic
- **DO** use correlation IDs for all request tracking
- **DO** implement proper error handling and logging
- **DO** follow async/await patterns for I/O operations
- **DO** use environment variables for all configuration

#### Code Organization
- **DO** keep services small and focused
- **DO** use dependency injection for service composition
- **DO** implement proper interfaces for service contracts
- **DO** follow single responsibility principle
- **DO** use meaningful names for variables and functions

#### API Design
- **DO** use RESTful conventions for API design
- **DO** implement proper HTTP status codes
- **DO** validate all input data
- **DO** provide clear error messages
- **DO** version APIs when making breaking changes

#### Security Practices
- **DO** validate all user inputs
- **DO** use parameterized queries for database operations
- **DO** implement proper authentication and authorization
- **DO** use HTTPS for all communications
- **DO** log security events appropriately

### Don'ts

#### Development Anti-Patterns
- **DON'T** use synchronous operations for I/O-bound tasks
- **DON'T** hardcode configuration values
- **DON'T** ignore error handling and logging
- **DON'T** use global variables for state management
- **DON'T** write monolithic functions

#### Code Quality Issues
- **DON'T** commit code without proper testing
- **DON'T** use `any` type in TypeScript
- **DON'T** ignore type hints in Python
- **DON'T** write deeply nested code
- **DON'T** use magic numbers or strings

#### Security Violations
- **DON'T** store sensitive data in code or configuration files
- **DON'T** disable authentication in production
- **DON'T** ignore input validation
- **DON'T** use weak encryption or hashing
- **DON'T** expose internal service endpoints

#### Performance Anti-Patterns
- **DON'T** make blocking calls in async functions
- **DON'T** load entire files into memory
- **DON'T** ignore database connection pooling
- **DON'T** disable caching mechanisms
- **DON'T** create unbounded loops or recursion

## Quality Standards

### Code Quality Requirements
- **Test Coverage**: Minimum 80% coverage for business logic
- **Code Complexity**: Maximum cyclomatic complexity of 10
- **Code Duplication**: Maximum 5% code duplication
- **Documentation**: All public APIs must be documented
- **Performance**: All API endpoints must respond within 2 seconds

### Security Requirements
- **Authentication**: All endpoints must require authentication
- **Authorization**: Proper role-based access control
- **Input Validation**: All inputs must be validated and sanitized
- **Error Handling**: No sensitive information in error messages
- **Logging**: Comprehensive audit logging for security events

### Reliability Requirements
- **Error Handling**: Graceful error handling with user-friendly messages
- **Retry Logic**: Exponential backoff for transient failures
- **Circuit Breakers**: Prevent cascade failures
- **Health Checks**: All services must implement health checks
- **Monitoring**: Comprehensive metrics and alerting

## Development Workflow Rules

### Git Workflow
- **Branching**: Use feature branches for all development
- **Commits**: Atomic commits with clear messages
- **Pull Requests**: Required for all code changes
- **Code Review**: Minimum one reviewer required
- **Testing**: All tests must pass before merge

### Testing Requirements
- **Unit Tests**: Required for all business logic
- **Integration Tests**: Required for service interactions
- **End-to-End Tests**: Required for critical user journeys
- **Performance Tests**: Required for all API endpoints
- **Security Tests**: Required for authentication and authorization

### Deployment Rules
- **Environment Isolation**: Separate environments for dev/staging/prod
- **Configuration Management**: Use environment-specific configurations
- **Rollback Strategy**: Always have a rollback plan
- **Health Validation**: Verify service health after deployment
- **Monitoring**: Monitor deployment success and system health

## Technology-Specific Rules

### Python/FastAPI Rules
- **Async Patterns**: Use async/await for all I/O operations
- **Dependency Injection**: Use FastAPI's dependency system
- **Error Handling**: Use HTTPException with proper status codes
- **Validation**: Use Pydantic models for request/response validation
- **Database**: Use async SQLAlchemy with proper session management

### TypeScript/Next.js Rules
- **Type Safety**: Strict TypeScript mode, no `any` types
- **Component Design**: Functional components with hooks
- **State Management**: Context API for global state
- **API Routes**: RESTful conventions with proper error handling
- **Performance**: Server components by default, client components when needed

### Docker Rules
- **Image Size**: Keep images small and optimized
- **Multi-stage Builds**: Use multi-stage builds for production
- **Security**: Use non-root users, scan for vulnerabilities
- **Health Checks**: Implement proper health checks
- **Resource Limits**: Set appropriate memory and CPU limits

### Database Rules
- **Migrations**: Use Alembic for all schema changes
- **Connection Pooling**: Use connection pooling for performance
- **Transactions**: Use transactions for data consistency
- **Indexes**: Proper indexes for query performance
- **Backups**: Regular database backups and testing

## Compliance Requirements

### Data Protection
- **GDPR Compliance**: User data protection and privacy
- **Data Retention**: Automatic cleanup of old data
- **Data Encryption**: Encryption at rest and in transit
- **Access Control**: Proper access controls for sensitive data
- **Audit Trail**: Comprehensive audit logging

### Financial Regulations
- **Data Accuracy**: Ensure financial data accuracy
- **Audit Requirements**: Maintain audit trails for financial operations
- **Security Standards**: Follow financial industry security standards
- **Compliance Testing**: Regular compliance testing and validation
- **Documentation**: Comprehensive documentation for compliance

## Monitoring and Observability

### Logging Requirements
- **Structured Logging**: JSON format with correlation IDs
- **Log Levels**: Proper use of log levels (DEBUG, INFO, WARN, ERROR)
- **Sensitive Data**: No sensitive data in logs
- **Log Retention**: Appropriate log retention policies
- **Log Aggregation**: Centralized log collection and analysis

### Metrics Requirements
- **Performance Metrics**: Request latency, throughput, error rates
- **Business Metrics**: Processing success rates, user engagement
- **Infrastructure Metrics**: CPU, memory, disk, network usage
- **Custom Metrics**: Service-specific business metrics
- **Alerting**: Appropriate alerting thresholds and notifications

### Health Check Requirements
- **Service Health**: Comprehensive health checks for all services
- **Dependency Health**: Health checks for external dependencies
- **Resource Health**: Monitor resource usage and availability
- **Automated Recovery**: Automated recovery from common failures
- **Manual Intervention**: Clear procedures for manual intervention
## Auto-Update Rules

### Context File Maintenance
- **Update Frequency**: Every 2 conversations
- **Discovery Logging**: All technical insights must be logged
- **File Synchronization**: Keep context files aligned with codebase understanding
- **Version Control**: Track changes to documentation

### Quality Standards
- **Accuracy**: All discoveries must be verified against actual code
- **Completeness**: Include file paths, function names, and technical details
- **Relevance**: Focus on actionable insights for development
- **Timeliness**: Update context immediately after discoveries
