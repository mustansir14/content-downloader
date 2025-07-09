class BaseContentDownloaderException(Exception):
    """Base exception for content downloader errors."""
    pass

class AuthenticationError(BaseContentDownloaderException):
    """Raised when authentication fails."""
    pass

class RequestFailedError(BaseContentDownloaderException):
    """Raised when a request fails"""
    pass