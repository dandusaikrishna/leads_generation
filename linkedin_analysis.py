"""
LinkedIn data analysis and integration.
Combines job data, recruiters, and emails for comprehensive company intelligence.
"""

import json
from typing import List, Dict, Optional
from datetime import datetime
from utils import logger
from linkedin_jobs import (
    search_linkedin_jobs_by_role,
    search_hiring_companies_linkedin,
    analyze_job_market_trends
)
from linkedin_recruiters import (
    find_recruiters_by_role,
    find_hiring_managers_by_company,
    build_recruiter_database
)
from linkedin_emails import (
    extract_company_emails_from_linkedin,
    compile_company_email_profile
)


def integrate_linkedin_data(
    company_name: str,
    domain: str = None,
    roles: List[str] = None
) -> Dict:
    """
    Integrate all LinkedIn data for a company.
    Combines jobs, recruiters, and email information.
    
    Args:
        company_name: Company name
        domain: Company domain
        roles: Roles to search for at this company
    
    Returns:
        Complete LinkedIn intelligence profile
    """
    if roles is None:
        roles = ["Backend Engineer", "Software Engineer", "Senior Engineer"]
    
    logger.info(f"Integrating LinkedIn data for {company_name}...")
    
    profile = {
        "company_name": company_name,
        "domain": domain,
        "integration_date": datetime.now().isoformat(),
        "hiring_activity": {},
        "team_intelligence": {},
        "contact_information": {},
        "market_position": {}
    }
    
    # Get hiring activity
    try:
        jobs = search_linkedin_jobs_by_role(
            role=roles[0] if roles else "Engineer",
            cities=["Hyderabad", "Bangalore"]
        )
        
        company_jobs = [j for j in jobs if j.get("company_name", "").lower() == company_name.lower()]
        profile["hiring_activity"]["open_positions"] = len(company_jobs)
        profile["hiring_activity"]["job_postings"] = company_jobs
    except Exception as e:
        logger.warning(f"Error fetching jobs: {str(e)}")
    
    # Get hiring team
    try:
        managers = find_hiring_managers_by_company(company_name, roles)
        profile["team_intelligence"]["hiring_managers"] = managers
        profile["team_intelligence"]["total_managers"] = len(managers)
    except Exception as e:
        logger.warning(f"Error fetching managers: {str(e)}")
    
    # Get email information
    try:
        emails = compile_company_email_profile(company_name, domain)
        profile["contact_information"]["emails"] = emails["all_unique_emails"]
        profile["contact_information"]["email_sources"] = {
            "linkedin_company_page": len(emails["verified_emails"]),
            "job_postings": len(emails["job_posting_emails"]),
            "company_posts": len(emails["post_emails"])
        }
    except Exception as e:
        logger.warning(f"Error fetching emails: {str(e)}")
    
    # Get market position
    profile["market_position"]["hiring_momentum"] = assess_hiring_momentum(
        company_name,
        roles
    )
    
    return profile


