"""
LinkedIn recruiter and hiring team discovery.
Finds recruiters, hiring managers, and HR professionals through public LinkedIn data.
"""

import time
import json
from typing import List, Dict, Optional
from datetime import datetime
from utils import serper_search, llm_query, clean_json_text, safe_json_loads, logger


def find_recruiters_by_role(
    role: str,
    cities: List[str] = None,
    countries: List[str] = None
) -> List[Dict]:
    """
    Find recruiters specializing in specific roles.
    
    Args:
        role: Job role to search for (e.g., "Backend Engineer")
        cities: Cities to focus on
        countries: Countries to search
    
    Returns:
        List of recruiter profiles
    """
    if cities is None:
        cities = ["Hyderabad", "Bangalore"]
    
    if countries is None:
        countries = ["India"]
    
    logger.info(f"Finding recruiters for {role} in {', '.join(cities)}...")
    
    recruiters = []
    
    # Search for recruiters with this specialization
    query = f'site:linkedin.com/in recruiter "{role}" ({" OR ".join(cities)})'
    results = serper_search(query, num=15)
    
    if not results:
        logger.warning(f"No recruiters found for {role}")
        return []
    
    # Extract recruiter info
    snippets = "\n".join([
        f"Profile: {r.get('title')}\nURL: {r.get('link')}\nInfo: {r.get('snippet')}"
        for r in results[:12]
    ])
    
    prompt = f"""Extract recruiter information from these LinkedIn profiles specializing in {role}.

For each recruiter, extract:
- recruiter_name: Full name
- linkedin_url: LinkedIn profile URL
- company_name: Current company/recruiting firm
- recruiter_type: Corporate Recruiter, Staffing/Agency, Independent, etc.
- specialization: Roles they recruit for
- location: Based in which city
- email: Email if visible in profile
- phone: Phone if visible
- expertise_areas: Areas of expertise
- active_status: Active (recent activity)

Return JSON array with these fields. Only extract publicly visible information.
Return ONLY the JSON array, no explanation.

Recruiters:
{snippets}"""
    
    raw = llm_query(prompt, max_tokens=1500)
    cleaned = clean_json_text(raw)
    extracted = safe_json_loads(cleaned, default=[])
    
    if isinstance(extracted, list):
        recruiters = [r for r in extracted if isinstance(r, dict) and r.get("recruiter_name")]
    
    logger.info(f"Found {len(recruiters)} recruiters for {role}")
    return recruiters


def find_hiring_managers_by_company(
    company_name: str,
    roles: List[str] = None
) -> List[Dict]:
    """
    Find hiring managers and team leads at a company.
    
    Args:
        company_name: Company name
        roles: Specific roles to find managers for
    
    Returns:
        List of hiring managers
    """
    logger.info(f"Finding hiring managers at {company_name}...")
    
    managers = []
    
    # Search for hiring managers at this company
    role_filter = f'({" OR ".join(roles)})' if roles else '(Engineering OR Product OR Backend OR Frontend)'
    query = f'site:linkedin.com/in "{company_name}" ({role_filter} Manager OR Lead OR Director)'
    results = serper_search(query, num=12)
    
    if not results:
        logger.warning(f"No hiring managers found at {company_name}")
        return []
    
    snippets = "\n".join([
        f"Profile: {r.get('title')}\nURL: {r.get('link')}\nInfo: {r.get('snippet')}"
        for r in results[:10]
    ])
    
    prompt = f"""Extract hiring manager information from {company_name} LinkedIn profiles.

For each manager, extract:
- manager_name: Full name
- linkedin_url: LinkedIn profile URL
- job_title: Current job title
- department: Department/team
- reporting_line: Reports to (if visible)
- team_size: Manages how many people (if mentioned)
- email: Email if visible
- location: Location/office
- hiring_activity: Any hiring-related activity visible
- recent_posts: Any recent company posts about hiring

Return JSON array. Extract ONLY public information.
Return ONLY the JSON array, no explanation.

Profiles:
{snippets}"""
    
    raw = llm_query(prompt, max_tokens=1200)
    cleaned = clean_json_text(raw)
    extracted = safe_json_loads(cleaned, default=[])
    
    if isinstance(extracted, list):
        managers = [m for m in extracted if isinstance(m, dict) and m.get("manager_name")]
    
    logger.info(f"Found {len(managers)} hiring managers at {company_name}")
    return managers


