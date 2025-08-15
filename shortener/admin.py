from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import URLShortener, URLClick, URLCategory


@admin.register(URLShortener)
class URLShortenerAdmin(admin.ModelAdmin):
    list_display = [
        'short_code_link', 'original_url_truncated', 'click_count', 
        'domain', 'created_by', 'created_at', 'is_active', 'status_indicator'
    ]
    list_filter = [
        'is_active', 'is_public', 'created_at', 'domain', 'category'
    ]
    search_fields = [
        'short_code', 'custom_alias', 'original_url', 'title', 'domain'
    ]
    readonly_fields = [
        'short_code', 'click_count', 'created_at', 'updated_at', 'get_short_url_display'
    ]
    fieldsets = (
        ('URL Information', {
            'fields': ('original_url', 'short_code', 'custom_alias', 'get_short_url_display')
        }),
        ('Metadata', {
            'fields': ('title', 'description', 'domain', 'category'),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': ('is_active', 'is_public', 'expires_at', 'created_by')
        }),
        ('Analytics', {
            'fields': ('click_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def short_code_link(self, obj):
        """Display short code as a clickable link"""
        url = obj.get_short_url()
        return format_html(
            '<a href="{}" target="_blank" style="font-family: monospace; font-weight: bold;">{}</a>',
            url, obj.custom_alias or obj.short_code
        )
    short_code_link.short_description = 'Short Code'
    short_code_link.admin_order_field = 'short_code'
    
    def original_url_truncated(self, obj):
        """Display truncated original URL"""
        if len(obj.original_url) > 60:
            return format_html(
                '<span title="{}">{}</span>',
                obj.original_url,
                obj.original_url[:60] + '...'
            )
        return obj.original_url
    original_url_truncated.short_description = 'Original URL'
    original_url_truncated.admin_order_field = 'original_url'
    
    def status_indicator(self, obj):
        """Display status with color indicator"""
        if not obj.is_active:
            return format_html('<span style="color: #dc3545;">● Inactive</span>')
        elif obj.is_expired():
            return format_html('<span style="color: #ffc107;">● Expired</span>')
        else:
            return format_html('<span style="color: #28a745;">● Active</span>')
    status_indicator.short_description = 'Status'
    
    def get_short_url_display(self, obj):
        """Display the full short URL"""
        return obj.get_short_url()
    get_short_url_display.short_description = 'Short URL'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by', 'category')


@admin.register(URLClick)
class URLClickAdmin(admin.ModelAdmin):
    list_display = [
        'url_short_code', 'ip_address', 'country', 'city', 
        'device_type', 'browser', 'created_at'
    ]
    list_filter = [
        'device_type', 'browser', 'country', 'created_at'
    ]
    search_fields = [
        'url__short_code', 'url__custom_alias', 'ip_address', 'country', 'city'
    ]
    readonly_fields = [
        'url', 'ip_address', 'user_agent', 'referer', 'country', 'city',
        'device_type', 'browser', 'os', 'created_at'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def url_short_code(self, obj):
        """Display the short code of the clicked URL"""
        return obj.url.custom_alias or obj.url.short_code
    url_short_code.short_description = 'Short Code'
    url_short_code.admin_order_field = 'url__short_code'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('url')
    
    def has_add_permission(self, request):
        """Disable manual addition of clicks"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Make clicks read-only"""
        return False


@admin.register(URLCategory)
class URLCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'color_display', 'icon_display', 'url_count', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']
    ordering = ['name']
    
    def color_display(self, obj):
        """Display color as a colored box"""
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border-radius: 3px; display: inline-block;"></div>',
            obj.color
        )
    color_display.short_description = 'Color'
    
    def icon_display(self, obj):
        """Display the icon"""
        if obj.icon:
            return format_html('<i class="{}"></i> {}', obj.icon, obj.icon)
        return '-'
    icon_display.short_description = 'Icon'
    
    def url_count(self, obj):
        """Display the number of URLs in this category"""
        return obj.urls.count()
    url_count.short_description = 'URLs Count'


# Customize admin site
admin.site.site_header = "URL Shortener Pro Admin"
admin.site.site_title = "URL Shortener Pro"
admin.site.index_title = "Welcome to URL Shortener Pro Administration"
