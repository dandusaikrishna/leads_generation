"""
India-focused company discovery and enrichment.
Targets software companies in Telangana, Karnataka, Maharashtra and other Indian cities.
"""

import time
from typing import List, Dict, Optional
from config import (
    INDIA_CITIES, PRIORITY_STATES, INDIA_SOFTWARE_ROLES, 
    INDIA_SCORE_MODIFIERS, SERPER_SEARCH_PER_QUERY
)
from utils import serper_search, llm_query, clean_json_text, safe_json_loads, logger
from company_discovery import discover_hiring_companies
from enhanced_sources import (
    find_companies_on_github, find_companies_on_crunchbase,
    find_active_companies_stackoverflow, find_recent_company_activity,
    discover_companies_multi_source
)
from email_verification import validate_email_quality, filter_working_emails


def discover_companies_in_india(
    cities: Optional[List[str]] = None,
    limit: int = 100,
    include_remote: bool = True
) -> List[Dict]:
    """
    Discover companies in India with software engineering presence.
    
    Args:
        cities: List of cities to target. Default: Hyderabad, Bangalore, Pune
        limit: Maximum companies to discover
        include_remote: Include remote-first companies
    
    Returns:
        List of discovered companies
    """
    if cities is None:
        cities = ["Hyderabad", "Bangalore", "Pune"]
    
    logger.info(f"Starting India-focused company discovery in: {', '.join(cities)}")
    
    all_companies = []
    
    # Discover from each city
    for city in cities:
        logger.info(f"Discovering companies in {city}...")
        
        # Multi-source discovery
        city_companies = discover_companies_multi_source(city, country="India")
        
        # Add city/state information
        state = INDIA_CITIES.get(city, {}).get("state", "Unknown")
        for company in city_companies:
            company["target_city"] = city
            company["target_state"] = state
            company["priority"] = INDIA_CITIES.get(city, {}).get("priority", 3)
        
        all_companies.extend(city_companies)
        time.sleep(0.5)
    
    # Add remote companies with India presence
    if include_remote:
        logger.info("Discovering remote-first companies with India presence...")
        remote_companies = find_remote_companies_with_india_presence(limit=20)
        all_companies.extend(remote_companies)
    
    # Deduplicate
    seen = set()
    unique = []
    for company in all_companies:
        key = company.get("company_name", "").lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(company)
    
    logger.info(f"Discovered {len(unique)} unique companies in India")
    return unique[:limit]


def find_remote_companies_with_india_presence(limit: int = 20) -> List[Dict]:
    """
    Find remote-first companies with India engineering presence.
    
    Args:
        limit: Maximum companies to find
    
    Returns:
        List of remote companies with India presence
    """
    logger.info("Finding remote companies with India presence...")
    
    query = 'site:linkedin.com/company ("India" OR "Hyderabad" OR "Bangalore") remote engineering'
    results = serper_search(query, num=15)
    
    if not results:
        return []
    
    snippets = "\n".join([f"- {r.get('title')}: {r.get('snippet')}" for r in results[:10]])
    
    prompt = f"""Find remote-first companies with engineering teams in India.
Extract:
- company_name: Company name
- domain: Company website
- india_presence: Description of India presence
- remote_friendly: Yes/No

Return JSON array. ONLY return JSON, no explanation.

Results:
{snippets}"""
    
    raw = llm_query(prompt, max_tokens=800)
    cleaned = clean_json_text(raw)
    companies = safe_json_loads(cleaned, default=[])
    
    result = []
    for company in companies:
        if isinstance(company, dict) and company.get("company_name"):
            company["source"] = "Remote + India Presence"
            company["is_remote"] = True
            result.append(company)
    
    return result[:limit]


def filter_companies_by_size(
    companies: List[Dict],
    min_employees: int = 50,
    max_employees: Optional[int] = None
) -> List[Dict]:
    """
    Filter companies by employee count.
    
    Args:
        companies: List of companies
        min_employees: Minimum employee count
        max_employees: Maximum employee count
    
    Returns:
        Filtered companies
    """
    logger.info(f"Filtering companies by size ({min_employees}-{max_employees} employees)...")
    
    filtered = []
    for company in companies:
        emp_count = company.get("employee_count")
        if isinstance(emp_count, int):
            if emp_count >= min_employees:
                if max_employees is None or emp_count <= max_employees:
                    filtered.append(company)
    
    logger.info(f"Filtered to {len(filtered)} companies")
    return filtered


