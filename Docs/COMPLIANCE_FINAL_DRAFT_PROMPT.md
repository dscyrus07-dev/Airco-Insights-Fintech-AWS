# Final Compliance Draft Generation Prompt

## Context
You are tasked with creating a comprehensive Final Compliance Draft for Airco Insights FinTech SaaS platform by combining information from two source documents:

1. **Source Document 1:** `@[Airco Compliance (2).docx]` - Contains the official compliance checklist with ticked/checked features that need to be provided as proof
2. **Source Document 2:** `@[Airco Compliance Features Draft.md]` - Contains deep technical analysis of implemented security features with code references and proof points

## Task
Create a **Final Compliance Draft** document that:

### 1. Structure
- Use the compliance categories from `Airco Compliance (2).docx` as the primary structure
- For each ticked/checked feature in the docx, provide detailed proof from the technical analysis
- Maintain a professional, audit-ready format suitable for regulatory submissions

### 2. Content Requirements
For each compliance feature:
- **Feature Name:** As listed in the docx
- **Status:** ✅ Implemented / ✅ Available / ⚠️ Partial
- **Technical Implementation:** Detailed explanation from the codebase analysis
- **Proof Points:**
  - Code file references (with line numbers where applicable)
  - Configuration values and settings
  - Verification commands that can be run
  - Log locations and evidence sources
- **Compliance Mapping:** Which regulations this satisfies (GDPR, PCI DSS, SOC 2, ISO 27001)
- **Audit Evidence:** How to verify this feature in production

### 3. Key Sections to Include
Based on typical FinTech compliance documents, include:

#### Executive Summary
- Overall security score
- Compliance readiness percentage
- Key strengths and areas for improvement

#### Authentication & Authorization
- Keycloak implementation details
- JWT validation mechanisms
- Role-based access control
- Multi-factor authentication capability

#### Data Security & Privacy
- Encryption at rest (MinIO)
- Encryption in transit (TLS 1.2/1.3)
- Data integrity checks
- Access controls and isolation

#### Infrastructure Security
- AWS EC2 security
- Network isolation
- SSL/TLS management
- Container security

#### Data Processing Security
- PDF integrity validation
- Data integrity guards
- AI-powered categorization
- Bank-specific processors

#### Audit & Monitoring
- Correlation ID tracking
- Structured logging
- Health monitoring
- Incident response

#### Input Validation & Security
- File upload validation
- API security measures
- Rate limiting
- Error handling

### 4. Formatting Guidelines
- Use Markdown with clear headings
- Include code blocks for technical implementations
- Use tables for compliance mappings
- Add checkmarks (✅) for implemented features
- Add warnings (⚠️) for partial implementations
- Include command-line examples for verification

### 5. Verification Section
Add a "Proof of Compliance" section at the end with:
- Quick verification commands
- Key file locations for auditors
- Log extraction commands
- Configuration validation steps

## Output Format
Create the final document as: `Airco Compliance Final Draft.md`

## Tone
Professional, technical, and audit-ready. Suitable for:
- Regulatory submissions
- Client presentations
- Internal audits
- Third-party security assessments

## Notes
- Prioritize features that are ticked/checked in the docx
- Use actual code references and file paths from the analysis
- Include real configuration values where appropriate
- Ensure all proof points are actionable and verifiable
- Maintain consistency with the technical analysis document

---

## Example Section Format

```markdown
## 1. Authentication & Authorization

### Feature: JWT Token Validation
**Status:** ✅ Implemented  
**Regulations:** GDPR, SOC 2, ISO 27001

**Technical Implementation:**
Airco Insights uses Keycloak for identity management with RS256 JWT tokens. Tokens are validated on every API request using the JWKS endpoint for public key rotation.

**Proof Points:**
- **Code:** `services/auth-service/app/services/keycloak_validator.py` (lines 45-95)
- **Algorithm:** RS256 with signature verification
- **Claims Validated:** sub, email, exp, iat, iss, aud, azp
- **Configuration:** `.env` lines 12-19

**Verification Command:**
```bash
docker exec airco_keycloak kc.sh show config
docker logs airco_auth_service --tail 100
```

**Audit Evidence Location:**
- Logs: `services/auth-service/app/utils/logging.py`
- Format: Structured JSON with correlation IDs
```
