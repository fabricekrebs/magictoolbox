"""
Custom middleware for MagicToolbox.

Provides request tracking, logging, and monitoring functionality.
"""
import uuid
import time
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class RequestIDMiddleware(MiddlewareMixin):
    """
    Adds a unique request ID to each request for tracking and logging.
    
    The request ID is stored in request.id and added to the response headers
    as X-Request-ID for client-side tracking.
    """
    
    def process_request(self, request):
        """Add unique ID to request object."""
        request.id = str(uuid.uuid4())
        request.start_time = time.time()
    
    def process_response(self, request, response):
        """Add request ID to response headers and log request duration."""
        if hasattr(request, 'id'):
            response['X-Request-ID'] = request.id
            
            # Log request duration
            if hasattr(request, 'start_time'):
                duration = time.time() - request.start_time
                logger.info(
                    f"Request {request.id} completed",
                    extra={
                        'request_id': request.id,
                        'method': request.method,
                        'path': request.path,
                        'status_code': response.status_code,
                        'duration_ms': round(duration * 1000, 2),
                    }
                )
        
        return response
