"""
Quick start script for India-focused company discovery.
Run this to get started with discovering software companies in India.
"""

import json
import os
from typing import List, Dict

# Ensure directories exist
os.makedirs("cache", exist_ok=True)
os.makedirs("logs", exist_ok=True)
os.makedirs("leads", exist_ok=True)
os.makedirs("backend", exist_ok=True)


def setup():
    """Setup the environment and create necessary files."""
    print("🚀 Setting up India Company Discovery Pipeline...")
    
    # Check if backend/.env exists
    if not os.path.exists("backend/.env"):
        print("Creating backend/.env from .env.example...")
        if os.path.exists(".env.example"):
            with open(".env.example", "r") as f:
                content = f.read()
            with open("backend/.env", "w") as f:
                f.write(content)
            print("✅ Created backend/.env with API keys")
        else:
            print("⚠️  .env.example not found")
    else:
        print("✅ backend/.env already exists")
    
    print("\n✅ Setup complete!")


def discover_india_companies(
    cities: List[str] = None,
    limit: int = 100,
    output_file: str = "leads/companies.json"
):
    """
    Discover companies in Indian cities.
    
    Args:
        cities: Cities to target (default: Hyderabad, Bangalore, Pune)
        limit: Number of companies to discover
        output_file: Where to save results
    """
    if cities is None:
        cities = ["Hyderabad", "Bangalore", "Pune"]
    
    print(f"\n🔍 Discovering {limit} companies in {', '.join(cities)}...")
    
    try:
        from india_discovery import discover_companies_in_india, prepare_india_discovery_report
        
        # Discover companies
        companies = discover_companies_in_india(cities=cities, limit=limit)
        
        if not companies:
            print("⚠️  No companies found")
            return []
        
        print(f"✅ Found {len(companies)} companies")
        
        # Save results
        with open(output_file, "w") as f:
            json.dump(companies, f, indent=2)
        print(f"💾 Saved to {output_file}")
        
        # Generate report
        report = prepare_india_discovery_report(companies)
        print("\n📊 Discovery Report:")
        print(f"  • Total companies: {report['total_companies']}")
        print(f"  • By city:")
        for city, count in report['by_city'].items():
            print(f"    - {city}: {count}")
        print(f"  • By state:")
        for state, count in report['by_state'].items():
            print(f"    - {state}: {count}")
        print(f"  • Verified emails: {report['working_email_count']}")
        print(f"  • Remote companies: {report['remote_companies']}")
        
        # Show top companies
        if report['top_companies']:
            print("\n🏆 Top Companies:")
            for i, company in enumerate(report['top_companies'][:5], 1):
                print(f"  {i}. {company['name']} ({company['city']}) - Score: {company['score']}")
        
        return companies
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("Make sure all required packages are installed: pip install -r requirements.txt")
        return []


def verify_company_emails(
    company: Dict,
    domain: str = None,
    min_quality: int = 70
):
    """
    Verify working emails for a company.
    
    Args:
        company: Company dictionary
        domain: Company domain
        min_quality: Minimum quality score (0-100)
    """
    try:
        from india_discovery import enrich_with_working_emails
        
        company_name = company.get("company_name", "Unknown")
        print(f"\n📧 Verifying emails for {company_name}...")
        
        enriched = enrich_with_working_emails(company, domain, min_quality)
        
        working = enriched.get("verified_emails", [])
        if working:
            print(f"✅ Found {len(working)} verified emails:")
            for email in working:
                quality = email.get("quality_score", 0)
                print(f"  • {email['email']} (Quality: {quality}%)")
        else:
            print("⚠️  No verified emails found")
        
        return enriched
    
    except Exception as e:
        print(f"❌ Error verifying emails: {str(e)}")
        return company


def filter_telangana(companies: List[Dict]) -> List[Dict]:
    """Filter for Telangana (Hyderabad) companies."""
    try:
        from india_discovery import prioritize_by_telangana
        
        print(f"\n🎯 Filtering for Telangana companies...")
        telangana = [c for c in companies if c.get("target_state") == "Telangana"]
        print(f"✅ Found {len(telangana)} companies in Telangana")
        
        return telangana
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return []


def score_companies(companies: List[Dict]) -> List[Dict]:
    """Score and sort companies by India-specific metrics."""
    try:
        from india_discovery import score_india_company
        
        print(f"\n🏅 Scoring {len(companies)} companies...")
        
        # Add scores
        for company in companies:
            company["india_score"] = score_india_company(company)
        
        # Sort by score
        sorted_companies = sorted(companies, key=lambda x: x.get("india_score", 0), reverse=True)
        
        print(f"✅ Top 5 companies by score:")
        for i, company in enumerate(sorted_companies[:5], 1):
            score = company.get("india_score", 0)
            city = company.get("target_city", "Unknown")
            print(f"  {i}. {company['company_name']} ({city}) - Score: {score}")
        
        return sorted_companies
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return companies


def main():
    """Main workflow."""
    print("""
╔════════════════════════════════════════════════════════════════╗
║   India Company Discovery Pipeline - Quick Start              ║
║   Discovering software companies in Telangana, Karnataka      ║
║   and Maharashtra with verified contact information           ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    # Step 1: Setup
    setup()
    
    # Step 2: Discover companies
    print("\n" + "="*60)
    print("STEP 1: Discover Companies")
    print("="*60)
    
    companies = discover_india_companies(
        cities=["Hyderabad", "Bangalore", "Pune"],
        limit=50  # Start small for testing
    )
    
    if not companies:
        print("❌ No companies discovered. Check API keys and try again.")
        return
    
    # Step 3: Filter for Telangana
    print("\n" + "="*60)
    print("STEP 2: Focus on Telangana/Hyderabad")
    print("="*60)
    
    telangana_companies = filter_telangana(companies)
    
    # Step 4: Score companies
    print("\n" + "="*60)
    print("STEP 3: Score Companies")
    print("="*60)
    
    scored = score_companies(telangana_companies[:10])
    
    # Step 5: Verify emails for top companies
    print("\n" + "="*60)
    print("STEP 4: Verify Working Emails")
    print("="*60)
    
    if scored:
        top_company = scored[0]
        verify_company_emails(top_company)
    
    # Final summary
    print("\n" + "="*60)
    print("✅ DISCOVERY COMPLETE")
    print("="*60)
    print(f"\n📊 Summary:")
    print(f"  • Discovered: {len(companies)} companies")
    print(f"  • Telangana focus: {len(telangana_companies)} companies")
    print(f"  • Results saved to: leads/companies.json")
    print(f"\n💡 Next steps:")
    print(f"  1. Review leads/companies.json for full details")
    print(f"  2. Verify emails for priority companies")
    print(f"  3. Export to CRM or sales system")
    print(f"  4. Scale up by increasing --limit parameter")
    print("")


if __name__ == "__main__":
    main()
