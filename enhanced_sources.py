"""
Enhanced data sources for company and contact discovery.
Includes GitHub, Crunchbase, Stack Overflow, and press releases.
"""

import time
import json
from typing import List, Dict
from utils import (
    serper_search, llm_query, clean_json_text, safe_json_loads,
    logger, extract_emails_from_text, validate_email
)


# ─────────────────────────────────────────────────────────────────────────────
# GitHub Enterprise Discovery
# ─────────────────────────────────────────────────────────────────────────────

def find_companies_on_github(city: str, country: str = "India") -> List[Dict]:
    """
    Find companies with engineering teams on GitHub.
    
    Args:
        city: City name (e.g., "Hyderabad", "Bangalore")
        country: Country
    
    Returns:
        List of companies with GitHub org info
    """
    logger.info(f"Finding companies on GitHub in {city}, {country}...")
    
    query = f'site:github.com/orgs location:"{city}" OR location:"{country}"'
    results = serper_search(query, num=15)
    
    if not results:
        logger.warning(f"No GitHub orgs found for {city}")
        return []
    
    snippets_text = "\n".join([
        f"- {r.get('title')}: {r.get('snippet')}"
        for r in results[:10]
    ])
    
    prompt = f"""Extract company information from these GitHub organization pages in {city}, {country}.
For each legitimate company, extract:
- company_name: Company or organization name
- github_url: GitHub organization URL
- domain: Company website domain if mentioned (or null)
- description: What the company does

Return JSON array with these fields only. Return ONLY the JSON array, no explanation.

Results:
{snippets_text}"""
    
    raw_response = llm_query(prompt, max_tokens=1000)
    cleaned = clean_json_text(raw_response)
    extracted = safe_json_loads(cleaned, default=[])
    
    if not isinstance(extracted, list):
        return []
    
    companies = []
    for item in extracted:
        if isinstance(item, dict) and item.get("company_name"):
            companies.append({
                "company_name": item.get("company_name"),
                "github_url": item.get("github_url"),
                "domain": item.get("domain"),
                "description": item.get("description"),
                "source": "GitHub"
            })
    
    logger.info(f"Found {len(companies)} companies on GitHub")
    return companies


def extract_github_team_members(github_url: str) -> List[Dict]:
    """Extract engineering team members from GitHub org profile"""
    logger.info(f"Extracting team from: {github_url}")
    
    query = f'site:{github_url} "members" OR "team"'
    results = serper_search(query, num=8)
    
    if not results:
        return []
    
    snippets = "\n".join([f"- {r.get('title')}: {r.get('snippet')}" for r in results[:5]])
    
    prompt = f"""Extract engineering team members from this GitHub organization: {github_url}
Extract visible team member information:
- name: Name if visible
- role: Role if mentioned (Engineer, Lead, etc.)
- github_username: GitHub username

Return JSON array. Return ONLY JSON, no explanation.

Results:
{snippets}"""
    
    raw = llm_query(prompt, max_tokens=500)
    cleaned = clean_json_text(raw)
    extracted = safe_json_loads(cleaned, default=[])
    
    return extracted if isinstance(extracted, list) else []


# ─────────────────────────────────────────────────────────────────────────────
# Crunchbase Company Intelligence
# ─────────────────────────────────────────────────────────────────────────────

def find_companies_on_crunchbase(city: str, country: str = "India", funding: str = None) -> List[Dict]:
    """
    Find funded companies on Crunchbase.
    
    Args:
        city: City name
        country: Country
        funding: Funding stage (e.g., "Seed", "Series A", "Series B")
    
    Returns:
        List of companies with funding info
    """
    logger.info(f"Finding companies on Crunchbase in {city}, {country}...")
    
    query = f'site:crunchbase.com "{city}" software engineering {country}'
    if funding:
        query += f' "{funding}"'
    
    results = serper_search(query, num=15)
    
    if not results:
        logger.warning(f"No companies found on Crunchbase")
        return []
    
    snippets_text = "\n".join([
        f"- {r.get('title')}: {r.get('snippet')}"
        for r in results[:10]
    ])
    
    prompt = f"""Extract company information from Crunchbase for {city}, {country}.
Extract:
- company_name: Company name
- crunchbase_url: Crunchbase profile URL
- funding_stage: Funding stage (Seed, Series A, etc.)
- domain: Website domain
- employee_count: Number of employees if mentioned
- industry: Industry focus

Return JSON array with these fields. Return ONLY JSON, no explanation.

Results:
{snippets_text}"""
    
    raw_response = llm_query(prompt, max_tokens=1000)
    cleaned = clean_json_text(raw_response)
    extracted = safe_json_loads(cleaned, default=[])
    
    if not isinstance(extracted, list):
        return []
    
    companies = []
    for item in extracted:
        if isinstance(item, dict) and item.get("company_name"):
            companies.append({
                "company_name": item.get("company_name"),
                "crunchbase_url": item.get("crunchbase_url"),
                "funding_stage": item.get("funding_stage"),
                "domain": item.get("domain"),
                "employee_count": item.get("employee_count"),
                "industry": item.get("industry"),
                "source": "Crunchbase"
            })
    
    logger.info(f"Found {len(companies)} companies on Crunchbase")
    return companies


