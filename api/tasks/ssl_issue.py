#!/usr/bin/env python3
"""
Cachenet CDN Platform SSL Certificate Management Tasks
ACME.sh integration for automatic SSL certificate issuance and renewal
"""

import os
import logging
import subprocess
import requests
from datetime import datetime, timedelta
from celery import shared_task
from models import db, Domain, SSLCertificate

logger = logging.getLogger(__name__)

ACME_PATH = '/acme.sh'
ACME_EMAIL = os.getenv('ACME_EMAIL', 'admin@cachenet.local')
ACME_SERVER = os.getenv('ACME_SERVER', 'https://acme-v02.api.letsencrypt.org/directory')
PDNS_API_URL = os.getenv('PDNS_API_URL', 'http://powerdns:8081/api/v1/servers/localhost')
PDNS_API_KEY = os.getenv('PDNS_API_KEY')
SSL_CERT_PATH = '/app/ssl-certificates'

def run_acme_command(command, timeout=300):
    """Run ACME.sh command with error handling"""
    try:
        # Ensure SSL certificate directory exists
        os.makedirs(SSL_CERT_PATH, exist_ok=True)
        
        # Set environment variables for ACME.sh
        env = os.environ.copy()
        env.update({
            'PDNS_Url': PDNS_API_URL,
            'PDNS_ServerId': 'localhost',
            'PDNS_Token': PDNS_API_KEY,
            'PDNS_Ttl': '60'
        })
        
        # Run ACME.sh command
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=ACME_PATH
        )
        
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'return_code': result.returncode
        }
        
    except subprocess.TimeoutExpired:
        logger.error(f"ACME command timed out: {command}")
        return {
            'success': False,
            'error': 'Command timed out',
            'return_code': -1
        }
    except Exception as e:
        logger.error(f"Error running ACME command: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'return_code': -1
        }

def copy_certificate_files(domain_name, cert_id):
    """Copy certificate files to permanent storage"""
    try:
        # Source paths (ACME.sh default locations)
        acme_domain_path = f"{ACME_PATH}/{domain_name}"
        
        # Destination paths
        cert_dir = f"{SSL_CERT_PATH}/{cert_id}"
        os.makedirs(cert_dir, exist_ok=True)
        
        cert_file = f"{cert_dir}/{domain_name}.crt"
        key_file = f"{cert_dir}/{domain_name}.key"
        chain_file = f"{cert_dir}/{domain_name}-chain.crt"
        
        # Copy certificate files
        copy_commands = [
            f"cp {acme_domain_path}/{domain_name}.cer {cert_file}",
            f"cp {acme_domain_path}/{domain_name}.key {key_file}",
            f"cp {acme_domain_path}/fullchain.cer {chain_file}"
        ]
        
        for cmd in copy_commands:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Failed to copy certificate file: {cmd}")
                return None
        
        # Set proper permissions
        os.chmod(cert_file, 0o644)
        os.chmod(key_file, 0o600)
        os.chmod(chain_file, 0o644)
        
        return {
            'certificate_path': cert_file,
            'private_key_path': key_file,
            'chain_path': chain_file
        }
        
    except Exception as e:
        logger.error(f"Error copying certificate files: {str(e)}")
        return None

