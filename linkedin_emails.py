"""
LinkedIn company emails extraction - Legal mining of publicly shared contact information.
Extracts company emails from LinkedIn company pages, posts, and job postings.
"""

import re
import time
import json
from typing import List, Dict, Set, Optional
from datetime import datetime
from utils import serper_search, llm_query, clean_json_text, safe_json_loads, logger
from email_verification import validate_email_quality, filter_working_emails


def extract_company_emails_from_linkedin(company_name: str) -> List[Dict]:
    """
    Extract company emails from LinkedIn company page and posts.
    
    Args:
        company_name: Name of company
    
    Returns:
        List of company emails with metadata
    """
    logger.info(f"Extracting emails for {company_name} from LinkedIn...")
    
    emails = []
    
    # Search company page and posts
    query = f'site:linkedin.com/company/ "{company_name}" (email OR contact OR careers OR hiring OR recruitment)'
    results = serper_search(query, num=15)
    
    if not results:
        logger.warning(f"No emails found for {company_name}")
        return []
    
    # Extract from snippets
    snippets_text = "\n".join([
        f"Title: {r.get('title')}\nSnippet: {r.get('snippet')}"
        for r in results[:12]
    ])
    
    prompt = f"""Extract company contact emails from {company_name} LinkedIn posts and pages.

Find and extract:
- email_address: Company email address
- category: Email category (careers, hr, recruitment, engineering, general, contact, support, hello, info)
- context: Where/how email is used
- contact_type: Type of contact (careers@, jobs@, hr@, engineering@, recruiting@, hello@, etc.)
- public_source: Where it's publicly mentioned (LinkedIn post, company page, job posting, etc.)
- confidence: High/Medium/Low based on how clearly visible

Extract ONLY emails explicitly mentioned or clearly visible in LinkedIn content.
Do NOT generate or guess emails.
Return JSON array with these fields.
Return ONLY the JSON array, no explanation.

Content:
{snippets_text}"""
    
    raw = llm_query(prompt, max_tokens=1000)
    cleaned = clean_json_text(raw)
    extracted = safe_json_loads(cleaned, default=[])
    
    if isinstance(extracted, list):
        for item in extracted:
            if isinstance(item, dict) and item.get("email_address"):
                # Validate email
                email = item["email_address"].lower().strip()
                if validate_email_basic(email):
                    emails.append({
                        "email": email,
                        "category": item.get("category", "general"),
                        "contact_type": item.get("contact_type", ""),
                        "source": f"LinkedIn - {company_name}",
                        "public_source": item.get("public_source", ""),
                        "confidence": item.get("confidence", "Medium")
                    })
    
    logger.info(f"Found {len(emails)} company emails for {company_name}")
    return emails


def extract_emails_from_job_postings(
    company_name: str,
    limit: int = 5
) -> List[Dict]:
    """
    Extract company/recruiter emails from job postings.
    
    Args:
        company_name: Company name
        limit: Max emails to find
    
    Returns:
        List of emails from job postings
    """
    logger.info(f"Extracting emails from {company_name} job postings...")
    
    emails = []
    
    # Search job postings
    query = f'site:linkedin.com/jobs "{company_name}" (apply OR email OR contact)'
    results = serper_search(query, num=10)
    
    if not results:
        logger.warning(f"No job postings found for {company_name}")
        return []
    
    snippets = "\n".join([f"{r.get('title')}: {r.get('snippet')}" for r in results[:8]])
    
    prompt = f"""Extract emails mentioned in {company_name} job postings for application or contact.

Extract:
- email: Email address
- purpose: Purpose of email (apply, contact, info, recruiter contact, etc.)
- job_title: Job title where this email appears
- recruiter_name: Recruiter name if mentioned with email
- department: Department/team if mentioned

Extract ONLY emails explicitly mentioned in job postings.
Return JSON array. Return ONLY the JSON array, no explanation.

Job Postings:
{snippets}"""
    
    raw = llm_query(prompt, max_tokens=600)
    cleaned = clean_json_text(raw)
    extracted = safe_json_loads(cleaned, default=[])
    
    if isinstance(extracted, list):
        for item in extracted:
            if isinstance(item, dict) and item.get("email"):
                email = item["email"].lower().strip()
                if validate_email_basic(email) and email not in [e.get("email") for e in emails]:
                    emails.append({
                        "email": email,
                        "source": f"Job Posting - {company_name}",
                        "purpose": item.get("purpose", ""),
                        "job_title": item.get("job_title", ""),
                        "recruiter_name": item.get("recruiter_name", ""),
                        "confidence": "High"
                    })
    
    return emails[:limit]


