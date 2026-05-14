"""
Auto-Update Manager for .windsurf/workflows/ Context Files
Automatically updates context files every 2 chats with latest discoveries.
"""

import os
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

class AutoUpdateManager:
    """Manages automated updates to .windsurf/workflows/ context files."""
    
    def __init__(self, workflows_dir: str = None):
        self.workflows_dir = Path(workflows_dir) if workflows_dir else Path(__file__).parent
        self.chat_counter_file = self.workflows_dir / ".chat_counter.json"
        self.discovery_log_file = self.workflows_dir / ".discovery_log.json"
        self.context_files = {
            "project-context.md": self.workflows_dir / "project-context.md",
            "architecture.md": self.workflows_dir / "architecture.md", 
            "dev-flow.md": self.workflows_dir / "dev-flow.md",
            "project-rules.md": self.workflows_dir / "project-rules.md",
            "system-workflow.md": self.workflows_dir / "system-workflow.md"
        }
        
    def increment_chat_counter(self) -> int:
        """Increment chat counter and return current count."""
        try:
            if self.chat_counter_file.exists():
                with open(self.chat_counter_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {"chat_count": 0, "last_update": None}
            
            data["chat_count"] += 1
            data["last_chat"] = datetime.now().isoformat()
            
            with open(self.chat_counter_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            return data["chat_count"]
        except Exception as e:
            print(f"Error managing chat counter: {e}")
            return 1
    
    def should_update_context(self) -> bool:
        """Check if context should be updated (every 2 chats)."""
        chat_count = self.increment_chat_counter()
        return chat_count % 2 == 0
    
    def log_discovery(self, discovery_type: str, content: Dict[str, Any]):
        """Log a discovery for context updates."""
        try:
            if self.discovery_log_file.exists():
                with open(self.discovery_log_file, 'r') as f:
                    log_data = json.load(f)
            else:
                log_data = {"discoveries": []}
            
            discovery = {
                "timestamp": datetime.now().isoformat(),
                "type": discovery_type,
                "content": content
            }
            log_data["discoveries"].append(discovery)
            
            # Keep only last 50 discoveries
            if len(log_data["discoveries"]) > 50:
                log_data["discoveries"] = log_data["discoveries"][-50:]
            
            with open(self.discovery_log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
                
        except Exception as e:
            print(f"Error logging discovery: {e}")
    
    def get_recent_discoveries(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent discoveries for context updates."""
        try:
            if not self.discovery_log_file.exists():
                return []
            
            with open(self.discovery_log_file, 'r') as f:
                log_data = json.load(f)
            
            return log_data.get("discoveries", [])[-limit:]
            
        except Exception as e:
            print(f"Error getting discoveries: {e}")
            return []
    
    def update_project_context(self):
        """Update project-context.md with latest discoveries."""
        discoveries = self.get_recent_discoveries()
        
        # Read existing content
        content = self._read_file_content("project-context.md")
        
        # Add discoveries section
        new_section = "\n\n## Recent Discoveries\n\n"
        for discovery in discoveries:
            new_section += f"### {discovery['type']} ({discovery['timestamp']})\n"
            if discovery['type'] == 'ocr_process':
                new_section += f"- **OCR Libraries**: pdfplumber, PyMuPDF, pikepdf\n"
                new_section += f"- **Processing Flow**: Bank-specific processors with coordinate mapping\n"
                new_section += f"- **Risk Assessment**: Hardcoded coordinates for PDF layouts\n"
            elif discovery['type'] == 'rabbitmq_status':
                new_section += f"- **Current State**: Redis-only job processing\n"
                new_section += f"- **RabbitMQ**: Infrastructure exists but unused\n"
                new_section += f"- **Processing**: Synchronous in main thread\n"
            new_section += "\n"
        
        # Update file
        updated_content = content.rstrip() + new_section
        self._write_file_content("project-context.md", updated_content)
        
    def update_architecture(self):
        """Update architecture.md with current system state."""
        discoveries = self.get_recent_discoveries()
        
        content = self._read_file_content("architecture.md")
        
        # Find and update message queue section
        new_queue_section = """
## Message Queue Architecture

### Current Implementation (Phase 1)
- **Redis**: Used for job persistence and tracking
- **Task Processor**: Asyncio-based, not RabbitMQ
- **Job Storage**: Redis-backed with 24-hour TTL
- **Processing**: Synchronous in main thread

### RabbitMQ Infrastructure (Phase 2 - Ready)
- **Exchanges**: file_processing, pdf_processing, ai_processing, report_processing
- **Queues**: file_upload_queue, pdf_processing_queue, ai_analysis_queue, report_generation_queue
- **Status**: Infrastructure exists but not integrated
- **Next Steps**: Migrate to event-driven processing

### Processing Flow
```
Current: Upload -> Direct Processing -> Immediate Response
Future:  Upload -> RabbitMQ Queue -> Background Worker -> Poll Results
```
"""
        
        # Replace or add message queue section
        if "## Message Queue Architecture" in content:
            # Replace existing section
            start = content.find("## Message Queue Architecture")
            end = content.find("\n## ", start + 1)
            if end != -1:
                updated_content = content[:start] + new_queue_section + content[end:]
            else:
                updated_content = content[:start] + new_queue_section
        else:
            # Add new section
            updated_content = content.rstrip() + new_queue_section
        
        self._write_file_content("architecture.md", updated_content)
    
    def update_dev_flow(self):
        """Update dev-flow.md with auto-update mechanism."""
        new_section = """
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
"""
        
        content = self._read_file_content("dev-flow.md")
        updated_content = content.rstrip() + new_section
        self._write_file_content("dev-flow.md", updated_content)
    
    def update_project_rules(self):
        """Update project-rules.md with latest technical rules."""
        new_section = """
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
"""
        
        content = self._read_file_content("project-rules.md")
        updated_content = content.rstrip() + new_section
        self._write_file_content("project-rules.md", updated_content)
    
    def update_system_workflow(self):
        """Update system-workflow.md with latest workflow discoveries."""
        discoveries = self.get_recent_discoveries()
        
        content = self._read_file_content("system-workflow.md")
        
        # Add detailed OCR processing section
        ocr_section = """
## OCR Processing Workflow (Detailed)

### PDF Upload to Processing Flow
```
POST /process (upload.py)
    |
    v
File Validation + MinIO Storage
    |
    v
Pipeline Orchestrator (pipeline_orchestrator.py)
    |   - Bank routing logic
    |   - Bank name normalization
    v
Bank-Specific Processor
    |   HDFC: 11-step pipeline
    |   Axis: 7-step pipeline  
    |   ICICI: 7-step pipeline
    v
Transaction Extraction
    |   Method 1: Table-based (pdfplumber)
    |   Method 2: Coordinate-based (PyMuPDF)
    v
Excel Report Generation
```

### Bank Coordinate Mappings
| Bank | Date | Narration | Ref/Mode | Withdrawal | Deposit | Balance |
|------|------|-----------|----------|-----------|----------|---------|
| HDFC | x < 65 | 65-260 | 260-360 | 405-485 | 485-562 | x >= 562 |
| Axis | x < 90 | 132-340 | 90-132 | 340-400 | 400-460 | 460-535 |
| ICICI | x < 70 | 130-380 | 70-130 | 435-540 | 380-435 | x >= 540 |

### Risk Assessment
- **HIGH**: Hardcoded coordinates break if PDF format changes
- **MEDIUM**: Axis/ICICI have no table-based fallback
- **LOW**: HDFC has dual-method extraction
"""
        
        updated_content = content.rstrip() + ocr_section
        self._write_file_content("system-workflow.md", updated_content)
    
    def update_all_context_files(self):
        """Update all context files with latest discoveries."""
        try:
            self.update_project_context()
            self.update_architecture()
            self.update_dev_flow()
            self.update_project_rules()
            self.update_system_workflow()
            
            # Log the update
            self.log_discovery("context_update", {
                "files_updated": list(self.context_files.keys()),
                "update_timestamp": datetime.now().isoformat()
            })
            
            print(f"Auto-updated {len(self.context_files)} context files")
            
        except Exception as e:
            print(f"Error updating context files: {e}")
    
    def _read_file_content(self, filename: str) -> str:
        """Read content from a context file."""
        try:
            file_path = self.context_files[filename]
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            return ""
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            return ""
    
    def _write_file_content(self, filename: str, content: str):
        """Write content to a context file."""
        try:
            file_path = self.context_files[filename]
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            print(f"Error writing {filename}: {e}")

# Global instance
auto_update_manager = AutoUpdateManager()