@shared_task(bind=True, max_retries=3)
def issue_ssl_certificate(self, certificate_id):
    """Issue SSL certificate using ACME.sh and DNS-01 challenge"""
    try:
        logger.info(f"Issuing SSL certificate for certificate ID: {certificate_id}")
        
        # Get certificate record
        certificate = SSLCertificate.query.get(certificate_id)
        if not certificate:
            logger.error(f"Certificate not found: {certificate_id}")
            return {'error': 'Certificate not found'}
        
        domain_name = certificate.domain_name
        
        # Update certificate status
        certificate.status = 'issuing'
        db.session.commit()
        
        # Issue certificate using ACME.sh with DNS-01 challenge
        acme_command = f"""
        /acme.sh/acme.sh --issue \\
            --dns dns_pdns \\
            --server {ACME_SERVER} \\
            --email {ACME_EMAIL} \\
            -d {domain_name} \\
            -d www.{domain_name} \\
            --force
        """
        
        logger.info(f"Running ACME.sh command for domain: {domain_name}")
        result = run_acme_command(acme_command, timeout=600)
        
        if result['success']:
            logger.info(f"Certificate issued successfully for domain: {domain_name}")
            
            # Copy certificate files to permanent storage
            file_paths = copy_certificate_files(domain_name, certificate_id)
            
            if file_paths:
                # Update certificate record
                certificate.certificate_path = file_paths['certificate_path']
                certificate.private_key_path = file_paths['private_key_path']
                certificate.chain_path = file_paths['chain_path']
                certificate.status = 'active'
                certificate.issued_at = datetime.utcnow()
                certificate.expires_at = datetime.utcnow() + timedelta(days=90)  # Let's Encrypt default
                certificate.updated_at = datetime.utcnow()
                
                # Update associated domains
                Domain.query.filter_by(domain_name=domain_name).update({
                    'ssl_certificate_id': certificate.id,
                    'ssl_enabled': True,
                    'updated_at': datetime.utcnow()
                })
                
                db.session.commit()
                
                logger.info(f"Certificate record updated for domain: {domain_name}")
                
                return {
                    'success': True,
                    'domain': domain_name,
                    'certificate_id': certificate_id,
                    'expires_at': certificate.expires_at.isoformat()
                }
            else:
                logger.error(f"Failed to copy certificate files for domain: {domain_name}")
                certificate.status = 'error'
                certificate.updated_at = datetime.utcnow()
                db.session.commit()
                return {'error': 'Failed to copy certificate files'}
        else:
            logger.error(f"Certificate issuance failed for domain {domain_name}: {result.get('stderr', 'Unknown error')}")
            certificate.status = 'error'
            certificate.updated_at = datetime.utcnow()
            db.session.commit()
            raise Exception(f"Certificate issuance failed: {result.get('stderr', 'Unknown error')}")
        
    except Exception as e:
        logger.error(f"SSL certificate issuance error for certificate {certificate_id}: {str(e)}")
        
        # Update certificate status to error
        try:
            certificate = SSLCertificate.query.get(certificate_id)
            if certificate:
                certificate.status = 'error'
                certificate.updated_at = datetime.utcnow()
                db.session.commit()
        except:
            pass
        
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying SSL certificate issuance for certificate {certificate_id}")
            raise self.retry(countdown=120 * (self.request.retries + 1))
        
        return {'error': str(e)}

@shared_task(bind=True, max_retries=3)
def renew_ssl_certificate(self, certificate_id):
    """Renew SSL certificate"""
    try:
        logger.info(f"Renewing SSL certificate for certificate ID: {certificate_id}")
        
        # Get certificate record
        certificate = SSLCertificate.query.get(certificate_id)
        if not certificate:
            logger.error(f"Certificate not found: {certificate_id}")
            return {'error': 'Certificate not found'}
        
        domain_name = certificate.domain_name
        
        # Update certificate status
        certificate.status = 'renewing'
        db.session.commit()
        
        # Renew certificate using ACME.sh
        acme_command = f"""
        /acme.sh/acme.sh --renew \\
            --dns dns_pdns \\
            -d {domain_name} \\
            --force
        """
        
        logger.info(f"Running ACME.sh renewal for domain: {domain_name}")
        result = run_acme_command(acme_command, timeout=600)
        
        if result['success']:
            logger.info(f"Certificate renewed successfully for domain: {domain_name}")
            
            # Copy renewed certificate files
            file_paths = copy_certificate_files(domain_name, certificate_id)
            
            if file_paths:
                # Update certificate record
                certificate.certificate_path = file_paths['certificate_path']
                certificate.private_key_path = file_paths['private_key_path']
                certificate.chain_path = file_paths['chain_path']
                certificate.status = 'active'
                certificate.issued_at = datetime.utcnow()
                certificate.expires_at = datetime.utcnow() + timedelta(days=90)
                certificate.updated_at = datetime.utcnow()
                
                db.session.commit()
                
                logger.info(f"Certificate renewal completed for domain: {domain_name}")
                
                return {
                    'success': True,
                    'domain': domain_name,
                    'certificate_id': certificate_id,
                    'expires_at': certificate.expires_at.isoformat()
                }
            else:
                logger.error(f"Failed to copy renewed certificate files for domain: {domain_name}")
                certificate.status = 'error'
                certificate.updated_at = datetime.utcnow()
                db.session.commit()
                return {'error': 'Failed to copy renewed certificate files'}
        else:
            logger.error(f"Certificate renewal failed for domain {domain_name}: {result.get('stderr', 'Unknown error')}")
            certificate.status = 'error'
            certificate.updated_at = datetime.utcnow()
            db.session.commit()
            raise Exception(f"Certificate renewal failed: {result.get('stderr', 'Unknown error')}")
        
    except Exception as e:
        logger.error(f"SSL certificate renewal error for certificate {certificate_id}: {str(e)}")
        
        # Update certificate status to error
        try:
            certificate = SSLCertificate.query.get(certificate_id)
            if certificate:
                certificate.status = 'error'
                certificate.updated_at = datetime.utcnow()
                db.session.commit()
        except:
            pass
        
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying SSL certificate renewal for certificate {certificate_id}")
            raise self.retry(countdown=120 * (self.request.retries + 1))
        
        return {'error': str(e)}

