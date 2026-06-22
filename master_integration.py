"""
Master integration - Combines all data collection sources for complete company intelligence.
India-focused discovery + Legal LinkedIn data + Email verification = Complete profiles.
"""

import json
import time
import os
from typing import List, Dict, Optional
from datetime import datetime
from utils import logger

# Import all modules
from india_discovery import discover_companies_in_india, prepare_india_discovery_report
from linkedin_jobs import search_linkedin_jobs_by_role, analyze_job_market_trends
from linkedin_recruiters import find_hiring_managers_by_company, find_recruiters_by_role
from linkedin_emails import compile_company_email_profile
from linkedin_analysis import integrate_linkedin_data, create_outreach_list
from email_verification import filter_working_emails


class CompanyIntelligenceSystem:
    """
    Master system for gathering complete company intelligence.
    Integrates: India discovery + LinkedIn data + Email verification
    """
    
    def __init__(self):
        """Initialize the system."""
        self.companies = []
        self.linkedin_data = {}
        self.email_data = {}
        self.final_profiles = []
        
        # Create output directory
        os.makedirs("linkedin_data", exist_ok=True)
        
        logger.info("🚀 Company Intelligence System Initialized")
    
    def phase_1_discover_companies(
        self,
        cities: List[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Phase 1: Discover companies in India.
        
        Args:
            cities: Target cities
            limit: Max companies to discover
        
        Returns:
            List of discovered companies
        """
        if cities is None:
            cities = ["Hyderabad", "Bangalore", "Pune"]
        
        logger.info(f"📍 PHASE 1: Discovering companies in {', '.join(cities)}...")
        
        companies = discover_companies_in_india(cities=cities, limit=limit)
        self.companies = companies
        
        logger.info(f"✅ Found {len(companies)} companies")
        return companies
    
    def phase_2_linkedin_intelligence(self) -> Dict:
        """
        Phase 2: Gather LinkedIn intelligence for each company.
        
        Returns:
            LinkedIn data dictionary
        """
        logger.info(f"🔗 PHASE 2: Gathering LinkedIn intelligence...")
        
        linkedin_data = {}
        
        for i, company in enumerate(self.companies, 1):
            name = company.get("company_name")
            domain = company.get("domain")
            
            if not name:
                continue
            
            logger.info(f"  [{i}/{len(self.companies)}] {name}...", end=" ", flush=True)
            
            try:
                intel = integrate_linkedin_data(name, domain)
                linkedin_data[name] = intel
                logger.info("✅")
            except Exception as e:
                logger.info(f"⚠️ ({str(e)})")
            
            time.sleep(0.5)  # Rate limiting
        
        self.linkedin_data = linkedin_data
        logger.info(f"✅ Gathered LinkedIn data for {len(linkedin_data)} companies")
        
        return linkedin_data
    
    def phase_3_extract_emails(self) -> Dict:
        """
        Phase 3: Extract and verify company emails.
        
        Returns:
            Email data dictionary
        """
        logger.info(f"📧 PHASE 3: Extracting and verifying emails...")
        
        email_data = {}
        
        for i, company in enumerate(self.companies, 1):
            name = company.get("company_name")
            domain = company.get("domain")
            
            if not name:
                continue
            
            logger.info(f"  [{i}/{len(self.companies)}] {name}...", end=" ", flush=True)
            
            try:
                profile = compile_company_email_profile(name, domain)
                
                # Verify emails
                if domain and profile.get("all_unique_emails"):
                    working = filter_working_emails(
                        profile["all_unique_emails"],
                        domain,
                        min_quality=70
                    )
                    profile["verified_working_emails"] = working
                
                email_data[name] = profile
                logger.info(f"✅ {len(profile['all_unique_emails'])} emails")
            except Exception as e:
                logger.info(f"⚠️ ({str(e)})")
            
            time.sleep(0.5)
        
        self.email_data = email_data
        logger.info(f"✅ Extracted emails for {len(email_data)} companies")
        
        return email_data
    
    def phase_4_compile_profiles(self) -> List[Dict]:
        """
        Phase 4: Compile complete company profiles.
        
        Returns:
            List of complete company profiles
        """
        logger.info(f"📋 PHASE 4: Compiling complete profiles...")
        
        profiles = []
        
        for company in self.companies:
            name = company.get("company_name")
            if not name:
                continue
            
            profile = {
                "company_name": name,
                "target_city": company.get("target_city"),
                "target_state": company.get("target_state"),
                "domain": company.get("domain"),
                "source": company.get("source"),
                
                # India discovery data
                "india_discovery": {
                    "priority": company.get("priority"),
                    "funding_stage": company.get("funding_stage"),
                    "employee_count": company.get("employee_count"),
                    "industry": company.get("industry"),
                },
                
                # LinkedIn data
                "linkedin_data": self.linkedin_data.get(name, {}),
                
                # Email data
                "email_data": self.email_data.get(name, {}),
                
                # Compiled timestamp
                "profile_compiled": datetime.now().isoformat(),
            }
            
            profiles.append(profile)
        
        self.final_profiles = profiles
        logger.info(f"✅ Compiled {len(profiles)} complete profiles")
        
        return profiles
    
    def phase_5_generate_outreach_list(self) -> Dict:
        """
        Phase 5: Generate prioritized outreach list.
        
        Returns:
            Outreach list
        """
        logger.info(f"🎯 PHASE 5: Generating outreach list...")
        
        outreach = create_outreach_list(self.companies)
        
        logger.info(f"✅ Generated outreach list with {len(outreach['contacts'])} companies")
        
        return outreach
    
    def export_all_data(self, output_dir: str = "linkedin_data") -> Dict:
        """
        Export all collected data to files.
        
        Args:
            output_dir: Output directory
        
        Returns:
            Export status dictionary
        """
        logger.info(f"💾 Exporting all data to {output_dir}...")
        
        os.makedirs(output_dir, exist_ok=True)
        
        status = {
            "export_date": datetime.now().isoformat(),
            "output_directory": output_dir,
            "files_exported": []
        }
        
        # Export companies
        try:
            with open(f"{output_dir}/discovered_companies.json", "w") as f:
                json.dump(self.companies, f, indent=2)
            status["files_exported"].append("discovered_companies.json")
            logger.info("  ✅ discovered_companies.json")
        except Exception as e:
            logger.warning(f"  ⚠️ Error exporting companies: {str(e)}")
        
        # Export LinkedIn data
        try:
            with open(f"{output_dir}/linkedin_intelligence.json", "w") as f:
                json.dump(self.linkedin_data, f, indent=2, default=str)
            status["files_exported"].append("linkedin_intelligence.json")
            logger.info("  ✅ linkedin_intelligence.json")
        except Exception as e:
            logger.warning(f"  ⚠️ Error exporting LinkedIn data: {str(e)}")
        
        # Export email data
        try:
            with open(f"{output_dir}/company_emails.json", "w") as f:
                json.dump(self.email_data, f, indent=2, default=str)
            status["files_exported"].append("company_emails.json")
            logger.info("  ✅ company_emails.json")
        except Exception as e:
            logger.warning(f"  ⚠️ Error exporting email data: {str(e)}")
        
        # Export complete profiles
        try:
            with open(f"{output_dir}/complete_profiles.json", "w") as f:
                json.dump(self.final_profiles, f, indent=2, default=str)
            status["files_exported"].append("complete_profiles.json")
            logger.info("  ✅ complete_profiles.json")
        except Exception as e:
            logger.warning(f"  ⚠️ Error exporting profiles: {str(e)}")
        
        # Export summary report
        try:
            summary = {
                "total_companies": len(self.companies),
                "total_linkedin_profiles": len(self.linkedin_data),
                "total_email_profiles": len(self.email_data),
                "export_date": datetime.now().isoformat(),
                "files": status["files_exported"]
            }
            
            with open(f"{output_dir}/export_summary.json", "w") as f:
                json.dump(summary, f, indent=2)
            status["files_exported"].append("export_summary.json")
            logger.info("  ✅ export_summary.json")
        except Exception as e:
            logger.warning(f"  ⚠️ Error exporting summary: {str(e)}")
        
        logger.info(f"✅ Exported {len(status['files_exported'])} files")
        
        return status
    
    def run_complete_discovery(
        self,
        cities: List[str] = None,
        company_limit: int = 50
    ) -> Dict:
        """
        Run complete discovery pipeline.
        
        Args:
            cities: Target cities
            company_limit: Max companies
        
        Returns:
            Complete results dictionary
        """
        logger.info("""
╔════════════════════════════════════════════════════════════════╗
║  Complete Company Intelligence System                          ║
║  India Discovery + LinkedIn Intelligence + Email Verification ║
╚════════════════════════════════════════════════════════════════╝
        """)
        
        results = {
            "start_time": datetime.now().isoformat(),
            "phases": {}
        }
        
        # Phase 1
        logger.info("\n" + "="*60)
        results["phases"]["discovery"] = self.phase_1_discover_companies(cities, company_limit)
        
        # Phase 2
        logger.info("\n" + "="*60)
        results["phases"]["linkedin"] = self.phase_2_linkedin_intelligence()
        
        # Phase 3
        logger.info("\n" + "="*60)
        results["phases"]["emails"] = self.phase_3_extract_emails()
        
        # Phase 4
        logger.info("\n" + "="*60)
        results["phases"]["profiles"] = self.phase_4_compile_profiles()
        
        # Phase 5
        logger.info("\n" + "="*60)
        results["phases"]["outreach"] = self.phase_5_generate_outreach_list()
        
        # Export
        logger.info("\n" + "="*60)
        results["export"] = self.export_all_data()
        
        results["end_time"] = datetime.now().isoformat()
        
        return results
    
    def get_summary(self) -> Dict:
        """Get summary of collected data."""
        return {
            "companies_discovered": len(self.companies),
            "linkedin_profiles": len(self.linkedin_data),
            "companies_with_emails": len(self.email_data),
            "total_emails_extracted": sum(
                len(e.get("all_unique_emails", []))
                for e in self.email_data.values()
            ),
            "open_positions_found": sum(
                l.get("hiring_activity", {}).get("open_positions", 0)
                for l in self.linkedin_data.values()
            ),
            "recruiters_found": sum(
                len(l.get("team_intelligence", {}).get("hiring_managers", []))
                for l in self.linkedin_data.values()
            ),
        }


def main():
    """Main execution."""
    
    # Create system
    system = CompanyIntelligenceSystem()
    
    # Run complete discovery
    results = system.run_complete_discovery(
        cities=["Hyderabad", "Bangalore", "Pune"],
        company_limit=50  # Start with 50 for testing
    )
    
    # Print summary
    logger.info("\n" + "="*60)
    logger.info("✅ DISCOVERY COMPLETE")
    logger.info("="*60)
    
    summary = system.get_summary()
    
    print(f"""
📊 Final Summary:
   • Companies Discovered: {summary['companies_discovered']}
   • LinkedIn Profiles: {summary['linkedin_profiles']}
   • Companies with Emails: {summary['companies_with_emails']}
   • Total Emails Extracted: {summary['total_emails_extracted']}
   • Open Positions Found: {summary['open_positions_found']}
   • Recruiters Identified: {summary['recruiters_found']}

📂 Output Files:
   • linkedin_data/discovered_companies.json
   • linkedin_data/linkedin_intelligence.json
   • linkedin_data/company_emails.json
   • linkedin_data/complete_profiles.json
   • linkedin_data/export_summary.json

🎯 Next Steps:
   1. Review complete_profiles.json for full details
   2. Use company_emails.json for outreach
   3. Reference linkedin_intelligence.json for hiring info
   4. Export to CRM or sales system
   5. Start targeted outreach campaigns
    """)


if __name__ == "__main__":
    main()
