from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import FormView, View
from django.urls import reverse_lazy
from django.http import JsonResponse, Http404
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.utils import timezone
from django.db import transaction, models
import logging

from .forms import UrlForm
from shortener.models import URLShortener, URLClick
from shortener.utils import (
    validate_url, is_safe_url, get_url_metadata,
    parse_user_agent, get_client_ip, generate_qr_code_url
)

logger = logging.getLogger(__name__)


class URLShortenerView(FormView):
    """Main view for URL shortening"""
    template_name = 'home.html'
    form_class = UrlForm
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        original_url = form.cleaned_data['link']
        custom_alias = form.cleaned_data.get('custom_alias')

        try:
            # Validate and normalize URL
            normalized_url = validate_url(original_url)

            # Check if URL is safe
            if not is_safe_url(normalized_url):
                self.success_url += '?link=Unsafe URL detected'
                return super().form_valid(form)

            # Check if URL already exists (only if no custom alias is provided)
            if not custom_alias:
                existing_url = URLShortener.objects.filter(
                    original_url=normalized_url,
                    is_active=True,
                    custom_alias__isnull=True
                ).first()

                if existing_url:
                    # Return existing short URL
                    short_url = existing_url.get_short_url()
                    self.success_url += f'?link={short_url}'
                    return super().form_valid(form)

            # Create new short URL
            with transaction.atomic():
                url_obj = URLShortener.objects.create(
                    original_url=normalized_url,
                    custom_alias=custom_alias if custom_alias else None,
                    created_by=self.request.user if self.request.user.is_authenticated else None
                )

                # Fetch metadata in background (non-blocking)
                try:
                    metadata = get_url_metadata(normalized_url)
                    if metadata['title']:
                        url_obj.title = metadata['title']
                    if metadata['description']:
                        url_obj.description = metadata['description']
                    url_obj.save(update_fields=['title', 'description'])
                except Exception as e:
                    logger.warning(f"Failed to fetch metadata for {normalized_url}: {str(e)}")

                short_url = url_obj.get_short_url()
                self.success_url += f'?link={short_url}'

                # Log successful creation
                alias_info = f" with alias '{custom_alias}'" if custom_alias else ""
                logger.info(f"Created short URL {url_obj.short_code}{alias_info} for {normalized_url}")

        except ValidationError as e:
            self.success_url += '?link=Give Valid Url'
            logger.warning(f"Invalid URL submitted: {original_url} - {str(e)}")
        except Exception as e:
            self.success_url += '?link=Error creating short URL'
            logger.error(f"Unexpected error creating short URL for {original_url}: {str(e)}")

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        link_param = self.request.GET.get('link')
        if link_param:
            context['link'] = link_param
        return context


class RedirectView(View):
    """Handle redirects from short URLs"""

    def get(self, request, short_code):
        try:
            # Try to find by short_code first, then by custom_alias
            url_obj = URLShortener.objects.filter(
                models.Q(short_code=short_code) | models.Q(custom_alias=short_code),
                is_active=True
            ).first()

            if not url_obj:
                raise Http404("Short URL not found")

            # Check if URL has expired
            if url_obj.is_expired():
                return render(request, 'error.html', {
                    'error_title': 'Link Expired',
                    'error_message': 'This short URL has expired and is no longer available.'
                })

            # Track the click
            self.track_click(request, url_obj)

            # Increment click count
            url_obj.increment_click_count()

            # Redirect to original URL
            return redirect(url_obj.original_url)

        except Http404:
            return render(request, 'error.html', {
                'error_title': 'Link Not Found',
                'error_message': 'The short URL you requested could not be found.'
            })
        except Exception as e:
            logger.error(f"Error redirecting short code {short_code}: {str(e)}")
            return render(request, 'error.html', {
                'error_title': 'Error',
                'error_message': 'An error occurred while processing your request.'
            })

    def track_click(self, request, url_obj):
        """Track click analytics with enhanced geolocation"""
        try:
            ip_address = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            referer = request.META.get('HTTP_REFERER', '')

            # Parse user agent
            ua_info = parse_user_agent(user_agent)

            # Get geolocation data from middleware
            geo_data = getattr(request, 'geo_data', {})

            # Create click record
            URLClick.objects.create(
                url=url_obj,
                ip_address=ip_address,
                user_agent=user_agent[:1000],  # Limit length
                referer=referer[:2000] if referer else None,
                device_type=ua_info['device_type'],
                browser=ua_info['browser'],
                os=ua_info['os'],
                country=geo_data.get('country', ''),
                city=geo_data.get('city', '')
            )

        except Exception as e:
            logger.warning(f"Failed to track click for {url_obj.short_code}: {str(e)}")


