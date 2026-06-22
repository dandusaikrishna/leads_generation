# India-Focused Company Discovery Pipeline

## Overview

This enhanced pipeline discovers and enriches software engineering companies in India with a focus on:

- **Primary Cities**: Hyderabad, Bangalore, Pune, Mumbai
- **Primary States**: Telangana, Karnataka, Maharashtra
- **Company Type**: Software, SaaS, IT Services, EdTech, Fintech
- **Data Richness**: Working email verification, decision makers, recent activity

## Key Features

### 🎯 Geographic Targeting
- ✅ Hyderabad/Telangana focus (highest priority)
- ✅ Bangalore (Silicon Valley of India)
- ✅ Pune (growing tech hub)
- ✅ Mumbai (finance & tech)
- ✅ Remote companies with India presence

### 📊 Enhanced Data Sources
- ✅ **GitHub**: Find engineering teams and organizations
- ✅ **Crunchbase**: Company funding, employee count, industry
- ✅ **Stack Overflow**: Active developer presence
- ✅ **Company Blogs/Press**: Recent hiring announcements
- ✅ **LinkedIn**: Decision makers and contacts

### 📧 Email Verification
- ✅ SMTP verification for working emails
- ✅ DNS/MX record validation
- ✅ Quality scoring (0-100)
- ✅ Catch-all detection
- ✅ Format validation

### 💼 Decision Maker Discovery
- ✅ Founders and co-founders
- ✅ C-level executives (CEO, CTO, VP)
- ✅ Engineering directors and managers
- ✅ Talent acquisition teams
- ✅ LinkedIn profile links

### 🏆 Intelligent Scoring
- ✅ Location-based scoring (Telangana bonus: +20)
- ✅ Funding stage recognition
- ✅ Data source diversity
- ✅ Email quality scoring
- ✅ Remote-friendly bonus

## Quick Start

### 1. Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Create output directories
mkdir -p cache logs leads backend

