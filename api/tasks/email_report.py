#!/usr/bin/env python3
"""
XenCDN v8.2 - Email Report Tasks
Automated weekly email reports for clients
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging
from datetime import datetime, timedelta
from celery import shared_task
import json

logger = logging.getLogger(__name__)

# Email configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.sendgrid.net')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', 'apikey')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
SMTP_FROM = os.getenv('SMTP_FROM', 'reports@xencdn.com')

def send_email(to_email, subject, body_html, body_text=None, attachments=None):
    """Send email via SMTP"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SMTP_FROM
        msg['To'] = to_email
        
        # Add text part
        if body_text:
            text_part = MIMEText(body_text, 'plain')
            msg.attach(text_part)
        
        # Add HTML part
        html_part = MIMEText(body_html, 'html')
        msg.attach(html_part)
        
        # Add attachments
        if attachments:
            for attachment in attachments:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment['content'])
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {attachment["filename"]}'
                )
                msg.attach(part)
        
        # Send email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return {'success': True, 'message': 'Email sent successfully'}
    
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return {'success': False, 'error': str(e)}

def generate_weekly_report_html(user, report_data):
    """Generate HTML email template for weekly report"""
    
    html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>XenCDN Weekly Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 10px 10px 0 0;
        }}
        .content {{
            background: white;
            padding: 30px;
            border: 1px solid #ddd;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
        }}
        .domains-list {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .domain-item {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            border-radius: 0 0 10px 10px;
            font-size: 0.9em;
            color: #666;
        }}
        .cta-button {{
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 6px;
            margin: 20px 0;
        }}
        @media (max-width: 600px) {{
            .stats-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Your Weekly XenCDN Report</h1>
        <p>Performance summary for {report_data['period_start']} - {report_data['period_end']}</p>
    </div>
    
    <div class="content">
        <h2>Hello {user.first_name}!</h2>
        <p>Here's how your CDN performed this week:</p>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{report_data['total_requests']:,}</div>
                <div class="stat-label">Total Requests</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{report_data['cache_hit_ratio']:.1f}%</div>
                <div class="stat-label">Cache Hit Ratio</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{report_data['bandwidth_saved_gb']:.1f} GB</div>
                <div class="stat-label">Bandwidth Saved</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">${report_data['bandwidth_cost_saved']:.2f}</div>
                <div class="stat-label">Money Saved</div>
            </div>
        </div>
        
        <h3>🎯 Performance Highlights</h3>
        <ul>
            <li>Your CDN served <strong>{report_data['total_requests']:,} requests</strong> this week</li>
            <li>Cache hit ratio of <strong>{report_data['cache_hit_ratio']:.1f}%</strong> (industry average: 85%)</li>
            <li>Saved <strong>{report_data['bandwidth_saved_gb']:.1f} GB</strong> of bandwidth</li>
            <li>Average response time: <strong>{report_data['avg_response_time_ms']:.0f}ms</strong></li>
        </ul>
        
        <h3>🚀 Top Performing Domains</h3>
        <div class="domains-list">
            {generate_domain_list_html(report_data.get('top_domains', []))}
        </div>
        
        <div style="text-align: center;">
            <a href="https://{os.getenv('CLIENT_PORTAL_DOMAIN', 'client.xencdn.com')}/dashboard" class="cta-button">
                View Full Dashboard
            </a>
        </div>
        
        <h3>💡 Performance Tips</h3>
        <p>To improve your CDN performance:</p>
        <ul>
            <li>Enable compression for text files (HTML, CSS, JS)</li>
            <li>Set appropriate cache headers for static assets</li>
            <li>Use WebP images for better compression</li>
            <li>Enable HTTP/2 on your origin server</li>
        </ul>
    </div>
    
    <div class="footer">
        <p>This report was generated automatically by XenCDN v8.2</p>
        <p>Questions? Reply to this email or visit our <a href="https://{os.getenv('HOMEPAGE_DOMAIN', 'xencdn.com')}/support">support center</a></p>
        <p style="font-size: 0.8em; color: #999;">
            You're receiving this because you have an active XenCDN account.<br>
            <a href="#">Unsubscribe</a> | <a href="#">Preferences</a>
        </p>
    </div>
</body>
</html>
"""
    
    return html_template

def generate_domain_list_html(domains):
    """Generate HTML for top domains list"""
    if not domains:
        return "<p>No domain data available for this period.</p>"
    
    html = ""
    for domain in domains[:5]:  # Top 5 domains
        html += f"""
        <div class="domain-item">
            <span><strong>{domain['name']}</strong></span>
            <span>{domain['requests']:,} requests</span>
        </div>
        """
    
    return html

@shared_task(bind=True, max_retries=3)
def generate_weekly_report(self, user_id):
    """Generate weekly report for a user"""
    try:
        from models import db, User, Domain, CacheStats, EmailReport
        
        user = User.query.get(user_id)
        if not user:
            return {'error': 'User not found'}
        
        # Calculate date range (last 7 days)
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=7)
        
        # Get user's domains
        domains = Domain.query.filter_by(user_id=user_id).all()
        domain_ids = [d.id for d in domains]
        
        if not domain_ids:
            logger.info(f"No domains found for user {user_id}, skipping report")
            return {'message': 'No domains to report on'}
        
        # Get cache stats for the period
        stats = CacheStats.query.filter(
            CacheStats.domain_id.in_(domain_ids),
            CacheStats.date >= start_date,
            CacheStats.date <= end_date
        ).all()
        
        if not stats:
            logger.info(f"No stats found for user {user_id} in period, skipping report")
            return {'message': 'No stats available for this period'}
        
        # Calculate totals
        total_requests = sum(stat.requests for stat in stats)
        total_cache_hits = sum(stat.cache_hits for stat in stats)
        total_bandwidth_saved = sum(stat.bandwidth_saved for stat in stats)
        
        # Calculate averages
        cache_hit_ratio = (total_cache_hits / total_requests * 100) if total_requests > 0 else 0
        bandwidth_saved_gb = total_bandwidth_saved / (1024**3)
        avg_response_time = sum(stat.response_time_avg for stat in stats) / len(stats)
        
        # Estimate cost savings ($0.05 per GB)
        bandwidth_cost_saved = bandwidth_saved_gb * 0.05
        
        # Get top domains by traffic
        domain_stats = {}
        for stat in stats:
            domain = next((d for d in domains if d.id == stat.domain_id), None)
            if domain:
                if domain.domain_name not in domain_stats:
                    domain_stats[domain.domain_name] = {
                        'name': domain.domain_name,
                        'requests': 0,
                        'cache_hits': 0,
                        'bandwidth_saved': 0
                    }
                domain_stats[domain.domain_name]['requests'] += stat.requests
                domain_stats[domain.domain_name]['cache_hits'] += stat.cache_hits
                domain_stats[domain.domain_name]['bandwidth_saved'] += stat.bandwidth_saved
        
        top_domains = sorted(domain_stats.values(), key=lambda x: x['requests'], reverse=True)
        
        # Prepare report data
        report_data = {
            'period_start': start_date.strftime('%Y-%m-%d'),
            'period_end': end_date.strftime('%Y-%m-%d'),
            'total_requests': total_requests,
            'cache_hit_ratio': cache_hit_ratio,
            'bandwidth_saved_gb': bandwidth_saved_gb,
            'bandwidth_cost_saved': bandwidth_cost_saved,
            'avg_response_time_ms': avg_response_time,
            'top_domains': top_domains
        }
        
        # Save report to database
        email_report = EmailReport(
            user_id=user_id,
            report_period_start=datetime.combine(start_date, datetime.min.time()),
            report_period_end=datetime.combine(end_date, datetime.min.time()),
            total_requests=total_requests,
            cache_hit_ratio=cache_hit_ratio,
            bandwidth_saved_gb=bandwidth_saved_gb,
            bandwidth_cost_saved=bandwidth_cost_saved,
            avg_response_time_ms=avg_response_time,
            top_domains=json.dumps(top_domains)
        )
        
        db.session.add(email_report)
        db.session.commit()
        
        # Generate and send email
        html_content = generate_weekly_report_html(user, report_data)
        text_content = f"""
XenCDN Weekly Report for {user.first_name}

Performance Summary ({start_date} - {end_date}):
- Total Requests: {total_requests:,}
- Cache Hit Ratio: {cache_hit_ratio:.1f}%
- Bandwidth Saved: {bandwidth_saved_gb:.1f} GB
- Cost Saved: ${bandwidth_cost_saved:.2f}
- Avg Response Time: {avg_response_time:.0f}ms

View your full dashboard at: https://{os.getenv('CLIENT_PORTAL_DOMAIN', 'client.xencdn.com')}/dashboard

Best regards,
The XenCDN Team
"""
        
        email_result = send_email(
            to_email=user.email,
            subject=f"🚀 Your XenCDN Weekly Report - {bandwidth_saved_gb:.1f} GB Saved!",
            body_html=html_content,
            body_text=text_content
        )
        
        if email_result['success']:
            # Mark report as sent
            email_report.email_sent = True
            email_report.sent_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"Weekly report sent successfully to {user.email}")
            return {
                'success': True,
                'user_email': user.email,
                'report_data': report_data
            }
        else:
            logger.error(f"Failed to send weekly report to {user.email}: {email_result['error']}")
            return {'error': f'Failed to send email: {email_result["error"]}'}
        
    except Exception as e:
        logger.error(f"Failed to generate weekly report for user {user_id}: {str(e)}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=300 * (self.request.retries + 1), exc=e)  # 5 min, 10 min, 15 min
        
        return {'error': str(e)}

@shared_task
def send_weekly_reports_batch():
    """Send weekly reports to all active users"""
    try:
        from models import User, ClientRegistration
        
        # Get all active client users
        active_users = User.query.join(ClientRegistration).filter(
            User.is_active == True,
            ClientRegistration.subscription_status == 'active'
        ).all()
        
        total_sent = 0
        total_errors = 0
        
        for user in active_users:
            try:
                # Queue individual report generation
                generate_weekly_report.delay(user.id)
                total_sent += 1
                
            except Exception as e:
                logger.error(f"Failed to queue report for user {user.id}: {str(e)}")
                total_errors += 1
        
        logger.info(f"Queued weekly reports: {total_sent} sent, {total_errors} errors")
        
        return {
            'success': True,
            'reports_queued': total_sent,
            'errors': total_errors
        }
        
    except Exception as e:
        logger.error(f"Failed to send weekly reports batch: {str(e)}")
        return {'error': str(e)}

@shared_task(bind=True, max_retries=3)
def send_alert_email(self, user_id, alert_type, alert_data):
    """Send alert email to user"""
    try:
        from models import User
        
        user = User.query.get(user_id)
        if not user:
            return {'error': 'User not found'}
        
        # Generate alert email based on type
        subject = ""
        html_content = ""
        
        if alert_type == 'ssl_expiring':
            subject = f"🔒 SSL Certificate Expiring - {alert_data['domain']}"
            html_content = f"""
            <h2>SSL Certificate Expiring</h2>
            <p>Your SSL certificate for <strong>{alert_data['domain']}</strong> will expire in {alert_data['days_until_expiry']} days.</p>
            <p>We will automatically renew it for you, but please ensure your DNS settings are correct.</p>
            """
        
        elif alert_type == 'domain_down':
            subject = f"🚨 Domain Offline - {alert_data['domain']}"
            html_content = f"""
            <h2>Domain Offline Alert</h2>
            <p>Your domain <strong>{alert_data['domain']}</strong> appears to be offline.</p>
            <p>Our edge servers are unable to reach your origin server at {alert_data['origin_ip']}.</p>
            <p>Please check your origin server status.</p>
            """
        
        elif alert_type == 'bandwidth_limit':
            subject = f"📊 Bandwidth Limit Warning - {alert_data['usage_percent']}% Used"
            html_content = f"""
            <h2>Bandwidth Usage Warning</h2>
            <p>You have used <strong>{alert_data['usage_percent']}%</strong> of your monthly bandwidth limit.</p>
            <p>Current usage: {alert_data['used_gb']:.1f} GB of {alert_data['limit_gb']} GB</p>
            <p>Consider upgrading your plan to avoid service interruption.</p>
            """
        
        else:
            return {'error': 'Unknown alert type'}
        
        # Wrap in standard template
        full_html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #f8f9fa; padding: 20px; border-radius: 10px;">
                <h1 style="color: #667eea;">XenCDN Alert</h1>
                {html_content}
                <p style="margin-top: 30px;">
                    <a href="https://{os.getenv('CLIENT_PORTAL_DOMAIN', 'client.xencdn.com')}/dashboard" 
                       style="background: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                        View Dashboard
                    </a>
                </p>
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
                <p style="font-size: 0.9em; color: #666;">
                    This is an automated alert from XenCDN v8.2<br>
                    Visit our <a href="https://{os.getenv('HOMEPAGE_DOMAIN', 'xencdn.com')}/support">support center</a> if you need help.
                </p>
            </div>
        </div>
        """
        
        email_result = send_email(
            to_email=user.email,
            subject=subject,
            body_html=full_html
        )
        
        if email_result['success']:
            logger.info(f"Alert email sent to {user.email}: {alert_type}")
            return {
                'success': True,
                'alert_type': alert_type,
                'user_email': user.email
            }
        else:
            return {'error': f'Failed to send alert email: {email_result["error"]}'}
        
    except Exception as e:
        logger.error(f"Failed to send alert email: {str(e)}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (self.request.retries + 1), exc=e)
        
        return {'error': str(e)}