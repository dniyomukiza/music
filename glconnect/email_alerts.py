"""
Email Alert System for Application Monitoring
Sends email alerts via Mailtrap for critical events and system monitoring
"""

import os
import psutil
import traceback
from datetime import datetime
from mailtrap import MailtrapClient, Mail, Address
from typing import Optional, Dict, List


class EmailAlertService:
    """Service for sending email alerts for monitoring and critical events"""
    
    def __init__(self):
        self.sender = os.getenv("SENDER_MAIL", "info@ndotonic.com")
        self.receiver = os.getenv("RECEIVER_MAIL", "info@ndotonic.com")
        self.api_key = os.getenv("MAIL_TRAP")
        
        if not self.api_key:
            print("WARNING: MAIL_TRAP API key not set. Email alerts will be disabled.")
            self.enabled = False
        else:
            self.enabled = True
            self.client = MailtrapClient(token=self.api_key)
    
    def _send_email(self, subject: str, body: str, category: str = "System Alert", priority: str = "normal"):
        """Internal method to send email via Mailtrap"""
        if not self.enabled:
            print(f"Email alert disabled. Would send: {subject}")
            return False
        
        try:
            mail = Mail(
                sender=Address(email=self.sender, name="GLC System Monitor"),
                to=[Address(email=self.receiver)],
                subject=subject,
                text=body,
                category=category
            )
            self.client.send(mail)
            return True
        except Exception as e:
            print(f"ERROR: Failed to send email alert: {e}")
            return False
    
    # ==================== CRITICAL ALERTS ====================
    
    def send_critical_error(self, error_type: str, error_message: str, 
                          traceback_str: Optional[str] = None, 
                          context: Optional[Dict] = None):
        """Send alert for critical application errors"""
        body = f"""
CRITICAL ERROR ALERT
====================

Error Type: {error_type}
Error Message: {error_message}

Timestamp: {datetime.now().isoformat()}

"""
        if traceback_str:
            body += f"Traceback:\n{traceback_str}\n\n"
        
        if context:
            body += "Context Information:\n"
            for key, value in context.items():
                body += f"  {key}: {value}\n"
        
        body += "\nPlease investigate immediately."
        
        return self._send_email(
            subject=f"🚨 CRITICAL ERROR: {error_type}",
            body=body,
            category="Critical Error"
        )
    
    def send_database_error(self, error_message: str, query: Optional[str] = None, 
                           connection_info: Optional[Dict] = None):
        """Send alert for database connection or query errors"""
        body = f"""
DATABASE ERROR ALERT
====================

Error: {error_message}
Timestamp: {datetime.now().isoformat()}

"""
        if query:
            body += f"Query: {query}\n\n"
        
        if connection_info:
            body += "Connection Info:\n"
            for key, value in connection_info.items():
                body += f"  {key}: {value}\n"
        
        body += "\nDatabase connectivity may be affected."
        
        return self._send_email(
            subject="⚠️ Database Error Detected",
            body=body,
            category="Database Error"
        )
    
    def send_service_down_alert(self, service_name: str, health_check_url: str, 
                               error_message: Optional[str] = None):
        """Send alert when a service is down or unhealthy"""
        body = f"""
SERVICE DOWN ALERT
==================

Service: {service_name}
Health Check URL: {health_check_url}
Timestamp: {datetime.now().isoformat()}

"""
        if error_message:
            body += f"Error: {error_message}\n\n"
        
        body += "The service is not responding to health checks. Immediate action required."
        
        return self._send_email(
            subject=f"🔴 Service Down: {service_name}",
            body=body,
            category="Service Down"
        )
    
    # ==================== RESOURCE MONITORING ====================
    
    def send_high_memory_alert(self, memory_percent: float, memory_mb: float, 
                              threshold: float = 85.0, process_info: Optional[List] = None):
        """Send alert when memory usage exceeds threshold"""
        body = f"""
HIGH MEMORY USAGE ALERT
=======================

Memory Usage: {memory_percent:.1f}%
Threshold: {threshold}%
Memory Used: {memory_mb:.1f} MB
Timestamp: {datetime.now().isoformat()}

"""
        if process_info:
            body += "Top Memory Consumers:\n"
            for proc in process_info[:5]:
                body += f"  - {proc.get('name', 'Unknown')}: {proc.get('memory_mb', 0):.1f} MB\n"
        
        body += "\nConsider restarting services or investigating memory leaks."
        
        return self._send_email(
            subject=f"⚠️ High Memory Usage: {memory_percent:.1f}%",
            body=body,
            category="Resource Alert"
        )
    
    def send_high_cpu_alert(self, cpu_percent: float, threshold: float = 90.0,
                           duration: Optional[str] = None):
        """Send alert when CPU usage is high"""
        body = f"""
HIGH CPU USAGE ALERT
====================

CPU Usage: {cpu_percent:.1f}%
Threshold: {threshold}%
Timestamp: {datetime.now().isoformat()}

"""
        if duration:
            body += f"Duration: {duration}\n\n"
        
        body += "High CPU usage may indicate performance issues or resource contention."
        
        return self._send_email(
            subject=f"⚠️ High CPU Usage: {cpu_percent:.1f}%",
            body=body,
            category="Resource Alert"
        )
    
    def send_disk_space_alert(self, disk_percent: float, disk_path: str = "/",
                            available_gb: Optional[float] = None):
        """Send alert when disk space is low"""
        body = f"""
LOW DISK SPACE ALERT
====================

Disk Usage: {disk_percent:.1f}%
Path: {disk_path}
Timestamp: {datetime.now().isoformat()}

"""
        if available_gb:
            body += f"Available Space: {available_gb:.2f} GB\n\n"
        
        body += "Low disk space may cause application failures. Consider cleanup or expansion."
        
        return self._send_email(
            subject=f"⚠️ Low Disk Space: {disk_percent:.1f}%",
            body=body,
            category="Resource Alert"
        )
    
    # ==================== APPLICATION EVENTS ====================
    
    def send_news_generation_failed(self, task_id: str, topics: List[str], 
                                   error_message: str, retry_count: int = 0):
        """Send alert when news generation fails"""
        body = f"""
NEWS GENERATION FAILED
======================

Task ID: {task_id}
Topics: {', '.join(topics)}
Error: {error_message}
Retry Count: {retry_count}
Timestamp: {datetime.now().isoformat()}

The news generation process has failed. Manual intervention may be required.
"""
        return self._send_email(
            subject=f"⚠️ News Generation Failed: Task {task_id[:8]}",
            body=body,
            category="Application Error"
        )
    
    def send_api_key_error(self, service_name: str, api_key_name: str):
        """Send alert when API key is missing or invalid"""
        body = f"""
API KEY ERROR
=============

Service: {service_name}
API Key: {api_key_name}
Timestamp: {datetime.now().isoformat()}

The API key is missing or invalid. Service functionality may be limited.
"""
        return self._send_email(
            subject=f"⚠️ API Key Error: {service_name}",
            body=body,
            category="Configuration Error"
        )
    
    def send_ssl_certificate_expiring(self, domain: str, days_until_expiry: int):
        """Send alert when SSL certificate is expiring soon"""
        body = f"""
SSL CERTIFICATE EXPIRING
========================

Domain: {domain}
Days Until Expiry: {days_until_expiry}
Timestamp: {datetime.now().isoformat()}

SSL certificate will expire soon. Please renew to avoid service interruption.
"""
        return self._send_email(
            subject=f"⚠️ SSL Certificate Expiring: {domain} ({days_until_expiry} days)",
            body=body,
            category="Security Alert"
        )
    
    # ==================== BUSINESS EVENTS ====================
    
    def send_high_user_registration(self, count: int, time_period: str = "1 hour"):
        """Send alert for unusual spike in user registrations"""
        body = f"""
HIGH USER REGISTRATION RATE
============================

New Registrations: {count}
Time Period: {time_period}
Timestamp: {datetime.now().isoformat()}

Unusual spike in user registrations detected. May indicate:
- Successful marketing campaign
- Bot activity
- System issue
"""
        return self._send_email(
            subject=f"📈 High Registration Rate: {count} users in {time_period}",
            body=body,
            category="Business Event"
        )
    
    def send_payment_error(self, transaction_id: Optional[str], error_message: str,
                          user_email: Optional[str] = None, amount: Optional[float] = None):
        """Send alert for payment processing errors"""
        body = f"""
PAYMENT PROCESSING ERROR
=========================

Transaction ID: {transaction_id or 'N/A'}
Error: {error_message}
Timestamp: {datetime.now().isoformat()}

"""
        if user_email:
            body += f"User: {user_email}\n"
        if amount:
            body += f"Amount: ${amount:.2f}\n"
        
        body += "\nPayment processing has failed. Immediate attention required."
        
        return self._send_email(
            subject=f"💳 Payment Error: {transaction_id or 'Unknown'}",
            body=body,
            category="Payment Error"
        )
    
    def send_book_upload_failed(self, book_id: Optional[str], user_email: str,
                               error_message: str, file_size: Optional[int] = None):
        """Send alert when book upload fails"""
        body = f"""
BOOK UPLOAD FAILED
==================

Book ID: {book_id or 'N/A'}
User: {user_email}
Error: {error_message}
Timestamp: {datetime.now().isoformat()}

"""
        if file_size:
            body += f"File Size: {file_size / 1024 / 1024:.2f} MB\n\n"
        
        body += "Book upload has failed. User may need assistance."
        
        return self._send_email(
            subject=f"📚 Book Upload Failed: {user_email}",
            body=body,
            category="Application Error"
        )
    
    # ==================== DAILY/WEEKLY SUMMARIES ====================
    
    def send_daily_summary(self, stats: Dict):
        """Send daily summary of application metrics"""
        body = f"""
DAILY APPLICATION SUMMARY
=========================

Date: {datetime.now().strftime('%Y-%m-%d')}
Timestamp: {datetime.now().isoformat()}

"""
        for key, value in stats.items():
            body += f"{key}: {value}\n"
        
        body += "\n--- End of Daily Summary ---"
        
        return self._send_email(
            subject=f"📊 Daily Summary: {datetime.now().strftime('%Y-%m-%d')}",
            body=body,
            category="Daily Summary"
        )
    
    def send_weekly_summary(self, stats: Dict):
        """Send weekly summary of application metrics"""
        body = f"""
WEEKLY APPLICATION SUMMARY
===========================

Week Ending: {datetime.now().strftime('%Y-%m-%d')}
Timestamp: {datetime.now().isoformat()}

"""
        for key, value in stats.items():
            body += f"{key}: {value}\n"
        
        body += "\n--- End of Weekly Summary ---"
        
        return self._send_email(
            subject=f"📈 Weekly Summary: {datetime.now().strftime('%Y-%m-%d')}",
            body=body,
            category="Weekly Summary"
        )