def prioritize_by_telangana(companies: List[Dict]) -> List[Dict]:
    """
    Prioritize companies in Telangana (Hyderabad).
    
    Args:
        companies: List of companies
    
    Returns:
        Sorted list with Telangana companies first
    """
    telangana = []
    others = []
    
    for company in companies:
        state = company.get("target_state", "")
        city = company.get("target_city", "")
        
        if state == "Telangana" or city == "Hyderabad":
            telangana.append(company)
        else:
            others.append(company)
    
    return telangana + others


def enrich_with_working_emails(
    company: Dict,
    domain: Optional[str] = None,
    min_quality: int = 70
) -> Dict:
    """
    Enrich company with verified working emails.
    
    Args:
        company: Company dictionary
        domain: Company domain
        min_quality: Minimum email quality (0-100)
    
    Returns:
        Company with verified emails
    """
    if not domain and "domain" in company:
        domain = company["domain"]
    
    if not domain:
        logger.warning(f"No domain for {company.get('company_name')}")
        return company
    
    # Get emails from company_info if available
    emails = company.get("public_emails", [])
    email_list = [e.get("email") if isinstance(e, dict) else e for e in emails]
    
    if email_list:
        logger.info(f"Verifying emails for {company.get('company_name')}...")
        working = filter_working_emails(email_list, domain, min_quality)
        company["verified_emails"] = working
        company["working_email_count"] = len(working)
    
    return company


def score_india_company(company: Dict, city_preference: str = "Hyderabad") -> int:
    """
    Calculate India-specific company score (0-100).
    
    Args:
        company: Company dictionary
        city_preference: Preferred city for scoring boost
    
    Returns:
        Score 0-100
    """
    score = 0
    
    # Location scoring
    state = company.get("target_state", "")
    city = company.get("target_city", "")
    
    if state in PRIORITY_STATES:
        score += 20
    
    if city == "Hyderabad":
        score += 10
    elif city == "Bangalore":
        score += 8
    elif city == "Pune":
        score += 7
    
    # Funding scoring
    funding = company.get("funding_stage", "")
    if funding:
        score += 15
    
    # Data source scoring
    sources = company.get("source", [])
    if isinstance(sources, str):
        sources = [sources]
    
    if "GitHub" in sources:
        score += 10
    if "Crunchbase" in sources:
        score += 12
    if "Stack Overflow" in sources:
        score += 8
    
    # Email quality scoring
    working_emails = company.get("working_email_count", 0)
    score += min(working_emails * 3, 15)
    
    # Remote friendly bonus
    if company.get("is_remote"):
        score += 5
    
    # Has hiring mention
    if company.get("hiring_mentions", 0) > 0:
        score += 15
    
    return min(score, 100)


def prepare_india_discovery_report(
    companies: List[Dict],
    city_focus: Optional[str] = None
) -> Dict:
    """
    Prepare summary report for India discovery.
    
    Args:
        companies: List of discovered companies
        city_focus: Optional city to focus on
    
    Returns:
        Report dictionary
    """
    logger.info("Preparing India discovery report...")
    
    report = {
        "total_companies": len(companies),
        "by_city": {},
        "by_state": {},
        "by_funding": {},
        "by_source": {},
        "working_email_count": 0,
        "remote_companies": 0,
        "top_companies": []
    }
    
    for company in companies:
        # By city
        city = company.get("target_city", "Unknown")
        report["by_city"][city] = report["by_city"].get(city, 0) + 1
        
        # By state
        state = company.get("target_state", "Unknown")
        report["by_state"][state] = report["by_state"].get(state, 0) + 1
        
        # By funding
        funding = company.get("funding_stage", "Unfunded")
        report["by_funding"][funding] = report["by_funding"].get(funding, 0) + 1
        
        # By source
        source = company.get("source", "Unknown")
        report["by_source"][source] = report["by_source"].get(source, 0) + 1
        
        # Working emails
        report["working_email_count"] += company.get("working_email_count", 0)
        
        # Remote
        if company.get("is_remote"):
            report["remote_companies"] += 1
    
    # Top 10 companies
    sorted_companies = sorted(
        companies,
        key=lambda x: score_india_company(x),
        reverse=True
    )
    
    report["top_companies"] = [
        {
            "name": c.get("company_name"),
            "city": c.get("target_city"),
            "score": score_india_company(c),
            "working_emails": c.get("working_email_count", 0)
        }
        for c in sorted_companies[:10]
    ]
    
    return report
