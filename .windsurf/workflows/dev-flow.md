# Airco Insights FinTech - AI-Assisted Development Flow

## AI Behavior Guidelines

### Core Principles
- **Context-First**: Always read relevant context files before making changes
- **Incremental Development**: Make small, focused changes with clear intent
- **Verification**: Test changes before considering them complete
- **Documentation**: Update documentation when making architectural changes
- **Safety**: Never break existing functionality without explicit approval

### AI Development Workflow

#### 1. Context Analysis Phase
```
User Request Analysis
    |
    v
Read Context Files (project-context.md, architecture.md, project-rules.md)
    |
    v
Analyze Current Code State
    |
    v
Identify Impact & Dependencies
    |
    v
Plan Implementation Approach
```

#### 2. Implementation Phase
```
Create/Update Todo List
    |
    v
Implement Changes (smallest possible units)
    |
    v
Test Implementation
    |
    v
Verify No Regressions
    |
    v
Update Documentation (if needed)
```

#### 3. Validation Phase
```
Run Tests
    |
    v
Verify Production Readiness
    |
    v
Document Changes
```

## Specialized Workflows

### Compliance Analysis Workflow
```
Compliance Request
    |
    v
Read Compliance Documents (.docx, analysis drafts)
    |
    v
Deep Codebase Analysis
    |
    v
Extract Security Features
    |
    v
Document Proof Points
    |
    v
Create Compliance Report
```

### EC2 Management Workflow
```
Infrastructure Request
    |
    v
Use manage-ec2-instance.ps1
    |
    v
Actions Available:
    - start: Start EC2 + Docker
    - stop: Stop Docker + EC2
    - status: Show instance status
    - restart: Restart Docker only
    - fullstart: Ensure instance + Docker running
    - rebuild: Rebuild Docker stack
    |
    v
Verify Service Health
```

### Security Review Workflow
```
Security Assessment Request
    |
    v
Analyze Authentication (Keycloak)
    |
    v
Review Storage Security (MinIO)
    |
    v
Check Infrastructure (AWS/SSL)
    |
    v
Examine Data Processing (Algorithms)
    |
    v
Document Findings with Proof
    |
    v
Generate Compliance Report
```

## Key Files for Context

### Production Management
- `manage-ec2-instance.ps1` - EC2 lifecycle management
- `.env` - Production configuration
- `docker-compose.ec2.yml` - Production stack

### Compliance & Security
- Compliance analysis documents
- Security implementation files
- Audit logs and monitoring

### Development
- `docker-compose.yml` - Local development
- `docker-compose.local.yml` - Local port exposure
- `scripts/` - Utility scripts

## Recent Updates (2026-04-20)

### Production Deployment
- Elastic IP allocated: 98.83.22.152
- SSL certificates from Let's Encrypt
- Permanent domain: test.theairco.ai
- Health monitoring enabled

### Security Implementation
- Keycloak fully configured
- JWT validation with RS256
- Role-based access control
- Correlation ID tracking

### Compliance Documentation
- Deep security analysis completed
- All features documented with proof points
- Overall security score: 8.5/10
- Compliance readiness: 75-85%
    |
    v
Check Service Health
    |
    v
Verify Business Logic
    |
    v
Confirm Performance
    |
    v
Mark Task Complete
```

## Update & Memory Rules

### When to Update Context Files

#### project-context.md Updates
- **Tech Stack Changes**: New dependencies, version updates
- **Business Logic Changes**: New features, modified workflows
- **Architecture Changes**: Service additions, major refactoring
- **Problem Areas**: New challenges, resolved issues

#### architecture.md Updates
- **Service Changes**: New services, modified service boundaries
- **Data Flow Changes**: Modified processing pipelines
- **Infrastructure Changes**: New components, configuration changes
- **Communication Patterns**: New APIs, modified event flows

#### project-rules.md Updates
- **New Constraints**: Performance, security, business constraints
- **Coding Standards**: New best practices, modified rules
- **Quality Standards**: Updated requirements, new standards
- **Technology Rules**: New frameworks, modified guidelines

#### dev-flow.md Updates
- **Workflow Changes**: Modified development processes
- **AI Behavior Changes**: New guidelines, modified behaviors
- **Tool Changes**: New tools, modified tool usage
- **Process Improvements**: Better ways of working

### Memory Creation Rules

#### When to Create Memories
- **Reusable Patterns**: Common code patterns, architectural decisions
- **Problem Solutions**: Bug fixes, workarounds, solutions
- **Configuration Patterns**: Environment setups, deployment patterns
- **Business Logic**: Important domain knowledge, business rules

#### Memory Categories
- **Architecture**: Service patterns, data flow patterns
- **Code Patterns**: Reusable code snippets, common implementations
- **Configuration**: Environment setups, deployment configurations
- **Problem-Solving**: Bug fixes, troubleshooting steps
- **Business Logic**: Domain-specific rules and knowledge

#### Memory Format
```markdown
## [Memory Title]

