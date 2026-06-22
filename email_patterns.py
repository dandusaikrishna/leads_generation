"""
Email pattern analysis module - analyzing publicly visible email patterns.
"""

import re
from typing import List, Dict, Optional
from utils import (
    serper_search, llm_query, clean_json_text, safe_json_loads,
    logger, extract_emails_from_text, validate_email, normalize_email,
    split_name
)
from config import EMAIL_PATTERNS


def analyze_email_patterns(domain: str, company_name: str) -> List[Dict]:
    """
    Analyze publicly visible email patterns at a company domain.
    
    Searches for publicly visible emails and identifies common patterns.
    
    Args:
        domain: Company domain
        company_name: Company name
    
    Returns:
        List of detected email patterns with confidence scores
    """
    logger.info(f"Analyzing email patterns for: {domain}")
    
    # Search for emails on domain
    query = f'site:{domain} email OR contact OR "@{domain}"'
    results = serper_search(query, num=15)
    
    if not results:
        logger.warning(f"No publicly visible emails found on {domain}")
        return []
    
    # Extract email addresses from search results
    all_emails = []
    for result in results:
        text = f"{result.get('title', '')} {result.get('snippet', '')}"
        emails = extract_emails_from_text(text)
        for email in emails:
            if email.endswith(f"@{domain}"):
                all_emails.append(email)
    
    all_emails = list(set(all_emails))
    
    if not all_emails:
        logger.warning(f"No emails found on {domain}")
        return []
    
    logger.info(f"Found {len(all_emails)} public emails on {domain}")
    
    # Analyze patterns
    patterns = _extract_patterns_from_emails(all_emails, domain)
    
    # Score patterns by frequency
    pattern_counts = {}
    for pattern in patterns:
        pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
    
    # Convert to result format
    results_list = []
    total_emails = len(all_emails)
    
    for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True):
        confidence = min(100, (count / total_emails) * 100 * 1.5)  # Normalize confidence
        results_list.append({
            "pattern": pattern,
            "examples": [e for e in all_emails if _matches_pattern(e, pattern, domain)][:3],
            "confidence_score": int(confidence),
            "frequency": count,
            "source_url": domain
        })
    
    logger.info(f"Identified {len(results_list)} email patterns")
    return results_list


def _extract_patterns_from_emails(emails: List[str], domain: str) -> List[str]:
    """
    Extract email patterns from a list of emails.
    
    Args:
        emails: List of email addresses
        domain: Company domain
    
    Returns:
        List of identified patterns
    """
    patterns = []
    
    for email in emails:
        # Extract local part (before @)
        local = email.split("@")[0] if "@" in email else email
        
        # Identify pattern type
        if "." in local and "_" not in local:
            # Could be firstname.lastname
            parts = local.split(".")
            if len(parts) == 2 and len(parts[0]) > 0 and len(parts[1]) > 0:
                patterns.append("firstname.lastname")
                patterns.append("firstinitial.lastname")  # j.doe format
        
        elif "_" in local and "." not in local:
            patterns.append("firstname_lastname")
        
        elif len(local) <= 4 and local.isalpha():
            patterns.append("firstname")  # Single word like "john"
        
        elif len(local) <= 8 and local[0].isalpha() and local[-1].isalpha():
            patterns.append("firstinitiallastname")  # jdoe format
    
    return list(set(patterns))


def _matches_pattern(email: str, pattern: str, domain: str) -> bool:
    """Check if email matches a pattern"""
    local = email.replace(f"@{domain}", "").lower()
    
    if pattern == "firstname.lastname":
        return "." in local and "_" not in local
    elif pattern == "firstname_lastname":
        return "_" in local
    elif pattern == "firstinitiallastname":
        return len(local) <= 8 and len(local) >= 3
    elif pattern == "firstname":
        return len(local) <= 6 and local.isalpha()
    elif pattern == "firstinitial.lastname":
        return "." in local and len(local.split(".")[0]) == 1
    
    return False


def generate_email_candidates(name: str, domain: str) -> List[Dict]:
    """
    Generate email address candidates for a person.
    
    Based on the person's name and identified email patterns.
    
    Args:
        name: Person's full name
        domain: Company domain
    
    Returns:
        List of email candidates with pattern information
    """
    first, last = split_name(name)
    
    if not first:
        return []
    
    domain = domain.lower()
    candidates = []
    
    patterns_to_try = [
        (f"{first}.{last}@{domain}" if last else None, "firstname.lastname"),
        (f"{first}@{domain}", "firstname"),
        (f"{first}{last}@{domain}" if last else None, "firstnamelastname"),
        (f"{first[0]}{last}@{domain}" if last else None, "firstinitiallastname"),
        (f"{first}.{last[0]}@{domain}" if last else None, "firstname.lastinitial"),
        (f"{first}_{last}@{domain}" if last else None, "firstname_lastname"),
        (f"{last}@{domain}" if last else None, "lastname"),
        (f"{first[0]}.{last}@{domain}" if last else None, "firstinitial.lastname"),
    ]
    
    for email, pattern in patterns_to_try:
        if email and validate_email(email):
            candidates.append({
                "email": email,
                "pattern": pattern,
                "confidence": 50  # Base confidence, increased if pattern is common
            })
    
    return candidates


def verify_email_pattern_validity(domain: str, pattern: str, examples: List[str]) -> int:
    """
    Verify if a pattern is actually valid based on examples.
    
    Args:
        domain: Company domain
        pattern: Email pattern
        examples: Example emails with this pattern
    
    Returns:
        Confidence score 0-100
    """
    if not examples:
        return 20
    
    # If we have multiple examples, confidence is higher
    confidence = min(100, 30 + len(examples) * 25)
    
    # Check if all examples are valid format
    all_valid = all(validate_email(e) for e in examples)
    if not all_valid:
        confidence = max(0, confidence - 30)
    
    logger.debug(f"Pattern '{pattern}' confidence: {confidence}")
    return confidence


def predict_email_from_name(contact_name: str, domain: str, 
                           identified_patterns: List[Dict]) -> Optional[str]:
    """
    Predict the most likely email for a contact based on patterns.
    
    Args:
        contact_name: Contact's full name
        domain: Company domain
        identified_patterns: List of identified patterns with scores
    
    Returns:
        Most likely email address or None
    """
    candidates = generate_email_candidates(contact_name, domain)
    
    if not candidates:
        return None
    
    # Score each candidate based on identified patterns
    for candidate in candidates:
        pattern = candidate.get("pattern")
        candidate_pattern = pattern.lower().replace("_", ".").replace("-", "")
        
        # Find matching identified pattern
        for identified in identified_patterns:
            if candidate_pattern in identified.get("pattern", "").lower():
                candidate["confidence"] = identified.get("confidence_score", 50)
                break
    
    # Return highest confidence candidate
    best = max(candidates, key=lambda x: x.get("confidence", 0))
    return best.get("email") if best.get("confidence", 0) > 20 else None