def find_hr_professionals(
    cities: List[str] = None,
    company_size: str = None
) -> List[Dict]:
    """
    Find HR and talent acquisition professionals.
    
    Args:
        cities: Target cities
        company_size: Company size filter (Startup, Mid-size, Enterprise, etc.)
    
    Returns:
        List of HR professionals
    """
    if cities is None:
        cities = ["Hyderabad", "Bangalore", "Pune"]
    
    logger.info(f"Finding HR professionals in {', '.join(cities)}...")
    
    hr_professionals = []
    
    # Search for HR professionals
    size_filter = f'"{company_size}"' if company_size else ""
    query = f'site:linkedin.com/in "HR" OR "Talent Acquisition" OR "Recruiter" ({" OR ".join(cities)}) {size_filter}'
    results = serper_search(query, num=15)
    
    if not results:
        logger.warning(f"No HR professionals found")
        return []
    
    snippets = "\n".join([
        f"Profile: {r.get('title')}\nURL: {r.get('link')}\nInfo: {r.get('snippet')}"
        for r in results[:12]
    ])
    
    prompt = f"""Find HR and talent acquisition professionals from these LinkedIn profiles in {', '.join(cities)}.

Extract:
- professional_name: Full name
- linkedin_url: LinkedIn profile URL
- current_title: Job title
- current_company: Current employer
- company_type: Company type (Startup, MNC, Agency, etc.)
- specialization: What they specialize in
- location: City/region
- email: Email if visible
- phone: Phone if visible
- hiring_focus: Roles they typically hire for
- experience_years: Years of experience (if visible)

Return JSON array. Extract ONLY public information.
Return ONLY the JSON array, no explanation.

HR Professionals:
{snippets}"""
    
    raw = llm_query(prompt, max_tokens=1500)
    cleaned = clean_json_text(raw)
    extracted = safe_json_loads(cleaned, default=[])
    
    if isinstance(extracted, list):
        hr_professionals = [h for h in extracted if isinstance(h, dict) and h.get("professional_name")]
    
    logger.info(f"Found {len(hr_professionals)} HR professionals")
    return hr_professionals


def extract_recruiter_contact_info(recruiter_url: str) -> Dict:
    """
    Extract detailed contact information from a recruiter's profile.
    
    Args:
        recruiter_url: LinkedIn profile URL
    
    Returns:
        Contact information
    """
    logger.info(f"Extracting contact info from: {recruiter_url}")
    
    # Search for the profile details
    query = f'site:linkedin.com {recruiter_url.split("/in/")[1] if "/in/" in recruiter_url else ""}'
    results = serper_search(query, num=5)
    
    if not results:
        return {}
    
    snippets = "\n".join([f"{r.get('title')}: {r.get('snippet')}" for r in results[:3]])
    
    prompt = f"""Extract all contact information from this LinkedIn profile:

- email_address: Email (if publicly visible)
- phone_number: Phone (if publicly visible)
- website: Personal website or company website
- location: Address or city
- company_linkedin: Company LinkedIn page
- messaging_preference: How they prefer to be contacted
- about_section: Professional summary
- current_focus: What they're currently focusing on

Extract ONLY publicly visible information from profile.
Return ONLY JSON, no explanation.

Profile:
{snippets}"""
    
    raw = llm_query(prompt, max_tokens=600)
    cleaned = clean_json_text(raw)
    contact = safe_json_loads(cleaned, default={})
    
    contact["profile_url"] = recruiter_url
    contact["extraction_date"] = datetime.now().isoformat()
    
    return contact


