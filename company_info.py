"""
Company information collection module.
"""

import re
from typing import Optional, Dict
from utils import (
    serper_search, llm_query, clean_json_text, safe_json_loads,
    logger, extract_domain, normalize_domain, make_url
)


def resolve_company_domain(company_name: str, country: str) -> Optional[str]:
    """
    Resolve the official website domain for a company.
    
    Args:
        company_name: Company name
        country: Country where company operates
    
    Returns:
        Domain name (e.g., "company.com") or None
    """
    logger.info(f"Resolving domain for: {company_name} in {country}")
    
    query = f"{company_name} {country} official website"
    results = serper_search(query, num=8)
    
    if not results:
        return None
    
    snippets_text = "\n".join([
        f"- Title: {r.get('title')}\n  Link: {r.get('link')}\n  Snippet: {r.get('snippet')}"
        for r in results
    ])
    
    prompt = f"""From these search results, find the official website domain for '{company_name}' based in {country}.
Extract ONLY the domain (e.g., 'company.com' or 'company.eg'), without http://, www., or trailing slash.
Exclude: LinkedIn, social media, news sites, Wikipedia unless there's no other source.
Return ONLY the domain in lowercase, or 'null' if not found. No explanation, just the domain or null.

Results:
{snippets_text}"""
    
    raw_response = llm_query(prompt, max_tokens=50)
    domain = clean_json_text(raw_response).lower().strip()
    
    # Fallback: extract from URLs if LLM fails
    if "null" in domain or not domain or " " in domain:
        blocked = ["linkedin.com", "facebook.com", "instagram.com", "twitter.com", 
                   "wikipedia.org", "crunchbase.com", "news", "reddit"]
        for result in results:
            link = result.get("link", "")
            extracted_domain = extract_domain(link)
            if extracted_domain and not any(b in extracted_domain for b in blocked):
                logger.info(f"Resolved domain: {extracted_domain}")
                return extracted_domain
        return None
    
    logger.info(f"Resolved domain: {domain}")
    return domain if domain and "null" not in domain else None


def get_company_info(company_name: str, domain: Optional[str], country: str) -> Dict:
    """
    Get company information (industry, size, location, etc.).
    
    Args:
        company_name: Company name
        domain: Company domain (optional)
        country: Country
    
    Returns:
        Dictionary with company info
    """
    logger.info(f"Fetching company info for: {company_name}")
    
    search_terms = f"{company_name} company profile industry size employees {country}"
    results = serper_search(search_terms, num=8)
    
    if not results:
        logger.warning(f"No company info found for {company_name}")
        return {"industry": None, "company_size": None, "location": country}
    
    snippets_text = "\n".join([
        f"- Title: {r.get('title')}\n  Snippet: {r.get('snippet')}"
        for r in results[:5]
    ])
    
    prompt = f"""From these search results, extract company information for '{company_name}':
- industry: Industry/sector (e.g., "Software", "FinTech", "E-commerce")
- company_size: Company size (e.g., "50-100", "1000+", "5-10")
- location: Headquarters location

Return JSON with these fields only. If not found, use null. Return ONLY JSON, no explanation.

Results:
{snippets_text}"""
    
    raw_response = llm_query(prompt, max_tokens=200)
    cleaned = clean_json_text(raw_response)
    info = safe_json_loads(cleaned, default={})
    
    return {
        "industry": info.get("industry"),
        "company_size": info.get("company_size"),
        "location": info.get("location") or country
    }


def find_linkedin_company_profile(company_name: str) -> Optional[str]:
    """
    Find LinkedIn company profile URL.
    
    Args:
        company_name: Company name
    
    Returns:
        LinkedIn company URL or None
    """
    logger.info(f"Finding LinkedIn profile for: {company_name}")
    
    query = f'site:linkedin.com/company/ "{company_name}"'
    results = serper_search(query, num=3)
    
    for result in results:
        link = result.get("link", "")
        if "linkedin.com/company/" in link:
            logger.info(f"Found LinkedIn profile: {link}")
            return link
    
    return None


def find_careers_page(domain: str) -> Optional[str]:
    """
    Find company careers page URL.
    
    Args:
        domain: Company domain
    
    Returns:
        Careers page URL or None
    """
    logger.info(f"Finding careers page for: {domain}")
    
    common_paths = [
        "/careers",
        "/jobs",
        "/hiring",
        "/work-with-us",
        "/join-us",
        "/career",
        "/jobs.html",
        "/careers.html"
    ]
    
    for path in common_paths:
        url = make_url(domain, path)
        try:
            response = __import__('requests').head(url, timeout=5, allow_redirects=True)
            if response.status_code == 200:
                logger.info(f"Found careers page: {url}")
                return url
        except:
            pass
    
    # Try searching for careers page
    query = f'site:{domain} careers OR jobs OR hiring'
    results = serper_search(query, num=3)
    
    for result in results:
        link = result.get("link", "")
        if any(keyword in link.lower() for keyword in ["career", "job", "hiring"]):
            logger.info(f"Found careers page: {link}")
            return link
    
    return None


def collect_public_emails_from_domain(domain: str, company_name: str) -> list:
    """
    Collect public emails from company domain and website.
    
    Args:
        domain: Company domain
        company_name: Company name
    
    Returns:
        List of public emails with confidence scores
    """
    logger.info(f"Collecting public emails from: {domain}")
    
    emails = []
    
    # Search for public emails associated with domain
    query = f'site:{domain} email OR contact OR careers'
    results = serper_search(query, num=10)
    
    if results:
        snippets_text = "\n".join([
            f"- {r.get('title')}: {r.get('snippet')}"
            for r in results[:5]
        ])
        
        prompt = f"""Extract public email addresses from these search results for '{company_name}' ({domain}).
Look for emails like: careers@, hiring@, jobs@, hr@, contact@, hello@, info@, support@, etc.
Extract:
- email: Email address
- category: Type (careers, hiring, hr, support, contact, etc.)
- source: Where found (careers page, website, etc.)
- confidence: 0-100 confidence score

Return JSON array. ONLY return JSON array, no explanation.

Results:
{snippets_text}"""
        
        raw_response = llm_query(prompt, max_tokens=500)
        cleaned = clean_json_text(raw_response)
        extracted = safe_json_loads(cleaned, default=[])
        
        if isinstance(extracted, list):
            for item in extracted:
                if isinstance(item, dict) and item.get("email"):
                    emails.append({
                        "email": item.get("email"),
                        "category": item.get("category", "general"),
                        "confidence_score": min(100, max(0, item.get("confidence", 60))),
                        "source": item.get("source", domain)
                    })
    
    logger.info(f"Found {len(emails)} public emails")
    return emails
