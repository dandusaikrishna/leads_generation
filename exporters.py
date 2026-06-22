"""
Output and export functions for companies.json and emails.txt
"""

import json
import os
from typing import List, Dict
from datetime import datetime
from models import Company
from utils import logger, deduplicate_emails
from config import COMPANIES_OUTPUT_FILE, EMAILS_OUTPUT_FILE


def export_companies_json(companies: List[Company], output_path: str = COMPANIES_OUTPUT_FILE):
    """
    Export companies to companies.json with full details.
    
    Args:
        companies: List of Company objects
        output_path: Output file path
    """
    logger.info(f"Exporting {len(companies)} companies to {output_path}")
    
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    
    companies_data = {
        "metadata": {
            "export_date": datetime.utcnow().isoformat(),
            "total_companies": len(companies),
            "version": "1.0"
        },
        "companies": [company.to_dict() for company in companies]
    }
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(companies_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Successfully exported to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to export JSON: {e}")
        return False


def export_emails_txt(companies: List[Company], output_path: str = EMAILS_OUTPUT_FILE):
    """
    Export companies and contacts to formatted emails.txt file.
    
    Format:
    ==================================================
    COMPANY: Company Name
    SCORE: 95
    WEBSITE: https://example.com
    LINKEDIN: https://linkedin.com/company/example
    
    PUBLIC EMAILS:
    careers@example.com
    hr@example.com
    
    CONTACTS:
    Jane Doe | CTO
    John Smith | Head of Engineering
    
    PATTERNS:
    firstname.lastname
    ==================================================
    
    Args:
        companies: List of Company objects
        output_path: Output file path
    """
    logger.info(f"Exporting emails report to {output_path}")
    
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    
    lines = []
    
    # Header
    lines.append("=" * 60)
    lines.append(f"Job-Company Discovery & Contact Intelligence Report")
    lines.append(f"Generated: {datetime.utcnow().isoformat()}")
    lines.append(f"Total Companies: {len(companies)}")
    lines.append("=" * 60)
    lines.append("")
    
    # Process each company
    for company in companies:
        lines.append("=" * 60)
        lines.append(f"COMPANY: {company.company_name}")
        lines.append(f"SCORE: {company.score}")
        
        if company.website:
            lines.append(f"WEBSITE: {company.website}")
        
        if company.linkedin_url:
            lines.append(f"LINKEDIN: {company.linkedin_url}")
        
        if company.industry:
            lines.append(f"INDUSTRY: {company.industry}")
        
        if company.company_size:
            lines.append(f"COMPANY SIZE: {company.company_size}")
        
        if company.location:
            lines.append(f"LOCATION: {company.location}")
        
        # Active jobs
        if company.jobs:
            lines.append("")
            lines.append("ACTIVE JOBS:")
            for job in company.jobs[:5]:  # Top 5 jobs
                lines.append(f"  - {job.get('title', job.title)}")
        
        # Public emails
        if company.public_emails:
            lines.append("")
            lines.append("PUBLIC EMAILS:")
            for email_obj in company.public_emails:
                email = email_obj.get("email") if isinstance(email_obj, dict) else email_obj.email
                category = email_obj.get("category") if isinstance(email_obj, dict) else email_obj.category
                confidence = email_obj.get("confidence_score") if isinstance(email_obj, dict) else email_obj.confidence_score
                
                lines.append(f"  - {email} ({category}, {confidence}% confidence)")
        
        # Senior contacts
        if company.contacts:
            lines.append("")
            lines.append("SENIOR CONTACTS & DECISION MAKERS:")
            for contact in company.contacts[:10]:  # Top 10 contacts
                name = contact.get("name") if isinstance(contact, dict) else contact.name
                role = contact.get("role") if isinstance(contact, dict) else contact.role
                score = contact.get("role_score") if isinstance(contact, dict) else contact.role_score
                linkedin = contact.get("linkedin_url") if isinstance(contact, dict) else contact.public_profile_url
                
                lines.append(f"  - {name} | {role} (Score: {score})")
                if linkedin:
                    lines.append(f"    LinkedIn: {linkedin}")
        
        # Email patterns
        if company.email_patterns:
            lines.append("")
            lines.append("EMAIL PATTERNS IDENTIFIED:")
            for pattern_obj in company.email_patterns[:5]:  # Top 5 patterns
                pattern = pattern_obj.get("pattern") if isinstance(pattern_obj, dict) else pattern_obj.pattern
                confidence = pattern_obj.get("confidence_score") if isinstance(pattern_obj, dict) else pattern_obj.confidence_score
                examples = pattern_obj.get("examples") if isinstance(pattern_obj, dict) else pattern_obj.examples
                
                lines.append(f"  - {pattern} ({confidence}% confidence)")
                if examples:
                    for ex in examples[:2]:
                        lines.append(f"      Example: {ex}")
        
        # Score breakdown
        if company.score_breakdown:
            lines.append("")
            lines.append("SCORE BREAKDOWN:")
            for component, component_score in company.score_breakdown.items():
                lines.append(f"  - {component.replace('_', ' ').title()}: {component_score}")
        
        lines.append("=" * 60)
        lines.append("")
    
    # Summary stats
    lines.append("")
    lines.append("=" * 60)
    lines.append("SUMMARY STATISTICS")
    lines.append("=" * 60)
    
    companies_with_contacts = len([c for c in companies if c.contacts])
    companies_with_emails = len([c for c in companies if c.public_emails])
    companies_with_patterns = len([c for c in companies if c.email_patterns])
    avg_score = sum(c.score for c in companies) / len(companies) if companies else 0
    
    lines.append(f"Total Companies: {len(companies)}")
    lines.append(f"Companies with Contacts: {companies_with_contacts} ({companies_with_contacts/len(companies)*100:.1f}%)")
    lines.append(f"Companies with Public Emails: {companies_with_emails} ({companies_with_emails/len(companies)*100:.1f}%)")
    lines.append(f"Companies with Email Patterns: {companies_with_patterns} ({companies_with_patterns/len(companies)*100:.1f}%)")
    lines.append(f"Average Company Score: {avg_score:.1f}")
    
    total_contacts = sum(len(c.contacts) for c in companies)
    total_emails = sum(len(c.public_emails) for c in companies)
    
    lines.append(f"Total Unique Contacts Found: {total_contacts}")
    lines.append(f"Total Public Emails Found: {total_emails}")
    
    lines.append("=" * 60)
    
    # Write to file
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        logger.info(f"Successfully exported to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to export TXT: {e}")
        return False


def export_summary(companies: List[Company]) -> Dict:
    """
    Create a summary of collected data.
    
    Args:
        companies: List of companies
    
    Returns:
        Summary dictionary
    """
    all_emails = []
    all_contacts = []
    
    for company in companies:
        for email_obj in company.public_emails:
            email = email_obj.get("email") if isinstance(email_obj, dict) else email_obj.email
            all_emails.append(email)
        
        for contact in company.contacts:
            all_contacts.append({
                "name": contact.get("name") if isinstance(contact, dict) else contact.name,
                "role": contact.get("role") if isinstance(contact, dict) else contact.role,
                "company": company.company_name
            })
    
    all_emails = deduplicate_emails(all_emails)
    
    summary = {
        "total_companies": len(companies),
        "companies_with_contacts": len([c for c in companies if c.contacts]),
        "companies_with_emails": len([c for c in companies if c.public_emails]),
        "companies_with_patterns": len([c for c in companies if c.email_patterns]),
        "total_unique_contacts": len(all_contacts),
        "total_unique_emails": len(all_emails),
        "average_company_score": sum(c.score for c in companies) / len(companies) if companies else 0,
        "high_tier_companies": len([c for c in companies if c.score >= 75]),
        "medium_tier_companies": len([c for c in companies if 50 <= c.score < 75]),
        "low_tier_companies": len([c for c in companies if c.score < 50]),
    }
    
    return summary