def find_recruiting_agencies_in_region(
    region: str,
    specialization: str = None
) -> List[Dict]:
    """
    Find recruiting agencies operating in a region.
    
    Args:
        region: Region/city name
        specialization: Tech, Finance, etc.
    
    Returns:
        List of recruiting agencies
    """
    logger.info(f"Finding recruiting agencies in {region}...")
    
    spec_filter = f'"{specialization}"' if specialization else ""
    query = f'site:linkedin.com/company/ recruiting OR staffing OR "talent solutions" "{region}" {spec_filter}'
    results = serper_search(query, num=12)
    
    if not results:
        logger.warning(f"No agencies found in {region}")
        return []
    
    snippets = "\n".join([
        f"Company: {r.get('title')}\nURL: {r.get('link')}\nInfo: {r.get('snippet')}"
        for r in results[:10]
    ])
    
    prompt = f"""Extract recruiting agency information from these LinkedIn company pages in {region}.

For each agency:
- agency_name: Agency name
- linkedin_url: LinkedIn company URL
- website: Company website (if mentioned)
- specialization: What they specialize in
- locations: Offices/locations
- services: Recruitment services offered
- contact_email: Contact email if visible
- phone: Phone number if visible

Return JSON array. Extract ONLY public information.
Return ONLY the JSON array, no explanation.

Agencies:
{snippets}"""
    
    raw = llm_query(prompt, max_tokens=1000)
    cleaned = clean_json_text(raw)
    agencies = safe_json_loads(cleaned, default=[])
    
    return agencies if isinstance(agencies, list) else []


def build_recruiter_database(
    roles: List[str],
    cities: List[str] = None
) -> Dict:
    """
    Build comprehensive recruiter database for target roles and cities.
    
    Args:
        roles: Roles to recruit for
        cities: Target cities
    
    Returns:
        Complete recruiter database
    """
    if cities is None:
        cities = ["Hyderabad", "Bangalore", "Pune"]
    
    logger.info(f"Building recruiter database for {', '.join(roles)}...")
    
    database = {
        "build_date": datetime.now().isoformat(),
        "roles": roles,
        "cities": cities,
        "recruiters": [],
        "hiring_managers": [],
        "hr_professionals": [],
        "agencies": [],
        "total_contacts": 0
    }
    
    # Find recruiters for each role
    for role in roles:
        recruiters = find_recruiters_by_role(role, cities)
        database["recruiters"].extend(recruiters)
        time.sleep(0.5)
    
    # Find HR professionals
    hr_pros = find_hr_professionals(cities)
    database["hr_professionals"].extend(hr_pros)
    
    # Find recruiting agencies
    for city in cities:
        agencies = find_recruiting_agencies_in_region(city, "Technology")
        database["agencies"].extend(agencies)
        time.sleep(0.5)
    
    # Calculate totals
    database["total_contacts"] = (
        len(database["recruiters"]) + 
        len(database["hr_professionals"]) + 
        len(database["agencies"])
    )
    
    logger.info(f"Built database with {database['total_contacts']} total contacts")
    
    return database


def export_recruiters_to_json(
    recruiters: List[Dict],
    output_file: str
) -> bool:
    """
    Export recruiter list to JSON file.
    
    Args:
        recruiters: List of recruiter dictionaries
        output_file: Output file path
    
    Returns:
        True if successful
    """
    try:
        logger.info(f"Exporting {len(recruiters)} recruiters to {output_file}...")
        
        data = {
            "export_date": datetime.now().isoformat(),
            "total_recruiters": len(recruiters),
            "recruiters": recruiters
        }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Exported to {output_file}")
        return True
    except Exception as e:
        logger.error(f"❌ Export failed: {str(e)}")
        return False
