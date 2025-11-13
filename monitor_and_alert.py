#!/usr/bin/env python3
"""
Automated Monitoring and Alerting Script
Periodically checks system health and sends email alerts via Mailtrap
"""

import time
import requests
import psutil
import os
import sys
from datetime import datetime, timedelta
from glconnect.email_alerts import alert_service, check_and_alert_resources

# Configuration
CHECK_INTERVAL = 300  # Check every 5 minutes (300 seconds)
HEALTH_CHECK_URLS = {
    'app': 'http://localhost:5000/health',
    'fastapi': 'http://localhost:8002/health',
}
MEMORY_THRESHOLD = 85.0
CPU_THRESHOLD = 90.0
DISK_THRESHOLD = 90.0

# Track last alert times to avoid spam
last_alerts = {
    'memory': None,
    'cpu': None,
    'disk': None,
    'service_down': {}
}
ALERT_COOLDOWN = 3600  # Don't send same alert more than once per hour


def check_service_health(service_name: str, url: str):
    """Check if a service is healthy"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'healthy':
                return True, "Service is healthy"
            else:
                return False, f"Service unhealthy: {data.get('error', 'Unknown error')}"
        else:
            return False, f"HTTP {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Connection refused - service may be down"
    except requests.exceptions.Timeout:
        return False, "Request timeout"
    except Exception as e:
        return False, f"Error: {str(e)}"


def should_send_alert(alert_type: str, service_name: str = None) -> bool:
    """Check if we should send an alert (avoid spam)"""
    key = f"{alert_type}_{service_name}" if service_name else alert_type
    last_alert = last_alerts.get(key)
    
    if last_alert is None:
        return True
    
    time_since_last = (datetime.now() - last_alert).total_seconds()
    return time_since_last >= ALERT_COOLDOWN


def update_alert_time(alert_type: str, service_name: str = None):
    """Update the last alert time"""
    key = f"{alert_type}_{service_name}" if service_name else alert_type
    last_alerts[key] = datetime.now()


def monitor_services():
    """Monitor all services and send alerts if any are down"""
    for service_name, url in HEALTH_CHECK_URLS.items():
        is_healthy, error_message = check_service_health(service_name, url)
        
        if not is_healthy:
            if should_send_alert('service_down', service_name):
                alert_service.send_service_down_alert(
                    service_name=service_name,
                    health_check_url=url,
                    error_message=error_message
                )
                update_alert_time('service_down', service_name)
                print(f"⚠️ Alert sent: {service_name} is down - {error_message}")
        else:
            print(f"✅ {service_name} is healthy")


def monitor_resources():
    """Monitor system resources and send alerts if thresholds exceeded"""
    alerts = check_and_alert_resources(
        memory_threshold=MEMORY_THRESHOLD,
        cpu_threshold=CPU_THRESHOLD,
        disk_threshold=DISK_THRESHOLD
    )
    
    for alert_type in alerts:
        if should_send_alert(alert_type):
            update_alert_time(alert_type)
            print(f"⚠️ Alert sent: High {alert_type} usage")


def check_database_connection():
    """Check database connectivity"""
    try:
        from glconnect import create_app, db
        from glconnect.models import User
        
        app, _ = create_app()
        with app.app_context():
            # Simple query to test connection
            User.query.limit(1).all()
            return True, None
    except Exception as e:
        error_msg = str(e)
        if should_send_alert('database_error'):
            alert_service.send_database_error(
                error_message=error_msg,
                connection_info={'database_url': os.getenv('DATABASE_URL', 'Not set')[:50] + '...'}
            )
            update_alert_time('database_error')
            print(f"⚠️ Alert sent: Database connection error - {error_msg}")
        return False, error_msg


def main():
    """Main monitoring loop"""
    print("=" * 60)
    print("🚀 Starting Application Monitoring and Alerting System")
    print("=" * 60)
    print(f"Check Interval: {CHECK_INTERVAL} seconds ({CHECK_INTERVAL/60:.1f} minutes)")
    print(f"Memory Threshold: {MEMORY_THRESHOLD}%")
    print(f"CPU Threshold: {CPU_THRESHOLD}%")
    print(f"Disk Threshold: {DISK_THRESHOLD}%")
    print(f"Alert Cooldown: {ALERT_COOLDOWN} seconds ({ALERT_COOLDOWN/60:.1f} minutes)")
    print("=" * 60)
    print()
    
    iteration = 0
    
    try:
        while True:
            iteration += 1
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Check #{iteration}")
            print("-" * 60)
            
            # Check services
            print("Checking services...")
            monitor_services()
            
            # Check resources
            print("Checking system resources...")
            monitor_resources()
            
            # Check database
            print("Checking database connection...")
            db_ok, db_error = check_database_connection()
            if db_ok:
                print("✅ Database connection OK")
            
            print(f"\nNext check in {CHECK_INTERVAL} seconds...")
            time.sleep(CHECK_INTERVAL)
    
    except KeyboardInterrupt:
        print("\n\n🛑 Monitoring stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Fatal error in monitoring: {e}")
        import traceback
        traceback.print_exc()
        alert_service.send_critical_error(
            error_type=type(e).__name__,
            error_message=str(e),
            traceback_str=traceback.format_exc(),
            context={'component': 'monitor_and_alert.py'}
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

