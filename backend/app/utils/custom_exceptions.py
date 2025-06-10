from fastapi import status as http_status

class CoreServiceError(Exception):
    """Base exception for core service layer errors."""
    def __init__(
        self,
        message: str,
        status_code: int = http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str | None = None,
        headers: dict | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__ # Default error code to class name
        self.headers = headers
        super().__init__(self.message)

class FileProcessingError(CoreServiceError):
    """Exception related to file processing (saving, reading, etc.)."""
    def __init__(self, message: str, error_code: str = "FILE_PROCESSING_ERROR"):
        super().__init__(message, status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, error_code=error_code)

class OCRProcessingError(CoreServiceError):
    """Exception during OCR processing."""
    def __init__(self, message: str, error_code: str = "OCR_PROCESSING_ERROR"):
        super().__init__(message, status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, error_code=error_code)

class PDFParsingError(CoreServiceError): # Or RuleParsingError if generic
    """Exception during PDF/Rule file parsing."""
    def __init__(self, message: str, error_code: str = "RULE_PARSING_ERROR"):
        super().__init__(message, status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, error_code=error_code)

class VisualAnalysisError(CoreServiceError):
    """Exception during visual analysis (OpenCV)."""
    def __init__(self, message: str, error_code: str = "VISUAL_ANALYSIS_ERROR"):
        super().__init__(message, status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, error_code=error_code)

class RuleEngineError(CoreServiceError):
    """Exception within the rule matching engine."""
    def __init__(self, message: str, error_code: str = "RULE_ENGINE_ERROR"):
        super().__init__(message, status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, error_code=error_code)

class DatabaseError(CoreServiceError):
    """Exception related to database operations."""
    def __init__(self, message: str, error_code: str = "DATABASE_ERROR"):
        super().__init__(message, status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, error_code=error_code)

class ConfigurationError(CoreServiceError):
    """Exception for misconfiguration issues."""
    def __init__(self, message: str, error_code: str = "CONFIGURATION_ERROR"):
        super().__init__(message, status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, error_code=error_code)

# Example of a more specific validation error that might be caught by the generic handler
# but could also have its own handler if needed.
class InvalidRuleDefinitionError(CoreServiceError):
    def __init__(self, message: str, error_code: str = "INVALID_RULE_DEFINITION"):
        super().__init__(message, status_code=http_status.HTTP_400_BAD_REQUEST, error_code=error_code)

