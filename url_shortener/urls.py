from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import URLShortenerView, RedirectView, AnalyticsView, QRCodeView, DashboardView, BulkShortenerView, APIDocsView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('shortener.api_urls')),
    path('api/docs/', APIDocsView.as_view(), name="api_docs"),
    path('', URLShortenerView.as_view(), name="home"),
    path('dashboard/', DashboardView.as_view(), name="dashboard"),
    path('bulk/', BulkShortenerView.as_view(), name="bulk"),
    path('analytics/<str:short_code>/', AnalyticsView.as_view(), name="analytics"),
    path('qr/<str:short_code>/', QRCodeView.as_view(), name="qr_code"),
    path('<str:short_code>/', RedirectView.as_view(), name="redirect"),
]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