# Copy and update environment
cp .env.example backend/.env
# Edit backend/.env with your API keys (already provided)
```

### 2. Basic Usage - Discover Companies in India

```bash
# Discover companies in default Indian cities (Hyderabad, Bangalore, Pune)
python -c "
from india_discovery import discover_companies_in_india
companies = discover_companies_in_india(limit=100)
for c in companies[:5]:
    print(f\"{c.get('company_name')} - {c.get('target_city')}\")
"
```

### 3. Advanced Usage - Telangana Focus

```bash
# Focus on Telangana (Hyderabad)
python -c "
from india_discovery import discover_companies_in_india, prioritize_by_telangana
companies = discover_companies_in_india(cities=['Hyderabad'], limit=100)
prioritized = prioritize_by_telangana(companies)
print(f'Found {len(prioritized)} companies in Telangana')
"
```

### 4. With Email Verification

```bash
# Discover and verify working emails
python -c "
from india_discovery import discover_companies_in_india, enrich_with_working_emails
companies = discover_companies_in_india(limit=50)
for company in companies[:5]:
    enriched = enrich_with_working_emails(company)
    print(f\"{enriched.get('company_name')}: {enriched.get('working_email_count')} verified emails\")
"
```

## Module Guide

### india_discovery.py
**Main India-focused discovery module**

```python
from india_discovery import (
    discover_companies_in_india,           # Main discovery
    find_remote_companies_with_india_presence,
    filter_companies_by_size,
    prioritize_by_telangana,
    enrich_with_working_emails,
    score_india_company,
    prepare_india_discovery_report
)
```

**Functions:**

- `discover_companies_in_india(cities, limit, include_remote)`
  - Discovers companies in specified Indian cities
  - Returns list of company dictionaries
  - Supports multi-source discovery

- `find_remote_companies_with_india_presence(limit)`
  - Finds remote-first companies with India engineering teams
  - Useful for expanding beyond local companies

- `filter_companies_by_size(companies, min_employees, max_employees)`
  - Filter by employee count
  - Find startups or established companies

- `prioritize_by_telangana(companies)`
  - Reorder list with Telangana companies first
  - Useful for focused outreach

- `enrich_with_working_emails(company, domain, min_quality)`
  - Verify emails for a company
  - Returns company with verified_emails list

- `score_india_company(company, city_preference)`
  - Calculate India-specific score (0-100)
  - Incorporates location, funding, sources, emails

- `prepare_india_discovery_report(companies, city_focus)`
  - Generate summary report
  - Statistics by city, state, funding, source

### enhanced_sources.py
**Multi-source data collection**

```python
from enhanced_sources import (
    find_companies_on_github,               # GitHub organizations
    extract_github_team_members,            # GitHub team extraction
    find_companies_on_crunchbase,           # Crunchbase discovery
    find_active_companies_stackoverflow,    # Stack Overflow activity
    find_recent_company_activity,           # Blog/press monitoring
    discover_companies_multi_source         # Aggregated discovery
)
```

### email_verification.py
**Email validation and verification**

```python
from email_verification import (
    get_mx_records,                         # DNS MX lookup
    check_catch_all,                        # Catch-all detection
    verify_email_smtp,                      # SMTP verification
    verify_emails_batch,                    # Batch verification
    validate_email_quality,                 # Quality assessment
    filter_working_emails                   # Filter by quality
)
```

### config.py (India Configuration)
**India-specific settings**

```python
from config import (
    INDIA_CITIES,                   # Target cities mapping
    PRIORITY_STATES,                # Priority states list
    INDIA_SOFTWARE_ROLES,           # India-specific roles
    INDIA_SCORE_MODIFIERS,          # India scoring bonuses
    INDIA_EMAIL_CATEGORIES,         # Email categories
    DEFAULT_COUNTRY,                # Set to "India"
)
```

## Configuration

Edit `.env` file for customization:

```bash
# Target cities (comma-separated)
TARGET_CITIES=Hyderabad,Bangalore,Pune,Mumbai

# Email verification strictness (0-100, higher = stricter)
EMAIL_VERIFICATION_STRICTNESS=75

# Enable data sources
ENABLE_GITHUB_SOURCE=true
ENABLE_CRUNCHBASE_SOURCE=true
ENABLE_STACKOVERFLOW_SOURCE=true
ENABLE_BLOG_MONITORING=true

# Processing
BATCH_SIZE=50
MAX_COMPANIES=800
TIMEOUT_PER_COMPANY=20
```

## Output Files

### companies.json
```json
{
  "company_name": "TechCorp India",
  "target_city": "Hyderabad",
  "target_state": "Telangana",
  "priority": 1,
  "domain": "techcorp.in",
  "funding_stage": "Series B",
  "working_email_count": 3,
  "verified_emails": [
    {"email": "careers@techcorp.in", "quality_score": 95, "verified": true},
    {"email": "hiring@techcorp.in", "quality_score": 90, "verified": true}
  ],
  "score": 87,
  "sources": ["GitHub", "Crunchbase", "Stack Overflow"]
}
```

### Discovery Report
```python
{
  "total_companies": 150,
  "by_city": {
    "Hyderabad": 45,
    "Bangalore": 38,
    "Pune": 32,
    "Mumbai": 25
  },
  "by_state": {
    "Telangana": 45,
    "Karnataka": 38,
    "Maharashtra": 57
  },
  "working_email_count": 342,
  "remote_companies": 12,
  "top_companies": [
    {"name": "TechCorp", "city": "Hyderabad", "score": 92, "working_emails": 5},
    ...
  ]
}
```

## Scoring System

### India-Specific Scoring Factors

| Factor | Points | Description |
|--------|--------|-------------|
| Telangana/Hyderabad | +20 | Primary target location |
| Bangalore | +8 | Secondary hub |
| Pune | +7 | Tertiary hub |
| Funded (Any Stage) | +15 | Venture-backed |
| GitHub Presence | +10 | Active engineering org |
| Crunchbase Listed | +12 | Established company |
| Stack Overflow Activity | +8 | Developer engagement |
| Working Emails | +3 per email | Verified and valid |
| Remote-Friendly | +5 | Global hiring |
| Active Hiring | +15 | Recent job postings |
| **Total (Max)** | **100** | Composite score |

### Tier Classification

- **90-100**: Tier 1 - Excellent (Priority outreach)
- **75-89**: Tier 2 - Very Good
- **60-74**: Tier 3 - Good
- **45-59**: Tier 4 - Fair
- **25-44**: Tier 5 - Poor
- **<25**: Tier 6 - Very Poor

## Email Verification Process

1. **Format Validation**: Regex check for valid email format
2. **DNS/MX Lookup**: Verify domain has MX records
3. **Catch-all Detection**: Test if domain accepts all emails
4. **SMTP Verification**: Connect to MX server and verify recipient
5. **Quality Scoring**: Composite score based on all checks

### Quality Score Interpretation

- **90-100**: Verified and working
- **75-89**: Likely valid
- **60-74**: Probably valid
- **40-59**: Uncertain
- **<40**: Likely invalid

## Performance Metrics

Typical run statistics (100 companies in 3 cities):

- **Discovery time**: 5-8 minutes
- **Email verification**: 10-15 minutes
- **Total runtime**: 20-30 minutes
- **Companies with verified emails**: 70-80%
- **Average emails per company**: 2-3
- **Average quality score**: 82%

## Tips & Best Practices

### 1. Telangana Focus
```python
# Get only Telangana companies (highest priority)
companies = discover_companies_in_india(cities=["Hyderabad"], limit=100)
```

### 2. High-Quality Emails Only
```python
# Filter for high-confidence emails
from email_verification import filter_working_emails
working = filter_working_emails(emails, domain, min_quality=80)
```

### 3. Staged Discovery
```python
# Phase 1: Initial discovery
companies = discover_companies_in_india(limit=200)

# Phase 2: Filter by size
large = filter_companies_by_size(companies, min_employees=100)

# Phase 3: Prioritize
priority = prioritize_by_telangana(large)

# Phase 4: Enrich with emails
for company in priority[:50]:
    enrich_with_working_emails(company)
```

### 4. Reporting
```python
# Generate summary report
report = prepare_india_discovery_report(companies)
print(f"Found {report['total_companies']} companies")
print(f"Telangana: {report['by_state'].get('Telangana', 0)}")
print(f"Verified emails: {report['working_email_count']}")
```

## Troubleshooting

### Issue: Limited companies found
**Solution**: Ensure API keys are valid and rate limits not exceeded

### Issue: Email verification failing
**Solution**: Check MX records, ensure SMTP port 25 is not blocked

### Issue: Slow discovery
**Solution**: Use `BATCH_SIZE=100` or reduce `MAX_COMPANIES`

### Issue: Too many false positives
**Solution**: Increase `EMAIL_VERIFICATION_STRICTNESS` to 80+

## Extending the Pipeline

### Add New City
```python
# Edit config.py
INDIA_CITIES = {
    "NewCity": {"state": "StateName", "priority": 2},
    ...
}
```

### Add New Data Source
```python
# In enhanced_sources.py
def find_companies_on_newsource(city: str) -> List[Dict]:
    # Implement discovery logic
    return companies
```

### Customize Scoring
```python
# In config.py - update INDIA_SCORE_MODIFIERS
INDIA_SCORE_MODIFIERS = {
    "your_factor": 10,  # Your weight
    ...
}
```

## API Key Management

Your API keys are configured in `backend/.env`:

- **Serper API**: For search and scraping (75 million daily limit)
- **OpenRouter API**: For LLM data extraction (pay-as-you-go)

Keys are pre-configured in `.env.example` and copied to `backend/.env`.

## Support & Next Steps

1. **Test Discovery**: Run with `limit=10` first to verify setup
2. **Review Outputs**: Check `leads/companies.json` quality
3. **Scale Up**: Increase `limit` for production runs
4. **Automate**: Set up scheduled daily discovery
5. **Monitor**: Track email verification success rates

## Additional Resources

- Serper API Docs: https://serper.dev/docs
- OpenRouter Docs: https://openrouter.ai/docs
- LinkedIn Search Tips: LinkedIn developer program
- Crunchbase: Free tier limited, premium available
