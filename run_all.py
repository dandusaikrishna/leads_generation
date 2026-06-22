"""
UNIFIED LEADS RUNNER - STARTUP FOCUS
Focuses on Indian Startups (NOT MNCs)
Extracts HR and Founder emails
Features:
  - Deduplication: Skips companies already discovered
  - Versioned Output: Creates new dated files each run
  - Incremental: Builds on previous discoveries
  - LinkedIn Integration: Fetches company profiles
  - Flexible Input: CSV or search queries
"""

import json
import time
import re
import csv
from datetime import datetime
from utils.utils import serper_search, logger
from modules.models import Company, PublicEmail
from modules.config import ROLE_SCORES
import os
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION SECTION - EDIT THESE VARIABLES
# ═══════════════════════════════════════════════════════════════════════════════

# SEARCH QUERIES (for discovery mode - edit these to change searches)
SEARCH_QUERIES = [
    "Indian software startups Hyderabad hiring",
    "tech startup companies Bangalore engineers",
    "SaaS startup Pune India recruiting",
    "AI startup India hiring developers",
    "fintech startup India Hyderabad engineers",
    "blockchain startup India developers",
    "edtech startup India hiring",
    "health tech startup India recruiting",
]

# INPUT FILE OPTIONS
ENRICHMENT_CSV_PATH = "input_companies.csv"  # If exists, uses enrichment mode (name, website)
ENABLE_LINKEDIN_SEARCH = True  # Search LinkedIn for company profiles
ENABLE_LINKEDIN_SCRAPING = True  # Extract company emails from LinkedIn
LINKEDIN_API_TYPE = "serper"  # Options: "serper", "google", "custom"

# OUTPUT SETTINGS
STARTUP_DISCOVERY_LIMIT = 50  # Max new startups to discover per run
EMAILS_PER_COMPANY = 10  # Target emails per company
INCLUDE_ARCHIVED_JOBS = False  # Include archived job postings

