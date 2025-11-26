"""
Custom middleware for MagicToolbox.

Provides request tracking, logging, and monitoring functionality.
"""
import uuid
import time
import logging
import ipaddress
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

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


class HealthCheckMiddleware(MiddlewareMixin):
    """
    Bypass ALLOWED_HOSTS validation for health check requests from internal IPs.
    
    Azure Container Apps health probes come from internal IPs (typically 100.100.0.0/16)
    which don't match the public FQDN in ALLOWED_HOSTS. This middleware allows these
    health check requests to proceed without host validation.
    """
    
    # Azure Container Apps internal network ranges
    INTERNAL_SUBNETS = [
        ipaddress.ip_network('100.100.0.0/16'),  # Azure Container Apps internal
        ipaddress.ip_network('10.0.0.0/8'),      # Private network range
        ipaddress.ip_network('172.16.0.0/12'),   # Private network range
        ipaddress.ip_network('192.168.0.0/16'),  # Private network range
    ]
    
    def process_request(self, request):
        """
        Check if this is a health check from an internal IP.
        If so, temporarily bypass ALLOWED_HOSTS validation.
        """
        # Only process health check endpoint
        if request.path in ['/health/', '/health', '/readiness/', '/liveness/']:
            # Get the actual client IP (considering X-Forwarded-For if behind proxy)
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                # Get the first IP in the chain (original client)
                client_ip = x_forwarded_for.split(',')[0].strip()
            else:
                client_ip = request.META.get('REMOTE_ADDR', '')
            
            # Check if IP is from internal subnet
            try:
                ip_obj = ipaddress.ip_address(client_ip)
                is_internal = any(ip_obj in subnet for subnet in self.INTERNAL_SUBNETS)
                
                if is_internal:
                    # For internal health checks, we'll allow any host
                    # by temporarily modifying the Host header to match ALLOWED_HOSTS
                    if settings.ALLOWED_HOSTS:
                        # Use the first allowed host or a wildcard pattern
                        allowed_host = settings.ALLOWED_HOSTS[0]
                        if allowed_host.startswith('.'):
                            # Domain pattern like .azurecontainerapps.io
                            request.META['HTTP_HOST'] = f"app{allowed_host}"
                        elif allowed_host == '*':
                            # Wildcard - no change needed
                            pass
                        else:
                            # Specific host
                            request.META['HTTP_HOST'] = allowed_host
                    
                    logger.debug(
                        f"Health check from internal IP {client_ip} allowed",
                        extra={'client_ip': client_ip, 'path': request.path}
                    )
            except ValueError:
                # Invalid IP address, let Django's normal validation handle it
                pass
        
        return None

