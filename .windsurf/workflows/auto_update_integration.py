"""
Auto-Update Integration for AI Assistant
Integrates with AI assistant to automatically update context files.
"""

import json
from datetime import datetime
from pathlib import Path
from auto_update_manager import AutoUpdateManager

class AutoUpdateIntegration:
    """Integration layer for automatic context file updates."""
    
    def __init__(self):
        self.manager = AutoUpdateManager()
        self.current_session_insights = []
        
    def log_discovery(self, discovery_type: str, insights: dict):
        """Log a discovery from current conversation."""
        discovery_data = {
            "timestamp": datetime.now().isoformat(),
            "type": discovery_type,
            "insights": insights,
            "session_id": self._get_session_id()
        }
        
        self.manager.log_discovery(discovery_type, insights)
        self.current_session_insights.append(discovery_data)
        
        # Check if we should update context files
        if self.manager.should_update_context():
            self.trigger_auto_update()
    
    def trigger_auto_update(self):
        """Trigger automatic context file update."""
        print("Auto-update triggered! Updating context files...")
        self.manager.update_all_context_files()
        
        # Clear current session insights after update
        self.current_session_insights = []
        
        print("Context files updated successfully!")
    
    def log_ocr_discovery(self, libraries: list, processing_flow: str, risks: list):
        """Log OCR processing discoveries."""
        insights = {
            "libraries": libraries,
            "processing_flow": processing_flow,
            "risks": risks,
            "key_files": [
                "backend/app/services/pdf_processor.py",
                "backend/app/services/pipeline_orchestrator.py",
                "backend/app/services/banks/hdfc/parser.py",
                "backend/app/services/banks/axis/parser.py",
                "backend/app/services/banks/icici/parser.py"
            ]
        }
        self.log_discovery("ocr_process", insights)
    
    def log_rabbitmq_discovery(self, current_state: str, infrastructure_status: str, processing_mode: str):
        """Log RabbitMQ/Redis discoveries."""
        insights = {
            "current_state": current_state,
            "infrastructure_status": infrastructure_status,
            "processing_mode": processing_mode,
            "key_files": [
                "backend/app/services/task_processor.py",
                "backend/app/services/redis_job_store.py",
                "backend/app/services/message_queue.py"
            ]
        }
        self.log_discovery("rabbitmq_status", insights)
    
    def log_bank_processor_discovery(self, bank_name: str, coordinates: dict, pipeline_steps: int, excel_sheets: int):
        """Log bank-specific processor discoveries."""
        insights = {
            "bank_name": bank_name,
            "coordinates": coordinates,
            "pipeline_steps": pipeline_steps,
            "excel_sheets": excel_sheets,
            "parser_file": f"backend/app/services/banks/{bank_name.lower()}/parser.py",
            "processor_file": f"backend/app/services/banks/{bank_name.lower()}/processor.py"
        }
        self.log_discovery("bank_processor", insights)
    
    def log_architecture_discovery(self, component: str, discovery: str, impact: str):
        """Log general architecture discoveries."""
        insights = {
            "component": component,
            "discovery": discovery,
            "impact": impact
        }
        self.log_discovery("architecture", insights)
    
    def _get_session_id(self) -> str:
        """Generate a session ID for tracking."""
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def get_update_status(self) -> dict:
        """Get current update status."""
        try:
            counter_file = self.manager.chat_counter_file
            if counter_file.exists():
                with open(counter_file, 'r') as f:
                    counter_data = json.load(f)
                return {
                    "chat_count": counter_data.get("chat_count", 0),
                    "last_chat": counter_data.get("last_chat"),
                    "next_update_in": 2 - (counter_data.get("chat_count", 0) % 2),
                    "session_insights": len(self.current_session_insights)
                }
        except:
            pass
        
        return {
            "chat_count": 0,
            "last_chat": None,
            "next_update_in": 2,
            "session_insights": 0
        }

# Global integration instance
auto_update = AutoUpdateIntegration()
