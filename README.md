# URL Shortener API

A production-grade URL shortening service with advanced analytics, built with FastAPI, PostgreSQL, and Redis.

## 🚀 Features

- **URL Shortening**: Convert long URLs into short, shareable codes
- **Analytics Tracking**: Track clicks, geographic data, device information, and referrers
- **Multi-user Support**: API key-based authentication for multiple users
- **Caching Layer**: Redis integration for high-performance caching
- **Production Ready**: Docker containerization, health checks, and multi-worker setup
- **Comprehensive Testing**: 14+ automated tests with 100% endpoint coverage
- **Interactive Documentation**: Auto-generated Swagger/OpenAPI documentation

## 📊 Project Status

- ✅ Backend: Production-ready
- ✅ API: 7 fully functional endpoints
- ✅ Tests: 14/14 passing (100% coverage)
- ✅ Documentation: Swagger UI + README
- ✅ Deployment: Docker Compose (local)
- ⏳ Cloud Deployment: GCP Cloud Run (coming soon)

## 🛠️ Tech Stack

- **Backend**: FastAPI 0.135.3
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **ORM**: SQLAlchemy 2.0
- **Testing**: Pytest
- **Containerization**: Docker & Docker Compose
- **API Documentation**: Swagger/OpenAPI

## 📋 Requirements

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15
- Redis 7

## 🚀 Getting Started

### Local Development

1. **Clone the repository**
```bash
git clone https://github.com/mircothibes/url-shortener.git
cd url-shortener
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Start containers**
```bash
docker compose up -d
```

5. **Create test user**
```bash
python create_test_user.py
```

6. **Access API**
- API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Production Deployment

```bash
docker compose -f docker-compose.prod.yml up -d
```

## 📚 API Endpoints

### Health Check
- `GET /health` - API health status

### URLs Management
- `POST /api/v1/urls` - Create shortened URL
- `GET /api/v1/urls` - List user's URLs
- `GET /api/v1/urls/{url_id}` - Get URL details
- `DELETE /api/v1/urls/{url_id}` - Delete URL

### Analytics
- `GET /api/v1/urls/{url_id}/analytics` - Get URL analytics

### Redirects
- `GET /{short_code}` - Redirect to original URL

## 🔐 Authentication

All API endpoints (except `/health` and `/{short_code}`) require Bearer token authentication:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" http://localhost:8000/api/v1/urls
```

## 🧪 Testing

Run the test suite:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/ -v
```

Test coverage: 14 tests, 100% endpoint coverage

## 📊 Project Structure
