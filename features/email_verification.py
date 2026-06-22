"""
Email Verification Module - SMTP and DNS validation
Verifies email addresses using SMTP connections and MX record lookups
"""

import smtplib
import dns.resolver
import socket
import random
import string
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)

# Cache for MX records and catch-all checks
MX_CACHE = {}
CATCH_ALL_CACHE = {}
DOMAINS_FAILED_CONN = set()


def get_mx_hosts(domain: str, timeout: float = 8.0) -> List[str]:
    """Get MX records for a domain."""
    domain = domain.strip().lower()
    if domain in MX_CACHE:
        return MX_CACHE[domain]
    
    try:
        answers = dns.resolver.resolve(domain, 'MX')
        hosts = [str(r.exchange).rstrip('.').lower() for r in sorted(answers, key=lambda r: r.preference)]
        MX_CACHE[domain] = hosts
        return hosts
    except Exception as e:
        logger.debug(f"MX lookup failed for {domain}: {e}")
        MX_CACHE[domain] = []
        return []


def check_catch_all(domain: str, mx_hosts: List[str], timeout: float = 6.0) -> bool:
    """Check if domain accepts all email addresses (catch-all)."""
    domain = domain.strip().lower()
    if domain in CATCH_ALL_CACHE:
        return CATCH_ALL_CACHE[domain]
    
    if not mx_hosts or domain in DOMAINS_FAILED_CONN:
        return False
    
    rand_prefix = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(16))
    bogus_email = f"verify-test-{rand_prefix}@{domain}"
    
    logger.info(f"Checking if domain '{domain}' is catch-all...")
    
    connected_any = False
    for mx in mx_hosts[:2]:
        try:
            with smtplib.SMTP(mx, 25, timeout=timeout) as smtp:
                connected_any = True
                smtp.helo("leads.ai")
                smtp.mail("verify@leads.ai")
                code, msg = smtp.rcpt(bogus_email)
                if code in (250, 251, 252):
                    logger.info(f"Domain '{domain}' IS catch-all")
                    CATCH_ALL_CACHE[domain] = True
                    return True
                elif code >= 500:
                    logger.info(f"Domain '{domain}' is NOT catch-all")
                    CATCH_ALL_CACHE[domain] = False
                    return False
        except Exception as e:
            logger.debug(f"SMTP connection to {mx} failed: {e}")
    
    if not connected_any:
        logger.warning(f"Could not connect to any MX for {domain}")
        DOMAINS_FAILED_CONN.add(domain)
    
    return False


def verify_email_smtp(email: str, domain: str, mx_hosts: List[str], timeout: float = 6.0) -> Tuple[str, int, str]:
    """
    Verify email using SMTP.
    
    Returns:
        Tuple[status, confidence_score (0-100), details]
    """
    if not mx_hosts:
        return "Invalid", 0, "No MX records found"
    
    if domain in DOMAINS_FAILED_CONN:
        return "Unknown", 30, "Domain unreachable (cached)"
    
    is_catch_all = check_catch_all(domain, mx_hosts, timeout)
    
    if domain in DOMAINS_FAILED_CONN:
        return "Unknown", 30, "Domain unreachable"
    
    connected_any = False
    for mx in mx_hosts[:2]:
        try:
            with smtplib.SMTP(mx, 25, timeout=timeout) as smtp:
                connected_any = True
                smtp.helo("leads.ai")
                smtp.mail("verify@leads.ai")
                code, msg = smtp.rcpt(email)
                msg_text = msg.decode("utf-8", errors="ignore") if isinstance(msg, bytes) else str(msg)
                
                block_keywords = ["spam", "block", "blacklist", "denied", "abuse", "reputation"]
                is_blocked = any(kw in msg_text.lower() for kw in block_keywords)
                
                if code in (250, 251, 252):
                    if is_blocked:
                        return "Unknown", 40, f"Accepted but IP blocked: {msg_text[:100]}"
                    if is_catch_all:
                        return "Probable", 65, "Domain accepts all addresses"
                    else:
                        return "Verified", 95, "Email verified"
                elif code >= 500:
                    return "Invalid", 10, f"Hard reject ({code})"
                elif code >= 400:
                    return "Unknown", 35, f"Temp reject ({code})"
        
        except socket.timeout:
            logger.debug(f"SMTP timeout for {email}")
            continue
        except Exception as e:
            logger.debug(f"SMTP error: {e}")
            continue
    
    if not connected_any:
        logger.warning(f"Could not connect to any MX for {domain}")
        DOMAINS_FAILED_CONN.add(domain)
    
    return "Unknown", 30, "SMTP connections failed"
