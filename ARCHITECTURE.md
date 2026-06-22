# Project Architecture

## Overview

This is a production-ready, modular job-company discovery and contact intelligence pipeline built with:

- **Scalability**: Parallel processing, caching, checkpoints
- **Modularity**: Separate concerns for discovery, enrichment, scoring, export
- **Robustness**: Retry logic, error handling, detailed logging
- **Extensibility**: Easy to add new data sources or processors

## Directory Structure

```
leads/
├── config.py                 # Configuration, constants, roles, scoring rules
├── models.py                 # Data models (Company, Contact, Email, etc.)
├── utils.py                  # Utilities (HTTP, logging, caching, text processing)
├── company_discovery.py      # Company discovery from job boards
├── company_info.py           # Company information collection
├── contact_discovery.py      # Senior contact and decision maker discovery
├── email_patterns.py         # Email pattern analysis and prediction
├── scoring.py                # Scoring system and company ranking
├── pipeline.py               # Main orchestrator
├── exporters.py              # Output generation (JSON, TXT)
├── leads.py                  # New CLI entry point
├── leads_apxor.py            # Legacy API wrapper (backwards compatible)
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── README.md                 # Full documentation
├── QUICK_START.md            # Quick start guide
├── ARCHITECTURE.md           # This file
├── leads/                    # Output directory
│   ├── companies.json        # Complete company database
│   ├── emails.txt            # Human-readable report
│   └── hiring_leads.xlsx     # Excel report (legacy)
├── cache/                    # Caching directory
│   ├── companies_cache.json  # Company cache
│   ├── contacts_cache.json   # Contact cache
│   └── emails_cache.json     # Email cache
├── logs/                     # Log files
│   ├── leads_pipeline.log
│   ├── enrich_leads_hiring_legacy.log
│   └── ...
└── backend/
    └── .env                  # Environment variables (not in repo)
```

## Module Responsibilities

### config.py
Centralized configuration management:
- API keys and endpoints
- Target roles and scoring rules
- Email patterns and categories
- Rate limits and timeouts
- File paths
- Environment setup

```python
from config import TARGET_ROLES, ROLE_SCORES, SCORE_MODIFIERS
```

### models.py
Data structures with serialization:
- `Company`: Main data container
- `SeniorContact`: Decision maker information
- `PublicEmail`: Email with metadata
- `EmailPattern`: Pattern with confidence
- `JobPosting`: Job listing
- `DiscoveryResult`: Wrapper with metadata
- `PipelineStats`: Statistics container

Key methods:
- `.to_dict()`: Convert to JSON-serializable format
- `.from_dict()`: Deserialize from JSON

```python
from models import Company, SeniorContact, PublicEmail
```

### utils.py
Utility functions:
- **HTTP**: `serper_search()`, `llm_query()`, `requests.Session`
- **Logging**: `setup_logger()`, `logger` instance
- **Caching**: `Cache` class for persistent storage
- **Retry**: `@retry_on_failure` decorator
- **Text Processing**: URL/domain parsing, email validation, name splitting
- **Deduplication**: Company, email, contact deduplication

```python
from utils import serper_search, llm_query, Cache, setup_logger, logger
from utils import extract_domain, normalize_email, split_name
from utils import extract_emails_from_text, deduplicate_emails
```

### company_discovery.py
Finding companies actively hiring:

**Functions:**
- `discover_hiring_companies()`: Main discovery
  - Searches job boards using Serper
  - Uses LLM to extract company info
  - Deduplicates results
  - Returns up to N companies

- `search_related_companies()`: Find similar companies
  - Takes reference company and industry
  - Finds competitors/peers in same sector

```python
from company_discovery import discover_hiring_companies, search_related_companies

companies = discover_hiring_companies(
    roles=["Backend Engineer"],
    country="USA",
    limit=100
)
```

### company_info.py
Collecting company details:

**Functions:**
- `resolve_company_domain()`: Find official website
- `get_company_info()`: Collect industry, size, location
- `find_linkedin_company_profile()`: LinkedIn company URL
- `find_careers_page()`: Dedicated careers page
- `collect_public_emails_from_domain()`: Public company emails

```python
from company_info import (
    resolve_company_domain,
    get_company_info,
    find_linkedin_company_profile,
    find_careers_page,
    collect_public_emails_from_domain
)
```

### contact_discovery.py
Finding decision makers:

**Functions:**
- `find_senior_contacts()`: CTOs, VPs, directors, founders
- `find_recruiting_team()`: HR and recruiting staff
- `search_engineering_leadership()`: Engineering managers/leads

Uses LinkedIn search + LLM extraction.

```python
from contact_discovery import (
    find_senior_contacts,
    find_recruiting_team,
    search_engineering_leadership
)
```

### email_patterns.py
Email address pattern discovery:

**Functions:**
- `analyze_email_patterns()`: Extract patterns from public emails
- `generate_email_candidates()`: Create likely addresses for a person
- `predict_email_from_name()`: Predict most likely email using patterns

```python
from email_patterns import (
    analyze_email_patterns,
    generate_email_candidates,
    predict_email_from_name
)
```

### scoring.py
Weighted scoring system:

**Functions:**
- `calculate_company_score()`: Composite score (0-100)
  - Decision maker quality (0-35)
  - Public emails (0-20)
  - Email patterns (0-15)
  - Job postings (0-15)
  - Company info (0-15)

- `score_contact()`: Individual contact score
- `get_company_tier()`: Tier classification (Tier 1-6)
- `get_confidence_level()`: Confidence descriptor

