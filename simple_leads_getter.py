"""
Simple leads collector - Get companies, contacts, and jobs quickly
"""

import json
import time
from utils import serper_search, logger
from datetime import datetime
import os
import re

def collect_companies():
    """Collect software companies in India."""
    
    print("\n[1/4] Collecting Indian software companies...")
    print("="*60)
    
    companies = []
    searches = [
        "software development companies Hyderabad India",
        "IT companies Bangalore engineering jobs",
        "tech startups Pune India hiring",
        "Python developer companies India",
        "backend engineer jobs India",
        "SaaS companies India Bangalore",
        "fintech startups India hiring",
        "AI startup jobs India",
    ]
    
    for i, search_query in enumerate(searches, 1):
        try:
            print(f"  [{i}/{len(searches)}] {search_query}...", end="", flush=True)
            
            results = serper_search(search_query, num=10)
            
            if results and results.get("organic"):
                for result in results["organic"][:3]:
                    title = result.get("title", "")
                    link = result.get("link", "")
                    
                    if link and len(title) > 5:
                        company = {
                            "name": title[:80],
                            "url": link,
                            "source": search_query,
                            "found_at": datetime.now().isoformat()
                        }
                        companies.append(company)
                        print(" [OK]")
                        break
                else:
                    print(" [SKIP]")
            else:
                print(" [NO RESULTS]")
            
            time.sleep(0.3)
            
        except Exception as e:
            print(f" [ERROR: {str(e)[:30]}]")
            time.sleep(1)
    
    # Deduplicate
    unique = {}
    for c in companies:
        key = c["url"].lower()
        if key not in unique:
            unique[key] = c
    
    companies = list(unique.values())
    print(f"\nFound {len(companies)} unique companies")
    
    return companies


def extract_contacts(companies):
    """Extract recruiter and HR contacts."""
    
    print("\n[2/4] Extracting recruiter contacts...")
    print("="*60)
    
    contacts = []
    
    for i, company in enumerate(companies, 1):
        try:
            name = company.get("name", "")[:40]
            url = company.get("url", "")
            
            print(f"  [{i}/{len(companies)}] {name}...", end="", flush=True)
            
            # Search for hiring info
            search = f"recruiters at {name} hiring contacts India"
            results = serper_search(search, num=3)
            
            if results and results.get("organic"):
                snippet = results["organic"][0].get("snippet", "")[:150]
                
                contact = {
                    "company": name,
                    "url": url,
                    "info": snippet,
                    "source_url": results["organic"][0].get("link", ""),
                    "found_at": datetime.now().isoformat()
                }
                contacts.append(contact)
                print(" [OK]")
            else:
                print(" [SKIP]")
            
            time.sleep(0.3)
            
        except Exception as e:
            print(f" [ERROR]")
    
    print(f"Found {len(contacts)} contacts")
    
    return contacts


def extract_emails(companies):
    """Extract company emails."""
    
    print("\n[3/4] Extracting company emails...")
    print("="*60)
    
    email_list = []
    
    for i, company in enumerate(companies, 1):
        try:
            name = company.get("name", "")[:40]
            url = company.get("url", "")
            
            print(f"  [{i}/{len(companies)}] {name}...", end="", flush=True)
            
            # Search for company emails
            search = f"{name} careers contact email India"
            results = serper_search(search, num=3)
            
            emails = []
            
            if results and results.get("organic"):
                for result in results["organic"][:2]:
                    snippet = result.get("snippet", "")
                    # Extract emails
                    found = re.findall(r'[\w\.-]+@[\w\.-]+\.[\w]+', snippet)
                    emails.extend(found)
            
            if emails:
                email_list.append({
                    "company": name,
                    "url": url,
                    "emails": list(set(emails))[:5],
                    "count": len(set(emails)),
                    "found_at": datetime.now().isoformat()
                })
                print(f" [OK - {len(set(emails))} emails]")
            else:
                print(" [SKIP]")
            
            time.sleep(0.3)
            
        except Exception as e:
            print(f" [ERROR]")
    
    print(f"Found emails for {len(email_list)} companies")
    
    return email_list


