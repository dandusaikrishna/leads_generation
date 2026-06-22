"""
Enhanced email verification and validation.
Checks if emails are actually working and valid.
"""

import socket
import smtplib
import time
from typing import List, Tuple, Dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import dns.resolver
from utils import logger, validate_email, normalize_email

# Cache for DNS lookups
MX_CACHE = {}
SMTP_CACHE = {}


def get_mx_records(domain: str) -> List[str]:
    """
    Get MX records for a domain using DNS.
    
    Args:
        domain: Email domain
    
    Returns:
        List of MX server hostnames
    """
    if domain in MX_CACHE:
        return MX_CACHE[domain]
    
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        mx_hosts = [str(mx.exchange).rstrip('.') for mx in sorted(
            mx_records, key=lambda x: x.preference
        )]
        MX_CACHE[domain] = mx_hosts
        logger.debug(f"Found {len(mx_hosts)} MX records for {domain}")
        return mx_hosts
    except Exception as e:
        logger.warning(f"MX lookup failed for {domain}: {str(e)}")
        MX_CACHE[domain] = []
        return []


def check_catch_all(domain: str, mx_hosts: List[str], timeout: int = 10) -> bool:
    """
    Check if domain has catch-all email configured.
    
    Args:
        domain: Email domain
        mx_hosts: List of MX servers
        timeout: Connection timeout
    
    Returns:
        True if catch-all, False otherwise
    """
    if not mx_hosts:
        return False
    
    try:
        smtp = smtplib.SMTP(timeout=timeout)
        smtp.connect(mx_hosts[0])
        
        # Test with fake email
        smtp.helo(smtp.local_hostname)
        smtp.mail(f'test@test.com')
        
        # Try random address
        code, message = smtp.rcpt(f'random{int(time.time())}@{domain}')
        smtp.quit()
        
        is_catch_all = code != 550
        logger.debug(f"Catch-all check for {domain}: {is_catch_all}")
        return is_catch_all
    except Exception as e:
        logger.warning(f"Catch-all check failed for {domain}: {str(e)}")
        return False


def verify_email_smtp(email: str, domain: str, mx_hosts: List[str], timeout: int = 10) -> Tuple[bool, int, str]:
    """
    Verify email existence via SMTP.
    
    Args:
        email: Email address to verify
        domain: Email domain
        mx_hosts: List of MX servers
        timeout: Connection timeout
    
    Returns:
        (exists, confidence_score, notes)
        - exists: True if email appears to exist
        - confidence_score: 0-100 confidence
        - notes: Description of verification result
    """
    email = normalize_email(email)
    
    if not validate_email(email):
        return False, 0, "Invalid email format"
    
    if not mx_hosts:
        mx_hosts = get_mx_records(domain)
    
    if not mx_hosts:
        return False, 10, "No MX records found"
    
    cache_key = f"{email}"
    if cache_key in SMTP_CACHE:
        cached_result = SMTP_CACHE[cache_key]
        return cached_result
    
    try:
        smtp = smtplib.SMTP(timeout=timeout)
        smtp.connect(mx_hosts[0])
        
        smtp.helo(smtp.local_hostname)
        smtp.mail('test@test.com')
        
        # Verify recipient
        code, message = smtp.rcpt(email)
        smtp.quit()
        
        if code == 250:
            result = (True, 95, "Email verified via SMTP")
        elif code == 550:
            result = (False, 10, "Email rejected (550)")
        elif code == 551:
            result = (False, 15, "User not local (551)")
        elif code == 552:
            result = (False, 20, "Exceeded storage (552)")
        elif code == 553:
            result = (False, 15, "Invalid mailbox (553)")
        else:
            result = (True, 60, f"Uncertain (code {code})")
        
        SMTP_CACHE[cache_key] = result
        return result
    
    except smtplib.SMTPServerDisconnected:
        logger.debug(f"SMTP disconnected for {email}")
        return False, 30, "SMTP disconnected"
    except socket.timeout:
        logger.debug(f"SMTP timeout for {email}")
        return False, 25, "Connection timeout"
    except Exception as e:
        logger.warning(f"SMTP verification failed for {email}: {str(e)}")
        return False, 20, str(e)


