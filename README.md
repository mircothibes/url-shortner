# URL Shortener API

![Tests](https://github.com/mircothibes/url-shortener/workflows/Tests%20&%20Code%20Quality/badge.svg)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

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

---

## ⚡ Quick Start (5 minutes)

### 1️⃣ Get Your API Key

The test user is created automatically when you start the containers:

```bash
API_KEY="test-api-key-12345678901234567890123456789012"
BASE_URL="http://localhost:8000"
```

### 2️⃣ Create Your First Short URL

```bash
curl -X POST $BASE_URL/api/v1/urls \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "original_url": "https://github.com/mircothibes",
    "description": "My GitHub Profile"
  }'
```

**Expected response:**
```json
{
  "id": 1,
  "short_code": "aBcDeF12",
  "original_url": "https://github.com/mircothibes",
  "created_at": "2026-04-17T19:03:38.050197Z",
  "total_clicks": 0,
  "is_active": true
}
```

### 3️⃣ Use Your Short URL

```bash
# This will redirect to the original URL and record analytics
curl -L $BASE_URL/aBcDeF12
```

### 4️⃣ List Your URLs

```bash
curl $BASE_URL/api/v1/urls \
  -H "Authorization: Bearer $API_KEY"
```

### 5️⃣ Check Analytics

```bash
curl $BASE_URL/api/v1/urls/1/analytics \
  -H "Authorization: Bearer $API_KEY"
```

**Response:**
```json
{
  "total_clicks": 5,
  "unique_visitors": 3,
  "top_country": "BR",
  "top_device": "Desktop",
  "device_breakdown": {"Desktop": 3, "Mobile": 2},
  "country_breakdown": {"BR": 5}
}
```

### 6️⃣ Delete a URL

```bash
curl -X DELETE $BASE_URL/api/v1/urls/1 \
  -H "Authorization: Bearer $API_KEY"
```

---

## 🐍 Python Example

```python
import requests

API_KEY = "test-api-key-12345678901234567890123456789012"
BASE_URL = "http://localhost:8000"
headers = {"Authorization": f"Bearer {API_KEY}"}

# Create a short URL
response = requests.post(
    f"{BASE_URL}/api/v1/urls",
    json={"original_url": "https://example.com"},
    headers=headers
)
data = response.json()
print(f"Short code: {data['short_code']}")

# Get analytics
analytics = requests.get(
    f"{BASE_URL}/api/v1/urls/{data['id']}/analytics",
    headers=headers
).json()
print(f"Total clicks: {analytics['total_clicks']}")
```

---

## ❌ Common Errors & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `401 Unauthorized` | Missing/invalid API key | Check your `Authorization` header |
| `422 Validation Error` | Invalid URL format | Ensure URL starts with `http://` or `https://` |
| `409 Conflict` | Custom slug already exists | Choose a different `custom_slug` |
| `404 Not Found` | URL doesn't exist or wrong user | Verify the `url_id` belongs to your user |
| `Connection refused` | Containers not running | Run `docker compose -f docker-compose.prod.yml up -d` |

---

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
```bash
url-shortener/
├── app/
│   ├── main.py           # FastAPI application
│   ├── models.py         # SQLAlchemy models
│   ├── database.py       # Database configuration
│   ├── cache.py          # Redis cache setup
│   └── tasks.py          # Background tasks
├── tests/
│   ├── conftest.py       # Pytest configuration
│   └── test_endpoints.py # Endpoint tests
├── docker-compose.yml    # Development environment
├── docker-compose.prod.yml # Production environment
├── Dockerfile            # Container image
└── requirements.txt      # Python dependencies
```

## 🔄 Development Workflow

1. **Code**: Write feature in `app/main.py`
2. **Test**: Add tests in `tests/test_endpoints.py`
3. **Build**: `docker build -t url-shortener-api:latest .`
4. **Run**: `docker compose -f docker-compose.prod.yml up -d`
5. **Deploy**: Push to repository

## 📈 Performance

- **Requests/second**: 100+ (single container, 4 workers)
- **Database**: PostgreSQL with connection pooling
- **Caching**: Redis for hot data
- **Response time**: <100ms average

## 🚀 Upcoming Features

- [ ] GCP Cloud Run deployment
- [x] Custom domain support
- [ ] QR code generation
- [x] Link expiration
- [x] Password protection
- [x] Rate limiting
- [ ] Advanced analytics dashboard

## 📝 License

MIT License - See LICENSE file for details

## 👨‍💻 Author

Marcos ([@marcosvtkemer](https://linkedin.com/in/marcosvtkemer))

Part of the #PythonJourney series documenting backend development progression.

## 🙏 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

**Built with ❤️ using FastAPI, PostgreSQL, and Docker**



