"""
CLI entry point for the job-company discovery and contact intelligence pipeline.
"""

import argparse
import sys
import json
import os
from typing import List

from utils import logger, setup_logger
from config import TARGET_ROLES, OUTPUT_DIR, CACHE_DIR
from pipeline import DiscoveryPipeline

# Ensure output directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)


def main():
    """Main CLI entry point"""
    
    parser = argparse.ArgumentParser(
        description="Job-Company Discovery & Contact Intelligence Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage - discover hiring companies in USA
  python leads.py --country "USA" --limit 50
  
  # Specify target roles
  python leads.py --country "USA" --roles "Software Engineer,Backend Engineer" --limit 100
  
  # Disable parallel processing
  python leads.py --country "USA" --sequential
  
  # Custom output paths
  python leads.py --country "USA" --output-json custom_companies.json --output-txt custom_emails.txt
        """
    )
    
    parser.add_argument(
        "--country",
        default="USA",
        help="Target country (e.g., USA, UK, India, etc.)"
    )
    
    parser.add_argument(
        "--roles",
        default=",".join(TARGET_ROLES[:5]),  # Default to first 5 roles
        help="Comma-separated target job roles"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of companies to discover (default: 50)"
    )
    
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Process companies sequentially instead of parallel"
    )
    
    parser.add_argument(
        "--output-json",
        default="leads/companies.json",
        help="Output path for companies.json"
    )
    
    parser.add_argument(
        "--output-txt",
        default="leads/emails.txt",
        help="Output path for emails.txt report"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    if args.debug:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    
    # Parse roles
    roles = [r.strip() for r in args.roles.split(",") if r.strip()]
    if not roles:
        logger.error("No valid roles specified")
        return 1
    
    logger.info(f"Starting discovery pipeline:")
    logger.info(f"  Country: {args.country}")
    logger.info(f"  Roles: {', '.join(roles)}")
    logger.info(f"  Limit: {args.limit}")
    logger.info(f"  Parallel: {not args.sequential}")
    logger.info(f"  Output JSON: {args.output_json}")
    logger.info(f"  Output TXT: {args.output_txt}")
    
    # Create pipeline
    pipeline = DiscoveryPipeline()
    
    # Run discovery
    try:
        companies = pipeline.discover_and_process_companies(
            country=args.country,
            roles=roles,
            limit=args.limit,
            parallel=not args.sequential
        )
        
        if not companies:
            logger.warning("No companies were discovered")
            return 1
        
        logger.info(f"\nDiscovered and enriched {len(companies)} companies")
        
        # Export results
        logger.info("\nExporting results...")
        
        # Update output paths
        from exporters import export_companies_json, export_emails_txt, export_summary
        
        export_companies_json(companies, args.output_json)
        export_emails_txt(companies, args.output_txt)
        summary = export_summary(companies)
        
        logger.info("\n" + "=" * 70)
        logger.info("PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("=" * 70)
        logger.info(f"Results saved to:")
        logger.info(f"  - {args.output_json}")
        logger.info(f"  - {args.output_txt}")
        logger.info("\nSummary:")
        for key, value in summary.items():
            key_formatted = key.replace("_", " ").title()
            logger.info(f"  {key_formatted}: {value}")
        
        return 0
    
    except KeyboardInterrupt:
        logger.warning("\nPipeline interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=args.debug)
        return 1


if __name__ == "__main__":
    sys.exit(main())
