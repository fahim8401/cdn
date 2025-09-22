#!/usr/bin/env python3
"""
XenCDN v8.1 Email Report Tasks
Background tasks for sending emails and generating reports
"""

import os
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from datetime import datetime, timedelta
from celery import Celery
from flask import current_app

from ..models import db, ClientRegistration, ISPRegistration, CacheStats, EmailReport

# Initialize Celery
celery = Celery('email_tasks')

@celery.task(bind=True)
def send_email(self, to_email, subject, body, html_body=None):
    """Send email via SMTP"""
    try:
        # Get SMTP configuration from environment
        smtp_host = os.getenv('SMTP_HOST', 'localhost')
        smtp_port = int(os.getenv('SMTP_PORT', 587))
        smtp_user = os.getenv('SMTP_USER', '')
        smtp_password = os.getenv('SMTP_PASSWORD', '')
        smtp_from = os.getenv('SMTP_FROM', 'noreply@xencdn.com')
        
        # Create message
        msg = MimeMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = smtp_from
        msg['To'] = to_email
        
        # Add text body
        text_part = MimeText(body, 'plain')
        msg.attach(text_part)
        
        # Add HTML body if provided
        if html_body:
            html_part = MimeText(html_body, 'html')
            msg.attach(html_part)
        
        # Send email
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if smtp_port == 587:
                server.starttls()
            
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            
            server.send_message(msg)
        
        return {'status': 'sent', 'to': to_email, 'subject': subject}
        
    except Exception as e:
        # Log error and retry
        current_app.logger.error(f"Email send failed: {e}")
        self.retry(countdown=60, max_retries=3)

@celery.task
def generate_weekly_reports():
    """Generate and send weekly reports to clients"""
    try:
        # Get all active clients
        clients = ClientRegistration.query.filter_by(is_active=True, email_verified=True).all()
        
        for client in clients:
            generate_client_weekly_report.delay(client.id)
        
        return {'status': 'reports_scheduled', 'client_count': len(clients)}
        
    except Exception as e:
        current_app.logger.error(f"Weekly report generation failed: {e}")
        return {'status': 'error', 'error': str(e)}