**Category**: [architecture|code-patterns|configuration|problem-solving|business-logic]

**Context**: Where this pattern applies

**Implementation**: How to implement this pattern

**Examples**: Code examples or configuration examples

**Related Files**: Files that use or relate to this pattern

**Notes**: Additional considerations or warnings
```

## AI Decision Making Framework

### Before Making Changes
1. **Read Context**: Always read relevant context files first
2. **Analyze Impact**: Understand what will be affected
3. **Check Dependencies**: Identify related components
4. **Plan Approach**: Determine the best implementation strategy
5. **Verify Safety**: Ensure no breaking changes

### Change Implementation Rules
1. **Small Changes**: Make the smallest possible change that works
2. **Test First**: Write tests before implementing (when possible)
3. **Verify Results**: Test the change thoroughly
4. **Check Regressions**: Ensure existing functionality still works
5. **Update Documentation**: Update relevant documentation

### Error Handling Rules
1. **Graceful Degradation**: Handle errors gracefully
2. **User-Friendly Messages**: Provide clear error messages
3. **Logging**: Log errors with appropriate context
4. **Recovery**: Implement error recovery when possible
5. **Monitoring**: Monitor error rates and patterns

## Code Analysis Guidelines

### Reading Code Strategy
1. **Start High-Level**: Read architecture and context first
2. **Identify Patterns**: Look for common patterns and conventions
3. **Understand Flow**: Trace data flow through the system
4. **Find Entry Points**: Identify API endpoints and service boundaries
5. **Check Dependencies**: Understand service dependencies

### Code Modification Strategy
1. **Understand First**: Never modify code without understanding it
2. **Follow Patterns**: Use existing patterns and conventions
3. **Test Changes**: Always test modifications
4. **Preserve Interface**: Don't break existing interfaces
5. **Document Changes**: Update relevant documentation

### Debugging Strategy
1. **Reproduce Issue**: Understand how to reproduce the problem
2. **Check Logs**: Look for relevant error messages
3. **Trace Flow**: Follow the execution path
4. **Isolate Problem**: Find the specific location of the issue
5. **Test Fix**: Verify the fix resolves the issue

## Testing Guidelines

### Test Requirements
1. **Unit Tests**: Test individual functions and methods
2. **Integration Tests**: Test service interactions
3. **End-to-End Tests**: Test complete user workflows
4. **Performance Tests**: Test performance characteristics
5. **Security Tests**: Test security measures

### Test Writing Rules
1. **Clear Tests**: Write tests that are easy to understand
2. **Comprehensive Coverage**: Test all important scenarios
3. **Edge Cases**: Test edge cases and error conditions
4. **Maintainable**: Keep tests maintainable and up-to-date
5. **Fast Execution**: Write tests that run quickly

### Test Execution Rules
1. **Run All Tests**: Run the full test suite before deployment
2. **Check Coverage**: Ensure adequate test coverage
3. **Fix Failures**: Fix all test failures before proceeding
4. **Performance Checks**: Verify performance doesn't degrade
5. **Regression Testing**: Ensure no regressions introduced

## Communication Guidelines

### User Interaction Rules
1. **Clear Communication**: Use clear, concise language
2. **Progress Updates**: Provide regular progress updates
3. **Ask Questions**: Ask for clarification when needed
4. **Explain Decisions**: Explain why certain decisions were made
5. **Provide Options**: Offer multiple approaches when appropriate

### Status Reporting Rules
1. **Regular Updates**: Update todo list regularly
2. **Completion Status**: Mark tasks as completed when done
3. **Blockers**: Report blockers and impediments
4. **Next Steps**: Clearly communicate next steps
5. **Summary**: Provide summary of completed work

### Documentation Rules
1. **Update Context**: Update context files when making changes
2. **Code Comments**: Add comments when code is complex
3. **API Documentation**: Keep API documentation up-to-date
4. **Architecture Docs**: Update architecture documentation
5. **User Documentation**: Update user-facing documentation

## Tool Usage Guidelines

### lean-ctx Tools
1. **Context Reading**: Use `ctx_read` for reading files
2. **Code Search**: Use `ctx_search` for finding code patterns
3. **File Operations**: Use `ctx_edit` for making changes
4. **Tree View**: Use `ctx_tree` for understanding structure
5. **Symbol Analysis**: Use `ctx_symbol` for understanding code

### Native Tools
1. **File Creation**: Use `write_to_file` for new files
2. **Multi-Edit**: Use `multi_edit` for complex changes
3. **Terminal Commands**: Use `bash` for running commands
4. **Web Access**: Use `read_url_content` for external resources
5. **Browser Preview**: Use `browser_preview` for web applications

### Tool Selection Rules
1. **Prefer lean-ctx**: Use lean-ctx tools when available
2. **Right Tool for Job**: Choose the appropriate tool for the task
3. **Efficiency**: Use tools that provide the best efficiency
4. **Safety**: Use tools that provide the best safety
5. **Verification**: Use tools that provide verification capabilities

## Quality Assurance Rules

### Code Quality Standards
1. **Type Safety**: Ensure type safety in all code
2. **Error Handling**: Implement proper error handling
3. **Performance**: Write performant code
4. **Security**: Follow security best practices
5. **Maintainability**: Write maintainable code

### Review Process
1. **Self-Review**: Review own code before considering complete
2. **Pattern Consistency**: Ensure consistency with existing patterns
3. **Test Coverage**: Verify adequate test coverage
4. **Documentation**: Ensure documentation is up-to-date
5. **Performance**: Verify performance requirements are met

### Validation Rules
1. **Functional Testing**: Verify functionality works correctly
2. **Integration Testing**: Verify integrations work correctly
3. **Performance Testing**: Verify performance requirements
4. **Security Testing**: Verify security measures work
5. **User Testing**: Verify user experience is acceptable

## Continuous Improvement Rules

### Learning Rules
1. **Study Code**: Study existing code to understand patterns
2. **Analyze Problems**: Analyze problems to find root causes
3. **Document Solutions**: Document solutions for future reference
4. **Share Knowledge**: Share knowledge with the team
5. **Improve Processes**: Continuously improve development processes

### Adaptation Rules
1. **Context Changes**: Adapt to changing context
2. **New Requirements**: Adapt to new requirements
3. **Technology Changes**: Adapt to technology changes
4. **User Feedback**: Adapt to user feedback
5. **Performance Issues**: Adapt to performance requirements

### Optimization Rules
1. **Performance**: Continuously optimize for performance
2. **Efficiency**: Continuously optimize for efficiency
3. **Maintainability**: Continuously optimize for maintainability
4. **Security**: Continuously optimize for security
5. **User Experience**: Continuously optimize for user experience

## Emergency Procedures

### When Things Go Wrong
1. **Stop**: Stop making changes immediately
2. **Assess**: Assess the situation and impact
3. **Communicate**: Communicate the issue to the user
4. **Recover**: Implement recovery procedures
5. **Learn**: Learn from the experience

### Rollback Procedures
1. **Identify Changes**: Identify what changes were made
2. **Revert Changes**: Revert changes that caused issues
3. **Verify Recovery**: Verify the system is working correctly
4. **Document**: Document what went wrong
5. **Prevent Recurrence**: Implement measures to prevent recurrence

### Escalation Rules
1. **Recognize Issues**: Recognize when issues need escalation
2. **Communicate**: Communicate issues clearly
3. **Provide Context**: Provide relevant context and information
4. **Suggest Solutions**: Suggest possible solutions
5. **Follow Up**: Follow up on resolution

## Success Metrics

### Development Metrics
1. **Task Completion**: Complete tasks in a timely manner
2. **Code Quality**: Maintain high code quality standards
3. **Test Coverage**: Maintain adequate test coverage
4. **Documentation**: Keep documentation up-to-date
5. **User Satisfaction**: Ensure user satisfaction with results

### Process Metrics
1. **Efficiency**: Work efficiently and effectively
2. **Communication**: Communicate clearly and regularly
3. **Quality**: Deliver high-quality work
4. **Learning**: Continuously learn and improve
5. **Adaptation**: Adapt to changing requirements

### Quality Metrics
1. **Functionality**: Deliver functional solutions
2. **Performance**: Meet performance requirements
3. **Security**: Maintain security standards
4. **Maintainability**: Write maintainable code
5. **Usability**: Deliver user-friendly solutions
## Auto-Update Mechanism

### Context File Management
- **Auto-Update**: Every 2 chats automatically updates context files
- **Discovery Log**: Tracks all technical discoveries during conversations
- **File Updates**: Updates project-context.md, architecture.md, dev-flow.md
- **Chat Counter**: Tracks conversation count for update triggers

### Update Process
```
Chat #1: Discovery logged
Chat #2: Context files auto-updated with latest insights
Chat #3: New discoveries logged
Chat #4: Context files updated again
```

### Discovery Types
- **ocr_process**: PDF processing workflow discoveries
- **rabbitmq_status**: Message queue implementation details
- **bank_processors**: Bank-specific processing logic
- **coordinate_mapping**: PDF layout coordinate systems
