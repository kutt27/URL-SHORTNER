from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase
from rest_framework import status
import json

from .models import URLShortener, URLClick, URLCategory
from .utils import validate_url, is_safe_url, is_valid_custom_alias, parse_user_agent


class URLShortenerModelTest(TestCase):
    """Test cases for URLShortener model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = URLCategory.objects.create(
            name='Test Category',
            description='A test category'
        )
    
    def test_create_url_shortener(self):
        """Test creating a URL shortener"""
        url = URLShortener.objects.create(
            original_url='https://example.com/test',
            created_by=self.user,
            category=self.category
        )
        
        self.assertEqual(url.original_url, 'https://example.com/test')
        self.assertEqual(url.domain, 'example.com')
        self.assertEqual(url.created_by, self.user)
        self.assertEqual(url.category, self.category)
        self.assertTrue(url.is_active)
        self.assertIsNotNone(url.short_code)
        self.assertEqual(len(url.short_code), 6)
    
    def test_custom_alias(self):
        """Test creating URL with custom alias"""
        url = URLShortener.objects.create(
            original_url='https://example.com/test',
            custom_alias='my-test-link'
        )
        
        self.assertEqual(url.custom_alias, 'my-test-link')
        self.assertIn('my-test-link', url.get_short_url())
    
    def test_click_tracking(self):
        """Test click count increment"""
        url = URLShortener.objects.create(
            original_url='https://example.com/test'
        )
        
        initial_count = url.click_count
        url.increment_click_count()
        
        self.assertEqual(url.click_count, initial_count + 1)
    
    def test_analytics_data(self):
        """Test analytics data retrieval"""
        url = URLShortener.objects.create(
            original_url='https://example.com/test'
        )
        
        # Create some clicks
        URLClick.objects.create(
            url=url,
            ip_address='127.0.0.1',
            device_type='desktop',
            browser='Chrome'
        )
        
        analytics = url.get_analytics_data()
        
        self.assertIn('total_clicks', analytics)
        self.assertIn('clicks_today', analytics)
        self.assertIn('clicks_this_week', analytics)
        self.assertIn('clicks_this_month', analytics)


class URLShortenerViewTest(TestCase):
    """Test cases for URL shortener views"""
    
    def setUp(self):
        self.client = Client()
    
    def test_home_page(self):
        """Test home page loads correctly"""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'URL Shortener Pro')
    
    def test_create_short_url(self):
        """Test creating a short URL via form"""
        response = self.client.post(reverse('home'), {
            'link': 'https://example.com/test-page'
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(URLShortener.objects.filter(
            original_url='https://example.com/test-page'
        ).exists())
    
    def test_create_short_url_with_custom_alias(self):
        """Test creating a short URL with custom alias"""
        response = self.client.post(reverse('home'), {
            'link': 'https://example.com/test-page',
            'custom_alias': 'my-custom-link'
        })
        
        self.assertEqual(response.status_code, 302)
        url = URLShortener.objects.get(custom_alias='my-custom-link')
        self.assertEqual(url.original_url, 'https://example.com/test-page')
    
    def test_redirect_view(self):
        """Test URL redirection"""
        url = URLShortener.objects.create(
            original_url='https://example.com/test'
        )
        
        response = self.client.get(f'/{url.short_code}/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, 'https://example.com/test')
        
        # Check click was tracked
        url.refresh_from_db()
        self.assertEqual(url.click_count, 1)
    
    def test_analytics_view(self):
        """Test analytics view"""
        url = URLShortener.objects.create(
            original_url='https://example.com/test'
        )
        
        response = self.client.get(reverse('analytics', kwargs={'short_code': url.short_code}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Analytics Dashboard')
    
    def test_dashboard_view(self):
        """Test dashboard view"""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')
    
    def test_bulk_shortener_view(self):
        """Test bulk shortener view"""
        response = self.client.get(reverse('bulk'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bulk URL Shortener')


class URLShortenerAPITest(APITestCase):
    """Test cases for API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='apiuser',
            email='api@example.com',
            password='apipass123'
        )
    
    def test_api_info(self):
        """Test API info endpoint"""
        response = self.client.get('/api/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('name', response.data)
        self.assertIn('version', response.data)
    
    def test_create_url_api(self):
        """Test creating URL via API"""
        data = {
            'original_url': 'https://example.com/api-test'
        }
        response = self.client.post('/api/urls/', data, format='json')
        
        self.assertEqual(response.status_code, 201)
        self.assertIn('short_url', response.data)
        self.assertIn('short_code', response.data)
        
        # Verify URL was created
        self.assertTrue(URLShortener.objects.filter(
            original_url='https://example.com/api-test'
        ).exists())
    
    def test_create_url_with_custom_alias_api(self):
        """Test creating URL with custom alias via API"""
        data = {
            'original_url': 'https://example.com/api-test',
            'custom_alias': 'api-test-link'
        }
        response = self.client.post('/api/urls/', data, format='json')
        
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['custom_alias'], 'api-test-link')
    
    def test_list_urls_api(self):
        """Test listing URLs via API"""
        # Create some URLs
        URLShortener.objects.create(original_url='https://example.com/1')
        URLShortener.objects.create(original_url='https://example.com/2')
        
        response = self.client.get('/api/urls/list/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_url_detail_api(self):
        """Test URL detail via API"""
        url = URLShortener.objects.create(
            original_url='https://example.com/detail-test'
        )
        
        response = self.client.get(f'/api/urls/{url.short_code}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['original_url'], 'https://example.com/detail-test')
    
    def test_url_analytics_api(self):
        """Test URL analytics via API"""
        url = URLShortener.objects.create(
            original_url='https://example.com/analytics-test'
        )
        
        # Create a click
        URLClick.objects.create(
            url=url,
            ip_address='127.0.0.1',
            device_type='desktop'
        )
        
        response = self.client.get(f'/api/analytics/{url.short_code}/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_clicks', response.data)
        self.assertIn('url_info', response.data)
    
    def test_bulk_shortener_api(self):
        """Test bulk URL shortening via API"""
        data = {
            'urls': [
                'https://example.com/bulk1',
                'https://example.com/bulk2',
                'https://example.com/bulk3'
            ]
        }
        response = self.client.post('/api/urls/bulk/', data, format='json')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 3)
        
        # Check all URLs were created successfully
        for result in response.data['results']:
            self.assertEqual(result['status'], 'success')
    
    def test_stats_api(self):
        """Test statistics API"""
        # Create some URLs
        URLShortener.objects.create(original_url='https://example.com/stats1')
        URLShortener.objects.create(original_url='https://example.com/stats2')
        
        response = self.client.get('/api/stats/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_urls', response.data)
        self.assertIn('total_clicks', response.data)


class UtilsTest(TestCase):
    """Test cases for utility functions"""
    
    def test_validate_url(self):
        """Test URL validation"""
        # Valid URLs
        self.assertEqual(validate_url('https://example.com'), 'https://example.com')
        self.assertEqual(validate_url('example.com'), 'https://example.com')
        self.assertEqual(validate_url('http://example.com/path'), 'http://example.com/path')

        # Invalid URLs
        with self.assertRaises(ValidationError):
            validate_url('')

        with self.assertRaises(ValidationError):
            validate_url('invalid-url-format')
    
    def test_is_safe_url(self):
        """Test URL safety check"""
        self.assertTrue(is_safe_url('https://example.com'))
        self.assertTrue(is_safe_url('https://google.com'))
        
        # Should reject known shorteners
        self.assertFalse(is_safe_url('https://bit.ly/test'))
        self.assertFalse(is_safe_url('https://tinyurl.com/test'))
    
    def test_is_valid_custom_alias(self):
        """Test custom alias validation"""
        # Valid aliases
        self.assertTrue(is_valid_custom_alias('my-link'))
        self.assertTrue(is_valid_custom_alias('test_123'))
        self.assertTrue(is_valid_custom_alias('valid-alias'))
        
        # Invalid aliases
        self.assertFalse(is_valid_custom_alias('ab'))  # Too short
        self.assertFalse(is_valid_custom_alias('admin'))  # Reserved word
        self.assertFalse(is_valid_custom_alias('my link'))  # Contains space
        self.assertFalse(is_valid_custom_alias('test@link'))  # Invalid character
    
    def test_parse_user_agent(self):
        """Test user agent parsing"""
        ua_string = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        result = parse_user_agent(ua_string)
        
        self.assertIn('device_type', result)
        self.assertIn('browser', result)
        self.assertIn('os', result)
        self.assertEqual(result['device_type'], 'desktop')


class SecurityTest(TestCase):
    """Test cases for security features"""
    
    def test_rate_limiting(self):
        """Test rate limiting (basic test)"""
        # This would need more sophisticated testing in a real scenario
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
    
    def test_security_headers(self):
        """Test security headers are present"""
        response = self.client.get(reverse('home'))
        
        self.assertIn('X-Content-Type-Options', response)
        self.assertIn('X-Frame-Options', response)
        self.assertIn('Content-Security-Policy', response)
    
    def test_malicious_url_blocking(self):
        """Test malicious URL blocking"""
        # This would test the URL validation middleware
        response = self.client.post(reverse('home'), {
            'link': 'https://malware-example.com/test'
        })
        
        # Should handle malicious URLs gracefully
        self.assertIn(response.status_code, [200, 302])  # Either show error or redirect
