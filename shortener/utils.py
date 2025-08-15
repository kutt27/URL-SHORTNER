import re
import requests
from urllib.parse import urlparse, urlunparse
from django.core.exceptions import ValidationError
from django.utils import timezone
from user_agents import parse
import logging

logger = logging.getLogger(__name__)


def validate_url(url):
    """
    Validate and normalize a URL
    """
    if not url:
        raise ValidationError("URL cannot be empty")
    
    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Parse URL to validate structure
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            raise ValidationError("Invalid URL format")
        
        # Reconstruct URL to normalize it
        normalized_url = urlunparse((
            parsed.scheme,
            parsed.netloc.lower(),
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
        
        return normalized_url
        
    except Exception as e:
        raise ValidationError(f"Invalid URL: {str(e)}")


def is_safe_url(url):
    """
    Check if URL is safe (not malicious)
    This is a basic implementation - in production, you'd want to use
    more sophisticated malware/phishing detection services
    """
    dangerous_domains = [
        'bit.ly', 'tinyurl.com', 'short.link',  # Prevent double shortening
        'malware-example.com',  # Add known malicious domains
    ]
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Check against dangerous domains
        for dangerous in dangerous_domains:
            if dangerous in domain:
                return False
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}',  # IP addresses
            r'[a-z0-9]{20,}',  # Very long random strings
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, domain):
                return False
        
        return True
        
    except Exception:
        return False


def get_url_metadata(url, timeout=5):
    """
    Fetch metadata (title, description) from a URL
    """
    metadata = {
        'title': '',
        'description': '',
        'favicon': '',
        'status_code': None
    }
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        metadata['status_code'] = response.status_code
        
        if response.status_code == 200:
            content = response.text
            
            # Extract title
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
            if title_match:
                metadata['title'] = title_match.group(1).strip()[:200]
            
            # Extract description from meta tags
            desc_patterns = [
                r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']',
                r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']description["\']',
                r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']',
            ]
            
            for pattern in desc_patterns:
                desc_match = re.search(pattern, content, re.IGNORECASE)
                if desc_match:
                    metadata['description'] = desc_match.group(1).strip()[:500]
                    break
            
            # Extract favicon
            favicon_patterns = [
                r'<link[^>]*rel=["\']icon["\'][^>]*href=["\']([^"\']+)["\']',
                r'<link[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\']icon["\']',
                r'<link[^>]*rel=["\']shortcut icon["\'][^>]*href=["\']([^"\']+)["\']',
            ]
            
            for pattern in favicon_patterns:
                favicon_match = re.search(pattern, content, re.IGNORECASE)
                if favicon_match:
                    favicon_url = favicon_match.group(1)
                    if not favicon_url.startswith('http'):
                        parsed_url = urlparse(url)
                        if favicon_url.startswith('//'):
                            favicon_url = parsed_url.scheme + ':' + favicon_url
                        elif favicon_url.startswith('/'):
                            favicon_url = f"{parsed_url.scheme}://{parsed_url.netloc}{favicon_url}"
                        else:
                            favicon_url = f"{parsed_url.scheme}://{parsed_url.netloc}/{favicon_url}"
                    metadata['favicon'] = favicon_url
                    break
    
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch metadata for {url}: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error fetching metadata for {url}: {str(e)}")
    
    return metadata


def parse_user_agent(user_agent_string):
    """
    Parse user agent string to extract device, browser, and OS information
    """
    if not user_agent_string:
        return {
            'device_type': 'unknown',
            'browser': 'unknown',
            'os': 'unknown'
        }
    
    try:
        user_agent = parse(user_agent_string)
        
        # Determine device type
        if user_agent.is_mobile:
            device_type = 'mobile'
        elif user_agent.is_tablet:
            device_type = 'tablet'
        elif user_agent.is_pc:
            device_type = 'desktop'
        else:
            device_type = 'unknown'
        
        # Get browser info
        browser = f"{user_agent.browser.family}"
        if user_agent.browser.version_string:
            browser += f" {user_agent.browser.version_string}"
        
        # Get OS info
        os = f"{user_agent.os.family}"
        if user_agent.os.version_string:
            os += f" {user_agent.os.version_string}"
        
        return {
            'device_type': device_type,
            'browser': browser[:100],  # Limit length
            'os': os[:100]  # Limit length
        }
        
    except Exception as e:
        logger.warning(f"Failed to parse user agent '{user_agent_string}': {str(e)}")
        return {
            'device_type': 'unknown',
            'browser': 'unknown',
            'os': 'unknown'
        }


def get_client_ip(request):
    """
    Get the client's IP address from the request
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def is_valid_custom_alias(alias):
    """
    Validate custom alias format
    """
    if not alias:
        return True  # Empty alias is valid (will use generated code)
    
    # Check length
    if len(alias) < 3 or len(alias) > 50:
        return False
    
    # Check format (alphanumeric, hyphens, underscores only)
    if not re.match(r'^[a-zA-Z0-9_-]+$', alias):
        return False
    
    # Check for reserved words
    reserved_words = [
        'admin', 'api', 'www', 'mail', 'ftp', 'localhost',
        'dashboard', 'analytics', 'stats', 'help', 'support',
        'about', 'contact', 'privacy', 'terms', 'login', 'register'
    ]
    
    if alias.lower() in reserved_words:
        return False
    
    return True


def generate_qr_code_url(url, size=200):
    """
    Generate QR code URL using a free service
    """
    try:
        from urllib.parse import quote
        encoded_url = quote(url, safe='')
        return f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={encoded_url}"
    except Exception:
        return None
