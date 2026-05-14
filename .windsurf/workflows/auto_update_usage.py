"""
Auto-Update Usage Examples
Demonstrates how to use the auto-update system during conversations.
"""

from auto_update_integration import auto_update

def example_ocr_discovery():
    """Example: Log OCR processing discovery."""
    auto_update.log_ocr_discovery(
        libraries=["pdfplumber==0.10.4", "pymupdf==1.23.8", "pikepdf==8.11.2"],
        processing_flow="Bank-specific processors with coordinate mapping",
        risks=["Hardcoded coordinates break if PDF format changes", "No generic OCR engine"]
    )

def example_rabbitmq_discovery():
    """Example: Log RabbitMQ status discovery."""
    auto_update.log_rabbitmq_discovery(
        current_state="Redis-only job processing",
        infrastructure_status="RabbitMQ infrastructure exists but unused",
        processing_mode="Synchronous in main thread"
    )

def example_bank_processor_discovery():
    """Example: Log bank processor discovery."""
    auto_update.log_bank_processor_discovery(
        bank_name="HDFC",
        coordinates={
            "date": "x < 65",
            "narration": "65 <= x < 260",
            "balance": "x >= 562"
        },
        pipeline_steps=11,
        excel_sheets=6
    )

def example_architecture_discovery():
    """Example: Log architecture discovery."""
    auto_update.log_architecture_discovery(
        component="PDF Processing",
        discovery="Uses bank-specific processors instead of generic OCR",
        impact="Higher accuracy but requires maintenance per bank"
    )

# Usage in conversation:
# After discovering OCR details:
# auto_update.log_ocr_discovery(...)

# After finding RabbitMQ status:
# auto_update.log_rabbitmq_discovery(...)

# After analyzing bank processors:
# auto_update.log_bank_processor_discovery(...)

# Check update status:
# status = auto_update.get_update_status()
# print(f"Chat count: {status['chat_count']}")
# print(f"Next update in: {status['next_update_in']} chats")
