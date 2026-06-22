# Project Structure

```
leads_generation/
├── run_all.py                 # Main entry point - Unified leads discovery
├── README.md                  # Project documentation
│
├── modules/                   # Core modules
│   ├── __init__.py           # Package initialization
│   ├── models.py             # Data models (Company, PublicEmail, etc)
│   └── config.py             # Configuration & environment variables
│
├── utils/                     # Utility functions
│   ├── __init__.py           # Package initialization
│   └── utils.py              # HTTP requests, logging, caching
│
├── features/                  # Advanced features (optional)
│   ├── __init__.py           # Package initialization
│   ├── email_verification.py # SMTP and DNS validation
│   ├── email_enrichment.py   # Email pattern generation
│   └── excel_exporter.py     # Excel report generation
│
├── config_files/             # Configuration & secrets (gitignored)
│   ├── .env                  # API keys (DO NOT COMMIT)
│   ├── .env.example          # Example environment file
│   ├── requirements.txt      # Python dependencies
│   └── .gitignore           # Git ignore rules
│
├── output/                    # Generated outputs
│   ├── companies.json        # Master companies data
│   ├── emails_scored.txt     # Master email list
│   ├── companies_YYYY-MM-DD_HHMMSS.json  # Versioned companies
│   └── emails_scored_YYYY-MM-DD_HHMMSS.txt  # Versioned emails
│
├── logs/                      # Execution logs (auto-created)
│   └── leads_pipeline.log
│
└── .cache/                    # Cache directory (auto-created)
    └── companies_cache.json
```

## File Descriptions

### Core Entry Point
- **run_all.py**: Main unified runner for leads discovery. Handles all 5 phases:
  1. Discover startups (NOT MNCs)
  2. Extract HR & Founder emails
  3. Score email quality
  4. Build company models
  5. Export data (versioned + master files)

### Modules
- **models.py**: Data structures for Company, PublicEmail, EmailPattern, etc.
- **config.py**: API keys, directories, logging, email scoring config

### Utils
- **utils.py**: Serper API search, LLM queries, logging setup, caching

### Features (Optional Advanced Features)
- **email_verification.py**: SMTP verification, MX record lookup, catch-all detection
- **email_enrichment.py**: Generate email patterns, split names, filter emails
- **excel_exporter.py**: Create styled Excel reports with color coding

### Configuration
- **.env**: Store your API keys here (gitignored)
- **.env.example**: Template showing what keys are needed
- **requirements.txt**: All Python dependencies
- **.gitignore**: Files to exclude from git (secrets, cache, etc)

## Key Features

✅ **Deduplication**: Skips companies already discovered
✅ **Versioned Output**: Each run creates timestamped files
✅ **Master Files**: Incremental builds on previous discoveries
✅ **MNC Filtering**: Only discovers startups, not large companies
✅ **Email Scoring**: 0-100 quality scoring system
✅ **Pattern Generation**: Auto-generates email addresses when web search fails
✅ **Optional SMTP**: Verify emails with SMTP connections
✅ **Excel Export**: Professional styled reports

## Usage

```bash
# Setup
python -m pip install -r config_files/requirements.txt
cp config_files/.env.example config_files/.env
# Edit config_files/.env with your API keys

# Run
python run_all.py
```

Output files appear in `output/` folder with both versioned and master files.
