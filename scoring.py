"""
Scoring system for companies and contacts.
"""

from typing import Dict
from models import Company, SeniorContact
from utils import logger
from config import ROLE_SCORES, SCORE_MODIFIERS


def calculate_company_score(company: Company) -> int:
    """
    Calculate overall company score based on multiple factors.
    
    Factors:
    - Contact quality and scores
    - Email availability
    - Pattern confidence
    - Other signals
    
    Args:
        company: Company object
    
    Returns:
        Final score 0-100
    """
    scores = {}
    
    # 1. Decision maker quality (0-35 points)
    decision_maker_score = _score_decision_makers(company.contacts)
    scores["decision_makers"] = decision_maker_score
    
    # 2. Email availability (0-20 points)
    email_score = _score_emails(company.public_emails)
    scores["emails"] = email_score
    
    # 3. Email patterns (0-15 points)
    pattern_score = _score_patterns(company.email_patterns)
    scores["patterns"] = pattern_score
    
    # 4. Job posting signals (0-15 points)
    job_score = _score_jobs(company.jobs)
    scores["jobs"] = job_score
    
    # 5. Company info completeness (0-15 points)
    info_score = _score_company_info(company)
    scores["info"] = info_score
    
    total_score = sum(scores.values())
    company.score_breakdown = scores
    
    logger.debug(f"Score breakdown for {company.company_name}: {scores} (Total: {total_score})")
    
    return min(100, total_score)


def _score_decision_makers(contacts: list) -> int:
    """Score based on decision makers quality and quantity"""
    if not contacts:
        return 0
    
    score = 0
    
    # Prioritize top roles
    top_contacts = sorted(
        contacts,
        key=lambda c: c.get("role_score", 50) if isinstance(c, dict) else c.role_score,
        reverse=True
    )[:3]  # Top 3
    
    for i, contact in enumerate(top_contacts):
        contact_score = contact.get("role_score", 50) if isinstance(contact, dict) else contact.role_score
        weight = 0.5 if i == 0 else (0.3 if i == 1 else 0.2)
        score += int(contact_score * weight)
    
    # Cap at 35 points
    return min(35, score)


def _score_emails(emails: list) -> int:
    """Score based on public email availability and types"""
    if not emails:
        return 0
    
    score = 0
    email_types = set()
    
    for email in emails:
        category = email.get("category", "") if isinstance(email, dict) else email.category
        confidence = email.get("confidence_score", 0) if isinstance(email, dict) else email.confidence_score
        
        email_types.add(category.lower())
        
        # High confidence emails
        if confidence >= 80:
            score += 3
        elif confidence >= 50:
            score += 2
        else:
            score += 1
    
    # Bonus for diverse email types
    if "careers" in email_types:
        score += 3
    if "hiring" in email_types:
        score += 3
    if "hr" in email_types:
        score += 2
    
    # Cap at 20 points
    return min(20, score)


def _score_patterns(patterns: list) -> int:
    """Score based on email pattern confidence"""
    if not patterns:
        return 0
    
    score = 0
    high_confidence_patterns = 0
    
    for pattern in patterns:
        confidence = pattern.get("confidence_score", 0) if isinstance(pattern, dict) else pattern.confidence_score
        
        if confidence >= 75:
            score += 4
            high_confidence_patterns += 1
        elif confidence >= 50:
            score += 2
        else:
            score += 1
    
    # Bonus for multiple high-confidence patterns
    if high_confidence_patterns >= 2:
        score += 3
    
    # Cap at 15 points
    return min(15, score)


def _score_jobs(jobs: list) -> int:
    """Score based on active job postings"""
    if not jobs:
        return 0
    
    score = 0
    
    for job in jobs:
        role = job.get("role_matched", "") if isinstance(job, dict) else job.role_matched
        source = job.get("source", "") if isinstance(job, dict) else job.source
        
        # Base score for having jobs
        score += 3
        
        # Bonus for recent/active jobs
        posted_date = job.get("posted_date") if isinstance(job, dict) else job.posted_date
        if posted_date and "day" in str(posted_date).lower():
            score += 2
        elif posted_date and "week" in str(posted_date).lower():
            score += 1
        
        # Bonus for multiple jobs
        if "Senior" in role or "Lead" in role:
            score += 2
    
    # Cap at 15 points
    return min(15, score)


def _score_company_info(company: Company) -> int:
    """Score based on company information completeness"""
    score = 0
    
    # Website verified
    if company.website:
        score += 3
    
    # LinkedIn profile
    if company.linkedin_url:
        score += 2
    
    # Industry identified
    if company.industry:
        score += 3
    
    # Company size
    if company.company_size:
        score += 3
    
    # Location
    if company.location:
        score += 2
    
    # Multiple sources
    if len(company.source_urls) >= 3:
        score += 2
    
    # Cap at 15 points
    return min(15, score)


def score_contact(contact: Dict) -> int:
    """
    Score a single contact based on role and attributes.
    
    Args:
        contact: Contact dictionary
    
    Returns:
        Score 0-100
    """
    score = contact.get("role_score", 50)
    
    # Boost if has LinkedIn URL
    if contact.get("linkedin_url"):
        score = min(100, score + 5)
    
    # Boost if found in recent posts
    if contact.get("verification_score", 0) > 0:
        score = min(100, score + contact.get("verification_score", 0) // 2)
    
    return score


def get_company_tier(score: int) -> str:
    """
    Classify company into tier based on score.
    
    Args:
        score: Company score 0-100
    
    Returns:
        Tier name
    """
    if score >= 90:
        return "Tier 1 (Excellent)"
    elif score >= 75:
        return "Tier 2 (Very Good)"
    elif score >= 60:
        return "Tier 3 (Good)"
    elif score >= 45:
        return "Tier 4 (Fair)"
    elif score >= 25:
        return "Tier 5 (Poor)"
    else:
        return "Tier 6 (Very Poor)"


def get_confidence_level(score: int) -> str:
    """
    Get confidence level description.
    
    Args:
        score: Confidence score 0-100
    
    Returns:
        Confidence level string
    """
    if score >= 90:
        return "Very High"
    elif score >= 75:
        return "High"
    elif score >= 50:
        return "Medium"
    elif score >= 25:
        return "Low"
    else:
        return "Very Low"
