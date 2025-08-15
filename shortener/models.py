from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
import string
import random
import hashlib
from urllib.parse import urlparse


class URLShortener(models.Model):
    """Model for storing shortened URLs with analytics"""
    
    original_url = models.URLField(max_length=2048, help_text="The original long URL")
    short_code = models.CharField(max_length=10, unique=True, db_index=True, help_text="The short code for the URL")
    custom_alias = models.CharField(max_length=50, blank=True, null=True, unique=True, help_text="Custom alias for the URL")
    
    # Analytics fields
    click_count = models.PositiveIntegerField(default=0, help_text="Number of times the short URL was clicked")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(blank=True, null=True, help_text="Expiration date for the short URL")
    
    # Optional user association
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='shortened_urls')
    
    # Metadata
    title = models.CharField(max_length=200, blank=True, help_text="Title of the original page")
    description = models.TextField(blank=True, help_text="Description of the original page")
    domain = models.CharField(max_length=100, blank=True, help_text="Domain of the original URL")
    
    # Status
    is_active = models.BooleanField(default=True, help_text="Whether the short URL is active")
    is_public = models.BooleanField(default=True, help_text="Whether the short URL is publicly accessible")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Shortened URL"
        verbose_name_plural = "Shortened URLs"
        indexes = [
            models.Index(fields=['short_code']),
            models.Index(fields=['custom_alias']),
            models.Index(fields=['created_at']),
            models.Index(fields=['domain']),
        ]
    
    def __str__(self):
        return f"{self.get_short_url()} -> {self.original_url[:50]}..."
    
    def save(self, *args, **kwargs):
        if not self.short_code:
            self.short_code = self.generate_short_code()
        
        if not self.domain and self.original_url:
            try:
                parsed_url = urlparse(self.original_url)
                self.domain = parsed_url.netloc.lower()
            except:
                pass
        
        super().save(*args, **kwargs)
    
    def generate_short_code(self, length=6):
        """Generate a unique short code"""
        characters = string.ascii_letters + string.digits
        
        # Try to generate a unique code
        for _ in range(100):  # Max 100 attempts
            code = ''.join(random.choice(characters) for _ in range(length))
            if not URLShortener.objects.filter(short_code=code).exists():
                return code
        
        # If we can't generate a unique code, use a hash-based approach
        hash_input = f"{self.original_url}{timezone.now().isoformat()}"
        hash_object = hashlib.md5(hash_input.encode())
        return hash_object.hexdigest()[:length]
    
    def get_short_url(self):
        """Get the full short URL"""
        from django.conf import settings
        from django.contrib.sites.models import Site
        
        try:
            current_site = Site.objects.get_current()
            domain = current_site.domain
        except:
            domain = 'localhost:8000'
        
        protocol = 'https' if not settings.DEBUG else 'http'
        alias = self.custom_alias or self.short_code
        return f"{protocol}://{domain}/{alias}"
    
    def increment_click_count(self):
        """Increment the click count atomically"""
        self.click_count = models.F('click_count') + 1
        self.save(update_fields=['click_count'])
        self.refresh_from_db()
    
    def is_expired(self):
        """Check if the URL has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def get_analytics_data(self):
        """Get analytics data for this URL"""
        clicks_today = URLClick.objects.filter(
            url=self,
            created_at__date=timezone.now().date()
        ).count()
        
        clicks_this_week = URLClick.objects.filter(
            url=self,
            created_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).count()
        
        clicks_this_month = URLClick.objects.filter(
            url=self,
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).count()
        
        return {
            'total_clicks': self.click_count,
            'clicks_today': clicks_today,
            'clicks_this_week': clicks_this_week,
            'clicks_this_month': clicks_this_month,
            'created_at': self.created_at,
            'last_clicked': self.clicks.order_by('-created_at').first()
        }


class URLClick(models.Model):
    """Model for tracking individual clicks on shortened URLs"""
    
    url = models.ForeignKey(URLShortener, on_delete=models.CASCADE, related_name='clicks')
    ip_address = models.GenericIPAddressField(help_text="IP address of the visitor")
    user_agent = models.TextField(blank=True, help_text="User agent string")
    referer = models.URLField(blank=True, null=True, help_text="Referer URL")
    
    # Geographic data (can be populated by IP geolocation services)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    # Device/Browser info
    device_type = models.CharField(max_length=50, blank=True, help_text="mobile, desktop, tablet")
    browser = models.CharField(max_length=100, blank=True)
    os = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "URL Click"
        verbose_name_plural = "URL Clicks"
        indexes = [
            models.Index(fields=['url', 'created_at']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Click on {self.url.short_code} from {self.ip_address}"


class URLCategory(models.Model):
    """Model for categorizing URLs"""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#667eea', help_text="Hex color code")
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "URL Category"
        verbose_name_plural = "URL Categories"
    
    def __str__(self):
        return self.name


# Add category relationship to URLShortener
URLShortener.add_to_class('category', models.ForeignKey(
    URLCategory, 
    on_delete=models.SET_NULL, 
    blank=True, 
    null=True, 
    related_name='urls'
))
