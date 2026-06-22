"""
README - Job-Company Discovery & Contact Intelligence Pipeline

A comprehensive Python pipeline for discovering companies actively hiring for target
software engineering roles and collecting publicly available contact information.

## Features

- **Company Discovery**: Search job boards and identify companies hiring for target roles
- **Company Information**: Collect company details (industry, size, location, website, LinkedIn)
- **Contact Discovery**: Find senior contacts, decision makers, and recruiting team members
- **Public Email Collection**: Gather publicly available company and generic emails
- **Email Pattern Analysis**: Identify email address patterns from public emails
- **Scoring System**: Weighted scoring model for company quality and lead prioritization
- **Parallel Processing**: Process multiple companies concurrently with configurable batch size
- **Caching**: Smart caching to avoid redundant API calls and allow resume from checkpoints
- **Comprehensive Exports**: JSON database and formatted text reports

## Target Roles

The pipeline targets the following software engineering roles:
- Software Engineer
- Senior Software Engineer
- Backend Engineer
- Senior Backend Engineer
- Python Developer
- Django Developer
- Full Stack Developer
- Software Developer
- Platform Engineer
- API Engineer
- Engineering Manager
- And related software development roles

## Installation

### Prerequisites
- Python 3.8+
- pip or poetry

### Setup

1. Clone/create the project directory
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure API keys:
   ```bash
   # Create backend/.env file with:
   SERPER_API_KEY=your_serper_api_key
   OPENROUTER_API_KEY=your_openrouter_api_key
   ```

4. Create necessary directories:
   ```bash
   mkdir -p leads cache logs
   ```

## Usage

### Basic Usage

```bash
python leads.py --country "USA" --limit 50
```

### With Custom Roles

```bash
python leads.py \
  --country "USA" \
  --roles "Software Engineer,Backend Engineer,Python Developer" \
  --limit 100
```

### Sequential Processing (for debugging)

```bash
python leads.py --country "USA" --sequential
```

### With Custom Output Paths

```bash
python leads.py \
  --country "USA" \
  --output-json results/companies.json \
  --output-txt results/emails.txt \
  --limit 100
```

### Debug Mode

```bash
python leads.py --country "USA" --debug
```

## Output Files

### companies.json
Complete database with all discovered information for each company:

```json
{
  "metadata": {
    "export_date": "2024-06-23T...",
    "total_companies": 50,
    "version": "1.0"
  },
  "companies": [
    {
      "company_name": "TechCorp Inc",
      "website": "https://techcorp.com",
      "linkedin_url": "https://linkedin.com/company/techcorp",
      "industry": "Software",
      "company_size": "100-500",
      "location": "USA",
      "jobs": [
        {
          "title": "Senior Software Engineer",
          "url": "...",
          "role_matched": "Senior Software Engineer"
        }
      ],
      "public_emails": [
        {
          "email": "careers@techcorp.com",
          "category": "careers",
          "source_url": "https://techcorp.com/careers",
          "confidence_score": 95
        }
      ],
      "contacts": [
        {
          "name": "Jane Doe",
          "role": "CTO",
          "public_profile_url": "https://linkedin.com/in/janedoe",
          "role_score": 98
        }
      ],
      "email_patterns": [
        {
          "pattern": "firstname.lastname",
          "examples": ["john.doe@techcorp.com"],
          "confidence_score": 85
        }
      ],
      "score": 92,
      "score_breakdown": {
        "decision_makers": 35,
        "emails": 20,
        "patterns": 15,
        "jobs": 12,
        "info": 10
      }
    }
  ]
}
```

### emails.txt
Human-readable report with key contact and email information:

```
============================================================
COMPANY: TechCorp Inc
SCORE: 92
WEBSITE: https://techcorp.com
LINKEDIN: https://linkedin.com/company/techcorp
INDUSTRY: Software
COMPANY SIZE: 100-500
LOCATION: USA

ACTIVE JOBS:
  - Senior Software Engineer
  - Backend Engineer

PUBLIC EMAILS:
  - careers@techcorp.com (careers, 95% confidence)
  - hr@techcorp.com (hr, 90% confidence)

SENIOR CONTACTS & DECISION MAKERS:
  - Jane Doe | CTO (Score: 98)
    LinkedIn: https://linkedin.com/in/janedoe
  - John Smith | VP Engineering (Score: 95)
    LinkedIn: https://linkedin.com/in/johnsmith

EMAIL PATTERNS IDENTIFIED:
  - firstname.lastname (85% confidence)
      Example: john.doe@techcorp.com
      Example: jane.smith@techcorp.com

SCORE BREAKDOWN:
  - Decision Makers: 35
  - Emails: 20
  - Patterns: 15
  - Jobs: 12
  - Info: 10

============================================================
```

## Architecture

### Core Modules

**config.py**
- Configuration constants
- API keys management
- Role definitions and scoring rules
- Email patterns and scoring modifiers

**models.py**
- Data models: Company, Contact, PublicEmail, EmailPattern, etc.
- Serialization/deserialization methods
- Type definitions

**utils.py**
- HTTP/API helpers (Serper, OpenRouter)
- Logging setup
- Caching system
- Text processing utilities
- Retry mechanisms

**company_discovery.py**
- discover_hiring_companies(): Find companies from job postings
- search_related_companies(): Find similar companies in same industry

**company_info.py**
- resolve_company_domain(): Get official website domain
- get_company_info(): Collect industry, size, location
- find_linkedin_company_profile(): Get LinkedIn company URL
- find_careers_page(): Locate careers pages
- collect_public_emails_from_domain(): Extract public emails

**contact_discovery.py**
- find_senior_contacts(): Find decision makers and executives
- find_recruiting_team(): Locate HR and recruiting staff
- search_engineering_leadership(): Find engineering leaders

**email_patterns.py**
- analyze_email_patterns(): Identify email patterns
- generate_email_candidates(): Create likely email addresses
- predict_email_from_name(): Predict email using patterns

**scoring.py**
- calculate_company_score(): Comprehensive scoring system
- score_contact(): Score individual contacts
- get_company_tier(): Classify company tier

**exporters.py**
- export_companies_json(): Export to JSON
- export_emails_txt(): Export human-readable report
- export_summary(): Generate statistics

**pipeline.py**
- DiscoveryPipeline: Main orchestrator
- Parallel and sequential processing
- Full workflow coordination

**leads.py**
- CLI entry point
- Argument parsing
- Error handling

## Scoring System

### Company Score Breakdown (0-100)

**Decision Makers (0-35 points)**
- CTO: 98 points
- VP Engineering: 95 points
- Engineering Director: 92 points
- Head of Engineering: 90 points
- Engineering Manager: 85 points
- Talent Acquisition Lead: 80 points
- HR Manager: 75 points

**Public Emails (0-20 points)**
- High confidence emails: 3 points each
- Medium confidence emails: 2 points each
- Low confidence emails: 1 point each
- Careers email bonus: +3 points
- Hiring email bonus: +3 points
- HR email bonus: +2 points

**Email Patterns (0-15 points)**
- High confidence patterns (75%+): 4 points each
- Medium confidence patterns: 2 points each
- Low confidence patterns: 1 point each
- Multiple patterns bonus: +3 points

**Job Postings (0-15 points)**
- Base job: 3 points
- Recent posting: +2 points
- Senior roles: +2 points each

**Company Info (0-15 points)**
- Website verified: 3 points
- LinkedIn profile: 2 points
- Industry identified: 3 points
- Company size: 3 points
- Location verified: 2 points
- Multiple sources (3+): 2 points

### Company Tiers

- **Tier 1 (90-100)**: Excellent - Strong leadership, rich contact info, high data quality
- **Tier 2 (75-89)**: Very Good - Multiple decision makers, good email coverage
- **Tier 3 (60-74)**: Good - Some contacts/emails, decent data quality
- **Tier 4 (45-59)**: Fair - Limited contacts/emails, basic data
- **Tier 5 (25-44)**: Poor - Few contacts, minimal email data
- **Tier 6 (<25)**: Very Poor - Insufficient data

## Data Quality & Deduplication

**Company Deduplication**
- Removes duplicate companies by normalized name comparison
- Keeps unique entries only

**Email Deduplication**
- Normalizes email addresses (lowercase)
- Validates email format
- Removes duplicates

**Contact Deduplication**
- Removes duplicate contacts within same company by name
- Combines contact information from multiple sources

**Source Tracking**
- All data includes source URLs
- Supports verifying information origin
- Enables data reconciliation

## Performance Considerations

**Parallel Processing**
- Uses ThreadPoolExecutor with configurable batch size
- Respects API rate limits
- Caching avoids redundant calls

**API Rate Limiting**
- Serper: ~12 requests per API call
- OpenRouter: LLM calls with backoff
- Built-in retry mechanism with exponential backoff

**Caching System**
- Separate caches for companies, contacts, emails
- Enables resume from checkpoints
- Reduces API costs

**Processing Limits**
- Maximum 20 seconds per company processing
- Batch size of 50 companies for parallel mode
- Retry up to 3 times on failure

## Configuration

### Environment Variables (.env)

```
SERPER_API_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here
```

### Customizing Roles

Edit `config.py`:
```python
TARGET_ROLES = [
    "Your Custom Role",
    "Another Role",
]
```

### Customizing Scoring

Edit `config.py`:
```python
ROLE_SCORES = {
    "Your Title": 100,
    "Another Title": 90,
}

SCORE_MODIFIERS = {
    "recent_job_posting": 10,
    "dedicated_engineering_email": 15,
}
```

## Troubleshooting

**"API key missing" errors**
- Ensure backend/.env file exists
- Check API keys are correct
- Verify environment variables are loaded

**"No companies found"**
- Try different country names
- Expand target roles list
- Increase search limit
- Check API rate limits

**"Timeout errors"**
- Check network connectivity
- Try sequential mode instead of parallel
- Use debug mode to see detailed logs

**Low score companies**
- Missing contact information
- Limited public emails
- No careers page
- All normal for private companies

## Advanced Usage

### Custom Pipeline in Python

```python
from pipeline import DiscoveryPipeline

pipeline = DiscoveryPipeline()

companies = pipeline.discover_and_process_companies(
    country="UK",
    roles=["Backend Engineer", "Python Developer"],
    limit=100,
    parallel=True
)

for company in companies:
    print(f"{company.company_name}: Score {company.score}")
    for contact in company.contacts[:3]:
        print(f"  - {contact.name} ({contact.role})")
```

### Batch Processing Multiple Countries

```python
from pipeline import DiscoveryPipeline

countries = ["USA", "UK", "Canada", "Australia"]

for country in countries:
    pipeline = DiscoveryPipeline()
    companies = pipeline.discover_and_process_companies(
        country=country,
        limit=50
    )
    pipeline.export_results(companies)
```

## Limitations & Considerations

1. **Public Information Only**
   - All contacts and emails are publicly available
   - No personal email addresses are generated

2. **API Dependencies**
   - Requires Serper and OpenRouter APIs
   - Subject to their rate limits and availability

3. **Geographic Scope**
   - Optimized for English-language job boards
   - May have limited results for non-English regions

4. **Data Freshness**
   - Job postings cached locally
   - Recommend running periodically for updates

5. **Accuracy Notes**
   - Email patterns are inferred from public data
   - Confidence scores reflect data quality
   - Always verify results before use

## Support & Contributing

- Report issues with specific companies
- Suggest role additions
- Contribute improvements
- Share usage patterns

## License

[Your License Here]

## Contact

For questions or support: [Your Contact Info]
"""

# This serves as documentation. Store as README.md in the project root.
