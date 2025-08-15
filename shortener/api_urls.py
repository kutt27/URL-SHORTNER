from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

# API URL patterns
urlpatterns = [
    # API Info
    path('', api_views.api_info, name='api_info'),
    
    # URL Management
    path('urls/', api_views.URLShortenerCreateAPIView.as_view(), name='api_create_url'),
    path('urls/list/', api_views.URLShortenerListAPIView.as_view(), name='api_list_urls'),
    path('urls/bulk/', api_views.BulkURLShortenerAPIView.as_view(), name='api_bulk_urls'),
    path('urls/<str:short_code>/', api_views.URLShortenerDetailAPIView.as_view(), name='api_url_detail'),
    
    # Analytics
    path('analytics/<str:short_code>/', api_views.URLAnalyticsAPIView.as_view(), name='api_url_analytics'),
    
    # Statistics
    path('stats/', api_views.URLStatsAPIView.as_view(), name='api_stats'),
]