@shared_task
def check_expiring_certificates():
    """Check for certificates expiring within 30 days and renew them"""
    try:
        logger.info("Checking for expiring SSL certificates")
        
        # Get certificates expiring within 30 days
        expiry_threshold = datetime.utcnow() + timedelta(days=30)
        
        expiring_certs = SSLCertificate.query.filter(
            SSLCertificate.status == 'active',
            SSLCertificate.auto_renew == True,
            SSLCertificate.expires_at <= expiry_threshold
        ).all()
        
        if not expiring_certs:
            logger.info("No certificates require renewal")
            return {'success': True, 'renewals_started': 0}
        
        renewal_results = []
        
        for certificate in expiring_certs:
            try:
                # Start renewal process
                task = renew_ssl_certificate.delay(certificate.id)
                renewal_results.append({
                    'certificate_id': certificate.id,
                    'domain': certificate.domain_name,
                    'expires_at': certificate.expires_at.isoformat(),
                    'task_id': task.id
                })
                logger.info(f"Renewal started for certificate: {certificate.domain_name}")
            except Exception as e:
                logger.error(f"Error starting renewal for certificate {certificate.id}: {str(e)}")
                renewal_results.append({
                    'certificate_id': certificate.id,
                    'domain': certificate.domain_name,
                    'error': str(e)
                })
        
        logger.info(f"Certificate renewal check completed: {len(renewal_results)} renewals started")
        
        return {
            'success': True,
            'renewals_started': len(renewal_results),
            'renewal_results': renewal_results
        }
        
    except Exception as e:
        logger.error(f"Check expiring certificates error: {str(e)}")
        return {'error': str(e)}

@shared_task
def revoke_ssl_certificate(certificate_id):
    """Revoke SSL certificate"""
    try:
        logger.info(f"Revoking SSL certificate for certificate ID: {certificate_id}")
        
        # Get certificate record
        certificate = SSLCertificate.query.get(certificate_id)
        if not certificate:
            logger.error(f"Certificate not found: {certificate_id}")
            return {'error': 'Certificate not found'}
        
        domain_name = certificate.domain_name
        
        # Revoke certificate using ACME.sh
        acme_command = f"""
        /acme.sh/acme.sh --revoke \\
            -d {domain_name}
        """
        
        logger.info(f"Revoking certificate for domain: {domain_name}")
        result = run_acme_command(acme_command, timeout=300)
        
        if result['success']:
            logger.info(f"Certificate revoked successfully for domain: {domain_name}")
            
            # Update certificate status
            certificate.status = 'revoked'
            certificate.updated_at = datetime.utcnow()
            
            # Disable SSL for associated domains
            Domain.query.filter_by(ssl_certificate_id=certificate.id).update({
                'ssl_enabled': False,
                'updated_at': datetime.utcnow()
            })
            
            db.session.commit()
            
            return {
                'success': True,
                'domain': domain_name,
                'certificate_id': certificate_id
            }
        else:
            logger.error(f"Certificate revocation failed for domain {domain_name}: {result.get('stderr', 'Unknown error')}")
            return {
                'success': False,
                'error': result.get('stderr', 'Unknown error')
            }
        
    except Exception as e:
        logger.error(f"SSL certificate revocation error for certificate {certificate_id}: {str(e)}")
        return {'error': str(e)}