def assess_hiring_momentum(
    company_name: str,
    roles: List[str] = None,
    days: int = 30
) -> Dict:
    """
    Assess company's hiring momentum and growth trajectory.
    
    Args:
        company_name: Company name
        roles: Roles to analyze
        days: Time period to analyze
    
    Returns:
        Hiring momentum assessment
    """
    if roles is None:
        roles = ["Backend Engineer", "Software Engineer"]
    
    logger.info(f"Assessing hiring momentum for {company_name}...")
    
    momentum = {
        "company_name": company_name,
        "analysis_period_days": days,
        "hiring_status": "Unknown",
        "momentum_score": 0,  # 0-100
        "growth_indicators": [],
        "recommendation": ""
    }
    
    try:
        # Search for hiring activity
        hiring_companies = search_hiring_companies_linkedin("hiring", ["Hyderabad"])
        
        company_found = any(
            c.get("company_name", "").lower() == company_name.lower()
            for c in hiring_companies
        )
        
        if company_found:
            momentum["hiring_status"] = "Actively Hiring"
            momentum["momentum_score"] = 75
            momentum["growth_indicators"].append("Recently posted hiring announcements")
        else:
            momentum["hiring_status"] = "Not Recently Active"
            momentum["momentum_score"] = 30
            momentum["growth_indicators"].append("No recent hiring announcements")
        
        # Get trend data
        trends = analyze_job_market_trends(roles, ["Hyderabad"])
        
        if company_name in str(trends.get("top_companies", [])):
            momentum["growth_indicators"].append("In top hiring companies")
            momentum["momentum_score"] = min(momentum["momentum_score"] + 15, 100)
        
        # Recommendation
        if momentum["momentum_score"] >= 70:
            momentum["recommendation"] = "PRIORITY - Actively hiring with strong growth"
        elif momentum["momentum_score"] >= 50:
            momentum["recommendation"] = "POTENTIAL - Moderate hiring activity"
        else:
            momentum["recommendation"] = "LOW PRIORITY - Limited recent hiring activity"
    
    except Exception as e:
        logger.warning(f"Error assessing momentum: {str(e)}")
    
    return momentum


def create_outreach_list(
    companies: List[Dict],
    roles: List[str] = None
) -> Dict:
    """
    Create outreach list with all contact information.
    
    Args:
        companies: List of companies to target
        roles: Target roles
    
    Returns:
        Outreach-ready list with contacts
    """
    if roles is None:
        roles = ["Backend Engineer", "Software Engineer"]
    
    logger.info(f"Creating outreach list for {len(companies)} companies...")
    
    outreach_list = {
        "creation_date": datetime.now().isoformat(),
        "total_companies": len(companies),
        "target_roles": roles,
        "contacts": []
    }
    
    for company in companies:
        company_name = company.get("company_name")
        domain = company.get("domain")
        
        if not company_name:
            continue
        
        # Integrate all data
        intel = integrate_linkedin_data(company_name, domain, roles)
        
        # Extract key contacts
        managers = intel.get("team_intelligence", {}).get("hiring_managers", [])
        emails = intel.get("contact_information", {}).get("emails", [])
        
        contact_entry = {
            "company_name": company_name,
            "domain": domain,
            "hiring_momentum": intel.get("market_position", {}).get("hiring_momentum", {}),
            "open_positions": intel.get("hiring_activity", {}).get("open_positions", 0),
            "hiring_managers": managers[:3],  # Top 3
            "company_emails": emails[:5],  # Top 5
            "outreach_priority": calculate_outreach_priority(intel)
        }
        
        outreach_list["contacts"].append(contact_entry)
    
    logger.info(f"Created outreach list with {len(outreach_list['contacts'])} companies")
    
    return outreach_list


def calculate_outreach_priority(intel: Dict) -> str:
    """
    Calculate outreach priority based on LinkedIn intelligence.
    
    Args:
        intel: LinkedIn intelligence profile
    
    Returns:
        Priority level (Critical, High, Medium, Low)
    """
    score = 0
    
    # Hiring activity score
    open_positions = intel.get("hiring_activity", {}).get("open_positions", 0)
    score += min(open_positions * 10, 30)
    
    # Team size score
    managers = intel.get("team_intelligence", {}).get("hiring_managers", [])
    score += len(managers) * 5
    
    # Contact availability score
    emails = intel.get("contact_information", {}).get("emails", [])
    score += min(len(emails) * 10, 25)
    
    # Hiring momentum
    momentum = intel.get("market_position", {}).get("hiring_momentum", {}).get("momentum_score", 0)
    score += (momentum / 100) * 15
    
    # Determine priority
    if score >= 70:
        return "Critical"
    elif score >= 50:
        return "High"
    elif score >= 30:
        return "Medium"
    else:
        return "Low"


