"""
Direct leads collector - Simple, effective approach to finding companies and contacts
"""

import json
import time
from utils import serper_search, llm_query, clean_json_text, safe_json_loads, logger
from datetime import datetime
import os

def collect_indian_companies():
    """Collect software companies in India using direct Serper searches."""
    
    logger.info("🔍 Collecting Indian software companies...")
    
    companies = []
    
    # Simple, direct searches that Serper can handle
    searches = [
        "software development companies in Hyderabad India",
        "IT companies Bangalore India hiring engineers",
        "tech startups in Pune India recruitment",
        "Python Django companies in Hyderabad",
        "backend development companies in India",
        "SaaS companies India Bangalore",
        "fintech companies in Hyderabad India",
        "AI machine learning startups India",
        "cloud computing companies India",
        "software engineering jobs in India",
    ]
    
    for search_query in searches:
        try:
            logger.info(f"  Searching: {search_query}...", end=" ", flush=True)
            
            results = serper_search(search_query, num=10)
            
            if results and results.get("organic"):
                # Extract company names and URLs from results
                for result in results["organic"][:5]:
                    title = result.get("title", "")
                    snippet = result.get("snippet", "")
                    link = result.get("link", "")
                    
                    if any(word in title.lower() for word in ["company", "jobs", "careers", "hiring", "recruitment"]):
                        company_data = {
                            "name": title,
                            "url": link,
                            "source": search_query,
                            "discovered_at": datetime.now().isoformat()
                        }
                        companies.append(company_data)
                        logger.info(f"✅ ({len(companies)} found)")
                        break
                else:
                    logger.info("⏭️ (filtered)")
            else:
                logger.info("⚠️ (no results)")
            
            time.sleep(0.3)  # Rate limiting
            
        except Exception as e:
            logger.warning(f"❌ Error: {str(e)}")
            time.sleep(1)
    
    # Remove duplicates by name
    unique = {}
    for company in companies:
        name_lower = company["name"].lower()
        if name_lower not in unique:
            unique[name_lower] = company
    
    companies = list(unique.values())
    logger.info(f"\n✅ Found {len(companies)} unique companies")
    
    return companies


def extract_recruiter_contacts(companies):
    """Extract recruiter and HR contact information from companies."""
    
    logger.info("\n📧 Extracting recruiter contacts...")
    
    contacts = []
    
    for i, company in enumerate(companies, 1):
        try:
            company_name = company.get("name", "")
            url = company.get("url", "")
            
            if not company_name:
                continue
            
            logger.info(f"  [{i}/{len(companies)}] {company_name}...", end=" ", flush=True)
            
            # Search for hiring/recruiter info
            search = f"recruiting team at {company_name} hiring contacts email"
            results = serper_search(search, num=5)
            
            if results and results.get("organic"):
                # Extract email patterns
                snippet = results["organic"][0].get("snippet", "")
                
                contact_data = {
                    "company": company_name,
                    "company_url": url,
                    "recruiter_info": snippet[:200] if snippet else "Not found",
                    "source_url": results["organic"][0].get("link", ""),
                    "discovered_at": datetime.now().isoformat()
                }
                contacts.append(contact_data)
                logger.info("✅")
            else:
                logger.info("⏭️")
            
            time.sleep(0.3)
            
        except Exception as e:
            logger.warning(f"❌ {str(e)}")
    
    logger.info(f"✅ Extracted {len(contacts)} recruiter contacts")
    
    return contacts


def extract_emails(companies):
    """Extract company emails and contact information."""
    
    logger.info("\n📬 Extracting company emails...")
    
    email_data = []
    
    for i, company in enumerate(companies, 1):
        try:
            company_name = company.get("name", "")
            
            if not company_name:
                continue
            
            logger.info(f"  [{i}/{len(companies)}] {company_name}...", end=" ", flush=True)
            
            # Search for company emails
            search = f"{company_name} company email careers contact jobs"
            results = serper_search(search, num=5)
            
            emails = []
            
            if results and results.get("organic"):
                # Try to extract emails from snippets
                for result in results["organic"][:3]:
                    snippet = result.get("snippet", "")
                    
                    # Simple email extraction
                    import re
                    found_emails = re.findall(r'[\w\.-]+@[\w\.-]+\.com', snippet)
                    emails.extend(found_emails)
            
            email_data.append({
                "company": company_name,
                "emails": list(set(emails))[:5],  # Unique, max 5
                "email_count": len(set(emails)),
                "discovered_at": datetime.now().isoformat()
            })
            
            logger.info(f"✅ ({len(set(emails))} emails)")
            time.sleep(0.3)
            
        except Exception as e:
            logger.warning(f"❌ {str(e)}")
    
    logger.info(f"✅ Extracted emails for {len(email_data)} companies")
    
    return email_data


def search_job_postings():
    """Search for active job postings."""
    
    logger.info("\n💼 Searching job postings...")
    
    jobs = []
    
    job_searches = [
        "backend engineer jobs India 2026",
        "Python developer jobs Hyderabad",
        "senior software engineer jobs Bangalore",
        "DevOps engineer jobs India hiring",
        "full stack developer jobs India",
    ]
    
    for search in job_searches:
        try:
            logger.info(f"  {search}...", end=" ", flush=True)
            
            results = serper_search(search, num=8)
            
            if results and results.get("organic"):
                for result in results["organic"][:3]:
                    job = {
                        "title": result.get("title", ""),
                        "url": result.get("link", ""),
                        "snippet": result.get("snippet", "")[:150],
                        "search_term": search,
                        "discovered_at": datetime.now().isoformat()
                    }
                    jobs.append(job)
                
                logger.info(f"✅")
            else:
                logger.info("⏭️")
            
            time.sleep(0.3)
            
        except Exception as e:
            logger.warning(f"❌ {str(e)}")
    
    logger.info(f"✅ Found {len(jobs)} job postings")
    
    return jobs


