import time
import hashlib
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add security headers to all responses"""
    
    def process_response(self, request, response):
        # Security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Content Security Policy
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com",
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com",
            "img-src 'self' data: https:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'"
        ]
        response['Content-Security-Policy'] = '; '.join(csp_directives)
        
        return response


class RateLimitMiddleware(MiddlewareMixin):
    """Rate limiting middleware for additional protection"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        # Skip rate limiting for admin and static files
        if request.path.startswith('/admin/') or request.path.startswith('/static/'):
            return None
        
        # Get client IP
        ip = self.get_client_ip(request)
        
        # Different limits for different endpoints
        if request.path.startswith('/api/'):
            return self.check_api_rate_limit(request, ip)
        elif request.method == 'POST':
            return self.check_form_rate_limit(request, ip)
        
        return None
    
    def get_client_ip(self, request):
        """Get the client's IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def check_api_rate_limit(self, request, ip):
        """Check rate limit for API endpoints"""
        # Higher limits for authenticated users
        if request.user.is_authenticated:
            limit = 1000  # per hour
            window = 3600
        else:
            limit = 100  # per hour
            window = 3600
        
        cache_key = f"api_rate_limit:{ip}"
        return self.check_rate_limit(cache_key, limit, window)
    
    def check_form_rate_limit(self, request, ip):
        """Check rate limit for form submissions"""
        limit = 50  # per hour
        window = 3600
        
        cache_key = f"form_rate_limit:{ip}"
        return self.check_rate_limit(cache_key, limit, window)
    
    def check_rate_limit(self, cache_key, limit, window):
        """Generic rate limit checker"""
        try:
            current_requests = cache.get(cache_key, 0)
            
            if current_requests >= limit:
                response = HttpResponse(
                    "Rate limit exceeded. Please try again later.",
                    content_type="text/plain",
                    status=429
                )
                return response
            
            # Increment counter
            cache.set(cache_key, current_requests + 1, window)
            
        except Exception as e:
            logger.warning(f"Rate limiting error: {str(e)}")
            # Don't block requests if rate limiting fails
            pass
        
        return None


class ClickTrackingMiddleware(MiddlewareMixin):
    """Enhanced click tracking middleware"""

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        # Only process redirect requests
        if not self.is_redirect_request(request):
            return None

        # Add basic geo data placeholder to request
        request.geo_data = {}

        return None

    def is_redirect_request(self, request):
        """Check if this is a redirect request"""
        # Simple heuristic: single path segment that's not a known route
        path_parts = [p for p in request.path.split('/') if p]
        return (
            len(path_parts) == 1 and
            not request.path.startswith(('/admin/', '/api/', '/dashboard/', '/bulk/', '/analytics/', '/qr/'))
        )


class URLValidationMiddleware(MiddlewareMixin):
    """Additional URL validation and security checks"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Load malicious domain list (in production, this would be from a database or external service)
        self.malicious_domains = set([
            'malware-example.com',
            'phishing-site.net',
            'spam-domain.org',
            # Add more known malicious domains
        ])
        super().__init__(get_response)
    
    def process_request(self, request):
        # Only check URL creation requests
        if not (request.method == 'POST' and 
                (request.path == '/' or request.path.startswith('/api/urls/'))):
            return None
        
        # Get URL from request
        url = None
        if request.content_type == 'application/json':
            try:
                import json
                data = json.loads(request.body)
                url = data.get('original_url')
            except:
                pass
        else:
            url = request.POST.get('link') or request.POST.get('original_url')
        
        if url:
            # Check against malicious domains
            if self.is_malicious_url(url):
                if request.path.startswith('/api/'):
                    return JsonResponse({
                        'error': 'URL blocked for security reasons'
                    }, status=400)
                else:
                    # For web interface, let the view handle it
                    request.security_blocked = True
        
        return None
    
    def is_malicious_url(self, url):
        """Check if URL is potentially malicious"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url.lower())
            domain = parsed.netloc
            
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Check against known malicious domains
            if domain in self.malicious_domains:
                return True
            
            # Check for suspicious patterns
            suspicious_patterns = [
                'bit.ly',  # Prevent double shortening
                'tinyurl.com',
                'short.link',
                # Add more patterns as needed
            ]
            
            for pattern in suspicious_patterns:
                if pattern in domain:
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"URL validation error: {str(e)}")
            return False


class PerformanceMiddleware(MiddlewareMixin):
    """Performance monitoring and optimization"""
    
    def process_request(self, request):
        request.start_time = time.time()
        return None
    
    def process_response(self, request, response):
        # Add performance headers
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            response['X-Response-Time'] = f"{duration:.3f}s"
        
        # Add cache headers for static content
        if request.path.startswith('/static/'):
            response['Cache-Control'] = 'public, max-age=31536000'  # 1 year
        elif request.path.startswith('/api/'):
            response['Cache-Control'] = 'no-cache, must-revalidate'
        
        return response