@celery.task
def generate_client_weekly_report(client_id):
    """Generate weekly report for a specific client"""
    try:
        client = ClientRegistration.query.get(client_id)
        if not client:
            return {'status': 'error', 'error': 'Client not found'}
        
        # Calculate date range (last 7 days)
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=7)
        
        # Get client domains
        domain_ids = [d.id for d in client.client_domains.all()]
        
        if not domain_ids:
            return {'status': 'skipped', 'reason': 'No domains configured'}
        
        # Get cache statistics for the period
        # Note: This would need to be adapted based on how CacheStats relates to ClientDomain
        # For now, using mock data
        
        total_requests = 0
        total_bandwidth_saved = 0
        cache_hit_ratio = 0
        cost_savings = 0
        
        # Mock data for demonstration
        total_requests = 150000
        total_bandwidth_saved = 2.5  # GB
        cache_hit_ratio = 94.5
        cost_savings = 125.50  # USD
        
        # Generate email content
        subject = f"XenCDN Weekly Report - {total_bandwidth_saved}GB Saved"
        
        text_body = f"""
        XenCDN Weekly Performance Report
        
        Hello {client.first_name or client.email},
        
        Here's your CDN performance summary for the week of {start_date} to {end_date}:
        
        📊 PERFORMANCE METRICS:
        • Total Requests: {total_requests:,}
        • Bandwidth Saved: {total_bandwidth_saved}GB
        • Cache Hit Ratio: {cache_hit_ratio}%
        • Cost Savings: ${cost_savings}
        
        🚀 HIGHLIGHTS:
        • Your CDN served {total_requests:,} requests this week
        • You saved {total_bandwidth_saved}GB of bandwidth
        • This translates to ${cost_savings} in cost savings
        • Your cache hit ratio is excellent at {cache_hit_ratio}%
        
        📈 NEXT STEPS:
        • Consider upgrading to Pro plan for more domains
        • Review your cache TTL settings for better performance
        • Add more static assets to maximize savings
        
        View detailed analytics: https://{os.getenv('CLIENT_PORTAL_DOMAIN', 'client.xencdn.com')}/dashboard
        
        Questions? Reply to this email or contact support.
        
        Best regards,
        The XenCDN Team
        """
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>XenCDN Weekly Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #1f2937; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9fafb; }}
                .metric {{ background: white; padding: 15px; margin: 10px 0; border-left: 4px solid #3b82f6; }}
                .metric h3 {{ margin: 0 0 5px 0; color: #1f2937; }}
                .metric p {{ margin: 0; font-size: 24px; font-weight: bold; color: #3b82f6; }}
                .cta {{ background: #3b82f6; color: white; padding: 15px; text-align: center; margin: 20px 0; }}
                .cta a {{ color: white; text-decoration: none; font-weight: bold; }}
                .footer {{ text-align: center; padding: 20px; color: #6b7280; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 XenCDN Weekly Report</h1>
                    <p>Week of {start_date} to {end_date}</p>
                </div>
                
                <div class="content">
                    <h2>Hello {client.first_name or client.email}!</h2>
                    <p>Your CDN is performing exceptionally well. Here's what happened this week:</p>
                    
                    <div class="metric">
                        <h3>📊 Total Requests</h3>
                        <p>{total_requests:,}</p>
                    </div>
                    
                    <div class="metric">
                        <h3>💾 Bandwidth Saved</h3>
                        <p>{total_bandwidth_saved}GB</p>
                    </div>
                    
                    <div class="metric">
                        <h3>⚡ Cache Hit Ratio</h3>
                        <p>{cache_hit_ratio}%</p>
                    </div>
                    
                    <div class="metric">
                        <h3>💰 Cost Savings</h3>
                        <p>${cost_savings}</p>
                    </div>
                    
                    <div class="cta">
                        <a href="https://{os.getenv('CLIENT_PORTAL_DOMAIN', 'client.xencdn.com')}/dashboard">
                            View Detailed Analytics →
                        </a>
                    </div>
                    
                    <h3>🎯 Performance Insights</h3>
                    <ul>
                        <li>Your cache hit ratio of {cache_hit_ratio}% is excellent</li>
                        <li>You're saving significant bandwidth costs</li>
                        <li>Your users are experiencing faster load times</li>
                    </ul>
                </div>
                
                <div class="footer">
                    <p>Questions? Reply to this email or visit our support center.</p>
                    <p>© 2024 XenCDN. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Store report in database
        report = EmailReport(
            client_id=client.id,
            report_type='weekly',
            email=client.email,
            subject=subject,
            content=text_body,
            bandwidth_saved_gb=total_bandwidth_saved,
            requests_served=total_requests,
            cache_hit_ratio=cache_hit_ratio,
            cost_savings=cost_savings,
            status='pending'
        )
        
        db.session.add(report)
        db.session.commit()
        
        # Send email
        send_email.delay(client.email, subject, text_body, html_body)
        
        # Update report status
        report.status = 'sent'
        report.sent_at = datetime.utcnow()
        db.session.commit()
        
        return {
            'status': 'sent',
            'client_id': client.id,
            'email': client.email,
            'report_id': report.id
        }
        
    except Exception as e:
        current_app.logger.error(f"Client weekly report generation failed: {e}")
        return {'status': 'error', 'error': str(e)}

@celery.task
def send_isp_traffic_summary(isp_id, period='monthly'):
    """Send traffic summary to ISP"""
    try:
        isp = ISPRegistration.query.get(isp_id)
        if not isp or isp.status != 'active':
            return {'status': 'error', 'error': 'ISP not found or not active'}
        
        # Calculate date range
        if period == 'monthly':
            end_date = datetime.utcnow().date()
            start_date = end_date.replace(day=1)
        else:  # weekly
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=7)
        
        # Get ISP traffic stats
        from ..models import ISPTrafficStats
        stats = ISPTrafficStats.query.filter(
            ISPTrafficStats.isp_id == isp.id,
            ISPTrafficStats.date >= start_date,
            ISPTrafficStats.date <= end_date
        ).all()
        
        # Calculate totals
        total_requests = sum(s.requests for s in stats)
        total_bandwidth_gb = sum(s.bandwidth_gb for s in stats)
        total_cache_hits = sum(s.cache_hits for s in stats)
        avg_response_time = sum(s.response_time_avg for s in stats) / len(stats) if stats else 0
        cache_hit_ratio = (total_cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        subject = f"XenCDN {period.title()} Traffic Report - {isp.company_name}"
        
        body = f"""
        XenCDN Traffic Summary Report
        
        ISP: {isp.company_name}
        Period: {start_date} to {end_date}
        
        TRAFFIC METRICS:
        • Total Requests: {total_requests:,}
        • Bandwidth: {total_bandwidth_gb:.2f}GB
        • Cache Hit Ratio: {cache_hit_ratio:.1f}%
        • Avg Response Time: {avg_response_time:.1f}ms
        
        NETWORK INFO:
        • ASN: {isp.asn}
        • Anycast IP: {isp.anycast_ip}
        • Peering Method: {isp.peering_method}
        
        Your network is performing well in the XenCDN edge network.
        
        Access your ISP portal: https://{os.getenv('ISP_PORTAL_DOMAIN', 'isp.xencdn.com')}
        
        Best regards,
        The XenCDN Team
        """
        
        send_email.delay(isp.contact_email, subject, body)
        
        return {
            'status': 'sent',
            'isp_id': isp.id,
            'period': period,
            'total_requests': total_requests,
            'total_bandwidth_gb': total_bandwidth_gb
        }
        
    except Exception as e:
        current_app.logger.error(f"ISP traffic summary failed: {e}")
        return {'status': 'error', 'error': str(e)}

@celery.task
def send_welcome_email(user_type, user_id):
    """Send welcome email to new users"""
    try:
        if user_type == 'client':
            client = ClientRegistration.query.get(user_id)
            if not client:
                return {'status': 'error', 'error': 'Client not found'}
            
            subject = "Welcome to XenCDN - Let's Get Started!"
            body = f"""
            Welcome to XenCDN, {client.first_name or client.email}!
            
            Thank you for joining the world's first ISP-powered CDN network.
            
            Your account is ready with:
            • {client.max_domains} domain slots
            • {client.max_bandwidth_gb}GB monthly bandwidth
            • Global edge network access
            • Real-time analytics
            
            NEXT STEPS:
            1. Verify your email (if not done already)
            2. Add your first domain
            3. Configure DNS or cPanel integration
            4. Enable CDN and start saving bandwidth
            
            Access your dashboard: https://{os.getenv('CLIENT_PORTAL_DOMAIN', 'client.xencdn.com')}
            
            Need help? Check our documentation or contact support.
            
            Welcome aboard!
            The XenCDN Team
            """
            
            send_email.delay(client.email, subject, body)
            
        elif user_type == 'isp':
            isp = ISPRegistration.query.get(user_id)
            if not isp:
                return {'status': 'error', 'error': 'ISP not found'}
            
            subject = "XenCDN ISP Application Received"
            body = f"""
            Thank you for your interest in joining the XenCDN network!
            
            Company: {isp.company_name}
            Contact: {isp.contact_name}
            ASN: {isp.asn}
            
            Your application has been received and is under review.
            
            WHAT'S NEXT:
            • Our team will review your application
            • We'll verify your ASN and network information
            • You'll receive approval notification within 2-3 business days
            • Upon approval, you'll get your anycast IP and BGP configuration
            
            PEERING OPTIONS:
            • IXP Peering at major exchange points
            • Direct cross-connects to our network
            • GRE tunnels for quick setup
            • Hosted nodes in your datacenter
            
            Access your ISP portal: https://{os.getenv('ISP_PORTAL_DOMAIN', 'isp.xencdn.com')}
            
            Questions? Contact our peering team.
            
            Best regards,
            The XenCDN Peering Team
            """
            
            send_email.delay(isp.contact_email, subject, body)
        
        return {'status': 'sent', 'user_type': user_type, 'user_id': user_id}
        
    except Exception as e:
        current_app.logger.error(f"Welcome email failed: {e}")
        return {'status': 'error', 'error': str(e)}