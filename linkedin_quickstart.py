"""
LinkedIn data collection quick start.
Demonstrates how to use the LinkedIn modules for company intelligence gathering.
"""

import json
import os
from datetime import datetime
from linkedin_jobs import (
    search_linkedin_jobs_by_role,
    search_hiring_companies_linkedin,
    analyze_job_market_trends,
    export_jobs_to_json
)
from linkedin_recruiters import (
    find_recruiters_by_role,
    find_hiring_managers_by_company,
    build_recruiter_database,
    export_recruiters_to_json
)
from linkedin_emails import (
    extract_company_emails_from_linkedin,
    compile_company_email_profile,
    export_company_emails
)
from linkedin_analysis import (
    create_outreach_list,
    generate_linkedin_report,
    quick_linkedin_scan,
    export_linkedin_intelligence
)


def main():
    """Main workflow for LinkedIn data collection."""
    
    print("""
╔════════════════════════════════════════════════════════════════╗
║   LinkedIn Legal Data Collection & Analysis                   ║
║   Extract jobs, recruiters, and company emails from public data║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    # Ensure output directory
    os.makedirs("leads", exist_ok=True)
    os.makedirs("linkedin_data", exist_ok=True)
    
    print("\n" + "="*60)
    print("PHASE 1: Find Hiring Companies")
    print("="*60)
    
    # Find companies actively hiring
    hiring_companies = search_hiring_companies_linkedin(
        keyword="hiring",
        cities=["Hyderabad", "Bangalore"],
        days=30
    )
    
    if hiring_companies:
        print(f"\n✅ Found {len(hiring_companies)} companies actively hiring:")
        for i, company in enumerate(hiring_companies[:5], 1):
            print(f"  {i}. {company.get('company_name')} - {company.get('hiring_status')}")
        
        # Export jobs
        export_jobs_to_json(
            [{"company": c} for c in hiring_companies],
            "linkedin_data/hiring_companies.json"
        )
    
    print("\n" + "="*60)
    print("PHASE 2: Search Job Postings by Role")
    print("="*60)
    
    # Search jobs for specific roles
    roles = ["Backend Engineer", "Software Engineer", "Python Developer"]
    all_jobs = []
    
    for role in roles:
        print(f"\n🔍 Searching for {role}...")
        jobs = search_linkedin_jobs_by_role(
            role=role,
            cities=["Hyderabad", "Bangalore", "Pune"],
            days_posted=30
        )
        
        print(f"✅ Found {len(jobs)} {role} positions")
        all_jobs.extend(jobs)
        
        # Show sample
        if jobs:
            print(f"   Sample: {jobs[0].get('company_name')} - {jobs[0].get('job_title')}")
    
    # Export all jobs
    if all_jobs:
        export_jobs_to_json(all_jobs, "linkedin_data/job_postings.json")
        print(f"\n💾 Exported {len(all_jobs)} total job postings")
    
    print("\n" + "="*60)
    print("PHASE 3: Find Recruiters")
    print("="*60)
    
    # Find recruiters for each role
    recruiters_db = build_recruiter_database(roles[:2], ["Hyderabad", "Bangalore"])
    
    print(f"\n✅ Recruiter Database Built:")
    print(f"   • Total recruiters: {len(recruiters_db['recruiters'])}")
    print(f"   • HR professionals: {len(recruiters_db['hr_professionals'])}")
    print(f"   • Agencies: {len(recruiters_db['agencies'])}")
    
    # Show sample recruiters
    if recruiters_db['recruiters']:
        print(f"\n   Sample Recruiters:")
        for recruiter in recruiters_db['recruiters'][:3]:
            print(f"   - {recruiter.get('recruiter_name')} ({recruiter.get('company_name')})")
    
    # Export
    export_recruiters_to_json(
        recruiters_db['recruiters'] + recruiters_db['hr_professionals'],
        "linkedin_data/recruiters.json"
    )
    
    print("\n" + "="*60)
    print("PHASE 4: Extract Company Emails")
    print("="*60)
    
    # Extract emails for top companies
    if hiring_companies:
        print(f"\n📧 Extracting company emails...")
        
        company_emails = {}
        for company in hiring_companies[:10]:
            name = company.get('company_name')
            domain = company.get('website_domain')
            
            print(f"  • {name}...", end=" ", flush=True)
            
            profile = compile_company_email_profile(name, domain)
            company_emails[name] = profile
            
            emails_count = len(profile['all_unique_emails'])
            print(f"✅ {emails_count} emails")
        
        # Export
        export_company_emails(company_emails, "linkedin_data/company_emails.json")
        print(f"\n💾 Exported email data")
    
    print("\n" + "="*60)
    print("PHASE 5: Analyze Job Market Trends")
    print("="*60)
    
    # Market analysis
    trends = analyze_job_market_trends(roles, ["Hyderabad", "Bangalore"], 30)
    
    print(f"\n📊 Job Market Trends:")
    print(f"   Analysis Date: {trends.get('analysis_date')}")
    
    for role, data in trends.get('by_role', {}).items():
        print(f"\n   {role}:")
        print(f"     - Total postings: {data.get('total_postings')}")
        print(f"     - Companies hiring: {data.get('companies')}")
    
    print(f"\n   🏆 Top Hiring Companies:")
    for company in trends.get('top_companies', [])[:5]:
        print(f"     - {company['company']}: {company['open_positions']} positions")
    
    print("\n" + "="*60)
    print("PHASE 6: Generate Outreach List")
    print("="*60)
    
    # Create outreach list
    if hiring_companies:
        outreach_list = create_outreach_list(hiring_companies[:20], roles[:2])
        
        print(f"\n📋 Outreach List Created:")
        print(f"   • Total companies: {outreach_list['total_companies']}")
        print(f"   • Target roles: {', '.join(outreach_list['target_roles'])}")
        
        # Show prioritized companies
        print(f"\n   Priority Companies:")
        for contact in outreach_list['contacts'][:5]:
            priority = contact.get('outreach_priority', 'Low')
            print(f"   - {contact['company_name']} ({priority})")
        
        # Export
        export_linkedin_intelligence(
            outreach_list,
            "linkedin_data/outreach_list.json"
        )
    
    print("\n" + "="*60)
    print("PHASE 7: Final Report")
    print("="*60)
    
    # Generate comprehensive report
    if hiring_companies:
        report = generate_linkedin_report(hiring_companies[:15])
        
        print(f"\n📈 LinkedIn Market Report:")
        print(f"   Companies Analyzed: {report['companies_analyzed']}")
        print(f"   Total Open Positions: {report['summary'].get('total_open_positions', 0)}")
        print(f"   Companies Actively Hiring: {report['summary'].get('companies_actively_hiring', 0)}")
        print(f"   Total Company Emails: {report['summary'].get('total_company_emails', 0)}")
        
        print(f"\n   🏢 Top Hiring Companies:")
        for company in report['summary'].get('top_hiring_companies', []):
            print(f"   - {company['name']}: {company['open_positions']} positions")
        
        print(f"\n   💡 Recommendations:")
        for rec in report.get('recommendations', []):
            print(f"   • {rec}")
        
        # Export
        export_linkedin_intelligence(
            report,
            "linkedin_data/market_report.json"
        )
    
    print("\n" + "="*60)
    print("✅ COLLECTION COMPLETE")
    print("="*60)
    
    print(f"""
📂 Output Files Generated:
   • linkedin_data/hiring_companies.json - Companies actively hiring
   • linkedin_data/job_postings.json - All job postings
   • linkedin_data/recruiters.json - Recruiter database
   • linkedin_data/company_emails.json - Company emails
   • linkedin_data/outreach_list.json - Ready-to-use outreach list
   • linkedin_data/market_report.json - Comprehensive market analysis

📊 Key Metrics:
   • Total jobs found: {len(all_jobs)}
   • Total recruiters: {recruiters_db.get('total_contacts', 0)}
   • Companies analyzed: {len(hiring_companies)}

🚀 Next Steps:
   1. Review job_postings.json for open positions
   2. Check company_emails.json for contact information
   3. Use outreach_list.json for targeted outreach
   4. Reference market_report.json for strategy
   5. Use recruiters.json to find hiring managers

📧 Email Sources:
   • LinkedIn company pages
   • Job posting pages
   • Company LinkedIn posts
   • Publicly shared contact information

✨ All data collected legally from publicly available LinkedIn information
    """)


def quick_company_scan(company_name: str):
    """Quick scan of a single company."""
    print(f"\n🔍 Quick Scan: {company_name}\n")
    
    scan = quick_linkedin_scan(company_name)
    
    print(f"Company: {scan['company']}")
    print(f"Hiring Status: {scan['hiring_activity']}")
    print(f"Team Presence: {scan['team_presence']}")
    print(f"Contact Available: {'Yes' if scan['contact_available'] else 'No'}")
    print(f"\n{scan['recommendation']}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--scan":
        # Quick scan mode
        company = sys.argv[2] if len(sys.argv) > 2 else "Google"
        quick_company_scan(company)
    else:
        # Full collection
        main()