def extract_emails_from_company_posts(company_name: str) -> List[Dict]:
    """
    Extract emails from company's LinkedIn posts and announcements.
    
    Args:
        company_name: Company name
    
    Returns:
        List of emails from company posts
    """
    logger.info(f"Extracting emails from {company_name} LinkedIn posts...")
    
    emails = []
    
    # Search company posts
    query = f'site:linkedin.com/company/ "{company_name}" (careers OR join OR hiring OR team OR contact)'
    results = serper_search(query, num=12)
    
    if not results:
        logger.warning(f"No posts found for {company_name}")
        return []
    
    snippets = "\n".join([
        f"Post: {r.get('title')}\nContent: {r.get('snippet')}"
        for r in results[:10]
    ])
    
    prompt = f"""Extract contact emails from {company_name} LinkedIn posts about hiring, team, or careers.

Extract:
- email: Email address from post
- post_type: Type of post (hiring, culture, team, careers, etc.)
- department: Department mentioned
- post_summary: What the post is about
- mention_context: How email is mentioned

Extract ONLY emails explicitly shared in posts.
Return JSON array. Return ONLY the JSON array, no explanation.

Posts:
{snippets}"""
    
    raw = llm_query(prompt, max_tokens=800)
    cleaned = clean_json_text(raw)
    extracted = safe_json_loads(cleaned, default=[])
    
    if isinstance(extracted, list):
        for item in extracted:
            if isinstance(item, dict) and item.get("email"):
                email = item["email"].lower().strip()
                if validate_email_basic(email):
                    emails.append({
                        "email": email,
                        "source": f"LinkedIn Posts - {company_name}",
                        "post_type": item.get("post_type", ""),
                        "department": item.get("department", ""),
                        "context": item.get("mention_context", ""),
                        "confidence": "High"
                    })
    
    return emails


def find_hr_emails_by_pattern(
    company_name: str,
    company_domain: str = None
) -> List[str]:
    """
    Find HR emails using common patterns from company info.
    
    Args:
        company_name: Company name
        company_domain: Company domain (e.g., "company.com")
    
    Returns:
        List of likely HR email addresses
    """
    if not company_domain:
        logger.warning("Domain needed to predict HR emails")
        return []
    
    logger.info(f"Generating HR email patterns for {company_domain}...")
    
    # Common HR email patterns
    patterns = [
        f"careers@{company_domain}",
        f"jobs@{company_domain}",
        f"recruitment@{company_domain}",
        f"recruiting@{company_domain}",
        f"hr@{company_domain}",
        f"talent@{company_domain}",
        f"hiring@{company_domain}",
        f"humanresources@{company_domain}",
        f"people@{company_domain}",
        f"hr.recruitment@{company_domain}",
    ]
    
    return patterns


def compile_company_email_profile(
    company_name: str,
    company_domain: str = None
) -> Dict:
    """
    Compile comprehensive email profile for a company.
    
    Args:
        company_name: Company name
        company_domain: Company domain
    
    Returns:
        Complete email profile
    """
    logger.info(f"Compiling email profile for {company_name}...")
    
    profile = {
        "company_name": company_name,
        "domain": company_domain,
        "compiled_date": datetime.now().isoformat(),
        "verified_emails": [],
        "job_posting_emails": [],
        "post_emails": [],
        "pattern_predictions": [],
        "all_unique_emails": []
    }
    
    # Extract from different sources
    linkedin_emails = extract_company_emails_from_linkedin(company_name)
    time.sleep(0.3)
    
    job_emails = extract_emails_from_job_postings(company_name)
    time.sleep(0.3)
    
    post_emails = extract_emails_from_company_posts(company_name)
    time.sleep(0.3)
    
    profile["verified_emails"] = linkedin_emails
    profile["job_posting_emails"] = job_emails
    profile["post_emails"] = post_emails
    
    # Get pattern predictions if domain available
    if company_domain:
        patterns = find_hr_emails_by_pattern(company_name, company_domain)
        profile["pattern_predictions"] = patterns
    
    # Combine all unique emails
    all_emails = (
        [e.get("email") for e in linkedin_emails] +
        [e.get("email") for e in job_emails] +
        [e.get("email") for e in post_emails]
    )
    
    profile["all_unique_emails"] = list(set(all_emails))
    profile["total_unique_emails"] = len(profile["all_unique_emails"])
    
    logger.info(f"Compiled profile with {profile['total_unique_emails']} unique emails")
    
    return profile


def validate_email_basic(email: str) -> bool:
    """Basic email validation."""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.lower()))


def export_company_emails(companies: Dict, output_file: str) -> bool:
    """
    Export company email profiles to JSON.
    
    Args:
        companies: Dictionary of company email profiles
        output_file: Output file path
    
    Returns:
        True if successful
    """
    try:
        logger.info(f"Exporting company emails to {output_file}...")
        
        data = {
            "export_date": datetime.now().isoformat(),
            "total_companies": len(companies),
            "companies": companies
        }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Exported to {output_file}")
        return True
    except Exception as e:
        logger.error(f"❌ Export failed: {str(e)}")
        return False


def build_email_database(companies: List[Dict]) -> Dict:
    """
    Build comprehensive email database for multiple companies.
    
    Args:
        companies: List of company dictionaries with name and domain
    
    Returns:
        Email database
    """
    logger.info(f"Building email database for {len(companies)} companies...")
    
    database = {
        "build_date": datetime.now().isoformat(),
        "total_companies": len(companies),
        "email_count": 0,
        "companies": {}
    }
    
    for company in companies:
        name = company.get("company_name")
        domain = company.get("domain")
        
        if not name:
            continue
        
        profile = compile_company_email_profile(name, domain)
        database["companies"][name] = profile
        database["email_count"] += profile["total_unique_emails"]
        
        time.sleep(0.5)
    
    logger.info(f"Built database with {database['email_count']} total emails")
    
    return database
