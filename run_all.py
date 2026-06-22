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
import smtplib
import socket
import dns.resolver
import string
import random
from datetime import datetime
from utils.utils import serper_search, llm_query, logger
from modules.models import Company, PublicEmail
from modules.config import ROLE_SCORES
import os
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION SECTION - EDIT THESE VARIABLES
# ═══════════════════════════════════════════════════════════════════════════════

# SEARCH QUERIES (for discovery mode - edit these to change searches)
SEARCH_QUERIES = [
"apxor"
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

# ─────────────────────────────────────────────────────────────────────────────
# SMTP EMAIL VERIFICATION
# ─────────────────────────────────────────────────────────────────────────────

MX_CACHE = {}
DOMAINS_FAILED = set()

def get_mx_records(domain: str) -> list:
    """Get MX records for domain."""
    domain = domain.lower().strip()
    
    if domain in MX_CACHE:
        return MX_CACHE[domain]
    
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        hosts = sorted([str(r.exchange).rstrip('.').lower() for r in mx_records], 
                       key=lambda r: r.preference if hasattr(r, 'preference') else 0)
        MX_CACHE[domain] = hosts
        return hosts
    except Exception as e:
        logger.debug(f"MX lookup failed for {domain}: {e}")
        MX_CACHE[domain] = []
        return []

def verify_email_smtp(email: str, domain: str, mx_hosts: list = None) -> tuple:
    """Verify email via SMTP (returns: status, score, notes)."""
    
    if not mx_hosts:
        mx_hosts = get_mx_records(domain)
    
    if not mx_hosts or domain in DOMAINS_FAILED:
        return "Unknown", 30, "No MX records or domain unreachable"
    
    try:
        for mx in mx_hosts[:2]:
            try:
                with smtplib.SMTP(mx, 25, timeout=5) as smtp:
                    smtp.helo("deepta.ai")
                    smtp.mail("verify@deepta.ai")
                    code, msg = smtp.rcpt(email)
                    
                    if code in (250, 251, 252):
                        return "Valid", 95, f"SMTP verification successful"
                    elif code >= 500:
                        return "Invalid", 10, f"SMTP hard reject (code {code})"
                    else:
                        return "Unknown", 35, f"SMTP soft reject (code {code})"
            except socket.timeout:
                continue
            except Exception as e:
                logger.debug(f"SMTP error on {mx}: {e}")
                continue
        
        DOMAINS_FAILED.add(domain)
        return "Unknown", 30, "All MX connections failed"
        
    except Exception as e:
        logger.debug(f"Email verification error: {e}")
        return "Unknown", 30, str(e)[:50]

# ─────────────────────────────────────────────────────────────────────────────
# LLM-POWERED EMPLOYEE EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

def extract_employees_with_llm(company_name: str, search_results: list) -> list:
    """Use LLM to intelligently extract real employees from search results."""
    
    if not search_results:
        return []
    
    try:
        # Prepare search results for LLM
        snippets = "\n".join([
            f"- Title: {r.get('title', '')}\n  Link: {r.get('link', '')}\n  Snippet: {r.get('snippet', '')[:150]}"
            for r in search_results[:10]
        ])
        
        prompt = f"""Extract REAL employees and decision makers from '{company_name}' based on these search results.
For each legitimate person, extract:
- 'name': Full name
- 'role': Job title/role
- 'linkedin_url': LinkedIn profile URL (if found)

Focus on: Founders, CEOs, CTOs, VP Engineering, Engineering Managers, HR Managers, Recruiters.
Return ONLY a JSON array. Do not add markdown formatting or extra text.

Search results:
{snippets}"""
        
        response = llm_query(prompt, max_tokens=800)
        
        # Parse JSON response
        if not response:
            return []
        
        # Clean markdown
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        
        employees = json.loads(response.strip())
        
        if isinstance(employees, list):
            # Deduplicate by name
            seen = set()
            result = []
            for emp in employees:
                if isinstance(emp, dict) and "name" in emp:
                    name = emp.get("name", "").strip()
                    if name and name.lower() not in seen:
                        seen.add(name.lower())
                        result.append(emp)
            return result[:25]
        
        return []
        
    except json.JSONDecodeError as e:
        logger.debug(f"Failed to parse LLM response: {e}")
        return []
    except Exception as e:
        logger.error(f"LLM employee extraction error: {e}")
        return []

def extract_verified_company_emails(company_name: str, domain: str) -> list:
    """Extract VERIFIED company emails from public sources."""
    
    verified_emails = []
    sources = {}
    
    if not domain:
        return []
    
    try:
        # Source 1: Careers page - simpler query
        try:
            search_query = f"{domain} careers email contact"
            results = serper_search(search_query, num=5)
            
            if results:
                for result in results:
                    snippet = result.get("snippet", "")
                    emails = re.findall(r'[\w\.-]+@' + re.escape(domain), snippet)
                    for email in emails:
                        if email not in verified_emails:
                            verified_emails.append(email)
                            sources[email] = "careers_page"
        except Exception as e:
            logger.debug(f"Careers search failed: {e}")
        
        time.sleep(0.2)
        
        # Source 2: Contact page
        try:
            search_query = f"{domain} contact email"
            results = serper_search(search_query, num=5)
            
            if results:
                for result in results:
                    snippet = result.get("snippet", "")
                    emails = re.findall(r'[\w\.-]+@' + re.escape(domain), snippet)
                    for email in emails:
                        if email not in verified_emails:
                            verified_emails.append(email)
                            sources[email] = "contact_page"
        except Exception as e:
            logger.debug(f"Contact search failed: {e}")
        
        time.sleep(0.2)
        
        # Source 3: Job postings
        try:
            search_query = f"{clean_company_name(company_name)} hiring jobs email"
            results = serper_search(search_query, num=8)
            
            if results:
                for result in results:
                    snippet = result.get("snippet", "")
                    emails = re.findall(r'[\w\.-]+@' + re.escape(domain), snippet)
                    for email in emails:
                        if email not in verified_emails:
                            verified_emails.append(email)
                            sources[email] = "job_posting"
        except Exception as e:
            logger.debug(f"Job search failed: {e}")
        
        time.sleep(0.2)
        
        # Return with source info
        return [{"email": e, "source": sources.get(e, "company_domain"), "verified": True} for e in verified_emails[:5]]
        
    except Exception as e:
        logger.error(f"Error extracting verified emails: {e}")
        return []


def extract_email_format_pattern(verified_emails: list) -> str:
    """Analyze verified emails to determine company email format pattern."""
    
    if not verified_emails:
        return None
    
    # Extract patterns from verified emails
    patterns = {}
    
    for email_obj in verified_emails:
        email = email_obj.get("email", "")
        if "@" not in email:
            continue
        
        local_part = email.split("@")[0]
        
        # Analyze patterns
        if "." in local_part:
            if len(local_part.split(".")) == 2:
                patterns["firstname.lastname"] = patterns.get("firstname.lastname", 0) + 1
        
        if "_" in local_part:
            patterns["firstname_lastname"] = patterns.get("firstname_lastname", 0) + 1
        
        if not any(c in local_part for c in [".", "_"]):
            patterns["firstnamelastname"] = patterns.get("firstnamelastname", 0) + 1
        
        if local_part.count(local_part[0]) == len(local_part) - 1:  # first initial + last name
            patterns["f_lastname"] = patterns.get("f_lastname", 0) + 1
    
    # Return most common pattern
    if patterns:
        return max(patterns, key=patterns.get)
    
    return None


def extract_employees_from_multiple_sources(company_name: str, domain: str) -> list:
    """Extract REAL employees - directly from LinkedIn profiles."""
    
    clean_name = clean_company_name(company_name)
    
    if not clean_name:
        return []
    
    try:
        logger.info(f"[LINKEDIN] Fetching REAL employee data for: {clean_name}")
        
        all_employees = []
        all_results = []
        
        # Search queries - avoid site: operators (they cause 400 errors)
        search_queries = [
            f'{clean_name} linkedin founder CEO',
            f'{clean_name} linkedin employee profile',
            f'{clean_name} linkedin team members',
            f'{clean_name} linkedin engineering CTO',
            f'{clean_name} linkedin HR recruiter',
            f'{clean_name} linkedin product manager',
            f'{clean_name} linkedin designer developer',
        ]
        
        # Collect all search results
        for query in search_queries:
            try:
                logger.debug(f"  Searching: {query}")
                results = serper_search(query, num=12)
                
                if results:
                    all_results.extend(results)
                    logger.debug(f"    [+] Got {len(results)} results")
                
                time.sleep(0.4)
                
            except Exception as e:
                logger.debug(f"    [!] Error: {str(e)[:60]}")
                continue
        
        logger.info(f"  Total search results: {len(all_results)}")
        
        # Parse LinkedIn profiles from search results
        seen_names = set()
        for result in all_results:
            if not isinstance(result, dict):
                continue
            
            link = result.get("link", "")
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            
            # Must be LinkedIn profile
            if "linkedin.com/in/" not in link.lower():
                continue
            
            # Verify company mentioned
            if clean_name.lower() not in (snippet.lower() + title.lower()):
                continue
            
            # Extract REAL name from LinkedIn URL (most reliable source)
            # URL format: https://linkedin.com/in/firstname-lastname or https://linkedin.com/in/firstname-lastname-[id]
            # LinkedIn ID is usually a long alphanumeric sequence (8+ chars) or 5+ digit number
            url_match = re.search(r'linkedin\.com/in/([a-z0-9\-]+)', link.lower())
            if not url_match:
                continue
            
            url_slug = url_match.group(1).strip('-')
            
            # Remove LinkedIn ID patterns from the end
            # ID patterns: -12345 (5+ digits), -abcd1234efgh (8+ alphanumeric), etc.
            url_slug = re.sub(r'-[a-z0-9]{8,}$', '', url_slug)  # Remove 8+ char ID
            url_slug = re.sub(r'-\d{5,}$', '', url_slug)  # Remove 5+ digit ID
            url_slug = re.sub(r'-\d{3,}$', '', url_slug)  # Remove 3+ digit ID (additional cleanup)
            
            # Convert hyphens to spaces and title case
            name_from_url = url_slug.replace('-', ' ').title()
            
            # Validate name from URL
            if not name_from_url or len(name_from_url) < 5 or name_from_url.count(" ") < 1:
                continue
            
            if name_from_url.lower() in seen_names:
                continue
            
            # Extract role from search title/snippet (not used for name, only for context)
            role = None
            if "|" in title:
                parts = title.split("|")
                role = parts[1].strip() if len(parts) > 1 else None
            
            # Clean role - remove "at Company", LinkedIn, and job titles with "hr" or "manager"
            if role:
                # Remove company mentions
                role = re.sub(rf'\bat\s+{re.escape(clean_name)}.*', '', role, flags=re.IGNORECASE).strip()
                role = re.sub(r'\s+\|.*', '', role).strip()
                role = re.sub(r'\s+linkedin.*', '', role, flags=re.IGNORECASE).strip()
                # Remove excessive role info
                role = role[:60].strip()
            
            if not role or len(role) < 2:
                # Extract role from snippet if not in title
                role_match = re.search(r'(?:is|works as|role:)\s+([^,\.]+)', snippet, re.IGNORECASE)
                if role_match:
                    role = role_match.group(1).strip()[:60]
                else:
                    role = "Employee"
            
            seen_names.add(name_from_url.lower())
            all_employees.append({
                "name": name_from_url,
                "role": role,
                "linkedin_url": link,
                "source": "LinkedIn",
                "verified": True,
                "company": clean_name
            })
            
            logger.debug(f"    [+] {name_from_url} - {role}")
        
        if all_employees:
            logger.info(f"[OK] Found {len(all_employees)} REAL LinkedIn employees")
        else:
            logger.warning(f"[WARN] No LinkedIn employees found")
        
        return all_employees[:25]
        
    except Exception as e:
        logger.error(f"Error extracting employees: {e}")
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
    print(f"\n[OK] Found {len(companies_list)} NEW Indian startups (added to existing)\n")
    
    return companies_list


def extract_domain_from_url(url):
    """Extract domain from URL."""
    try:
        url = url.replace("https://", "").replace("http://", "").replace("www.", "")
        domain = url.split("/")[0].split("?")[0]
        return domain
    except:
        return ""


def clean_company_name(name):
    """Extract clean company name from title (remove descriptions, special chars)."""
    # Remove common patterns like "| description", "- description", ": description"
    name = re.split(r'[\|:\-]', name)[0].strip()
    
    # Remove common descriptors
    descriptors = [
        "reviews", "pricing", "features", "company profile", "team",
        "careers", "jobs", "hiring", "details", "information",
        "application", "platform", "software", "service", "product"
    ]
    
    for desc in descriptors:
        if name.lower().endswith(desc):
            name = name[:-len(desc)].strip()
    
    # Remove special characters but keep spaces and hyphens
    name = re.sub(r'[^a-zA-Z0-9\s\-]', '', name)
    
    # Remove extra spaces
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name if len(name) > 2 else ""


def split_name(fullname: str) -> tuple:
    """Split full name into first and last name, handling titles and special characters."""
    # Remove parentheses and their contents
    name = re.sub(r"\([^)]*\)", "", fullname)
    # Keep only word characters, spaces, and hyphens
    name = re.sub(r"[^\w\s-]", "", name)
    # Split into parts and lowercase
    parts = [p.strip().lower() for p in name.split() if p.strip()]
    
    # Remove titles
    titles = {"mr", "ms", "mrs", "dr", "prof", "eng", "mba", "phd"}
    parts = [p for p in parts if p not in titles]
    
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[-1]

def generate_email_candidates(fullname: str, domain: str, pattern: str = None) -> list:
    """Generate email candidates using ONLY the verified company email pattern."""
    first, last = split_name(fullname)
    if not first or not domain:
        return []
    
    domain = domain.lower()
    
    # If we have a verified pattern, use ONLY that pattern
    if pattern:
        if pattern == "firstname.lastname" and last:
            return [f"{first}.{last}@{domain}"]
        elif pattern == "firstname_lastname" and last:
            return [f"{first}_{last}@{domain}"]
        elif pattern == "firstnamelastname" and last:
            return [f"{first}{last}@{domain}"]
        elif pattern == "f_lastname" and last:
            return [f"{first[0]}{last}@{domain}"]
        elif pattern == "firstname":
            return [f"{first}@{domain}"]
        else:
            # Fallback
            if last:
                return [f"{first}.{last}@{domain}"]
            else:
                return [f"{first}@{domain}"]
    else:
        # No verified pattern - use all common patterns
        candidates = []
        if last:
            candidates = [
                f"{first}.{last}@{domain}",      # john.doe@domain.com
                f"{first}@{domain}",             # john@domain.com
                f"{first}{last}@{domain}",       # johndoe@domain.com
                f"{first[0]}{last}@{domain}",    # jdoe@domain.com
            ]
        else:
            candidates = [f"{first}@{domain}"]
        
        return candidates


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2: EXTRACT HR & FOUNDER EMAILS
# ─────────────────────────────────────────────────────────────────────────────

def extract_hr_founder_emails(companies):
    """Extract verified and inferred employee emails with clear source attribution."""
    
    print("[PHASE 2] Extracting VERIFIED emails + identifying employees...")
    print("="*70)
    
    email_raw = []
    
    for i, company in enumerate(companies, 1):
        try:
            # Clean company name for display and searches
            clean_name = clean_company_name(company["name"])
            display_name = (clean_name[:40] + "...") if len(clean_name) > 40 else clean_name
            
            website = company["website"]
            domain = extract_domain_from_url(website)
            
            print(f"  [{i:3d}/{len(companies)}] {display_name:43s}", end="", flush=True)
            
            if not domain:
                print(" [SKIP - no domain]")
                continue
            
            # Step 1: Extract VERIFIED company emails from public sources
            verified_emails = extract_verified_company_emails(clean_name, domain)
            
            # Step 2: Analyze email format pattern from verified emails
            email_format_pattern = extract_email_format_pattern(verified_emails)
            
            # Step 3: Extract REAL employees from multiple sources
            employees = extract_employees_from_multiple_sources(clean_name, domain)
            
            if not employees and not verified_emails:
                print(" [NO data found]")
                time.sleep(0.3)
                continue
            
            # Step 4: Add verified company emails
            for email_obj in verified_emails:
                email_raw.append({
                    "email": email_obj.get("email", ""),
                    "company": company["name"],
                    "website": website,
                    "domain": domain,
                    "role": "Company",
                    "type": "verified",
                    "source": email_obj.get("source", "unknown"),
                    "employee_name": None,
                    "employee_role": None
                })
            
            # Step 5: Generate emails for employees using VERIFIED PATTERN ONLY
            
            if employees and email_format_pattern:
                # Only generate emails if we have a verified pattern
                for employee in employees:
                    emp_name = employee.get("name", "")
                    emp_role = employee.get("role", "").lower()
                    emp_source = employee.get("source", "")
                    emp_url = employee.get("linkedin_url", "")
                    
                    if not emp_name:
                        continue
                    
                    # Generate ONLY ONE email using the verified pattern
                    candidates = generate_email_candidates(emp_name, domain, pattern=email_format_pattern)
                    
                    if not candidates:
                        continue
                    
                    # Get the primary email (first in list)
                    email_candidate = candidates[0]
                    
                    # Determine role category
                    if any(x in emp_role for x in ["founder", "ceo", "chief"]):
                        role_category = "Founder/CEO"
                    elif any(x in emp_role for x in ["hr", "recruit", "talent", "acquisition"]):
                        role_category = "HR"
                    elif any(x in emp_role for x in ["vp", "director", "manager", "engineer"]):
                        role_category = "Leadership/Engineering"
                    else:
                        role_category = "Employee"
                    
                    # Add SINGLE email per employee (using verified pattern)
                    email_raw.append({
                        "email": email_candidate,
                        "company": company["name"],
                        "website": website,
                        "domain": domain,
                        "role": role_category,
                        "type": "inferred_with_pattern",
                        "source": emp_source,
                        "employee_name": emp_name,
                        "employee_role": emp_role,
                        "pattern_type": email_format_pattern,
                        "employee_url": emp_url,
                        "pattern_confidence": "HIGH",
                        "linkedin_url": emp_url
                    })
            
            stats_str = f" [OK"
            if verified_emails:
                stats_str += f" - {len(verified_emails)} verified"
            if employees:
                stats_str += f", {len(employees)} employees"
            if email_format_pattern:
                stats_str += f", pattern:{email_format_pattern}"
            stats_str += "]"
            
            print(stats_str)
            time.sleep(0.3)
            
        except Exception as e:
            print(f" [ERROR: {str(e)[:30]}]")
            time.sleep(0.5)
    
    print(f"\n[OK] Extracted {len(email_raw)} total email records\n")
    
    return email_raw


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 3: SCORE EMAILS BY QUALITY
# ─────────────────────────────────────────────────────────────────────────────

def score_email_quality(email, role, email_type):
    """Score email quality (0-100) - weighted by source reliability."""
    
    # VERIFIED emails get highest base score
    if email_type == "verified":
        score = 95  # Verified emails are highest confidence
    # INFERRED from pattern get high score
    elif email_type == "inferred_with_pattern":
        score = 75  # Pattern-inferred emails are high confidence
    # GENERATED (random pattern) get medium score
    elif email_type == "generated":
        score = 50  # Generated patterns are lower confidence
    else:
        score = 50  # Default/found emails
    
    # Email pattern analysis
    local_part = email.split("@")[0].lower()
    domain = email.split("@")[1].lower() if "@" in email else ""
    
    # Old "found" emails get bonus
    if email_type == "found":
        score += 30
    
    # Role-specific patterns (only for non-verified)
    if email_type != "verified":
        if role == "HR":
            hr_keywords = ["hr", "hire", "recruit", "talent", "careers", "jobs"]
            for keyword in hr_keywords:
                if keyword in local_part:
                    score += 5
                    break
        elif role == "Founder/CEO":
            founder_keywords = ["founder", "ceo", "chief"]
            for keyword in founder_keywords:
                if keyword in local_part:
                    score += 5
                    break
    
    # Suspicious patterns (reduce score significantly)
    suspicious = ["noreply", "no-reply", "do-not-reply", "autodiscover", "test", "fake", "invalid"]
    for pattern in suspicious:
        if pattern in local_part:
            score -= 40
            break
    
    # Format validation
    if re.match(r'^[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email):
        if email_type != "verified":
            score += 5
    else:
        # Invalid format
        score -= 20
    
    # Domain quality (reduce for free email services, unless verified)
    if email_type != "verified":
        if domain.startswith("gmail") or domain.startswith("yahoo") or domain.startswith("hotmail"):
            score -= 10
    
    # Specific patterns (only for non-verified)
    if email_type != "verified" and local_part.count(".") <= 1:
        score += 3
    
    # Cap at 100
    score = min(100, max(0, score))
    
    return score



def score_and_rank_emails(emails):
    """Score and rank all emails - separate verified from inferred."""
    
    print("[PHASE 3] Scoring email quality...")
    print("="*70)
    
    scored = []
    
    for email_data in emails:
        score = score_email_quality(
            email_data["email"],
            email_data.get("role", ""),
            email_data.get("type", "generated")
        )
        
        scored.append({
            "email": email_data["email"],
            "company": email_data["company"],
            "website": email_data["website"],
            "role": email_data.get("role", ""),
            "type": email_data.get("type", "generated"),
            "source": email_data.get("source", ""),
            "employee_name": email_data.get("employee_name"),
            "employee_role": email_data.get("employee_role"),
            "pattern_type": email_data.get("pattern_type"),
            "pattern_confidence": email_data.get("pattern_confidence"),
            "score": score,
            "quality": "VERIFIED" if score >= 90 else "HIGH" if score >= 75 else "MEDIUM" if score >= 60 else "LOW"
        })
    
    # Sort by score descending
    scored = sorted(scored, key=lambda x: (-x["score"], x["type"]))
    
    verified = [e for e in scored if e["type"] == "verified"]
    inferred_pattern = [e for e in scored if e["type"] == "inferred_with_pattern"]
    generated = [e for e in scored if e["type"] == "generated"]
    found = [e for e in scored if e["type"] == "found"]
    
    high_quality = [e for e in scored if e["score"] >= 75]
    medium_quality = [e for e in scored if 60 <= e["score"] < 75]
    low_quality = [e for e in scored if e["score"] < 60]
    
    print(f"\nEMAIL SOURCE BREAKDOWN:")
    print(f"  Verified (from public sources):    {len(verified)}")
    print(f"  Inferred (from pattern analysis):  {len(inferred_pattern)}")
    print(f"  Generated (pattern-based):         {len(generated)}")
    print(f"  Found/Other:                       {len(found)}")
    
    print(f"\nQUALITY BREAKDOWN:")
    print(f"  High Quality (75-100):  {len(high_quality)} emails")
    print(f"  Medium Quality (60-74): {len(medium_quality)} emails")
    print(f"  Low Quality (0-59):     {len(low_quality)} emails")
    print(f"\n[OK] Scored {len(scored)} emails\n")
    
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
    
    print(f"\n[OK] Built {len(companies_models)} company models\n")
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
    
    print(f"  [OK] companies_{timestamp}.json ({len(companies_models)} companies)")
    
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
    """Export scored emails to versioned TXT file with clear source attribution."""
    
    # Create timestamped filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    output_file = os.path.join(OUTPUT_DIR, f"emails_scored_{timestamp}.txt")
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("="*90 + "\n")
        f.write("HR & FOUNDER EMAIL LEADS - REAL EMPLOYEES + VERIFIED SOURCES\n")
        f.write("="*90 + "\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Total Emails: {len(emails_scored)}\n")
        f.write("="*90 + "\n\n")
        
        # Categorize by type
        verified = [e for e in emails_scored if e.get("type") == "verified"]
        inferred = [e for e in emails_scored if e.get("type") == "inferred_with_pattern"]
        generated = [e for e in emails_scored if e.get("type") == "generated"]
        
        # VERIFIED EMAILS - Highest priority
        if verified:
            f.write("="*90 + "\n")
            f.write(f"[VERIFIED] EMAILS FROM PUBLIC SOURCES ({len(verified)} emails)\n")
            f.write("Real company emails found on careers pages, contact pages, job postings\n")
            f.write("="*90 + "\n")
            
            for email_data in sorted(verified, key=lambda x: -x["score"]):
                f.write(f"\n  Email:          {email_data['email']}\n")
                f.write(f"  Company:        {email_data['company']}\n")
                f.write(f"  Source:         {email_data.get('source', 'unknown')}\n")
                f.write(f"  Score:          {email_data['score']}/100 ({email_data['quality']})\n")
                f.write(f"  Website:        {email_data['website']}\n")
        
        # INFERRED FROM PATTERN - Medium-High priority
        if inferred:
            f.write("\n\n" + "="*90 + "\n")
            f.write(f"[INFERRED FROM PATTERN] EMAILS FROM REAL EMPLOYEES ({len(inferred)} emails)\n")
            f.write("Real employees found on LinkedIn/public sources + inferred from verified email format\n")
            f.write("="*90 + "\n")
            
            for email_data in sorted(inferred, key=lambda x: -x["score"]):
                f.write(f"\n  Email:          {email_data['email']}\n")
                f.write(f"  Employee:       {email_data.get('employee_name', 'N/A')}\n")
                f.write(f"  Role:           {email_data.get('employee_role', 'N/A')}\n")
                f.write(f"  Company:        {email_data['company']}\n")
                f.write(f"  Pattern Used:   {email_data.get('pattern_type', 'N/A')}\n")
                f.write(f"  Confidence:     {email_data.get('pattern_confidence', 'N/A')}\n")
                f.write(f"  Score:          {email_data['score']}/100 ({email_data['quality']})\n")
                f.write(f"  Website:        {email_data['website']}\n")
        
        # GENERATED - Lowest priority
        if generated:
            f.write("\n\n" + "="*90 + "\n")
            f.write(f"[GENERATED] PATTERN-BASED EMAILS ({len(generated)} emails)\n")
            f.write("Real employees found but NO verified email format pattern available\n")
            f.write("="*90 + "\n")
            
            for email_data in sorted(generated, key=lambda x: -x["score"]):
                f.write(f"\n  Email:          {email_data['email']}\n")
                f.write(f"  Employee:       {email_data.get('employee_name', 'N/A')}\n")
                f.write(f"  Role:           {email_data.get('employee_role', 'N/A')}\n")
                f.write(f"  Company:        {email_data['company']}\n")
                f.write(f"  Score:          {email_data['score']}/100 ({email_data['quality']})\n")
                f.write(f"  Website:        {email_data['website']}\n")
        
        f.write("\n\n" + "="*90 + "\n")
        f.write(f"SUMMARY\n")
        f.write(f"  Verified (Public):     {len(verified)}\n")
        f.write(f"  Inferred (Pattern):    {len(inferred)}\n")
        f.write(f"  Generated (Estimate):  {len(generated)}\n")
        f.write(f"  TOTAL:                 {len(emails_scored)}\n")
        f.write("="*90 + "\n")
    
    print(f"  [OK] emails_scored_{timestamp}.txt ({len(emails_scored)} total emails)")
    
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
            
            for email_data in sorted(new_emails, key=lambda x: -x["score"]):
                email_type = email_data.get("type", "unknown").upper()
                f.write(f"[{email_type}] {email_data['email']} | {email_data['company']} | Score: {email_data['score']}/100 | {email_data['quality']}\n")

    
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
    
    print(f"\n[MODE] Running in {mode.upper()} mode")
    
    if mode == "enrichment":
        print(f"[INPUT] Using CSV: {ENRICHMENT_CSV_PATH}")
        print("[NOTICE] SEARCH_QUERIES disabled (using input CSV instead)\n")
    else:
        print(f"[SEARCH] Using queries: {SEARCH_QUERIES}\n")
    
    # Load existing data for deduplication
    existing_companies = load_existing_companies()
    existing_emails = load_existing_emails()
    
    # Phase 1: Get companies
    if mode == "enrichment":
        print("[PHASE 1] Loading companies from CSV input...")
        print("="*70)
        companies = load_csv_companies(ENRICHMENT_CSV_PATH)
        
        if not companies:
            print("\nNo companies loaded from CSV. Exiting.\n")
            return
        
        print(f"[OK] Loaded {len(companies)} companies from {ENRICHMENT_CSV_PATH}\n")
        
    else:  # discovery mode
        print("[PHASE 1] Discovering Indian Startups...")
        print("="*70)
        # Discover startups (skip existing ones)
        companies = discover_companies_unified(existing_companies)
        
        if not companies:
            print("\nNo startups found. Please try again.\n")
            return
    
    # Phase 2: Extract HR & Founder emails
    print("[PHASE 2] Extracting VERIFIED emails + identifying employees...")
    print("="*70)
    emails_raw = extract_hr_founder_emails(companies)
    
    # Phase 3: Score emails
    print("[PHASE 3] Scoring email quality...")
    print("="*70)
    emails_scored = score_and_rank_emails(emails_raw)
    
    # Phase 4: Build models
    print("[PHASE 4] Building company models...")
    print("="*70)
    companies_models = build_company_models(companies, emails_scored)
    
    # Phase 5: Export
    print("[PHASE 5] Exporting data...")
    print("="*70)
    companies_versioned, companies_master = export_companies_json(companies_models)
    emails_versioned, emails_master = export_emails_txt(emails_scored)
    
    # Summary
    print("\n" + "="*70)
    print("[OK] EXECUTION COMPLETE")
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
