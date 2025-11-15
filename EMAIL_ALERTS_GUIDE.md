# Email Alerts and Monitoring Guide

This guide explains the email alerting system integrated with Mailtrap for monitoring your application.

## Overview

The email alert system (`glconnect/email_alerts.py`) provides comprehensive monitoring and alerting capabilities for your application. It sends email notifications via Mailtrap for critical events, resource issues, and important application events.

## Alert Types

### 🔴 Critical Alerts

#### 1. Critical Errors
**When:** Unhandled exceptions or critical application failures
**Usage:**
```python
from glconnect.email_alerts import alert_service, send_error_alert

# Automatic error catching
try:
    # your code
    pass
except Exception as e:
    send_error_alert(e, context={'user_id': 123, 'action': 'upload'})

# Manual alert
alert_service.send_critical_error(
    error_type="DatabaseConnectionError",
    error_message="Failed to connect to database",
    traceback_str=traceback.format_exc(),
    context={'component': 'payment_processor'}
)
```

#### 2. Database Errors
**When:** Database connection failures, query errors, transaction issues
**Usage:**
```python
alert_service.send_database_error(
    error_message="Connection timeout",
    query="SELECT * FROM users",
    connection_info={'host': 'localhost', 'port': 5432}
)
```

#### 3. Service Down Alerts
**When:** Health checks fail, services become unresponsive
**Usage:**
```python
alert_service.send_service_down_alert(
    service_name="app",
    health_check_url="http://localhost:5000/health",
    error_message="HTTP 500 - Internal Server Error"
)
```

### ⚠️ Resource Monitoring Alerts

#### 4. High Memory Usage
**When:** System memory exceeds threshold (default: 85%)
**Usage:**
```python
alert_service.send_high_memory_alert(
    memory_percent=87.5,
    memory_mb=3500,
    threshold=85.0,
    process_info=[
        {'name': 'python', 'memory_mb': 1200},
        {'name': 'nginx', 'memory_mb': 150}
    ]
)
```

#### 5. High CPU Usage
**When:** CPU usage exceeds threshold (default: 90%)
**Usage:**
```python
alert_service.send_high_cpu_alert(
    cpu_percent=95.2,
    threshold=90.0,
    duration="5 minutes"
)
```

#### 6. Low Disk Space
**When:** Disk usage exceeds threshold (default: 90%)
**Usage:**
```python
alert_service.send_disk_space_alert(
    disk_percent=92.5,
    disk_path="/",
    available_gb=5.2
)
```

### 📱 Application Event Alerts

#### 7. News Generation Failed
**When:** AI news generation process fails
**Usage:**
```python
alert_service.send_news_generation_failed(
    task_id="abc123",
    topics=["Technology", "Sports"],
    error_message="API rate limit exceeded",
    retry_count=3
)
```

#### 8. API Key Errors
**When:** Missing or invalid API keys
**Usage:**
```python
alert_service.send_api_key_error(
    service_name="Google TTS",
    api_key_name="GOOGLE_API_KEY"
)
```

#### 9. SSL Certificate Expiring
**When:** SSL certificate is expiring soon
**Usage:**
```python
alert_service.send_ssl_certificate_expiring(
    domain="www.glc.cool",
    days_until_expiry=30
)
```

### 💼 Business Event Alerts

#### 10. High User Registration Rate
**When:** Unusual spike in registrations (potential bot activity or success)
**Usage:**
```python
alert_service.send_high_user_registration(
    count=150,
    time_period="1 hour"
)
```

#### 11. Payment Errors
**When:** Payment processing fails
**Usage:**
```python
alert_service.send_payment_error(
    transaction_id="txn_123456",
    error_message="Insufficient funds",
    user_email="user@example.com",
    amount=99.99
)
```

#### 12. Book Upload Failed
**When:** Book upload process fails
**Usage:**
```python
alert_service.send_book_upload_failed(
    book_id="book_123",
    user_email="author@example.com",
    error_message="File size exceeds limit",
    file_size=104857600  # bytes
)
```

### 📊 Summary Reports

#### 13. Daily Summary
**When:** End of day metrics summary
**Usage:**
```python
alert_service.send_daily_summary({
    "Total Users": 1250,
    "New Registrations": 15,
    "Books Uploaded": 3,
    "News Generated": 12,
    "Errors": 2,
    "Average Response Time": "245ms"
})
```

#### 14. Weekly Summary
**When:** End of week metrics summary
**Usage:**
```python
alert_service.send_weekly_summary({
    "Total Users": 1250,
    "New Users This Week": 105,
    "Books Published": 21,
    "Revenue": "$1,250.00",
    "System Uptime": "99.8%"
})
```

## Automated Monitoring

### Running the Monitor Script

The `monitor_and_alert.py` script provides automated monitoring:

```bash
# Run the monitoring script
python3 monitor_and_alert.py
```

**What it monitors:**
- Service health (app, fastapi)
- System resources (memory, CPU, disk)
- Database connectivity
- Sends alerts when thresholds are exceeded

