"""
Main pipeline orchestrator for company discovery and contact intelligence.
"""

import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
from datetime import datetime

from models import Company, JobPosting, PublicEmail, SeniorContact, DiscoveryResult, PipelineStats
from utils import (
    logger, Cache, retry_on_failure, setup_logger,
    normalize_email, deduplicate_emails
)
from config import (
    COMPANIES_CACHE_FILE, CONTACTS_CACHE_FILE, EMAILS_CACHE_FILE,
    TARGET_ROLES, BATCH_SIZE, MAX_COMPANY_PROCESSING_TIME,
    COMPANIES_OUTPUT_FILE, EMAILS_OUTPUT_FILE
)
from company_discovery import discover_hiring_companies, search_related_companies
from company_info import (
    resolve_company_domain, get_company_info, find_linkedin_company_profile,
    find_careers_page, collect_public_emails_from_domain
)
from contact_discovery import (
    find_senior_contacts, find_recruiting_team, search_engineering_leadership
)
from email_patterns import analyze_email_patterns, generate_email_candidates
from scoring import calculate_company_score
from exporters import export_companies_json, export_emails_txt, export_summary


class DiscoveryPipeline:
    """Main orchestrator for company discovery pipeline"""
    
    def __init__(self):
        self.companies_cache = Cache(COMPANIES_CACHE_FILE)
        self.contacts_cache = Cache(CONTACTS_CACHE_FILE)
        self.emails_cache = Cache(EMAILS_CACHE_FILE)
        self.stats = PipelineStats()
    
    def discover_and_process_companies(
        self,
        country: str = "USA",
        roles: List[str] = None,
        limit: int = 100,
        parallel: bool = True
    ) -> List[Company]:
        """
        Main discovery pipeline.
        
        Args:
            country: Target country
            roles: List of target roles (defaults to TARGET_ROLES)
            limit: Maximum companies to discover
            parallel: Whether to use parallel processing
        
        Returns:
            List of discovered and enriched Company objects
        """
        if roles is None:
            roles = TARGET_ROLES
        
        logger.info("=" * 70)
        logger.info("STARTING COMPANY DISCOVERY & CONTACT INTELLIGENCE PIPELINE")
        logger.info("=" * 70)
        start_time = time.time()
        
        # Step 1: Discover hiring companies
        logger.info(f"\n[STEP 1] Discovering companies hiring for: {', '.join(roles[:3])}...")
        hiring_companies = discover_hiring_companies(roles, country, limit)
        
        if not hiring_companies:
            logger.error("No companies found. Exiting.")
            return []
        
        logger.info(f"✓ Found {len(hiring_companies)} companies actively hiring")
        self.stats.total_companies_discovered = len(hiring_companies)
        
        # Step 2: Process companies (sequential or parallel)
        logger.info(f"\n[STEP 2] Processing companies...")
        if parallel:
            companies = self._process_companies_parallel(hiring_companies, country)
        else:
            companies = self._process_companies_sequential(hiring_companies, country)
        
        # Calculate final statistics
        self.stats.companies_with_contacts = len([c for c in companies if c.contacts])
        self.stats.companies_with_emails = len([c for c in companies if c.public_emails])
        self.stats.duration = time.time() - start_time
        
        logger.info(f"\n✓ Processing complete")
        logger.info(f"  - Companies with contacts: {self.stats.companies_with_contacts}")
        logger.info(f"  - Companies with emails: {self.stats.companies_with_emails}")
        logger.info(f"  - Total duration: {self.stats.duration:.1f} seconds")
        
        return companies
    
    def _process_companies_sequential(self, companies: List[dict], country: str) -> List[Company]:
        """Process companies one at a time"""
        processed = []
        
        for idx, company_info in enumerate(companies, 1):
            logger.info(f"\n[{idx}/{len(companies)}] Processing: {company_info['company_name']}")
            
            start = time.time()
            company = self.process_single_company(company_info, country)
            duration = time.time() - start
            
            if company:
                processed.append(company)
                logger.info(f"  ✓ Score: {company.score}, Contacts: {len(company.contacts)}")
            
            logger.debug(f"  Processing time: {duration:.1f}s")
        
        return processed
    
    def _process_companies_parallel(self, companies: List[dict], country: str) -> List[Company]:
        """Process companies in parallel batches"""
        processed = []
        
        with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
            futures = {
                executor.submit(self.process_single_company, company, country): company
                for company in companies[:self.batch_size]  # Limit batch
            }
            
            completed = 0
            for future in as_completed(futures):
                try:
                    company = future.result()
                    if company:
                        processed.append(company)
                        completed += 1
                        logger.info(f"✓ [{completed}] {company.company_name}: Score {company.score}")
                except Exception as e:
                    logger.error(f"Error processing company: {e}")
        
        return processed
    
    def process_single_company(self, company_info: dict, country: str) -> Company:
        """
        Process a single company through the full discovery pipeline.
        
        Args:
            company_info: Company discovery data
            country: Country
        
        Returns:
            Enriched Company object
        """
        start_time = time.time()
        company_name = company_info.get("company_name", "")
        domain = company_info.get("domain")
        
        try:
            # Create company object
            company = Company(company_name=company_name)
            
            # Step 1: Resolve domain if needed
            if not domain:
                domain = resolve_company_domain(company_name, country)
            
            if not domain:
                logger.warning(f"Could not resolve domain for {company_name}")
                return None
            
            company.website = f"https://{domain}" if domain else None
            company.source_urls.append(company_info.get("job_url", ""))
            
            # Step 2: Get company info
            info = get_company_info(company_name, domain, country)
            company.industry = info.get("industry")
            company.company_size = info.get("company_size")
            company.location = info.get("location", country)
            
            # Step 3: Get LinkedIn profile
            linkedin = find_linkedin_company_profile(company_name)
            company.linkedin_url = linkedin
            
            # Step 4: Find careers page
            careers_page = find_careers_page(domain)
            if careers_page:
                company.source_urls.append(careers_page)
            
            # Step 5: Collect public emails
            public_emails = collect_public_emails_from_domain(domain, company_name)
            company.public_emails = [
                PublicEmail(
                    email=e["email"],
                    category=e["category"],
                    source_url=e["source"],
                    confidence_score=e["confidence_score"]
                )
                for e in public_emails
            ]
            
            # Step 6: Add job postings
            hiring_roles = company_info.get("hiring_roles", [])
            if company_info.get("job_url"):
                company.jobs = [
                    JobPosting(
                        title=role,
                        url=company_info.get("job_url"),
                        role_matched=role
                    )
                    for role in hiring_roles
                ]
            
            # Step 7: Find senior contacts
            senior_contacts = find_senior_contacts(company_name, domain, country)
            recruiting_team = find_recruiting_team(company_name, domain)
            engineering_leads = search_engineering_leadership(company_name)
            
            # Combine and deduplicate contacts
            all_contacts = senior_contacts + recruiting_team + engineering_leads
            seen_names = set()
            
            for contact in all_contacts:
                name = contact.get("name", "").lower()
                if name not in seen_names:
                    seen_names.add(name)
                    company.contacts.append(SeniorContact(
                        name=contact.get("name"),
                        role=contact.get("role", "Contact"),
                        public_profile_url=contact.get("linkedin_url"),
                        role_score=contact.get("role_score", 50)
                    ))
            
            # Step 8: Analyze email patterns
            patterns = analyze_email_patterns(domain, company_name)
            from models import EmailPattern
            company.email_patterns = [
                EmailPattern(
                    pattern=p["pattern"],
                    examples=p.get("examples", []),
                    confidence_score=p["confidence_score"],
                    source_url=domain
                )
                for p in patterns
            ]
            
            # Step 9: Calculate score
            company.score = calculate_company_score(company)
            company.last_updated = datetime.utcnow().isoformat()
            
            processing_time = time.time() - start_time
            if processing_time > MAX_COMPANY_PROCESSING_TIME:
                logger.warning(f"Processing took {processing_time:.1f}s (limit: {MAX_COMPANY_PROCESSING_TIME}s)")
            
            return company
        
        except Exception as e:
            logger.error(f"Error processing {company_name}: {e}")
            return None
    
    def export_results(self, companies: List[Company]) -> bool:
        """
        Export discovered companies to output files.
        
        Args:
            companies: List of companies to export
        
        Returns:
            True if successful
        """
        logger.info("\n[EXPORT] Exporting results...")
        
        # Export JSON
        success_json = export_companies_json(companies, COMPANIES_OUTPUT_FILE)
        
        # Export TXT
        success_txt = export_emails_txt(companies, EMAILS_OUTPUT_FILE)
        
        # Print summary
        summary = export_summary(companies)
        
        logger.info("\n" + "=" * 70)
        logger.info("PIPELINE SUMMARY")
        logger.info("=" * 70)
        for key, value in summary.items():
            logger.info(f"{key}: {value}")
        logger.info("=" * 70)
        
        return success_json and success_txt
