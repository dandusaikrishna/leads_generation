"""
LinkedIn job postings scraper - Legal extraction of public job data.
Uses Serper API to search public LinkedIn job postings, companies, and recruiter information.
"""

import time
import json
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from utils import serper_search, llm_query, clean_json_text, safe_json_loads, logger
from config import INDIA_CITIES


def search_linkedin_jobs_by_role(
    role: str,
    cities: List[str] = None,
    days_posted: int = 30
) -> List[Dict]:
    """
    Search public LinkedIn job postings by role and location.
    
    Args:
        role: Job title to search for
        cities: Cities to filter by (default: Hyderabad, Bangalore, Pune)
        days_posted: Only jobs posted in last N days
    
    Returns:
        List of job postings with details
    """
    if cities is None:
        cities = ["Hyderabad", "Bangalore", "Pune"]
    
    logger.info(f"Searching LinkedIn jobs for {role} in {', '.join(cities)}...")
    
    jobs = []
    
    for city in cities:
        # Search LinkedIn jobs for this role and city
        query = f'site:linkedin.com/jobs "{role}" "{city}" India'
        results = serper_search(query, num=15)
        
        if not results:
            logger.warning(f"No jobs found for {role} in {city}")
            continue
        
        # Extract job snippets
        snippets_text = "\n".join([
            f"Title: {r.get('title')}\nURL: {r.get('link')}\nSnippet: {r.get('snippet')}"
            for r in results[:10]
        ])
        
        prompt = f"""Extract detailed job posting information from these LinkedIn job listings for {role} in {city}.

For each job posting, extract:
- job_title: Exact job title
- company_name: Company name
- company_url: LinkedIn company URL if available
- location: Location (city/state)
- job_url: LinkedIn job posting URL
- posted_date: When posted (if available)
- job_type: Full-time, Contract, etc.
- salary_range: If mentioned
- key_requirements: Top 3 requirements
- hiring_contact: If recruiter/hiring manager name is visible
- application_email: Email address if mentioned

Return JSON array with these fields. Extract ONLY from the provided data.
Return ONLY the JSON array, no explanation.

Job Postings:
{snippets_text}"""
        
        raw = llm_query(prompt, max_tokens=1500)
        cleaned = clean_json_text(raw)
        extracted = safe_json_loads(cleaned, default=[])
        
        if isinstance(extracted, list):
            for job in extracted:
                if isinstance(job, dict) and job.get("company_name"):
                    job["city"] = city
                    job["search_role"] = role
                    job["source"] = "LinkedIn"
                    jobs.append(job)
        
        time.sleep(0.5)  # Rate limiting
    
    logger.info(f"Found {len(jobs)} job postings for {role}")
    return jobs


def search_hiring_companies_linkedin(
    keyword: str = "hiring",
    cities: List[str] = None,
    days: int = 30
) -> List[Dict]:
    """
    Find companies actively hiring using LinkedIn company posts.
    
    Args:
        keyword: Search keyword (default: "hiring")
        cities: Target cities
        days: Recent posts from last N days
    
    Returns:
        List of companies with hiring activity
    """
    if cities is None:
        cities = ["Hyderabad", "Bangalore", "Pune"]
    
    logger.info(f"Searching for companies actively hiring in {', '.join(cities)}...")
    
    companies = []
    
    for city in cities:
        # Search LinkedIn company posts about hiring
        query = f'site:linkedin.com/company/ "{keyword}" "{city}" (jobs OR recruitment OR engineers OR developers)'
        results = serper_search(query, num=12)
        
        if not results:
            logger.warning(f"No hiring posts found for {city}")
            continue
        
        snippets = "\n".join([
            f"Company: {r.get('title')}\nURL: {r.get('link')}\nPost: {r.get('snippet')}"
            for r in results[:8]
        ])
        
        prompt = f"""Find companies actively hiring from these LinkedIn company posts in {city}.

Extract:
- company_name: Company name
- linkedin_url: LinkedIn company URL
- website_domain: Company website domain if mentioned
- hiring_status: "Actively Hiring", "Recruiting", etc.
- open_positions: Types of roles being hired (Engineers, etc.)
- last_posting_date: When last hiring post was made
- hiring_regions: Regions they're hiring in
- posting_summary: Brief summary of hiring activity

Return JSON array. Extract ONLY from provided data.
Return ONLY the JSON array, no explanation.

LinkedIn Posts:
{snippets}"""
        
        raw = llm_query(prompt, max_tokens=1200)
        cleaned = clean_json_text(raw)
        extracted = safe_json_loads(cleaned, default=[])
        
        if isinstance(extracted, list):
            for company in extracted:
                if isinstance(company, dict) and company.get("company_name"):
                    company["city"] = city
                    company["source"] = "LinkedIn Company Posts"
                    companies.append(company)
        
        time.sleep(0.5)
    
    logger.info(f"Found {len(companies)} actively hiring companies")
    return companies


