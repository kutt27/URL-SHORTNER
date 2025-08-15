from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import logging

from .models import URLShortener, URLClick, URLCategory
from .serializers import (
    URLShortenerSerializer, URLShortenerCreateSerializer, URLShortenerListSerializer,
    URLAnalyticsSerializer, BulkURLShortenerSerializer, BulkURLResultSerializer,
    URLCategorySerializer, URLStatsSerializer
)
from .utils import get_url_metadata

logger = logging.getLogger(__name__)


class URLShortenerCreateAPIView(generics.CreateAPIView):
    """API endpoint for creating shortened URLs"""
    
    serializer_class = URLShortenerCreateSerializer
    throttle_classes = [AnonRateThrottle, UserRateThrottle]
    
    def perform_create(self, serializer):
        """Create URL with metadata fetching"""
        url_obj = serializer.save(
            created_by=self.request.user if self.request.user.is_authenticated else None
        )
        
        # Fetch metadata in background (non-blocking)
        try:
            metadata = get_url_metadata(url_obj.original_url)
            if metadata['title']:
                url_obj.title = metadata['title']
            if metadata['description']:
                url_obj.description = metadata['description']
            url_obj.save(update_fields=['title', 'description'])
        except Exception as e:
            logger.warning(f"Failed to fetch metadata for {url_obj.original_url}: {str(e)}")
    
    def create(self, request, *args, **kwargs):
        """Create shortened URL and return full details"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check if URL already exists (if no custom alias)
        original_url = serializer.validated_data['original_url']
        custom_alias = serializer.validated_data.get('custom_alias')
        
        if not custom_alias:
            existing_url = URLShortener.objects.filter(
                original_url=original_url,
                is_active=True,
                custom_alias__isnull=True
            ).first()
            
            if existing_url:
                response_serializer = URLShortenerSerializer(existing_url, context={'request': request})
                return Response(response_serializer.data, status=status.HTTP_200_OK)
        
        self.perform_create(serializer)
        
        # Return full URL details
        response_serializer = URLShortenerSerializer(serializer.instance, context={'request': request})
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class URLShortenerListAPIView(generics.ListAPIView):
    """API endpoint for listing shortened URLs"""
    
    serializer_class = URLShortenerListSerializer
    throttle_classes = [AnonRateThrottle, UserRateThrottle]
    
    def get_queryset(self):
        """Get URLs with optional filtering"""
        queryset = URLShortener.objects.filter(is_active=True).order_by('-created_at')
        
        # Filter by domain
        domain = self.request.query_params.get('domain')
        if domain:
            queryset = queryset.filter(domain__icontains=domain)
        
        # Filter by date range
        days = self.request.query_params.get('days')
        if days:
            try:
                days_int = int(days)
                since_date = timezone.now() - timedelta(days=days_int)
                queryset = queryset.filter(created_at__gte=since_date)
            except ValueError:
                pass
        
        return queryset


class URLShortenerDetailAPIView(generics.RetrieveAPIView):
    """API endpoint for retrieving URL details"""
    
    serializer_class = URLShortenerSerializer
    throttle_classes = [AnonRateThrottle, UserRateThrottle]
    lookup_field = 'short_code'
    
    def get_object(self):
        """Get URL by short_code or custom_alias"""
        short_code = self.kwargs['short_code']
        return get_object_or_404(
            URLShortener,
            Q(short_code=short_code) | Q(custom_alias=short_code),
            is_active=True
        )


class URLAnalyticsAPIView(APIView):
    """API endpoint for URL analytics"""
    
    throttle_classes = [AnonRateThrottle, UserRateThrottle]
    
    def get(self, request, short_code):
        """Get analytics for a specific URL"""
        url_obj = get_object_or_404(
            URLShortener,
            Q(short_code=short_code) | Q(custom_alias=short_code),
            is_active=True
        )
        
        # Get analytics data
        analytics_data = url_obj.get_analytics_data()
        
        # Get recent clicks
        recent_clicks = URLClick.objects.filter(
            url=url_obj,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).order_by('-created_at')[:50]
        
        # Aggregate data for charts
        click_data = self._get_click_analytics(url_obj)
        
        data = {
            'url_info': URLShortenerListSerializer(url_obj, context={'request': request}).data,
            'total_clicks': analytics_data['total_clicks'],
            'clicks_today': analytics_data['clicks_today'],
            'clicks_this_week': analytics_data['clicks_this_week'],
            'clicks_this_month': analytics_data['clicks_this_month'],
            'recent_clicks': [
                {
                    'ip_address': click.ip_address,
                    'country': click.country,
                    'city': click.city,
                    'device_type': click.device_type,
                    'browser': click.browser,
                    'created_at': click.created_at
                }
                for click in recent_clicks
            ],
            'click_data': click_data
        }
        
        return Response(data)
    
    def _get_click_analytics(self, url_obj):
        """Get aggregated click data for charts"""
        from django.db.models import Count
        
        # Last 30 days click data
        thirty_days_ago = timezone.now() - timedelta(days=30)
        daily_clicks = URLClick.objects.filter(
            url=url_obj,
            created_at__gte=thirty_days_ago
        ).extra(
            select={'day': 'date(created_at)'}
        ).values('day').annotate(
            clicks=Count('id')
        ).order_by('day')
        
        # Device type distribution
        device_clicks = URLClick.objects.filter(url=url_obj).values('device_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Browser distribution
        browser_clicks = URLClick.objects.filter(url=url_obj).values('browser').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Country distribution
        country_clicks = URLClick.objects.filter(
            url=url_obj
        ).exclude(
            country=''
        ).values('country').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        return {
            'daily_clicks': list(daily_clicks),
            'device_clicks': list(device_clicks),
            'browser_clicks': list(browser_clicks),
            'country_clicks': list(country_clicks),
        }


class BulkURLShortenerAPIView(APIView):
    """API endpoint for bulk URL shortening"""
    
    throttle_classes = [AnonRateThrottle, UserRateThrottle]
    
    def post(self, request):
        """Shorten multiple URLs at once"""
        serializer = BulkURLShortenerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        urls = serializer.validated_data['urls']
        results = []
        
        for original_url in urls:
            try:
                # Check if URL already exists
                existing_url = URLShortener.objects.filter(
                    original_url=original_url,
                    is_active=True
                ).first()
                
                if existing_url:
                    short_url = existing_url.get_short_url()
                    short_code = existing_url.custom_alias or existing_url.short_code
                else:
                    with transaction.atomic():
                        url_obj = URLShortener.objects.create(
                            original_url=original_url,
                            created_by=request.user if request.user.is_authenticated else None
                        )
                        short_url = url_obj.get_short_url()
                        short_code = url_obj.short_code
                
                results.append({
                    'original_url': original_url,
                    'short_url': short_url,
                    'short_code': short_code,
                    'status': 'success'
                })
                
            except Exception as e:
                logger.error(f"Error shortening URL {original_url}: {str(e)}")
                results.append({
                    'original_url': original_url,
                    'short_url': '',
                    'short_code': '',
                    'status': 'error',
                    'error': str(e)
                })
        
        return Response({'results': results})


class URLStatsAPIView(APIView):
    """API endpoint for overall URL statistics"""
    
    throttle_classes = [AnonRateThrottle, UserRateThrottle]
    
    def get(self, request):
        """Get overall statistics"""
        today = timezone.now().date()
        
        # Basic stats
        total_urls = URLShortener.objects.filter(is_active=True).count()
        total_clicks = sum(url.click_count for url in URLShortener.objects.filter(is_active=True))
        urls_today = URLShortener.objects.filter(created_at__date=today).count()
        clicks_today = URLClick.objects.filter(created_at__date=today).count()
        
        # Top domains
        top_domains = URLShortener.objects.filter(
            is_active=True
        ).values('domain').annotate(
            count=Count('id'),
            total_clicks=Count('clicks')
        ).order_by('-count')[:10]
        
        # Recent activity
        recent_urls = URLShortener.objects.filter(
            is_active=True
        ).order_by('-created_at')[:10]
        
        recent_activity = [
            {
                'type': 'url_created',
                'url': url.get_short_url(),
                'domain': url.domain,
                'created_at': url.created_at
            }
            for url in recent_urls
        ]
        
        data = {
            'total_urls': total_urls,
            'total_clicks': total_clicks,
            'urls_today': urls_today,
            'clicks_today': clicks_today,
            'top_domains': list(top_domains),
            'recent_activity': recent_activity
        }
        
        return Response(data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_info(request):
    """API information endpoint"""
    return Response({
        'name': 'URL Shortener Pro API',
        'version': '1.0',
        'description': 'REST API for URL shortening with analytics',
        'endpoints': {
            'create_url': '/api/urls/',
            'list_urls': '/api/urls/list/',
            'url_details': '/api/urls/{short_code}/',
            'url_analytics': '/api/analytics/{short_code}/',
            'bulk_shorten': '/api/urls/bulk/',
            'stats': '/api/stats/',
            'api_info': '/api/'
        },
        'documentation': request.build_absolute_uri('/api/docs/'),
        'rate_limits': {
            'anonymous': '100 requests per hour',
            'authenticated': '1000 requests per hour'
        }
    })
