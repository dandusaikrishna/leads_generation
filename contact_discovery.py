"""
Senior contact and decision maker discovery module.
"""

from typing import List
from utils import (
    serper_search, llm_query, clean_json_text, safe_json_loads,
    logger
)
from config import DECISION_MAKER_TITLES, ROLE_SCORES


def find_senior_contacts(company_name: str, domain: str, country: str) -> List[dict]:
    """
    Find senior contacts and decision makers at a company.
    
    Searches for: Founder, CEO, CTO, VP Engineering, Engineering Directors,
    Talent Acquisition managers, and HR managers.
    
    Args:
        company_name: Company name
        domain: Company domain
        country: Country
    
    Returns:
        List of contacts with name, role, LinkedIn URL, and score
    """
    logger.info(f"Finding senior contacts at: {company_name}")
    
    # Build LinkedIn search query
    titles = " OR ".join([f'"{title}"' for title in DECISION_MAKER_TITLES[:10]])
    query = f'site:linkedin.com/in "{company_name}" ({titles})'
    
    results = serper_search(query, num=15)
    
    if not results:
        logger.warning(f"No LinkedIn results found for {company_name}")
        return []
    
    snippets_text = "\n".join([
        f"- Title: {r.get('title')}\n  Link: {r.get('link')}\n  Snippet: {r.get('snippet')}"
        for r in results[:10]
    ])
    
    prompt = f"""Extract decision makers and senior contacts at '{company_name}' from these LinkedIn profiles.
Look for: Founders, CEOs, CTOs, VP of Engineering, Engineering Directors, Head of Engineering, 
Engineering Managers, Talent Acquisition leads, Recruiters, HR Managers.

For each person, extract:
- name: Full name
- role: Current title/role
- linkedin_url: Full LinkedIn profile URL (must start with https://www.linkedin.com/in/)
- source: Where you found them

Return a JSON array with these fields only. Return ONLY the JSON array, no explanation.
If no valid contacts found, return [].

Profiles:
{snippets_text}"""
    
    raw_response = llm_query(prompt, max_tokens=1500)
    cleaned = clean_json_text(raw_response)
    extracted = safe_json_loads(cleaned, default=[])
    
    if not isinstance(extracted, list):
        logger.error("LLM returned non-array for contacts")
        return []
    
    # Process and score contacts
    contacts = []
    seen_names = set()
    
    for item in extracted:
        try:
            name = item.get("name", "").strip()
            role = item.get("role", "").strip()
            linkedin_url = item.get("linkedin_url", "").strip()
            
            if not name or not role or not linkedin_url:
                continue
            
            # Skip duplicates
            name_lower = name.lower()
            if name_lower in seen_names:
                continue
            seen_names.add(name_lower)
            
            # Validate LinkedIn URL
            if not linkedin_url.startswith("https://www.linkedin.com/in/"):
                continue
            
            # Calculate role score
            role_score = 0
            for title, score in ROLE_SCORES.items():
                if title.lower() in role.lower():
                    role_score = max(role_score, score)
            
            if role_score == 0:
                role_score = 50  # Default for unrecognized roles
            
            contacts.append({
                "name": name,
                "role": role,
                "linkedin_url": linkedin_url,
                "role_score": role_score,
                "source_url": item.get("source", "")
            })
        
        except Exception as e:
            logger.debug(f"Error processing contact: {e}")
            continue
    
    # Sort by role score
    contacts.sort(key=lambda x: x["role_score"], reverse=True)
    
    logger.info(f"Found {len(contacts)} senior contacts")
    return contacts


def find_recruiting_team(company_name: str, domain: str) -> List[dict]:
    """
    Find recruiting/HR team members specifically.
    
    Args:
        company_name: Company name
        domain: Company domain
    
    Returns:
        List of recruiting team members
    """
    logger.info(f"Finding recruiting team at: {company_name}")
    
    recruiting_titles = [
        "Recruiter",
        "Senior Recruiter",
        "Talent Acquisition",
        "HR Manager",
        "HR Director",
        "People Operations",
        "People Manager",
        "Recruiting Manager"
    ]
    
    titles_search = " OR ".join([f'"{title}"' for title in recruiting_titles])
    query = f'site:linkedin.com/in "{company_name}" ({titles_search})'
    
    results = serper_search(query, num=10)
    
    if not results:
        logger.warning(f"No recruiting team found for {company_name}")
        return []
    
    snippets_text = "\n".join([
        f"- {r.get('title')}: {r.get('snippet')}"
        for r in results[:5]
    ])
    
    prompt = f"""From these LinkedIn profiles, extract recruiting and HR team members at '{company_name}'.
Extract:
- name: Full name
- role: Their title
- linkedin_url: LinkedIn profile URL (https://www.linkedin.com/in/...)

Return JSON array with these fields. ONLY return the JSON array.

Profiles:
{snippets_text}"""
    
    raw_response = llm_query(prompt, max_tokens=800)
    cleaned = clean_json_text(raw_response)
    extracted = safe_json_loads(cleaned, default=[])
    
    if not isinstance(extracted, list):
        return []
    
    team = []
    for item in extracted:
        if isinstance(item, dict) and item.get("name") and item.get("linkedin_url"):
            team.append({
                "name": item.get("name"),
                "role": item.get("role", "Recruiter"),
                "linkedin_url": item.get("linkedin_url"),
                "role_score": ROLE_SCORES.get("Recruiter", 70)
            })
    
    logger.info(f"Found {len(team)} recruiting team members")
    return team


def search_engineering_leadership(company_name: str) -> List[dict]:
    """
    Specifically search for engineering leadership.
    
    Args:
        company_name: Company name
    
    Returns:
        List of engineering leaders
    """
    logger.info(f"Finding engineering leadership at: {company_name}")
    
    engineering_titles = [
        "CTO",
        "VP Engineering",
        "Head of Engineering",
        "Engineering Manager",
        "Engineering Director",
        "VP Product Engineering",
        "Director of Engineering"
    ]
    
    titles_search = " OR ".join([f'"{title}"' for title in engineering_titles])
    query = f'site:linkedin.com/in "{company_name}" ({titles_search})'
    
    results = serper_search(query, num=8)
    
    if not results:
        logger.warning(f"No engineering leadership found for {company_name}")
        return []
    
    snippets_text = "\n".join([
        f"- {r.get('title')}: {r.get('snippet')}"
        for r in results[:5]
    ])
    
    prompt = f"""Extract engineering leadership from these profiles at '{company_name}'.
Extract:
- name: Full name  
- role: Title
- linkedin_url: LinkedIn URL (https://www.linkedin.com/in/...)

Return only JSON array with these 3 fields.

Profiles:
{snippets_text}"""
    
    raw_response = llm_query(prompt, max_tokens=800)
    cleaned = clean_json_text(raw_response)
    extracted = safe_json_loads(cleaned, default=[])
    
    if not isinstance(extracted, list):
        return []
    
    leaders = []
    for item in extracted:
        if isinstance(item, dict) and item.get("name") and item.get("linkedin_url"):
            role = item.get("role", "Engineering Manager")
            role_score = 0
            for title, score in ROLE_SCORES.items():
                if title.lower() in role.lower():
                    role_score = max(role_score, score)
            
            leaders.append({
                "name": item.get("name"),
                "role": role,
                "linkedin_url": item.get("linkedin_url"),
                "role_score": role_score or 85
            })
    
    logger.info(f"Found {len(leaders)} engineering leaders")
    return leaders
