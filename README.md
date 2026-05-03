# URL Shortener & Analytics SaaS

![Tests](https://github.com/mircothibes/url-shortener/workflows/Tests%20&%20Code%20Quality/badge.svg)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791)
![GCP](https://img.shields.io/badge/Deployment-GCP%20Cloud%20Run-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

A production-grade URL shortening service with advanced analytics and click tracking. Built with FastAPI, PostgreSQL, Redis, and deployed on Google Cloud Run.

## ✨ Status

- ✅ **Backend**: Production-ready
- ✅ **API**: 7 fully functional endpoints
- ✅ **Database**: PostgreSQL 15 (Cloud SQL)
- ✅ **Deployment**: GCP Cloud Run (Live)
- ✅ **Testing**: 14/14 tests passing
- 🚀 **Service URL**: https://url-shortener-1000156659602.us-central1.run.app

## 🎯 Features

- **URL Shortening**: Convert long URLs into short, memorable codes
- **Click Analytics**: Track clicks, geographic data, device types, and referrers
- **Multi-user Support**: API key-based authentication
- **Soft Delete**: Mark URLs inactive instead of permanent deletion
- **Analytics Aggregation**: Hourly click summaries for performance
- **Production Ready**: Docker containerization, health checks, auto-scaling
- **Interactive Docs**: Auto-generated Swagger/OpenAPI documentation

## 🛠️ Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Backend** | FastAPI | 0.104.1 |
| **Database** | PostgreSQL | 15 |
| **ORM** | SQLAlchemy | 1.4.46 |
| **Cache** | Redis | 7 |
| **API Server** | Uvicorn | 0.24.0 |
| **Testing** | Pytest | Latest |
| **Containerization** | Docker | Latest |
| **Cloud Platform** | GCP (Cloud Run + Cloud SQL) | - |

## 📋 Requirements

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15 (Cloud SQL for production)
- Redis 7 (for caching)
- GCP Account (for cloud deployment)

## 🚀 Getting Started

### Local Development (Docker Compose)

1. **Clone repository**
```bash
git clone https://github.com/mircothibes/url-shortener.git
cd url-shortener
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Start containers**
```bash
docker compose up -d
```

Services will be available at:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- PostgreSQL: localhost:5432
- Redis: localhost:6379

5. **Create tables and test user**
```bash
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/mirco/dev/url-shortener')
from app.database import engine
from app.models import Base
Base.metadata.create_all(bind=engine)
EOF
```

## ⚡ Quick Start (5 minutes)

### Test API Key
```bash
API_KEY="test-api-key-12345678901234567890123456789012"
BASE_URL="http://localhost:8000"
```

### 1. Health Check
```bash
curl $BASE_URL/health
```

### 2. Create Shortened URL
```bash
curl -X POST $BASE_URL/api/v1/urls \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "original_url": "https://github.com/mircothibes",
    "description": "My GitHub Profile",
    "tags": ["github", "profile"]
  }'
```

**Response:**
```json
{
  "id": 1,
  "short_code": "aBcDeF12",
  "original_url": "https://github.com/mircothibes",
  "created_at": "2026-04-28T06:43:00.826124Z",
  "total_clicks": 0,
  "is_active": true,
  "description": "My GitHub Profile"
}
```

### 3. List Your URLs
```bash
curl $BASE_URL/api/v1/urls \
  -H "Authorization: Bearer $API_KEY"
```

### 4. Get URL Details
```bash
curl $BASE_URL/api/v1/urls/1 \
  -H "Authorization: Bearer $API_KEY"
```

### 5. View Analytics
```bash
curl $BASE_URL/api/v1/urls/1/analytics \
  -H "Authorization: Bearer $API_KEY"
```

### 6. Redirect (Click Tracking)
```bash
curl -L $BASE_URL/aBcDeF12
```

### 7. Delete URL
```bash
curl -X DELETE $BASE_URL/api/v1/urls/1 \
  -H "Authorization: Bearer $API_KEY"
```

## 📚 API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | No | API health status |
| POST | `/api/v1/urls` | Yes | Create shortened URL |
| GET | `/api/v1/urls` | Yes | List user URLs |
| GET | `/api/v1/urls/{url_id}` | Yes | Get URL details |
| DELETE | `/api/v1/urls/{url_id}` | Yes | Soft delete URL |
| GET | `/api/v1/urls/{url_id}/analytics` | Yes | Get URL analytics |
| GET | `/{short_code}` | No | Redirect to original |

## 🔐 Authentication

All protected endpoints require Bearer token:

```bash
Authorization: Bearer YOUR_API_KEY
```

## 🐍 Python Example

```python
import requests

API_KEY = "test-api-key-12345678901234567890123456789012"
BASE_URL = "http://localhost:8000"
headers = {"Authorization": f"Bearer {API_KEY}"}

# Create short URL
response = requests.post(
    f"{BASE_URL}/api/v1/urls",
    json={"original_url": "https://example.com"},
    headers=headers
)
short_code = response.json()["short_code"]
print(f"Short URL: {BASE_URL}/{short_code}")

# Get analytics
analytics = requests.get(
    f"{BASE_URL}/api/v1/urls/{response.json()['id']}/analytics",
    headers=headers
).json()
print(f"Clicks: {analytics['total_clicks']}")
```

## 🧪 Testing

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/ -v --cov=app
```

**Test Coverage**: 14/14 tests passing (100% endpoint coverage)

## 🌐 Production Deployment (GCP Cloud Run)

### Deploy
```bash
gcloud run deploy url-shortener \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars 'DATABASE_URL=postgresql://app_user:dev_password@34.59.40.8:5432/url_shortener' \
  --memory 512Mi \
  --cpu 1
```

### Live Service

https://url-shortener-1000156659602.us-central1.run.app

### Production URLs
- Health: https://url-shortener-1000156659602.us-central1.run.app/health
- Swagger: https://url-shortener-1000156659602.us-central1.run.app/docs

## 📊 Database Schema

### Tables
- `users` - User accounts with API keys
- `urls` - Shortened URLs with metadata
- `clicks` - Individual click events with IP, device, country data
- `click_aggregates` - Hourly aggregated analytics
- `audit_logs` - Audit trail of all operations

## 🔄 Development Workflow

1. **Feature Branch**
```bash
git checkout -b feature/your-feature
```

2. **Code & Test**
```bash
docker compose up -d
pytest tests/ -v
```

3. **Commit**
```bash
git commit -m "Feature: description"
```

4. **Deploy**
```bash
git push origin feature/your-feature
gcloud run deploy url-shortener --source .
```

## ❌ Troubleshooting

| Issue | Solution |
|-------|----------|
| `401 Unauthorized` | Check Authorization header and API key |
| `422 Validation Error` | URL must start with `http://` or `https://` |
| `409 Conflict` | Custom slug already exists - choose different one |
| `503 Service Unavailable` | Check database connection and GCP permissions |
| Containers won't start | Run `docker compose down -v && docker compose up -d` |

## 🚀 Upcoming Features

- [ ] Custom domain support
- [ ] QR code generation
- [ ] Link expiration policies
- [x] Password protection
- [x] Rate limiting per user
- [ ] Advanced analytics dashboard
- [ ] Webhook integrations
- [ ] Batch URL creation

## 📈 Performance Metrics

- **Requests/second**: 100+ (single container)
- **Average response time**: <100ms
- **Database**: PostgreSQL with connection pooling
- **Caching**: Redis for hot data
- **Availability**: 99.95% uptime (GCP SLA)

## 📚 Documentation

- **Swagger UI**: Available at `/docs` endpoint
- **ReDoc**: Available at `/redoc` endpoint
- **Source Code**: Fully documented with docstrings

## 📝 Project Timeline

- **Day 161**: GCP Setup + Cloud Run Deployment
- **Day 162**: Code Organization + Documentation
- **Day 163**: SQLAlchemy Bug Fix (downgrade to 1.4.46)
- **Day 164**: Full Endpoint Testing (7/7 endpoints working)
- **Day 165**: Production Deployment ✅

## 👨‍💻 Author

**Marcos (mircothibes)**
- GitHub: https://github.com/mircothibes
- LinkedIn: https://linkedin.com/in/marcosvtkemer
- Location: Luxembourg 🇱🇺

## 📖 Part of #PythonJourney

Daily documentation of backend Python development journey toward securing a backend Python role in Europe.

## 📄 License

MIT License - See LICENSE file for details

---

**Built with ❤️ using FastAPI, PostgreSQL, Redis, and GCP Cloud Run**
