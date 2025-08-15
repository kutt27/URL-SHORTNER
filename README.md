# URL Shortener Pro 🔗

A modern, feature-rich URL shortener built with Django, featuring analytics, custom aliases, bulk processing, and a comprehensive REST API. Perfect for portfolio projects and production use.

![URL Shortener Pro](https://img.shields.io/badge/Django-5.1.1-green.svg)
![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

### 🎯 Core Features

- **Custom URL Shortening**: Create short, memorable links with optional custom aliases
- **Analytics Dashboard**: Comprehensive click tracking with charts and statistics
- **Bulk Processing**: Shorten multiple URLs at once with CSV export
- **QR Code Generation**: Automatic QR codes for all shortened URLs
- **Modern UI/UX**: Responsive design with dark/light theme toggle

### 🔒 Security & Performance

- **Rate Limiting**: Configurable limits for anonymous and authenticated users
- **Malicious URL Detection**: Built-in protection against harmful links
- **Security Headers**: Comprehensive security headers and CSP
- **Caching**: Optimized performance with intelligent caching
- **Geolocation**: IP-based location tracking for analytics

### 🚀 API & Integration

- **REST API**: Full-featured API with comprehensive documentation
- **Bulk Operations**: API endpoints for bulk URL processing
- **Real-time Analytics**: Detailed click tracking and statistics
- **Export Capabilities**: CSV export for analytics data

### 📊 Analytics & Insights

- **Click Tracking**: Detailed analytics with device, browser, and location data
- **Visual Charts**: Interactive charts powered by Chart.js
- **Time-based Analysis**: Daily, weekly, and monthly statistics
- **Export Options**: Download analytics data in various formats

## 🛠️ Technology Stack

- **Backend**: Django 5.1.1, Django REST Framework
- **Frontend**: Modern HTML5, CSS3, JavaScript (ES6+)
- **Database**: SQLite (development), PostgreSQL ready
- **Charts**: Chart.js for analytics visualization
- **Icons**: Font Awesome 6
- **Fonts**: Inter & Fira Code from Google Fonts

## 📦 Installation

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Git

### Quick Start

1. **Clone the repository**

```bash
git clone https://github.com/your-username/URL-Shortener-Pro.git
cd URL-Shortener-Pro
```

2. **Create and activate virtual environment**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Run database migrations**

```bash
python manage.py makemigrations
python manage.py migrate
```

5. **Create superuser (optional)**

```bash
python manage.py createsuperuser
```

6. **Start the development server**

```bash
python manage.py runserver
```

7. **Access the application**

- Main app: http://127.0.0.1:8000/
- Admin panel: http://127.0.0.1:8000/admin/
- API documentation: http://127.0.0.1:8000/api/docs/

## 🎮 Usage

### Web Interface

1. **Create Short URLs**

   - Enter your long URL in the main form
   - Optionally add a custom alias
   - Click "Shorten URL" to generate your short link

2. **View Analytics**

   - Click on any shortened URL to view detailed analytics
   - See click counts, geographic data, device types, and more
   - Export data as CSV for further analysis

3. **Bulk Processing**
   - Use the bulk shortener to process multiple URLs
   - Upload lists of URLs and get shortened versions
   - Download results as CSV

### API Usage

The REST API provides programmatic access to all features:

```bash
# Create a short URL
curl -X POST http://127.0.0.1:8000/api/urls/ \
  -H "Content-Type: application/json" \
  -d '{"original_url": "https://example.com/very/long/url"}'

# Get URL details
curl http://127.0.0.1:8000/api/urls/abc123/

# Get analytics
curl http://127.0.0.1:8000/api/analytics/abc123/

# Bulk shorten URLs
curl -X POST http://127.0.0.1:8000/api/urls/bulk/ \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://example.com/1", "https://example.com/2"]}'
```

## 🏗️ Project Structure

```
URL-Shortener-Pro/
├── url_shortener/          # Main Django project
│   ├── settings.py         # Django settings
│   ├── urls.py            # URL routing
│   └── views.py           # Main views
├── shortener/             # URL shortener app
│   ├── models.py          # Database models
│   ├── views.py           # App views
│   ├── api_views.py       # API views
│   ├── serializers.py     # API serializers
│   ├── utils.py           # Utility functions
│   ├── middleware.py      # Custom middleware
│   └── admin.py           # Admin configuration
├── templates/             # HTML templates
│   ├── home.html          # Main page
│   ├── analytics.html     # Analytics dashboard
│   ├── dashboard.html     # User dashboard
│   ├── bulk.html          # Bulk processor
│   └── api_docs.html      # API documentation
├── static/               # Static files
│   ├── css/              # Stylesheets
│   └── js/               # JavaScript files
└── requirements.txt      # Python dependencies
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
python manage.py test

# Run specific test modules
python manage.py test shortener.tests.URLShortenerModelTest
python manage.py test shortener.tests.URLShortenerAPITest

# Run with coverage (install coverage first: pip install coverage)
coverage run --source='.' manage.py test
coverage report
coverage html  # Generate HTML coverage report
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file for production settings:

```env
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:password@localhost/dbname

# Optional: External services
GOOGLE_ANALYTICS_ID=GA-XXXXXXXXX
SENTRY_DSN=https://your-sentry-dsn
```

### Production Settings

For production deployment, consider:

1. **Database**: Switch to PostgreSQL or MySQL
2. **Static Files**: Use WhiteNoise or CDN
3. **Caching**: Redis or Memcached
4. **Security**: HTTPS, secure cookies, HSTS
5. **Monitoring**: Sentry for error tracking

## 📊 API Documentation

### Authentication

The API supports session-based authentication. Higher rate limits apply to authenticated users.

### Rate Limits

- **Anonymous users**: 100 requests/hour
- **Authenticated users**: 1000 requests/hour

### Endpoints

| Method | Endpoint                 | Description           |
| ------ | ------------------------ | --------------------- |
| GET    | `/api/`                  | API information       |
| POST   | `/api/urls/`             | Create short URL      |
| GET    | `/api/urls/list/`        | List URLs (paginated) |
| GET    | `/api/urls/{code}/`      | Get URL details       |
| GET    | `/api/analytics/{code}/` | Get URL analytics     |
| POST   | `/api/urls/bulk/`        | Bulk shorten URLs     |
| GET    | `/api/stats/`            | Overall statistics    |

### Example Responses

**Create URL Response:**

```json
{
  "id": 1,
  "original_url": "https://example.com/very/long/url",
  "short_code": "abc123",
  "custom_alias": null,
  "short_url": "https://yourdomain.com/abc123",
  "click_count": 0,
  "title": "Example Page",
  "domain": "example.com",
  "is_active": true,
  "created_at": "2025-08-15T08:30:00Z"
}
```

**Analytics Response:**

```json
{
  "url_info": {...},
  "total_clicks": 150,
  "clicks_today": 12,
  "clicks_this_week": 45,
  "clicks_this_month": 120,
  "recent_clicks": [...],
  "click_data": {
    "daily_clicks": [...],
    "device_clicks": [...],
    "browser_clicks": [...],
    "country_clicks": [...]
  }
}
```

## 🚀 Deployment

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn", "url_shortener.wsgi:application", "--bind", "0.0.0.0:8000"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Write tests for new features
- Update documentation as needed
- Use meaningful commit messages

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-username/URL-Shortener-Pro/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/URL-Shortener-Pro/discussions)
- **Email**: satheesanamal6@gmail.com

## 🔮 Roadmap

- [ ] User authentication and personal dashboards
- [ ] Team collaboration features
- [ ] Advanced analytics with A/B testing
- [ ] Integration with popular services (Slack, Discord, etc.)
- [ ] Mobile app development
- [ ] Enterprise features and white-labeling
