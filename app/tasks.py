# app/tasks.py
from celery import shared_task
from maxminddb import open_database

geoip_db = open_database('GeoLite2-Country.mmdb')

@shared_task(bind=True, max_retries=3)
def process_click(self, url_id: int, ip_address: str, user_agent: str, referrer: str):
    """
    Background task: track a click with geolocation & device detection
    """
    try:
        db_session = SessionLocal()
        
        # Geolocation
        geo_data = geoip_db.get(ip_address) or {}
        country = geo_data.get('country', {}).get('iso_code', 'XX')
        
        # Device detection (from user_agent)
        device_type = parse_device_type(user_agent)
        
        # Save click
        click = Click(
            url_id=url_id,
            country=country,
            device_type=device_type,
            user_agent=user_agent,
            referrer=referrer,
            ip_address=ip_address
        )
        db_session.add(click)
        db_session.commit()
        
        # Trigger aggregation update (async)
        update_hourly_aggregates.delay(url_id)
        
    except Exception as exc:
        self.retry(exc=exc, countdown=60)
    finally:
        db_session.close()

@shared_task
def update_hourly_aggregates(url_id: int):
    """
    Aggregate clicks by hour for fast analytics queries
    """
    db_session = SessionLocal()
    
    hour_start = datetime.now().replace(minute=0, second=0, microsecond=0)
    
    # Query clicks from this hour
    clicks = db_session.query(Click).filter(
        Click.url_id == url_id,
        Click.clicked_at >= hour_start
    ).all()
    
    # Aggregate
    device_counts = {}
    country_counts = {}
    
    for click in clicks:
        device_counts[click.device_type] = device_counts.get(click.device_type, 0) + 1
        country_counts[click.country] = country_counts.get(click.country, 0) + 1
    
    # Save or update aggregate
    agg = db_session.query(ClickAggregate).filter_by(
        url_id=url_id,
        date_hour=hour_start
    ).first()
    
    if agg:
        agg.total_clicks = len(clicks)
        agg.device_breakdown = device_counts
        agg.country_breakdown = country_counts
    else:
        agg = ClickAggregate(
            url_id=url_id,
            date_hour=hour_start,
            total_clicks=len(clicks),
            device_breakdown=device_counts,
            country_breakdown=country_counts
        )
        db_session.add(agg)
    
    db_session.commit()
    db_session.close()

@shared_task
def cleanup_expired_urls():
    """
    Scheduled task (daily): delete expired URLs and their clicks
    """
    db_session = SessionLocal()
    
    expired = db_session.query(URL).filter(
        URL.expires_at < datetime.now(),
        URL.is_active == True
    ).all()
    
    for url in expired:
        url.is_active = False
    
    db_session.commit()
    db_session.close()
