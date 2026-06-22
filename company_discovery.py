"""
Company discovery module - finding companies actively hiring.
"""

import time
import json
from typing import List, Dict
from utils import (
    serper_search, llm_query, clean_json_text, safe_json_loads,
    logger, deduplicate_companies
)
from config import TARGET_ROLES, SERPER_SEARCH_PER_QUERY


def discover_hiring_companies(roles: List[str], country: str, limit: int = 100) -> List[Dict]:
    """
    Discover companies actively hiring for target roles using Serper.
    
    Args:
        roles: List of job titles to search for
        country: Target country
        limit: Maximum companies to return
    
    Returns:
        List of company dictionaries with hiring info
    """
    logger.info(f"Discovering hiring companies for roles: {roles} in {country}...")
    
    all_snippets = []
    
    # Search for each role
    for role in roles:
        queries = [
            f'"{role}" jobs in {country}',
            f'"{role}" hiring in {country}',
            f'"{role}" careers in {country}'
        ]
        
        for query in queries:
            logger.debug(f"Searching: {query}")
            results = serper_search(query, num=SERPER_SEARCH_PER_QUERY)
            
            for result in results:
                all_snippets.append({
                    "title": result.get("title", ""),
                    "link": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                    "target_role": role
                })
            
            time.sleep(0.3)  # Be respectful to API
    
    if not all_snippets:
        logger.warning("No job postings found")
        return []
    
    logger.info(f"Found {len(all_snippets)} total job posting snippets")
    
    # Use LLM to extract company info
    snippets_text = "\n".join([
        f"- Role: {s['target_role']}\n  Title: {s['title']}\n  Link: {s['link']}\n  Snippet: {s['snippet']}"
        for s in all_snippets[:min(50, len(all_snippets))]  # Limit to avoid token overflow
    ])
    
    prompt = f"""Analyze these job search results from {country} and extract hiring companies.
For each job posting from a legitimate company (not recruitment agencies), extract:
- company_name: The actual company name (not Lever, Greenhouse, etc.)
- hiring_roles: Array of exact job titles they're hiring for
- job_url: URL to the job posting
- domain: Inferred company domain (e.g., "stripe.com"), or null if unknown

Exclude: recruitment agencies (Randstad, Michael Page, etc.), freelance platforms
Focus on direct employers.

Return a JSON array with these fields only. Return ONLY the JSON array, no markdown, no explanation.

Job postings:
{snippets_text}"""
    
    raw_response = llm_query(prompt, max_tokens=2000)
    cleaned = clean_json_text(raw_response)
    extracted = safe_json_loads(cleaned, default=[])
    
    if not isinstance(extracted, list):
        logger.error("LLM returned non-array response")
        return []
    
    # Process and deduplicate
    companies = []
    seen_names = set()
    
    for item in extracted:
        try:
            company_name = item.get("company_name", "").strip()
            domain = item.get("domain", "")
            job_url = item.get("job_url", "")
            hiring_roles = item.get("hiring_roles", [])
            
            # Skip if missing required fields
            if not company_name:
                continue
            
            # Skip if we've seen this company
            name_lower = company_name.lower()
            if name_lower in seen_names:
                continue
            
            # Skip known non-employers
            if any(skip in name_lower for skip in ["greenhouse", "lever", "applicant tracking"]):
                continue
            
            seen_names.add(name_lower)
            
            companies.append({
                "company_name": company_name,
                "hiring_roles": hiring_roles if isinstance(hiring_roles, list) else [hiring_roles],
                "job_url": job_url,
                "domain": domain if domain and domain != "null" else None
            })
            
            if len(companies) >= limit:
                break
        
        except Exception as e:
            logger.debug(f"Error parsing company item: {e}")
            continue
    
    logger.info(f"Extracted {len(companies)} unique hiring companies")
    return companies


def search_related_companies(company_name: str, industry: str, country: str, limit: int = 5) -> List[Dict]:
    """
    Find related companies in the same industry.
    
    Args:
        company_name: Reference company
        industry: Industry category
        country: Target country
        limit: Max companies to return
    
    Returns:
        List of related companies
    """
    logger.info(f"Finding companies similar to {company_name} in {industry}...")
    
    query = f"companies like {company_name} {industry} hiring {country} software engineers"
    results = serper_search(query, num=10)
    
    if not results:
        return []
    
    snippets_text = "\n".join([
        f"- Title: {r.get('title')}\n  Link: {r.get('link')}\n  Snippet: {r.get('snippet')}"
        for r in results
    ])
    
    prompt = f"""Find companies similar to '{company_name}' in the {industry} sector from these search results.
Extract:
- company_name: Company name
- domain: Website domain
- why_similar: Brief reason (same sector, size, etc.)

Return JSON array with these fields only. ONLY return the JSON array.

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
                "domain": item.get("domain"),
                "reason": item.get("why_similar", "")
            })
            if len(companies) >= limit:
                break
    
    logger.info(f"Found {len(companies)} related companies")
    return companies