```python
from scoring import calculate_company_score, get_company_tier
```

### pipeline.py
Main orchestrator:

**Class: DiscoveryPipeline**
- `discover_and_process_companies()`: Main entry point
  - Orchestrates full workflow
  - Sequential or parallel processing
  - Handles caching and resumption

- `process_single_company()`: Process one company through all steps
- `export_results()`: Save outputs

```python
from pipeline import DiscoveryPipeline

pipeline = DiscoveryPipeline()
companies = pipeline.discover_and_process_companies(
    country="USA",
    roles=["Backend Engineer"],
    limit=50,
    parallel=True
)
```

### exporters.py
Output generation:

**Functions:**
- `export_companies_json()`: Full JSON database
- `export_emails_txt()`: Human-readable report
- `export_summary()`: Statistics and summary

```python
from exporters import (
    export_companies_json,
    export_emails_txt,
    export_summary
)
```

### leads.py
CLI interface for new pipeline:

```bash
python leads.py --country "USA" --limit 50
python leads.py --help
```

### leads_apxor.py
Legacy wrapper maintaining backwards compatibility:

```bash
python leads_apxor.py --country "USA" --limit 50
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ INPUT: Target Roles & Country                                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │ Company Discovery                 │
        │ (serper_search + LLM)             │
        └────────────┬──────────────────────┘
                     │
                     ▼
        ┌───────────────────────────────────────────────┐
        │ Process Each Company (Sequential or Parallel) │
        └────────────┬──────────────────────────────────┘
                     │
        ┌────────────┴──────────────────────────────┐
        │                                           │
        ▼                                           ▼
    Resolve Domain                         Get Company Info
    (Domain → Website)                      (Industry, Size, Location)
        │                                           │
        ├─────────────┬──────────────────────────────┤
        │             │                              │
        ▼             ▼                              ▼
    LinkedIn       Careers Page          Collect Public Emails
    Company URL    (if available)        (from domain/careers page)
        │             │                              │
        └─────────────┼──────────────────────────────┘
                      │
                      ▼
          ┌──────────────────────────┐
          │ Find Contacts            │
          │ - Senior contacts        │
          │ - Recruiting team        │
          │ - Engineering leadership │
          └──────────┬───────────────┘
                     │
                     ├─────────────┐
                     │             │
                     ▼             ▼
              Analyze Email       Predict Emails
              Patterns           for Contacts
                     │             │
                     └──────┬──────┘
                            │
                            ▼
                    ┌───────────────────┐
                    │ Calculate Score   │
                    │ (Weighted system) │
                    └────────┬──────────┘
                             │
                             ▼
                    ┌───────────────────┐
                    │ Export Results    │
                    ├───────────────────┤
                    │ - companies.json  │
                    │ - emails.txt      │
                    │ - Summary stats   │
                    └───────────────────┘
```

## API Interactions

### Serper API (Google Search)
```
Query: "Backend Engineer jobs in USA"
Returns: Top search results with titles, URLs, snippets
```

### OpenRouter API (LLM)
```
Prompt: "Extract companies from these search results"
Model: meta-llama/llama-3.3-70b-instruct
Returns: JSON with company data
```

### LinkedIn Search
```
Via Serper: site:linkedin.com/in "Company" "CTO"
Returns: LinkedIn profiles matching query
```

## Caching Strategy

Three separate caches:

**companies_cache.json**
- Company discovery results
- Domain resolutions
- Company info

**contacts_cache.json**
- Senior contacts
- Recruiting teams
- Decision makers

**emails_cache.json**
- Public emails
- Email patterns
- Verified emails

## Error Handling

- Retry logic with exponential backoff
- Graceful degradation (skip on failure)
- Detailed error logging
- Continues processing on individual company failures

## Performance

- Parallel processing: ThreadPoolExecutor with batch_size=50
- Time limits per company: 20 seconds
- API rate limiting: Controlled delays
- Caching: Avoids redundant calls
- Resume capability: Saves progress to cache

## Extensibility

### Adding New Data Sources

1. Create new module: `new_source.py`
2. Implement discovery function
3. Return standardized data structure
4. Integrate into pipeline

### Adding New Scoring Factors

1. Edit `scoring.py`
2. Add new scoring function
3. Update `calculate_company_score()`
4. Adjust weights as needed

### Adding New Export Formats

1. Create export function in `exporters.py`
2. Accept `List[Company]` parameter
3. Format and save output
4. Add to `pipeline.py` export_results()

## Testing & Validation

1. **Small runs**: `--limit 10` for testing
2. **Sequential mode**: `--sequential` for debugging
3. **Debug logging**: `--debug` flag
4. **Check outputs**: Verify JSON and TXT files
5. **Sample validation**: Manually verify scores and data quality

## Production Deployment

1. Create proper `.env` file with real API keys
2. Set up log rotation for `logs/` directory
3. Configure cache backup strategy
4. Schedule periodic runs (e.g., daily)
5. Monitor API rate limits
6. Validate output quality periodically

## Contributing

To extend or modify:

1. Follow existing code patterns
2. Add docstrings to functions
3. Update configuration in `config.py`
4. Add error handling
5. Test with small datasets first
6. Document changes in README

## Performance Metrics

Typical run statistics (50 companies):
- Discovery: 2-3 minutes
- Processing: 10-15 minutes
- Total runtime: 15-20 minutes
- Contacts found: 200-300
- Emails collected: 150-250
- Email patterns: 50-100
- Average score: 60-70