@shared_task
def cleanup_expired_certificates():
    """Clean up expired and revoked certificates"""
    try:
        logger.info("Cleaning up expired SSL certificates")
        
        # Get expired certificates (more than 7 days past expiry)
        cleanup_threshold = datetime.utcnow() - timedelta(days=7)
        
        expired_certs = SSLCertificate.query.filter(
            SSLCertificate.status.in_(['expired', 'revoked']),
            SSLCertificate.expires_at <= cleanup_threshold
        ).all()
        
        cleanup_count = 0
        
        for certificate in expired_certs:
            try:
                # Remove certificate files
                if certificate.certificate_path and os.path.exists(certificate.certificate_path):
                    os.remove(certificate.certificate_path)
                if certificate.private_key_path and os.path.exists(certificate.private_key_path):
                    os.remove(certificate.private_key_path)
                if certificate.chain_path and os.path.exists(certificate.chain_path):
                    os.remove(certificate.chain_path)
                
                # Remove certificate directory
                cert_dir = os.path.dirname(certificate.certificate_path) if certificate.certificate_path else None
                if cert_dir and os.path.exists(cert_dir) and os.path.isdir(cert_dir):
                    os.rmdir(cert_dir)
                
                # Delete certificate record
                db.session.delete(certificate)
                cleanup_count += 1
                
                logger.info(f"Cleaned up expired certificate: {certificate.domain_name}")
                
            except Exception as e:
                logger.error(f"Error cleaning up certificate {certificate.id}: {str(e)}")
        
        db.session.commit()
        
        logger.info(f"Certificate cleanup completed: {cleanup_count} certificates cleaned up")
        
        return {
            'success': True,
            'certificates_cleaned': cleanup_count
        }
        
    except Exception as e:
        logger.error(f"Cleanup expired certificates error: {str(e)}")
        return {'error': str(e)}

@shared_task
def bulk_issue_certificates(domain_names):
    """Bulk issue SSL certificates for multiple domains"""
    try:
        logger.info(f"Bulk issuing SSL certificates for {len(domain_names)} domains")
        
        issue_results = []
        
        for domain_name in domain_names:
            try:
                # Find or create certificate record
                certificate = SSLCertificate.query.filter_by(domain_name=domain_name).first()
                
                if not certificate:
                    # Find domain to get user_id
                    domain = Domain.query.filter_by(domain_name=domain_name).first()
                    if not domain:
                        logger.error(f"Domain not found in database: {domain_name}")
                        issue_results.append({
                            'domain': domain_name,
                            'error': 'Domain not found in database'
                        })
                        continue
                    
                    # Create certificate record
                    certificate = SSLCertificate(
                        user_id=domain.user_id,
                        domain_name=domain_name,
                        status='pending'
                    )
                    db.session.add(certificate)
                    db.session.commit()
                
                # Start certificate issuance
                task = issue_ssl_certificate.delay(certificate.id)
                issue_results.append({
                    'domain': domain_name,
                    'certificate_id': certificate.id,
                    'task_id': task.id
                })
                
            except Exception as e:
                logger.error(f"Error starting certificate issuance for domain {domain_name}: {str(e)}")
                issue_results.append({
                    'domain': domain_name,
                    'error': str(e)
                })
        
        logger.info(f"Bulk certificate issuance initiated for {len(issue_results)} domains")
        
        return {
            'success': True,
            'total_domains': len(domain_names),
            'issue_results': issue_results
        }
        
    except Exception as e:
        logger.error(f"Bulk issue certificates error: {str(e)}")
        return {'error': str(e)}