# Global instance for easy import
alert_service = EmailAlertService()


# ==================== HELPER FUNCTIONS ====================

def send_error_alert(error: Exception, context: Optional[Dict] = None):
    """Convenience function to send error alerts"""
    error_type = type(error).__name__
    error_message = str(error)
    traceback_str = traceback.format_exc()
    
    return alert_service.send_critical_error(
        error_type=error_type,
        error_message=error_message,
        traceback_str=traceback_str,
        context=context
    )


def check_and_alert_resources(memory_threshold: float = 85.0, 
                              cpu_threshold: float = 90.0,
                              disk_threshold: float = 90.0):
    """Check system resources and send alerts if thresholds exceeded"""
    alerts_sent = []
    
    try:
        # Check memory
        memory = psutil.virtual_memory()
        if memory.percent >= memory_threshold:
            process_info = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    if 'python' in proc.info['name'].lower():
                        process_info.append({
                            'name': proc.info['name'],
                            'memory_mb': proc.info['memory_info'].rss / 1024 / 1024
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            process_info.sort(key=lambda x: x['memory_mb'], reverse=True)
            alert_service.send_high_memory_alert(
                memory_percent=memory.percent,
                memory_mb=memory.used / 1024 / 1024,
                threshold=memory_threshold,
                process_info=process_info
            )
            alerts_sent.append("memory")
        
        # Check CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent >= cpu_threshold:
            alert_service.send_high_cpu_alert(
                cpu_percent=cpu_percent,
                threshold=cpu_threshold
            )
            alerts_sent.append("cpu")
        
        # Check disk
        disk = psutil.disk_usage('/')
        if disk.percent >= disk_threshold:
            alert_service.send_disk_space_alert(
                disk_percent=disk.percent,
                available_gb=disk.free / 1024 / 1024 / 1024
            )
            alerts_sent.append("disk")
    
    except Exception as e:
        print(f"Error checking resources: {e}")
    
    return alerts_sent