def search_jobs():
    """Search for job postings."""
    
    print("\n[4/4] Searching job postings...")
    print("="*60)
    
    jobs = []
    searches = [
        "backend engineer jobs India 2026",
        "Python developer jobs Hyderabad",
        "DevOps engineer jobs India hiring",
        "senior software engineer Bangalore",
        "full stack developer India jobs",
    ]
    
    for i, search_query in enumerate(searches, 1):
        try:
            print(f"  [{i}/{len(searches)}] {search_query}...", end="", flush=True)
            
            results = serper_search(search_query, num=5)
            
            if results and results.get("organic"):
                for result in results["organic"][:2]:
                    job = {
                        "title": result.get("title", ""),
                        "url": result.get("link", ""),
                        "snippet": result.get("snippet", "")[:120],
                        "search": search_query,
                        "found_at": datetime.now().isoformat()
                    }
                    jobs.append(job)
                
                print(" [OK]")
            else:
                print(" [SKIP]")
            
            time.sleep(0.3)
            
        except Exception as e:
            print(f" [ERROR]")
    
    print(f"Found {len(jobs)} job postings")
    
    return jobs


def save_leads(companies, contacts, emails, jobs):
    """Save all leads to files."""
    
    print("\n[EXPORT] Saving leads to files...")
    print("="*60)
    
    os.makedirs("leads_data", exist_ok=True)
    
    files = {
        "leads_data/companies.json": companies,
        "leads_data/contacts.json": contacts,
        "leads_data/emails.json": emails,
        "leads_data/jobs.json": jobs,
    }
    
    for filepath, data in files.items():
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            print(f"  {filepath}: {len(data)} items")
        except Exception as e:
            print(f"  ERROR saving {filepath}: {str(e)}")
    
    # Summary
    summary = {
        "date": datetime.now().isoformat(),
        "companies": len(companies),
        "contacts": len(contacts),
        "emails": sum(e["count"] for e in emails),
        "jobs": len(jobs),
        "total_emails": len(emails),
    }
    
    with open("leads_data/summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"  leads_data/summary.json: summary")
    
    return summary


def print_results(companies, contacts, emails, jobs):
    """Print results summary."""
    
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                    LEADS COLLECTED SUCCESSFULLY              ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    total_emails = sum(e["count"] for e in emails)
    
    print(f"""
📊 RESULTS
{'━'*60}
  Companies Found:       {len(companies):>3}
  Recruiter Contacts:    {len(contacts):>3}
  Companies w/ Emails:   {len(emails):>3}
  Total Email Addresses: {total_emails:>3}
  Job Postings Found:    {len(jobs):>3}

📁 SAVED TO
{'━'*60}
  leads_data/companies.json
  leads_data/contacts.json
  leads_data/emails.json
  leads_data/jobs.json
  leads_data/summary.json

📧 SAMPLE EMAILS
{'━'*60}
""")
    
    count = 0
    for email_data in emails:
        if email_data["emails"] and count < 10:
            print(f"  {email_data['company']:<30}")
            for email in email_data["emails"]:
                print(f"    • {email}")
                count += 1
    
    if count < total_emails:
        print(f"  ... and {total_emails - count} more emails")
    
    print(f"""
💼 JOB POSTINGS
{'━'*60}
""")
    
    for job in jobs[:5]:
        print(f"  {job['title'][:50]}")
        print(f"    {job['url']}")
    
    if len(jobs) > 5:
        print(f"  ... and {len(jobs)-5} more jobs")
    
    print(f"""
✨ Your leads are ready to use!
   View leads_data/summary.json for statistics
   Open leads_data/contacts.json for outreach targets
   Check leads_data/emails.json for email addresses
    """)


def main():
    """Main execution."""
    
    print("""
╔═══════════════════════════════════════════════════════════════╗
║           SIMPLE LEADS COLLECTOR                             ║
║  Indian software companies, contacts, emails & jobs          ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # Collect all data
    companies = collect_companies()
    contacts = extract_contacts(companies)
    emails = extract_emails(companies)
    jobs = search_jobs()
    
    # Save
    print("\n" + "="*60)
    summary = save_leads(companies, contacts, emails, jobs)
    
    # Print summary
    print_results(companies, contacts, emails, jobs)


if __name__ == "__main__":
    main()
