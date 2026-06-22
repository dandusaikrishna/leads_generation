"""
Email Enrichment Module - Pattern generation and email candidate creation
Generates email patterns based on company names and person names
"""

import re
from typing import List, Set


def split_name(fullname: str) -> tuple:
    """Split full name into first and last names."""
    # Remove parentheses content
    name = re.sub(r"\([^)]*\)", "", fullname)
    # Remove special characters
    name = re.sub(r"[^\w\s-]", "", name)
    parts = [p.strip().lower() for p in name.split() if p.strip()]
    
    # Remove titles
    titles = {"mr", "ms", "mrs", "dr", "prof", "eng", "mba", "phd", "mr.", "ms.", "mrs.", "dr."}
    parts = [p for p in parts if p.lower() not in titles]
    
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[-1]


def generate_email_candidates(fullname: str, domain: str) -> List[str]:
    """Generate email address candidates for a person at a domain."""
    first, last = split_name(fullname)
    if not first or not domain:
        return []
    
    domain = domain.lower().strip()
    candidates = []
    
    if last:
        patterns = [
            f"{first}.{last}@{domain}",      # john.doe@domain.com
            f"{first}@{domain}",             # john@domain.com
            f"{first}{last}@{domain}",       # johndoe@domain.com
            f"{first[0]}{last}@{domain}",    # jdoe@domain.com
            f"{first}.{last[0]}@{domain}",   # john.d@domain.com
            f"{first}_{last}@{domain}",      # john_doe@domain.com
            f"{last}@{domain}",              # doe@domain.com
            f"{first[0]}.{last}@{domain}",   # j.doe@domain.com
        ]
    else:
        patterns = [f"{first}@{domain}"]
    
    for p in patterns:
        if p not in candidates:
            candidates.append(p)
    
    return candidates


def generate_role_patterns(domain: str, role_type: str = "hr", names_list: dict = None) -> List[str]:
    """
    Generate email patterns for specific roles (HR, Founder, etc).
    
    Args:
        domain: Company domain (e.g., "example.com")
        role_type: "hr" or "founder"
        names_list: Dictionary with common first/last names
    """
    if not domain:
        return []
    
    domain = domain.lower().strip()
    emails = []
    
    if names_list is None:
        names_list = {
            "hr": ["priya", "rajesh", "amit", "neha", "arun", "anjali", "vikram", "pooja", "rahul", "shreya"],
            "founder": ["shah", "patel", "kumar", "singh", "gupta", "sharma", "verma", "chopra", "reddy", "nair"],
        }
    
    # Role-specific patterns
    if role_type == "hr":
        names = names_list.get("hr", [])
        for fname in names[:3]:
            emails.append(f"{fname}.hr@{domain}")
            emails.append(f"hr.{fname}@{domain}")
            emails.append(f"{fname}@{domain}")
        
        # Generic HR emails
        emails.extend([
            f"hr@{domain}",
            f"hire@{domain}",
            f"recruitment@{domain}",
            f"careers@{domain}",
            f"talent@{domain}",
            f"hiring@{domain}",
            f"jobs@{domain}",
            f"recruiter@{domain}",
            f"hr-manager@{domain}",
        ])
    
    elif role_type == "founder":
        surnames = names_list.get("founder", [])
        for surname in surnames[:3]:
            emails.append(f"founder.{surname}@{domain}")
            emails.append(f"{surname}@{domain}")
        
        # Generic founder emails
        emails.extend([
            f"founder@{domain}",
            f"ceo@{domain}",
            f"contact@{domain}",
            f"info@{domain}",
            f"hello@{domain}",
            f"support@{domain}",
        ])
    
    # Remove duplicates while preserving order
    unique_emails = []
    seen = set()
    for email in emails:
        if email not in seen:
            unique_emails.append(email)
            seen.add(email)
    
    return unique_emails


def extract_domain_from_url(url: str) -> str:
    """Extract clean domain from URL."""
    try:
        url = url.replace("https://", "").replace("http://", "").replace("www.", "")
        domain = url.split("/")[0].split("?")[0]
        return domain.lower().strip()
    except:
        return ""


def dedup_emails(emails: List[str]) -> List[str]:
    """Remove duplicate emails."""
    return list(set(emails))


def filter_emails(emails: List[str], exclude_domains: Set[str] = None) -> List[str]:
    """
    Filter out emails from excluded domains.
    
    Args:
        emails: List of email addresses
        exclude_domains: Set of domains to exclude (e.g., {'gmail.com', 'yahoo.com'})
    """
    if exclude_domains is None:
        exclude_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com"}
    
    filtered = []
    for email in emails:
        domain = email.split("@")[1].lower() if "@" in email else ""
        if domain not in exclude_domains:
            filtered.append(email)
    
    return filtered