class AnalyticsView(View):
    """View for displaying URL analytics"""

    def get(self, request, short_code):
        try:
            # Find the URL object
            url_obj = URLShortener.objects.filter(
                models.Q(short_code=short_code) | models.Q(custom_alias=short_code),
                is_active=True
            ).first()

            if not url_obj:
                raise Http404("Short URL not found")

            # Check if user has permission to view analytics
            if not url_obj.is_public and url_obj.created_by != request.user:
                if not request.user.is_authenticated:
                    return redirect('login')  # Redirect to login if not authenticated
                else:
                    raise Http404("Analytics not available")

            # Get analytics data
            analytics_data = url_obj.get_analytics_data()

            # Get recent clicks (last 30 days)
            recent_clicks = URLClick.objects.filter(
                url=url_obj,
                created_at__gte=timezone.now() - timezone.timedelta(days=30)
            ).order_by('-created_at')[:100]

            # Aggregate data for charts
            click_data = self.get_click_analytics(url_obj)

            context = {
                'url_obj': url_obj,
                'analytics_data': analytics_data,
                'recent_clicks': recent_clicks,
                'click_data': click_data,
                'qr_code_url': generate_qr_code_url(url_obj.get_short_url()),
            }

            return render(request, 'analytics.html', context)

        except Http404:
            return render(request, 'error.html', {
                'error_title': 'Analytics Not Found',
                'error_message': 'The analytics for this short URL could not be found or you do not have permission to view them.'
            })
        except Exception as e:
            logger.error(f"Error displaying analytics for {short_code}: {str(e)}")
            return render(request, 'error.html', {
                'error_title': 'Error',
                'error_message': 'An error occurred while loading the analytics.'
            })

    def get_click_analytics(self, url_obj):
        """Get aggregated click data for charts"""
        from django.db.models import Count
        from django.utils import timezone
        from datetime import timedelta

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
        ).order_by('-count')[:10]  # Top 10 browsers

        # Country distribution
        country_clicks = URLClick.objects.filter(
            url=url_obj
        ).exclude(
            country=''
        ).values('country').annotate(
            count=Count('id')
        ).order_by('-count')[:10]  # Top 10 countries

        return {
            'daily_clicks': list(daily_clicks),
            'device_clicks': list(device_clicks),
            'browser_clicks': list(browser_clicks),
            'country_clicks': list(country_clicks),
        }


class QRCodeView(View):
    """Generate QR code for a short URL"""

    def get(self, request, short_code):
        try:
            url_obj = URLShortener.objects.filter(
                models.Q(short_code=short_code) | models.Q(custom_alias=short_code),
                is_active=True
            ).first()

            if not url_obj:
                raise Http404("Short URL not found")

            qr_url = generate_qr_code_url(url_obj.get_short_url(), size=300)

            if qr_url:
                return redirect(qr_url)
            else:
                return JsonResponse({'error': 'Could not generate QR code'}, status=500)

        except Exception as e:
            logger.error(f"Error generating QR code for {short_code}: {str(e)}")
            return JsonResponse({'error': 'Error generating QR code'}, status=500)


class DashboardView(View):
    """Dashboard view for users to see their URLs"""

    def get(self, request):
        # Get recent URLs (last 50)
        recent_urls = URLShortener.objects.filter(
            is_active=True
        ).order_by('-created_at')[:50]

        # Get some statistics
        total_urls = URLShortener.objects.filter(is_active=True).count()
        total_clicks = sum(url.click_count for url in recent_urls)

        context = {
            'recent_urls': recent_urls,
            'total_urls': total_urls,
            'total_clicks': total_clicks,
        }

        return render(request, 'dashboard.html', context)


class BulkShortenerView(View):
    """View for bulk URL shortening"""

    def get(self, request):
        return render(request, 'bulk.html')

    def post(self, request):
        urls_text = request.POST.get('urls', '')
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]

        results = []
        for original_url in urls:
            try:
                normalized_url = validate_url(original_url)
                if is_safe_url(normalized_url):
                    # Check if URL already exists
                    existing_url = URLShortener.objects.filter(
                        original_url=normalized_url,
                        is_active=True
                    ).first()

                    if existing_url:
                        short_url = existing_url.get_short_url()
                    else:
                        url_obj = URLShortener.objects.create(
                            original_url=normalized_url,
                            created_by=request.user if request.user.is_authenticated else None
                        )
                        short_url = url_obj.get_short_url()

                    results.append({
                        'original': original_url,
                        'shortened': short_url,
                        'status': 'success'
                    })
                else:
                    results.append({
                        'original': original_url,
                        'shortened': '',
                        'status': 'error',
                        'error': 'Unsafe URL detected'
                    })
            except ValidationError as e:
                results.append({
                    'original': original_url,
                    'shortened': '',
                    'status': 'error',
                    'error': str(e)
                })
            except Exception as e:
                results.append({
                    'original': original_url,
                    'shortened': '',
                    'status': 'error',
                    'error': 'Error processing URL'
                })

        return JsonResponse({'results': results})


class APIDocsView(View):
    """View for API documentation"""

    def get(self, request):
        return render(request, 'api_docs.html')


# Keep the old class name for backward compatibility
class Urlgenerate(URLShortenerView):
    pass

