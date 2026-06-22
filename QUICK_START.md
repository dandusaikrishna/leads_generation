# Quick Start Guide

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p backend cache logs leads
```

## Configuration

1. Create `backend/.env` with your API keys:
```
SERPER_API_KEY=your_serper_key
OPENROUTER_API_KEY=your_openrouter_key
```

Or copy and edit the template:
```bash
cp .env.example backend/.env
```

## Usage

### Option 1: New Pipeline (Recommended)

```bash
# Discover companies in USA
python leads.py --country "USA" --limit 50

# Discover backend engineers in UK
python leads.py \
  --country "UK" \
  --roles "Backend Engineer,Python Developer" \
  --limit 100

# Custom output paths
python leads.py \
  --country "USA" \
  --output-json results/companies.json \
  --output-txt results/emails.txt
```

### Option 2: Legacy API (Backwards Compatible)

```bash
# Old interface still works
python leads_apxor.py \
  --country "USA" \
  --roles "Software Engineer,Backend Engineer" \
  --limit 50
```

### Option 3: Programmatic Use

```python
from pipeline import DiscoveryPipeline

pipeline = DiscoveryPipeline()

companies = pipeline.discover_and_process_companies(
    country="USA",
    roles=["Software Engineer", "Backend Engineer"],
    limit=50,
    parallel=True
)

# Export results
from exporters import export_companies_json, export_emails_txt
export_companies_json(companies, "output/companies.json")
export_emails_txt(companies, "output/emails.txt")

# Use the data
for company in companies:
    print(f"{company.company_name}: Score {company.score}")
    for contact in company.contacts[:3]:
        print(f"  - {contact.name} ({contact.role})")
```

## Output Files

After running the pipeline, you'll get:

**companies.json**
- Complete database with all discovered information
- Structured format for programmatic access
- Includes scores, patterns, and all metadata

**emails.txt**
- Human-readable report
- Easy for manual review
- Organized by company with contacts and patterns

**hiring_leads.xlsx** (if using legacy API)
- Excel spreadsheet with styled formatting
- Color-coded email verification status
- Hyperlinked URLs

## Understanding Scores

Company scores (0-100) indicate data quality and lead value:

- **90-100**: Tier 1 - Excellent (Strong leadership, rich data)
- **75-89**: Tier 2 - Very Good (Multiple contacts, good emails)
- **60-74**: Tier 3 - Good (Some contacts, decent data)
- **45-59**: Tier 4 - Fair (Limited contacts)
- **25-44**: Tier 5 - Poor (Few contacts)
- **<25**: Tier 6 - Very Poor (Insufficient data)

## Troubleshooting

**"API key missing" error**
- Check backend/.env file exists
- Verify keys are correct
- Ensure environment variables are loaded

**"No companies found"**
- Try different country names
- Expand target roles list
- Increase search limit
- Check API rate limits

**"Low scores" for companies**
- Missing public contact information
- Limited email availability
- No careers pages
- This is normal for some companies

## Next Steps

1. Review the output JSON/TXT files
2. Use scoring to prioritize outreach
3. Verify email patterns before using
4. Check LinkedIn URLs for current info
5. Cross-reference with your CRM

## Performance Tips

- Start with --limit 10 for testing
- Use --sequential flag for debugging
- Run daily for updated job postings
- Cache is automatically saved in `cache/` directory
- Check logs in `logs/` directory for details

## Support

For issues or questions:
1. Check README.md for detailed documentation
2. Review logs in `logs/` directory
3. Enable --debug flag for troubleshooting
4. Check the documentation in README.md