def generate_linkedin_report(companies: List[Dict]) -> Dict:
    """
    Generate comprehensive LinkedIn market analysis report.
    
    Args:
        companies: Companies to analyze
    
    Returns:
        Market analysis report
    """
    logger.info(f"Generating LinkedIn report for {len(companies)} companies...")
    
    report = {
        "report_date": datetime.now().isoformat(),
        "companies_analyzed": len(companies),
        "summary": {},
        "by_company": {},
        "market_insights": {},
        "recommendations": []
    }
    
    # Analyze each company
    for company in companies:
        name = company.get("company_name")
        if not name:
            continue
        
        intel = integrate_linkedin_data(name)
        report["by_company"][name] = intel
    
    # Generate market insights
    total_jobs = sum(
        c.get("hiring_activity", {}).get("open_positions", 0)
        for c in report["by_company"].values()
    )
    
    total_emails = sum(
        len(c.get("contact_information", {}).get("emails", []))
        for c in report["by_company"].values()
    )
    
    report["summary"]["total_open_positions"] = total_jobs
    report["summary"]["total_company_emails"] = total_emails
    report["summary"]["companies_actively_hiring"] = sum(
        1 for c in report["by_company"].values()
        if c.get("hiring_activity", {}).get("open_positions", 0) > 0
    )
    
    # Top companies
    top_companies = sorted(
        report["by_company"].items(),
        key=lambda x: x[1].get("hiring_activity", {}).get("open_positions", 0),
        reverse=True
    )[:5]
    
    report["summary"]["top_hiring_companies"] = [
        {"name": name, "open_positions": intel.get("hiring_activity", {}).get("open_positions", 0)}
        for name, intel in top_companies
    ]
    
    # Recommendations
    if report["summary"]["total_open_positions"] > 100:
        report["recommendations"].append("High market demand - Multiple opportunities available")
    
    if report["summary"]["companies_actively_hiring"] > 70:
        report["recommendations"].append("Strong hiring momentum across most companies")
    
    if report["summary"]["total_company_emails"] > 50:
        report["recommendations"].append("Good email contact availability for outreach")
    
    return report


def export_linkedin_intelligence(
    data: Dict,
    output_file: str,
    format: str = "json"
) -> bool:
    """
    Export LinkedIn intelligence to file.
    
    Args:
        data: Data to export
        output_file: Output file path
        format: Export format (json, csv, etc.)
    
    Returns:
        True if successful
    """
    try:
        logger.info(f"Exporting LinkedIn intelligence to {output_file}...")
        
        if format == "json":
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Exported to {output_file}")
        return True
    except Exception as e:
        logger.error(f"❌ Export failed: {str(e)}")
        return False


def quick_linkedin_scan(company_name: str) -> Dict:
    """
    Quick scan of a single company on LinkedIn.
    Returns key metrics without deep analysis.
    
    Args:
        company_name: Company name
    
    Returns:
        Quick scan results
    """
    logger.info(f"Quick scan for {company_name}...")
    
    scan = {
        "company": company_name,
        "scan_date": datetime.now().isoformat(),
        "hiring_activity": "Unknown",
        "team_presence": "Unknown",
        "contact_available": False,
        "recommendation": "Check full report for details"
    }
    
    try:
        # Quick hiring check
        hiring_companies = search_hiring_companies_linkedin("hiring", ["Hyderabad"])
        if any(c.get("company_name", "").lower() == company_name.lower() for c in hiring_companies):
            scan["hiring_activity"] = "Active"
        
        # Quick email check
        emails = extract_company_emails_from_linkedin(company_name)
        scan["contact_available"] = len(emails) > 0
        
        # Quick manager check
        managers = find_hiring_managers_by_company(company_name)
        scan["team_presence"] = f"{len(managers)} managers found"
    
    except Exception as e:
        logger.warning(f"Quick scan error: {str(e)}")
    
    return scan