def generate_outreach_list(companies, contacts, emails):
    """Generate a prioritized outreach list."""
    
    logger.info("\n🎯 Generating outreach list...")
    
    outreach = []
    
    for company in companies:
        company_name = company.get("name", "")
        
        # Find related contacts and emails
        related_contacts = [c for c in contacts if c["company"].lower() in company_name.lower() or company_name.lower() in c["company"].lower()]
        related_emails = [e for e in emails if e["company"].lower() in company_name.lower() or company_name.lower() in e["company"].lower()]
        
        outreach_item = {
            "company_name": company_name,
            "company_url": company.get("url", ""),
            "contacts": related_contacts,
            "email_contacts": related_emails,
            "priority": "HIGH" if (related_contacts or related_emails) else "MEDIUM",
            "outreach_strategy": "Email recruiting team" if related_emails else "Research hiring contacts"
        }
        
        outreach.append(outreach_item)
    
    return outreach


def export_leads(companies, contacts, emails, jobs, outreach):
    """Export all leads to JSON files."""
    
    logger.info("\n💾 Exporting leads...")
    
    os.makedirs("leads_data", exist_ok=True)
    
    exports = {
        "companies": ("leads_data/discovered_companies.json", companies),
        "contacts": ("leads_data/recruiter_contacts.json", contacts),
        "emails": ("leads_data/company_emails.json", emails),
        "jobs": ("leads_data/job_postings.json", jobs),
        "outreach": ("leads_data/outreach_list.json", outreach),
    }
    
    for name, (filepath, data) in exports.items():
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"  ✅ {filepath} ({len(data)} items)")
        except Exception as e:
            logger.error(f"  ❌ Error saving {filepath}: {str(e)}")
    
    # Summary
    summary = {
        "collection_date": datetime.now().isoformat(),
        "total_companies": len(companies),
        "total_contacts": len(contacts),
        "total_emails": sum(e["email_count"] for e in emails),
        "total_jobs": len(jobs),
        "outreach_ready": len(outreach),
        "files_exported": list(exports.keys())
    }
    
    with open("leads_data/summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"  ✅ leads_data/summary.json")
    
    return summary


def print_leads_summary(companies, contacts, emails, jobs, outreach):
    """Print a formatted summary of leads."""
    
    print("""
╔════════════════════════════════════════════════════════════════╗
║                    LEADS COLLECTION COMPLETE                   ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    print(f"""
📊 SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Companies Found:        {len(companies)}
✓ Recruiter Contacts:     {len(contacts)}
✓ Companies with Emails:  {len(emails)}
✓ Email Addresses:        {sum(e['email_count'] for e in emails)}
✓ Job Postings:           {len(jobs)}
✓ Ready for Outreach:     {len(outreach)}

📁 OUTPUT FILES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  leads_data/discovered_companies.json     ({len(companies)} companies)
  leads_data/recruiter_contacts.json       ({len(contacts)} contacts)
  leads_data/company_emails.json           ({len(emails)} companies)
  leads_data/job_postings.json             ({len(jobs)} jobs)
  leads_data/outreach_list.json            ({len(outreach)} outreach items)
  leads_data/summary.json                  (statistics)

🎯 NEXT STEPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Review: Open leads_data/discovered_companies.json
2. Check: Open leads_data/outreach_list.json for priority leads
3. Contact: Use emails from leads_data/company_emails.json
4. Jobs: Search leads_data/job_postings.json for opportunities
5. Analyze: Check leads_data/summary.json for statistics

📧 SAMPLE EMAIL CONTACTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
    
    total_emails = 0
    for email_data in emails[:5]:
        if email_data["emails"]:
            print(f"  {email_data['company']}:")
            for email in email_data["emails"]:
                print(f"    • {email}")
            total_emails += len(email_data["emails"])
    
    if total_emails > 0:
        print(f"\n  ... and {sum(e['email_count'] for e in emails) - total_emails} more emails")
    
    print(f"""
💡 TIPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Use outreach_list.json for HIGH priority companies
• Check job postings for context before reaching out
• Verify emails before bulk outreach
• Track responses in your CRM
• Schedule follow-ups after 7-10 days

✨ Your leads are ready to use!
    """)


def main():
    """Main execution."""
    
    logger.info("""
╔════════════════════════════════════════════════════════════════╗
║              DIRECT LEADS COLLECTOR                            ║
║  Finding Indian software companies and contacts               ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    # Phase 1: Collect companies
    logger.info("\n" + "="*60)
    companies = collect_indian_companies()
    
    # Phase 2: Extract recruiter contacts
    logger.info("\n" + "="*60)
    contacts = extract_recruiter_contacts(companies) if companies else []
    
    # Phase 3: Extract emails
    logger.info("\n" + "="*60)
    emails = extract_emails(companies) if companies else []
    
    # Phase 4: Search job postings
    logger.info("\n" + "="*60)
    jobs = search_job_postings()
    
    # Phase 5: Generate outreach list
    logger.info("\n" + "="*60)
    outreach = generate_outreach_list(companies, contacts, emails)
    
    # Phase 6: Export
    logger.info("\n" + "="*60)
    summary = export_leads(companies, contacts, emails, jobs, outreach)
    
    # Print summary
    logger.info("\n" + "="*60)
    print_leads_summary(companies, contacts, emails, jobs, outreach)
    
    logger.info("✅ Leads collection complete!")
    
    return summary


if __name__ == "__main__":
    main()