def extract_job_posting_details(job_url: str) -> Dict:
    """
    Extract detailed information from a LinkedIn job posting.
    
    Args:
        job_url: LinkedIn job posting URL
    
    Returns:
        Detailed job information
    """
    logger.info(f"Extracting details from job posting: {job_url}")
    
    query = f'site:linkedin.com/jobs {job_url.split("/")[-2]}'
    results = serper_search(query, num=5)
    
    if not results:
        return {}
    
    snippets = "\n".join([f"{r.get('title')}: {r.get('snippet')}" for r in results[:3]])
    
    prompt = f"""Extract comprehensive job posting details:

- job_title: Job title
- company_name: Company
- experience_level: Entry-level, Mid-level, Senior, etc.
- employment_type: Full-time, Contract, etc.
- required_skills: Top 10 skills required
- responsibilities: Key responsibilities (top 5)
- qualifications: Required qualifications
- salary_currency: Currency if mentioned
- salary_min: Minimum salary if available
- salary_max: Maximum salary if available
- benefits: Benefits mentioned
- application_method: How to apply (email, direct apply, etc.)
- hiring_contact_name: Recruiter/hiring manager name if visible
- hiring_company_email: Company email for applications
- team_size: Team size if mentioned
- report_to: Reports to (role title)

Extract from job posting. Return ONLY JSON.

Details:
{snippets}"""
    
    raw = llm_query(prompt, max_tokens=1000)
    cleaned = clean_json_text(raw)
    details = safe_json_loads(cleaned, default={})
    
    return details


def find_job_postings_by_company(
    company_name: str,
    city: str = None
) -> List[Dict]:
    """
    Find all public job postings by a specific company on LinkedIn.
    
    Args:
        company_name: Company name
        city: Optional city filter
    
    Returns:
        List of job postings by company
    """
    logger.info(f"Finding job postings by {company_name}...")
    
    city_filter = f'"{city}"' if city else ""
    query = f'site:linkedin.com/jobs "{company_name}" {city_filter}'
    results = serper_search(query, num=15)
    
    if not results:
        logger.warning(f"No jobs found for {company_name}")
        return []
    
    snippets_text = "\n".join([
        f"Title: {r.get('title')}\nSnippet: {r.get('snippet')}"
        for r in results[:10]
    ])
    
    prompt = f"""Extract job postings from {company_name}.

For each job:
- job_title: Job title
- job_url: LinkedIn job URL
- posted_date: When posted (extract if available)
- location: Job location
- role_level: Senior, Lead, Manager, etc.
- department: Department/team if mentioned

Return JSON array. Return ONLY the JSON array.

Postings:
{snippets_text}"""
    
    raw = llm_query(prompt, max_tokens=800)
    cleaned = clean_json_text(raw)
    jobs = safe_json_loads(cleaned, default=[])
    
    return jobs if isinstance(jobs, list) else []


