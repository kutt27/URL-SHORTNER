from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import URLShortener, URLClick, URLCategory
from .utils import validate_url, is_safe_url, is_valid_custom_alias


class URLShortenerSerializer(serializers.ModelSerializer):
    """Serializer for URL shortening"""
    
    short_url = serializers.SerializerMethodField()
    click_count = serializers.ReadOnlyField()
    created_at = serializers.ReadOnlyField()
    updated_at = serializers.ReadOnlyField()
    
    class Meta:
        model = URLShortener
        fields = [
            'id', 'original_url', 'short_code', 'custom_alias', 'short_url',
            'click_count', 'title', 'description', 'domain', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'short_code', 'domain', 'title', 'description']
    
    def get_short_url(self, obj):
        return obj.get_short_url()
    
    def validate_original_url(self, value):
        """Validate the original URL"""
        try:
            normalized_url = validate_url(value)
            if not is_safe_url(normalized_url):
                raise serializers.ValidationError("URL appears to be unsafe or malicious")
            return normalized_url
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))
    
    def validate_custom_alias(self, value):
        """Validate custom alias"""
        if value:
            if not is_valid_custom_alias(value):
                raise serializers.ValidationError(
                    "Custom alias must be 3-50 characters long and contain only letters, numbers, hyphens, and underscores. "
                    "Reserved words are not allowed."
                )
            
            # Check if alias already exists
            if URLShortener.objects.filter(custom_alias=value, is_active=True).exists():
                raise serializers.ValidationError("This custom alias is already taken.")
            
            # Check if it conflicts with short codes
            if URLShortener.objects.filter(short_code=value, is_active=True).exists():
                raise serializers.ValidationError("This alias conflicts with an existing short code.")
        
        return value


class URLShortenerCreateSerializer(URLShortenerSerializer):
    """Serializer for creating shortened URLs"""
    
    class Meta(URLShortenerSerializer.Meta):
        fields = ['original_url', 'custom_alias']


class URLShortenerListSerializer(serializers.ModelSerializer):
    """Serializer for listing URLs"""
    
    short_url = serializers.SerializerMethodField()
    analytics_url = serializers.SerializerMethodField()
    
    class Meta:
        model = URLShortener
        fields = [
            'id', 'original_url', 'short_code', 'custom_alias', 'short_url',
            'click_count', 'title', 'domain', 'is_active', 'created_at', 'analytics_url'
        ]
    
    def get_short_url(self, obj):
        return obj.get_short_url()
    
    def get_analytics_url(self, obj):
        from django.urls import reverse
        alias = obj.custom_alias or obj.short_code
        return self.context['request'].build_absolute_uri(
            reverse('analytics', kwargs={'short_code': alias})
        )


class URLClickSerializer(serializers.ModelSerializer):
    """Serializer for URL clicks"""
    
    class Meta:
        model = URLClick
        fields = [
            'id', 'ip_address', 'user_agent', 'referer', 'country', 'city',
            'device_type', 'browser', 'os', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class URLAnalyticsSerializer(serializers.Serializer):
    """Serializer for URL analytics data"""
    
    url_info = URLShortenerListSerializer(read_only=True)
    total_clicks = serializers.IntegerField(read_only=True)
    clicks_today = serializers.IntegerField(read_only=True)
    clicks_this_week = serializers.IntegerField(read_only=True)
    clicks_this_month = serializers.IntegerField(read_only=True)
    recent_clicks = URLClickSerializer(many=True, read_only=True)
    click_data = serializers.DictField(read_only=True)


class BulkURLShortenerSerializer(serializers.Serializer):
    """Serializer for bulk URL shortening"""
    
    urls = serializers.ListField(
        child=serializers.URLField(max_length=2048),
        max_length=50,
        help_text="List of URLs to shorten (maximum 50)"
    )
    
    def validate_urls(self, value):
        """Validate URLs"""
        validated_urls = []
        for url in value:
            try:
                normalized_url = validate_url(url)
                if not is_safe_url(normalized_url):
                    raise serializers.ValidationError(f"URL appears to be unsafe: {url}")
                validated_urls.append(normalized_url)
            except DjangoValidationError as e:
                raise serializers.ValidationError(f"Invalid URL '{url}': {str(e)}")
        
        return validated_urls


class BulkURLResultSerializer(serializers.Serializer):
    """Serializer for bulk URL shortening results"""
    
    original_url = serializers.URLField()
    short_url = serializers.URLField(required=False)
    short_code = serializers.CharField(required=False)
    status = serializers.ChoiceField(choices=['success', 'error'])
    error = serializers.CharField(required=False)


class URLCategorySerializer(serializers.ModelSerializer):
    """Serializer for URL categories"""
    
    url_count = serializers.SerializerMethodField()
    
    class Meta:
        model = URLCategory
        fields = ['id', 'name', 'description', 'color', 'icon', 'url_count', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_url_count(self, obj):
        return obj.urls.filter(is_active=True).count()


class URLStatsSerializer(serializers.Serializer):
    """Serializer for overall URL statistics"""
    
    total_urls = serializers.IntegerField()
    total_clicks = serializers.IntegerField()
    urls_today = serializers.IntegerField()
    clicks_today = serializers.IntegerField()
    top_domains = serializers.ListField(child=serializers.DictField())
    recent_activity = serializers.ListField(child=serializers.DictField())