**Configuration:**
- Check interval: 5 minutes (300 seconds)
- Memory threshold: 85%
- CPU threshold: 90%
- Disk threshold: 90%
- Alert cooldown: 1 hour (prevents spam)

### Running as a Background Service

```bash
# Run in background
nohup python3 monitor_and_alert.py > monitor.log 2>&1 &

# Or use systemd (create /etc/systemd/system/app-monitor.service)
[Unit]
Description=Application Monitor and Alert Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/music-1
ExecStart=/usr/bin/python3 /path/to/music-1/monitor_and_alert.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Integration Examples

### 1. Add Error Handling to Existing Code

```python
from glconnect.email_alerts import send_error_alert

@news_bp.route('/broadcast', methods=['POST'])
def broadcast():
    try:
        # your code
        pass
    except Exception as e:
        send_error_alert(e, context={
            'endpoint': '/broadcast',
            'user_id': current_user.id if current_user.is_authenticated else None
        })
        raise
```

### 2. Monitor Database Operations

```python
from glconnect.email_alerts import alert_service

def process_payment(user_id, amount):
    try:
        # payment processing
        pass
    except Exception as e:
        alert_service.send_payment_error(
            transaction_id=None,
            error_message=str(e),
            user_email=user.email,
            amount=amount
        )
        raise
```

### 3. Resource Monitoring in Background Tasks

```python
from glconnect.email_alerts import check_and_alert_resources

def background_task():
    while True:
        # Do work
        process_news_generation()
        
        # Check resources periodically
        alerts = check_and_alert_resources()
        if alerts:
            print(f"Resource alerts sent: {alerts}")
        
        time.sleep(60)
```

### 4. Health Check Integration

```python
from glconnect.email_alerts import alert_service

@app.route('/health')
def health():
    try:
        # health check logic
        return jsonify({'status': 'healthy'}), 200
    except Exception as e:
        alert_service.send_service_down_alert(
            service_name="app",
            health_check_url=request.url,
            error_message=str(e)
        )
        return jsonify({'status': 'unhealthy'}), 500
```

## Recommended Alert Strategy

### High Priority (Immediate Action Required)
1. **Critical Errors** - Any unhandled exceptions
2. **Service Down** - Health checks failing
3. **Database Errors** - Connection or query failures
4. **Payment Errors** - Financial transaction failures

### Medium Priority (Investigate Soon)
5. **High Memory/CPU** - Resource usage above 85%
6. **News Generation Failed** - AI content generation issues
7. **Book Upload Failed** - User-facing feature failures

### Low Priority (Monitor Trends)
8. **High Registration Rate** - May indicate bot activity
9. **API Key Errors** - Configuration issues
10. **SSL Certificate Expiring** - Plan renewal

### Informational (Regular Updates)
11. **Daily Summary** - End of day metrics
12. **Weekly Summary** - Weekly trends and statistics

## Configuration

### Environment Variables

Ensure these are set in your `docker-compose.yml`:
```yaml
environment:
  - SENDER_MAIL=info@ndotonic.com
  - RECEIVER_MAIL=info@ndotonic.com
  - MAIL_TRAP=your_mailtrap_api_key
```

### Customizing Thresholds

Edit `monitor_and_alert.py`:
```python
MEMORY_THRESHOLD = 85.0  # Adjust as needed
CPU_THRESHOLD = 90.0
DISK_THRESHOLD = 90.0
CHECK_INTERVAL = 300  # 5 minutes
ALERT_COOLDOWN = 3600  # 1 hour
```

## Best Practices

1. **Don't Over-Alert**: Use cooldowns to prevent spam
2. **Include Context**: Always provide relevant context in alerts
3. **Actionable Alerts**: Include information needed to resolve issues
4. **Regular Summaries**: Use daily/weekly summaries instead of constant updates
5. **Test Alerts**: Verify email delivery works before relying on it
6. **Monitor the Monitor**: Ensure the monitoring script itself is running

## Troubleshooting

### Alerts Not Sending

1. Check `MAIL_TRAP` environment variable is set
2. Verify Mailtrap API key is valid
3. Check email service logs for errors
4. Test with a simple alert:
   ```python
   from glconnect.email_alerts import alert_service
   alert_service.send_critical_error("Test", "This is a test alert")
   ```

### Too Many Alerts

1. Increase `ALERT_COOLDOWN` in `monitor_and_alert.py`
2. Adjust thresholds higher
3. Filter alerts by severity in your code

### Missing Alerts

1. Ensure monitoring script is running
2. Check that services are being monitored
3. Verify health check endpoints are accessible
4. Review application logs for errors

## Next Steps

1. **Integrate into existing error handlers** - Add alerts to try/except blocks
2. **Set up automated monitoring** - Run `monitor_and_alert.py` as a service
3. **Configure thresholds** - Adjust based on your system's normal usage
4. **Test alerts** - Send test alerts to verify email delivery
5. **Create daily summaries** - Set up cron job for daily summary emails