def analyze_job_market_trends(
    roles: List[str],
    cities: List[str] = None,
    days: int = 30
) -> Dict:
    """
    Analyze job market trends across multiple roles and cities.
    
    Args:
        roles: Roles to analyze
        cities: Target cities
        days: Analyze recent posts from N days
    
    Returns:
        Market trends analysis
    """
    if cities is None:
        cities = ["Hyderabad", "Bangalore", "Pune"]
    
    logger.info(f"Analyzing job market trends for {', '.join(roles)}...")
    
    trends = {
        "analysis_date": datetime.now().isoformat(),
        "roles_analyzed": roles,
        "cities": cities,
        "by_role": {},
        "top_companies": [],
        "hiring_regions": {},
        "salary_insights": {}
    }
    
    all_jobs = []
    
    # Collect jobs for all roles
    for role in roles:
        jobs = search_linkedin_jobs_by_role(role, cities, days)
        all_jobs.extend(jobs)
        
        trends["by_role"][role] = {
            "total_postings": len(jobs),
            "companies": len(set(j.get("company_name") for j in jobs)),
            "cities_hiring": list(set(j.get("city") for j in jobs))
        }
    
    # Analyze top hiring companies
    company_counts = {}
    for job in all_jobs:
        company = job.get("company_name")
        if company:
            company_counts[company] = company_counts.get(company, 0) + 1
    
    top_companies = sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    trends["top_companies"] = [{"company": name, "open_positions": count} for name, count in top_companies]
    
    # Analyze hiring by region
    for job in all_jobs:
        city = job.get("city", "Unknown")
        trends["hiring_regions"][city] = trends["hiring_regions"].get(city, 0) + 1
    
    # Analyze salary data
    salaries = [j for j in all_jobs if j.get("salary_range")]
    if salaries:
        trends["salary_insights"]["postings_with_salary"] = len(salaries)
        trends["salary_insights"]["sample_ranges"] = [s.get("salary_range") for s in salaries[:5]]
    
    logger.info(f"Analyzed {len(all_jobs)} job postings")
    return trends


def get_recent_hiring_activity(
    company_name: str,
    days: int = 30
) -> Dict:
    """
    Get recent hiring activity for a specific company.
    
    Args:
        company_name: Company name
        days: Look back N days
    
    Returns:
        Recent hiring activity summary
    """
    logger.info(f"Getting recent hiring activity for {company_name}...")
    
    # Search company LinkedIn page
    query = f'site:linkedin.com/company/{company_name.lower().replace(" ", "-")} (jobs OR hiring OR recruitment OR "we are hiring")'
    results = serper_search(query, num=10)
    
    if not results:
        logger.warning(f"No recent activity found for {company_name}")
        return {"company_name": company_name, "activity": []}
    
    snippets = "\n".join([f"{r.get('title')}: {r.get('snippet')}" for r in results[:8]])
    
    prompt = f"""Extract recent hiring activity from {company_name} LinkedIn page:

- hiring_announcement: Recent hiring announcements
- roles_being_hired: Job titles and departments
- expansion_news: Company expansion/growth announcements
- team_growth: Team expansion details
- funding_news: Any recent funding (related to hiring)
- office_locations: Where they're hiring
- hiring_urgency: Urgency level (High, Medium, Low)
- recent_date: Most recent posting date

Extract all visible activity. Return ONLY JSON.

Activity:
{snippets}"""
    
    raw = llm_query(prompt, max_tokens=800)
    cleaned = clean_json_text(raw)
    activity = safe_json_loads(cleaned, default={})
    
    activity["company_name"] = company_name
    activity["scraped_date"] = datetime.now().isoformat()
    
    return activity


def export_jobs_to_json(jobs: List[Dict], output_file: str) -> bool:
    """
    Export job postings to JSON file.
    
    Args:
        jobs: List of job dictionaries
        output_file: Output file path
    
    Returns:
        True if successful
    """
    try:
        logger.info(f"Exporting {len(jobs)} jobs to {output_file}...")
        
        data = {
            "export_date": datetime.now().isoformat(),
            "total_jobs": len(jobs),
            "jobs": jobs
        }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Exported to {output_file}")
        return True
    except Exception as e:
        logger.error(f"❌ Export failed: {str(e)}")
        return False