def verify_emails_batch(emails: List[str], domain: str) -> Dict[str, Dict]:
    """
    Verify multiple emails in batch.
    
    Args:
        emails: List of email addresses
        domain: Email domain
    
    Returns:
        Dictionary with verification results
    """
    logger.info(f"Verifying {len(emails)} emails for {domain}...")
    
    mx_hosts = get_mx_records(domain)
    results = {}
    
    for email in emails:
        email = normalize_email(email)
        if validate_email(email):
            exists, confidence, notes = verify_email_smtp(email, domain, mx_hosts)
            results[email] = {
                "exists": exists,
                "confidence": confidence,
                "notes": notes
            }
            time.sleep(0.1)  # Rate limiting
    
    verified_count = sum(1 for r in results.values() if r['exists'])
    logger.info(f"Verified {verified_count}/{len(emails)} emails")
    
    return results


def validate_email_quality(email: str, domain: str = None) -> Dict:
    """
    Comprehensive email quality check.
    
    Args:
        email: Email address
        domain: Email domain (extracted if not provided)
    
    Returns:
        Quality assessment dictionary
    """
    email = normalize_email(email)
    
    if not domain:
        if '@' in email:
            domain = email.split('@')[1]
        else:
            return {"valid": False, "quality_score": 0, "issues": ["Invalid email format"]}
    
    issues = []
    checks = {}
    
    # Format validation
    if not validate_email(email):
        issues.append("Invalid email format")
        return {"valid": False, "quality_score": 0, "issues": issues}
    
    checks["format_valid"] = True
    
    # Domain validation
    mx_hosts = get_mx_records(domain)
    if not mx_hosts:
        issues.append(f"No MX records for domain {domain}")
        checks["has_mx"] = False
    else:
        checks["has_mx"] = True
    
    # Catch-all check
    if checks["has_mx"]:
        is_catch_all = check_catch_all(domain, mx_hosts)
        if is_catch_all:
            checks["catch_all"] = True
            issues.append("Domain has catch-all configured")
        else:
            checks["catch_all"] = False
    
    # SMTP verification
    if checks["has_mx"]:
        exists, confidence, notes = verify_email_smtp(email, domain, mx_hosts)
        checks["smtp_verified"] = exists
        checks["verification_confidence"] = confidence
    
    # Calculate quality score
    quality_score = 100
    if issues:
        quality_score -= len(issues) * 10
    if not checks.get("smtp_verified", False):
        quality_score = min(quality_score, 50)
    
    quality_score = max(0, min(100, quality_score))
    
    return {
        "email": email,
        "valid": not bool(issues),
        "quality_score": quality_score,
        "checks": checks,
        "issues": issues,
        "verified": checks.get("smtp_verified", False),
        "verification_confidence": checks.get("verification_confidence", 0)
    }


def filter_working_emails(emails: List[str], domain: str = None, min_quality: int = 60) -> List[Dict]:
    """
    Filter for high-quality, working emails.
    
    Args:
        emails: List of email addresses
        domain: Email domain (optional)
        min_quality: Minimum quality score (0-100)
    
    Returns:
        List of verified, high-quality emails
    """
    logger.info(f"Filtering {len(emails)} emails for quality (min_quality={min_quality})...")
    
    working_emails = []
    
    for email in emails:
        email = normalize_email(email)
        quality = validate_email_quality(email, domain)
        
        if quality["quality_score"] >= min_quality:
            working_emails.append({
                "email": email,
                "quality_score": quality["quality_score"],
                "verified": quality["verified"],
                "confidence": quality["verification_confidence"]
            })
        
        time.sleep(0.05)  # Rate limiting
    
    # Sort by quality score descending
    working_emails = sorted(working_emails, key=lambda x: x["quality_score"], reverse=True)
    
    logger.info(f"Found {len(working_emails)} working emails (>={min_quality} quality)")
    return working_emails
