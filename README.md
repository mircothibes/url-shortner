# URL Shortener + Analytics API

A production-grade URL shortening service with real-time analytics, built to explore backend challenges like caching, async processing, and scalable API design.

## Features

- **URL Shortening**: Generate short, custom, or auto-generated short codes
- **Real-time Analytics**: Track clicks, geographic data, device types, and referrers
- **Password Protection**: Optional password-protected URLs
- **Expiration Dates**: Set URLs to expire at a specific time
- **Rate Limiting**: Built-in API rate limiting
- **Async Processing**: Background tasks with Celery and Redis
- **Production Ready**: Docker, PostgreSQL connection pooling, health checks

## Tech Stack

- **Backend**: FastAPI + Pydantic v2
- **Database**: PostgreSQL 15
- **Caching**: Redis 7
- **Async Tasks**: Celery + Celery Beat
- **Cloud**: GCP (Cloud Run, Cloud SQL, Cloud Memorystore)
- **Containerization**: Docker & Docker Compose

## Project Structure
```
url-shortener/
├── app/
│   ├── main.py           # FastAPI application & routes
│   ├── database.py       # Database configuration
│   ├── models.py         # SQLAlchemy ORM models
│   ├── cache.py          # Redis caching logic
│   └── tasks.py          # Celery background tasks
├── Dockerfile            # Container configuration
├── docker-compose.yml    # Multi-service orchestration
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables
└── README.md             # This file is the primary documentation
```

## Getting Started

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15 (via Docker)
- Redis 7 (via Docker)

### Local Development

1. **Clone the repository**
```bash
   git clone https://github.com/mircothibes/url-shortener.git
   cd url-shortener
```

2. **Create virtual environment**
```bash
   python3 -m venv venv
   source venv/bin/activate
```

3. **Install dependencies**
```bash
   pip install -r requirements.txt
```

4. **Create `.env` file**
```bash
   echo "DB_PASSWORD=dev_password" > .env
   echo "POSTGRES_USER=app_user" >> .env
```

5. **Start services**
```bash
   docker compose up -d
```

6. **Run the application**
```bash
   uvicorn app.main:app --reload
```

7. **Test the API**
```bash
   curl http://localhost:8000/health
```

## API Endpoints

### Health Check
```
GET /health
```

### Create Short URL
```
POST /api/v1/urls
Headers: Authorization: Bearer <api_key>
Body: {
  "original_url": "https://example.com/long/path",
  "custom_slug": "optional-slug",
  "expires_at": "2024-12-31T23:59:59Z",
  "password": "optional-password"
}
```

### Redirect
```
GET /{short_code}
```

### Get Analytics
```
GET /api/v1/urls/{url_id}/analytics
Headers: Authorization: Bearer <api_key>
```

## Docker Commands
```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down

# Rebuild images
docker compose build
```

## Development Status

- [x] Project setup & structure
- [x] FastAPI main.py with core endpoints
- [x] Database configuration (PostgreSQL)
- [x] Docker & Docker Compose
- [ ] SQLAlchemy models (WIP)
- [x] Tests with pytest
- [ ] API authentication
- [ ] Analytics aggregation
- [ ] GCP deployment

## Learning Journey

This project is part of my #PythonJourney learning series. Follow my progress:
- **GitHub**: [@mircothibes](https://github.com/mircothibes)
- **LinkedIn**: [@marcosvtkemer](https://www.linkedin.com/in/marcosvtkemer)

## License

MIT License - feel free to use this project for learning purposes.

---

## 🧑‍💻 Author

Marcos Vinicius Thibes Kemer