# ─────────────────────────────────────────────────────────────────────────────
# Stack Overflow Developer Community
# ─────────────────────────────────────────────────────────────────────────────

def find_active_companies_stackoverflow(city: str, country: str = "India") -> List[Dict]:
    """
    Find companies with active developer presence on Stack Overflow.
    
    Args:
        city: City name
        country: Country
    
    Returns:
        List of companies with developer activity
    """
    logger.info(f"Finding active companies on Stack Overflow in {city}...")
    
    query = f'site:stackoverflow.com company "{city}" OR "Bangalore" OR "Hyderabad" OR "Pune"'
    results = serper_search(query, num=12)
    
    if not results:
        logger.warning(f"No companies found on Stack Overflow")
        return []
    
    snippets_text = "\n".join([
        f"- {r.get('title')}: {r.get('snippet')}"
        for r in results[:8]
    ])
    
    prompt = f"""Find companies mentioned in Stack Overflow discussions from {city}, {country}.
Extract:
- company_name: Company name
- technology_stack: Technologies they use (Python, Java, etc.)
- activity_level: High/Medium/Low activity
- location: Location mentioned
- description: What they're working on

Return JSON array. Return ONLY JSON, no explanation.

Results:
{snippets_text}"""
    
    raw_response = llm_query(prompt, max_tokens=800)
    cleaned = clean_json_text(raw_response)
    extracted = safe_json_loads(cleaned, default=[])
    
    if not isinstance(extracted, list):
        return []
    
    companies = []
    for item in extracted:
        if isinstance(item, dict) and item.get("company_name"):
            companies.append({
                "company_name": item.get("company_name"),
                "technology_stack": item.get("technology_stack"),
                "activity_level": item.get("activity_level"),
                "location": item.get("location"),
                "description": item.get("description"),
                "source": "Stack Overflow"
            })
    
    logger.info(f"Found {len(companies)} companies on Stack Overflow")
    return companies


# ─────────────────────────────────────────────────────────────────────────────
# Company Blog & Press Releases
# ─────────────────────────────────────────────────────────────────────────────

def find_recent_company_activity(company_name: str, domain: str = None) -> Dict:
    """
    Find recent company activity from blogs and press releases.
    
    Args:
        company_name: Company name
        domain: Company domain (optional)
    
    Returns:
        Dictionary with recent activity info
    """
    logger.info(f"Finding recent activity for: {company_name}")
    
    search_terms = f'"{company_name}" (blog OR press OR news OR announcement) site:{domain}' if domain else f'"{company_name}" (blog OR press OR news) 2024 OR 2025'
    
    results = serper_search(search_terms, num=10)
    
    if not results:
        logger.warning(f"No recent activity found for {company_name}")
        return {
            "company_name": company_name,
            "recent_posts": [],
            "hiring_mentions": 0
        }
    
    snippets_text = "\n".join([
        f"- Title: {r.get('title')}\n  URL: {r.get('link')}\n  Snippet: {r.get('snippet')}"
        for r in results[:8]
    ])
    
    prompt = f"""Analyze recent activity from {company_name}. Extract:
- recent_posts: Array of recent blog posts/press releases (title, date)
- hiring_mentions: How many posts mention hiring/jobs
- product_updates: Recent product/feature announcements
- team_updates: Team expansions or leadership changes
- funding_news: Any funding announcements

Return JSON with these fields. Return ONLY JSON, no explanation.

Activity:
{snippets_text}"""
    
    raw_response = llm_query(prompt, max_tokens=800)
    cleaned = clean_json_text(raw_response)
    activity = safe_json_loads(cleaned, default={})
    
    return {
        "company_name": company_name,
        "recent_posts": activity.get("recent_posts", []),
        "hiring_mentions": activity.get("hiring_mentions", 0),
        "product_updates": activity.get("product_updates", []),
        "team_updates": activity.get("team_updates", []),
        "funding_news": activity.get("funding_news", [])
    }


# ─────────────────────────────────────────────────────────────────────────────
# Aggregated Company Discovery
# ─────────────────────────────────────────────────────────────────────────────

def discover_companies_multi_source(city: str, country: str = "India") -> List[Dict]:
    """
    Discover companies using multiple data sources.
    
    Args:
        city: Target city
        country: Target country
    
    Returns:
        Aggregated list of companies from all sources
    """
    logger.info(f"Starting multi-source company discovery for {city}, {country}...")
    
    all_companies = []
    
    # GitHub
    github_companies = find_companies_on_github(city, country)
    all_companies.extend(github_companies)
    
    # Crunchbase
    time.sleep(0.5)
    crunchbase_companies = find_companies_on_crunchbase(city, country)
    all_companies.extend(crunchbase_companies)
    
    # Stack Overflow
    time.sleep(0.5)
    stackoverflow_companies = find_active_companies_stackoverflow(city, country)
    all_companies.extend(stackoverflow_companies)
    
    # Deduplicate by company name
    seen = set()
    unique_companies = []
    for company in all_companies:
        name_key = company.get("company_name", "").lower().strip()
        if name_key not in seen:
            seen.add(name_key)
            unique_companies.append(company)
    
    logger.info(f"Found {len(unique_companies)} unique companies across all sources")
    return unique_companies