# ═══════════════════════════════════════════════════════════════════════════════
# END CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Create output folder
OUTPUT_DIR = os.path.join(os.getcwd(), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# DETECT OPERATING MODE
# ─────────────────────────────────────────────────────────────────────────────

def detect_mode():
    """Detect if running in enrichment mode (CSV input) or discovery mode (searches)."""
    if os.path.exists(ENRICHMENT_CSV_PATH):
        return "enrichment"
    return "discovery"

def load_csv_companies(csv_path):
    """Load companies from CSV file (columns: Company Name, Website)."""
    companies = []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Company Name") and row.get("Website"):
                    companies.append({
                        "name": row["Company Name"],
                        "website": row["Website"],
                        "source": "csv_input",
                        "discovered": datetime.now().isoformat()
                    })
        logger.info(f"Loaded {len(companies)} companies from {csv_path}")
        return companies
    except Exception as e:
        logger.error(f"Error loading CSV: {e}")
        return []

# ─────────────────────────────────────────────────────────────────────────────
# LOAD EXISTING DATA FOR DEDUPLICATION
# ─────────────────────────────────────────────────────────────────────────────

def load_existing_companies():
    """Load existing companies to avoid duplicates."""
    existing = set()
    base_file = os.path.join(OUTPUT_DIR, "companies.json")
    
    if os.path.exists(base_file):
        try:
            with open(base_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for company in data:
                    existing.add(company.get("company_name", "").lower())
            print(f"[DEDUP] Loaded {len(existing)} existing companies")
        except:
            pass
    
    return existing

def load_existing_emails():
    """Load existing emails to avoid duplicates."""
    existing = set()
    base_file = os.path.join(OUTPUT_DIR, "emails_scored.txt")
    
    if os.path.exists(base_file):
        try:
            with open(base_file, "r", encoding="utf-8") as f:
                for line in f:
                    if "@" in line:
                        email = line.split()[0].strip()
                        if "@" in email:
                            existing.add(email.lower())
        except:
            pass
    
    return existing

# Common HR and founder names to generate patterns
HR_TITLES = ["HR", "HR Manager", "Recruiter", "Talent Acquisition", "People Operations", "Head of HR"]
FOUNDER_TITLES = ["Founder", "CEO", "Co-founder", "Chief Executive Officer"]
COMMON_NAMES = {
    "hr": ["priya", "rajesh", "amit", "neha", "arun", "anjali", "vikram", "pooja", "rahul", "shreya"],
    "founder": ["shah", "patel", "kumar", "singh", "gupta", "sharma", "verma", "chopra", "reddy", "nair"],
}

# MNCs to exclude - filter for startups only
MNC_KEYWORDS = [
    "microsoft", "google", "amazon", "apple", "facebook", "uber", "netflix",
    "ibm", "accenture", "deloitte", "tcs", "infosys", "wipro", "cognizant", "capgemini",
    "ey", "pwc", "kpmg", "linkedin", "salesforce", "oracle", "cisco", "adobe",
    "vmware", "dell", "hp", "lenovo", "intel", "qualcomm", "nvidia", "amd",
    "mckinsey", "bcg", "bain", "goldman", "jpmorgan", "morgan", 
    "flipkart", "myntra", "ebay", "aliexpress", "shopify",
    "ola", "lyft", "zomato", "swiggy", "delivery",
    "airbnb", "booking", "expedia", "makemytrip", "goibibo",

]

def is_startup(company_name):
    """Check if company is likely a startup, not an MNC."""
    name_lower = company_name.lower()
    
    # If contains MNC keywords, it's not a startup
    for mnc in MNC_KEYWORDS:
        if mnc in name_lower:
            return False
    
    # Startups typically have shorter names
    if len(company_name) > 60:
        return False
    
    return True

# ─────────────────────────────────────────────────────────────────────────────
# LINKEDIN PROFILE SEARCH
# ─────────────────────────────────────────────────────────────────────────────

def search_linkedin_company(company_name):
    """Search for LinkedIn company profile and get details."""
    if not ENABLE_LINKEDIN_SEARCH:
        return None
    
    try:
        search_query = f"LinkedIn {company_name} company profile"
        results = serper_search(search_query, num=3)
        
        if results and isinstance(results, list):
            for result in results:
                if isinstance(result, dict):
                    link = result.get("link", "")
                    if "linkedin.com/company" in link:
                        return {
                            "linkedin_url": link,
                            "title": result.get("title", ""),
                            "snippet": result.get("snippet", "")
                        }
        
        time.sleep(0.3)
        return None
        
    except Exception as e:
        logger.error(f"Error searching LinkedIn for {company_name}: {e}")
        return None

def extract_linkedin_emails(company_name, linkedin_url):
    """Extract email addresses mentioned on LinkedIn company page."""
    if not ENABLE_LINKEDIN_SCRAPING or not linkedin_url:
        return []
    
    try:
        search_query = f"site:linkedin.com/company/{company_name.lower().replace(' ', '-')} email contact"
        results = serper_search(search_query, num=3)
        
        emails = []
        if results and isinstance(results, list):
            for result in results:
                if isinstance(result, dict):
                    snippet = result.get("snippet", "")
                    found = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', snippet)
                    emails.extend(found)
        
        time.sleep(0.3)
        return list(set(emails))
        
    except Exception as e:
        logger.error(f"Error extracting LinkedIn emails: {e}")
        return []

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1: DISCOVER STARTUPS (NOT MNCs)
# ─────────────────────────────────────────────────────────────────────────────

def discover_companies_unified(existing_companies):
    """Discover STARTUP companies using direct searches, skip existing ones."""
    
    print("\n[PHASE 1] Discovering Indian Startups...")
    print("="*70)
    print(f"Skipping {len(existing_companies)} already discovered companies\n")
    
    companies_raw = []
    
    # Use configurable search queries
    searches = SEARCH_QUERIES
    
    for i, search_query in enumerate(searches, 1):
        try:
            print(f"  [{i:2d}/{len(searches)}] Searching: {search_query[:48]}...", end="", flush=True)
            
            results = serper_search(search_query, num=10)
            
            if results and isinstance(results, list):
                for result in results[:8]:
                    if isinstance(result, dict):
                        url = result.get("link", "")
                        title = result.get("title", "")
                        
                        # Filter: must be a startup, not an MNC or job listing page
                        if url and len(title) > 5 and is_startup(title):
                            # Exclude job listing pages
                            if not any(x in url.lower() for x in ["linkedin", "indeed", "naukri", "glassdoor", "careercup"]):
                                # SKIP if already exists
                                if title.lower() not in existing_companies:
                                    companies_raw.append({
                                        "name": title[:80],
                                        "website": url,
                                        "source": search_query,
                                        "discovered": datetime.now().isoformat()
                                    })
                
                print(f" [OK]")
            else:
                print(" [SKIP]")
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f" [ERROR]")
            time.sleep(1)
    
    # Deduplicate by website and filter startups
    unique = {}
    for c in companies_raw:
        key = c["website"].lower()
        if key not in unique and is_startup(c["name"]):
            unique[key] = c
    
    companies_list = list(unique.values())[:STARTUP_DISCOVERY_LIMIT]
    print(f"\n✓ Found {len(companies_list)} NEW Indian startups (added to existing)\n")
    
    return companies_list


def extract_domain_from_url(url):
    """Extract domain from URL."""
    try:
        url = url.replace("https://", "").replace("http://", "").replace("www.", "")
        domain = url.split("/")[0].split("?")[0]
        return domain
    except:
        return ""


def generate_email_patterns(domain, role_type="hr"):
    """Generate email patterns for HR or Founders."""
    
    emails = []
    
    if not domain:
        return emails
    
    domain_name = domain.split(".")[0]
    
    if role_type == "hr":
        names = COMMON_NAMES["hr"]
        for fname in names[:3]:
            emails.append(f"{fname}.hr@{domain}")
            emails.append(f"hr.{fname}@{domain}")
            emails.append(f"{fname}@{domain}")
    else:  # founder
        surnames = COMMON_NAMES["founder"]
        for surname in surnames[:3]:
            emails.append(f"founder.{surname}@{domain}")
            emails.append(f"{surname}@{domain}")
    
    if role_type == "hr":
        emails.extend([
            f"hr@{domain}",
            f"hire@{domain}",
            f"recruitment@{domain}",
            f"careers@{domain}",
            f"talent@{domain}",
            f"hiring@{domain}",
            f"jobs@{domain}",
        ])
    else:  # founder
        emails.extend([
            f"founder@{domain}",
            f"ceo@{domain}",
            f"contact@{domain}",
        ])
    
    return emails


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2: EXTRACT HR & FOUNDER EMAILS
# ─────────────────────────────────────────────────────────────────────────────

def extract_hr_founder_emails(companies):
    """Extract HR and Founder emails, or generate if not found."""
    
    print("[PHASE 2] Extracting HR & Founder emails (+ LinkedIn)...")
    print("="*70)
    
    email_raw = []
    
    for i, company in enumerate(companies, 1):
        try:
            name = company["name"][:40]
            website = company["website"]
            domain = extract_domain_from_url(website)
            
            print(f"  [{i:3d}/{len(companies)}] {name:40s}", end="", flush=True)
            
            found_emails = {}
            linkedin_data = None
            
            # Search for LinkedIn profile
            if ENABLE_LINKEDIN_SEARCH:
                linkedin_data = search_linkedin_company(company["name"])
            
            # Search for HR emails
            search_hr = f"{company['name']} HR recruitment careers email"
            results = serper_search(search_hr, num=5)
            
            hr_emails = []
            if results and isinstance(results, list):
                for result in results[:3]:
                    if isinstance(result, dict):
                        snippet = result.get("snippet", "")
                        found = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', snippet)
                        hr_emails.extend(found)
            
            hr_emails = list(set(hr_emails))
            
            if hr_emails:
                found_emails["hr"] = hr_emails
            
            time.sleep(0.2)
            
            # Search for Founder emails
            search_founder = f"{company['name']} founder CEO contact email"
            results = serper_search(search_founder, num=5)
            
            founder_emails = []
            if results and isinstance(results, list):
                for result in results[:3]:
                    if isinstance(result, dict):
                        snippet = result.get("snippet", "")
                        found = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', snippet)
                        founder_emails.extend(found)
            
            founder_emails = list(set(founder_emails))
            
            if founder_emails:
                found_emails["founder"] = founder_emails
            
            time.sleep(0.2)
            
            # Extract LinkedIn company page emails if available
            linkedin_emails = []
            if linkedin_data and ENABLE_LINKEDIN_SCRAPING:
                linkedin_emails = extract_linkedin_emails(company["name"], linkedin_data.get("linkedin_url"))
            
            # If no emails found, generate patterns
            if not hr_emails:
                hr_emails = generate_email_patterns(domain, "hr")
            
            if not founder_emails:
                founder_emails = generate_email_patterns(domain, "founder")
            
            # Merge and limit to EMAILS_PER_COMPANY
            all_emails = []
            
            # Add HR emails
            for email in hr_emails[:int(EMAILS_PER_COMPANY/2)]:
                all_emails.append({
                    "email": email,
                    "company": company["name"],
                    "website": website,
                    "domain": domain,
                    "role": "HR",
                    "type": "found" if email in found_emails.get("hr", []) else "generated",
                    "linkedin_url": linkedin_data.get("linkedin_url") if linkedin_data else None
                })
            
            # Add Founder emails
            for email in founder_emails[:int(EMAILS_PER_COMPANY/2)]:
                all_emails.append({
                    "email": email,
                    "company": company["name"],
                    "website": website,
                    "domain": domain,
                    "role": "Founder/CEO",
                    "type": "found" if email in found_emails.get("founder", []) else "generated",
                    "linkedin_url": linkedin_data.get("linkedin_url") if linkedin_data else None
                })
            
            # Add LinkedIn emails
            for email in linkedin_emails[:2]:
                all_emails.append({
                    "email": email,
                    "company": company["name"],
                    "website": website,
                    "domain": domain,
                    "role": "LinkedIn",
                    "type": "found",
                    "linkedin_url": linkedin_data.get("linkedin_url") if linkedin_data else None
                })
            
            email_raw.extend(all_emails)
            
            found_count = len(found_emails.get("hr", [])) + len(found_emails.get("founder", []))
            gen_count = len(hr_emails) + len(founder_emails) - found_count
            linkedin_count = len(linkedin_emails)
            
            status = f" [OK"
            if found_count > 0:
                status += f" - {found_count} found"
            if gen_count > 0:
                status += f", {gen_count} gen"
            if linkedin_count > 0:
                status += f", {linkedin_count} LinkedIn"
            status += "]"
            
            print(status)
            
        except Exception as e:
            print(f" [ERROR]")
            time.sleep(0.5)
    
    print(f"\n✓ Extracted {len(email_raw)} HR/Founder/LinkedIn email addresses\n")
    
    return email_raw


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 3: SCORE EMAILS BY QUALITY
# ─────────────────────────────────────────────────────────────────────────────

def score_email_quality(email, role, email_type):
    """Score email quality (0-100)."""
    
    score = 50  # Base score
    
    # Email pattern analysis
    local_part = email.split("@")[0].lower()
    domain = email.split("@")[1].lower() if "@" in email else ""
    
    # Found emails get bonus
    if email_type == "found":
        score += 30
    
    # Role-specific patterns
    if role == "HR":
        hr_keywords = ["hr", "hire", "recruit", "talent", "careers", "jobs"]
        for keyword in hr_keywords:
            if keyword in local_part:
                score += 15
                break
    elif role == "Founder/CEO":
        founder_keywords = ["founder", "ceo", "chief"]
        for keyword in founder_keywords:
            if keyword in local_part:
                score += 15
                break
    
    # Suspicious patterns (reduce score)
    suspicious = ["noreply", "no-reply", "do-not-reply", "autodiscover", "test"]
    for pattern in suspicious:
        if pattern in local_part:
            score -= 20
            break
    
    # Format validation
    if re.match(r'^[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email):
        score += 10
    
    # Domain quality
    if domain.startswith("gmail") or domain.startswith("yahoo") or domain.startswith("hotmail"):
        score -= 10
    
    # Specific patterns
    if local_part.count(".") <= 1:
        score += 5
    
    # Cap at 100
    score = min(100, max(0, score))
    
    return score


def score_and_rank_emails(emails):
    """Score and rank all emails."""
    
    print("[PHASE 3] Scoring email quality...")
    print("="*70)
    
    scored = []
    
    for email_data in emails:
        score = score_email_quality(
            email_data["email"],
            email_data["role"],
            email_data["type"]
        )
        
        scored.append({
            "email": email_data["email"],
            "company": email_data["company"],
            "website": email_data["website"],
            "role": email_data["role"],
            "type": email_data["type"],
            "score": score,
            "quality": "HIGH" if score >= 75 else "MEDIUM" if score >= 60 else "LOW"
        })
    
    # Sort by score descending
    scored = sorted(scored, key=lambda x: (-x["score"], x["type"]))
    
    high_quality = [e for e in scored if e["score"] >= 75]
    medium_quality = [e for e in scored if 60 <= e["score"] < 75]
    low_quality = [e for e in scored if e["score"] < 60]
    found = [e for e in scored if e["type"] == "found"]
    generated = [e for e in scored if e["type"] == "generated"]
    
    print(f"\n  Found Emails:         {len(found)}")
    print(f"  Generated Patterns:   {len(generated)}")
    print(f"  High Quality (75-100):  {len(high_quality)} emails")
    print(f"  Medium Quality (60-74): {len(medium_quality)} emails")
    print(f"  Low Quality (0-59):     {len(low_quality)} emails")
    print(f"\n✓ Scored {len(scored)} emails\n")
    
    return scored


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 4: BUILD COMPANY MODELS
# ─────────────────────────────────────────────────────────────────────────────

def build_company_models(companies, emails_scored):
    """Build Company models with PublicEmail objects."""
    
    print("[PHASE 4] Building company data models...")
    print("="*70)
    
    companies_models = []
    
    for i, company in enumerate(companies, 1):
        try:
            # Find emails for this company
            company_emails = [e for e in emails_scored if e["company"] == company["name"]]
            
            # Create PublicEmail objects
            public_emails = [
                PublicEmail(
                    email=e["email"],
                    category=e["role"],
                    source_url=e["website"],
                    confidence_score=e["score"]
                )
                for e in company_emails
            ]
            
            # Create Company model
            company_model = Company(
                company_name=company["name"],
                website=company["website"],
                public_emails=public_emails
            )
            companies_models.append(company_model)
            
            if i % 5 == 0:
                print(f"  [{i}/{len(companies)}] Processed")
                
        except Exception as e:
            pass
    
    print(f"\n✓ Built {len(companies_models)} company models\n")
    return companies_models


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 5: EXPORT DATA
# ─────────────────────────────────────────────────────────────────────────────

def export_companies_json(companies_models):
    """Export companies to versioned JSON file."""
    
    # Create timestamped filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    output_file = os.path.join(OUTPUT_DIR, f"companies_{timestamp}.json")
    
    data = [company.to_dict() for company in companies_models]
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"  ✓ companies_{timestamp}.json ({len(companies_models)} companies)")
    
    # Also update master file
    master_file = os.path.join(OUTPUT_DIR, "companies.json")
    if os.path.exists(master_file):
        try:
            with open(master_file, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except:
            existing_data = []
    else:
        existing_data = []
    
    # Merge: add new companies, skip existing
    existing_names = {c.get("company_name", "").lower() for c in existing_data}
    for company in data:
        if company.get("company_name", "").lower() not in existing_names:
            existing_data.append(company)
    
    # Save merged master file
    with open(master_file, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)
    
    return output_file, master_file


def export_emails_txt(emails_scored):
    """Export scored emails to versioned TXT file."""
    
    # Create timestamped filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    output_file = os.path.join(OUTPUT_DIR, f"emails_scored_{timestamp}.txt")
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("="*90 + "\n")
        f.write("HR & FOUNDER EMAIL LEADS - INDIAN STARTUPS (NEW)\n")
        f.write("="*90 + "\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Total New Emails: {len(emails_scored)}\n")
        f.write("="*90 + "\n\n")
        
        # Summary by quality
        high = [e for e in emails_scored if e["score"] >= 75]
        medium = [e for e in emails_scored if 60 <= e["score"] < 75]
        found = [e for e in emails_scored if e["type"] == "found"]
        generated = [e for e in emails_scored if e["type"] == "generated"]
        
        f.write(f"HIGH QUALITY EMAILS ({len(high)} total)\n")
        f.write(f"Found: {len([e for e in high if e['type'] == 'found'])} | Generated: {len([e for e in high if e['type'] == 'generated'])}\n")
        f.write("-"*90 + "\n")
        
        for email_data in high:
            type_badge = "[FOUND]" if email_data["type"] == "found" else "[GENERATED]"
            f.write(f"\n{type_badge} {email_data['role']}\n")
            f.write(f"  Email:    {email_data['email']}\n")
            f.write(f"  Company:  {email_data['company']}\n")
            f.write(f"  Website:  {email_data['website']}\n")
            f.write(f"  Score:    {email_data['score']}/100 ({email_data['quality']})\n")
        
        if medium:
            f.write(f"\n\n" + "="*90 + "\n")
            f.write(f"MEDIUM QUALITY EMAILS ({len(medium)} total)\n")
            f.write(f"Found: {len([e for e in medium if e['type'] == 'found'])} | Generated: {len([e for e in medium if e['type'] == 'generated'])}\n")
            f.write("-"*90 + "\n")
            
            for email_data in medium:
                type_badge = "[FOUND]" if email_data["type"] == "found" else "[GENERATED]"
                f.write(f"\n{type_badge} {email_data['role']}\n")
                f.write(f"  Email:    {email_data['email']}\n")
                f.write(f"  Company:  {email_data['company']}\n")
                f.write(f"  Website:  {email_data['website']}\n")
                f.write(f"  Score:    {email_data['score']}/100 ({email_data['quality']})\n")
    
    print(f"  ✓ emails_scored_{timestamp}.txt ({len(emails_scored)} new emails)")
    
    # Also append to master file
    master_file = os.path.join(OUTPUT_DIR, "emails_scored.txt")
    existing_emails = load_existing_emails()
    
    new_emails = [e for e in emails_scored if e["email"].lower() not in existing_emails]
    
    if new_emails:
        with open(master_file, "a", encoding="utf-8") as f:
            if os.path.getsize(master_file) > 100:
                f.write("\n" + "="*90 + "\n")
                f.write(f"BATCH UPDATE - {timestamp}\n")
                f.write("="*90 + "\n\n")
            
            for email_data in new_emails:
                type_badge = "[FOUND]" if email_data["type"] == "found" else "[GENERATED]"
                f.write(f"\n{type_badge} {email_data['role']}\n")
                f.write(f"  Email:    {email_data['email']}\n")
                f.write(f"  Company:  {email_data['company']}\n")
                f.write(f"  Website:  {email_data['website']}\n")
                f.write(f"  Score:    {email_data['score']}/100 ({email_data['quality']})\n")
    
    return output_file, master_file
    
    return output_file


# ─────────────────────────────────────────────────────────────────────────────
# MAIN EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

def main():
    """Main unified execution."""
    
    print("""
========================================================================
              STARTUP LEADS RUNNER - ADVANCED                
         HR & Founder Emails from Indian Startups Only                
========================================================================
    """)
    
    start_time = datetime.now()
    
    # Detect operating mode
    mode = detect_mode()
    print(f"\n[MODE] Running in {mode.upper()} mode\n")
    
    # Load existing data for deduplication
    existing_companies = load_existing_companies()
    existing_emails = load_existing_emails()
    
    # Phase 1: Get companies
    if mode == "enrichment":
        print("[PHASE 1] Loading companies from CSV...")
        print("="*70)
        companies = load_csv_companies(ENRICHMENT_CSV_PATH)
        
        if not companies:
            print("\nNo companies loaded from CSV. Exiting.\n")
            return
        
        print(f"✓ Loaded {len(companies)} companies\n")
        
    else:  # discovery mode
        # Discover startups (skip existing ones)
        companies = discover_companies_unified(existing_companies)
        
        if not companies:
            print("\nNo startups found. Please try again.\n")
            return
    
    # Phase 2: Extract HR & Founder emails
    emails_raw = extract_hr_founder_emails(companies)
    
    # Phase 3: Score emails
    emails_scored = score_and_rank_emails(emails_raw)
    
    # Phase 4: Build models
    companies_models = build_company_models(companies, emails_scored)
    
    # Phase 5: Export
    print("[PHASE 5] Exporting data...")
    print("="*70)
    companies_versioned, companies_master = export_companies_json(companies_models)
    emails_versioned, emails_master = export_emails_txt(emails_scored)
    
    # Summary
    print("\n" + "="*70)
    print("✓ EXECUTION COMPLETE")
    print("="*70)
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    found_emails = [e for e in emails_scored if e["type"] == "found"]
    generated_emails = [e for e in emails_scored if e["type"] == "generated"]
    high_quality = [e for e in emails_scored if e["score"] >= 75]
    hr_emails = [e for e in emails_scored if e["role"] == "HR"]
    founder_emails = [e for e in emails_scored if e["role"] == "Founder/CEO"]
    linkedin_emails = [e for e in emails_scored if e["role"] == "LinkedIn"]
    
    print(f"""
SUMMARY - INDIAN STARTUPS
========================================================================
  Mode:                      {mode.upper()}
  Companies Processed:       {len(companies):>3}
  Total Emails (Found+Gen):  {len(emails_scored):>3}
  Found from Web:            {len(found_emails):>3}
  Generated Patterns:        {len(generated_emails):>3}
  From LinkedIn:             {len(linkedin_emails):>3}
  High Quality Emails:       {len(high_quality):>3}
  Processing Time:           {elapsed:.1f}s

EMAIL BREAKDOWN
========================================================================
  HR Emails:                 {len(hr_emails):>3}
  Founder/CEO Emails:        {len(founder_emails):>3}
  LinkedIn Emails:           {len(linkedin_emails):>3}
  
  High Quality (75-100):     {len([e for e in emails_scored if e['score'] >= 75]):>3}
  Medium Quality (60-74):    {len([e for e in emails_scored if 60 <= e['score'] < 75]):>3}
  Low Quality (0-59):        {len([e for e in emails_scored if e['score'] < 60]):>3}

OUTPUT FILES
========================================================================
  Versioned companies:       {companies_versioned}
  Master companies:          {companies_master}
  Versioned emails:          {emails_versioned}
  Master emails:             {emails_master}

CONFIGURATION
========================================================================
  LinkedIn Search:           {str(ENABLE_LINKEDIN_SEARCH)}
  LinkedIn Scraping:         {str(ENABLE_LINKEDIN_SCRAPING)}
  Discovery Limit:           {STARTUP_DISCOVERY_LIMIT}
  Emails Per Company:        {EMAILS_PER_COMPANY}

Check ./output/ folder for detailed results.
    """)


if __name__ == "__main__":
    main()
