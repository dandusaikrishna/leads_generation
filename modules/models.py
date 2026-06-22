"""
Data models for the job-company discovery pipeline.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


@dataclass
class PublicEmail:
    """Publicly available email address"""
    email: str
    category: str  # e.g., "careers", "hr", "support"
    source_url: str  # Where this email was found
    confidence_score: int  # 0-100
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class EmailPattern:
    """Discovered email pattern at a company"""
    pattern: str  # e.g., "firstname.lastname"
    examples: List[str] = field(default_factory=list)  # [john.doe@company.com, ...]
    confidence_score: int = 0  # 0-100
    source_url: str = ""  # Where pattern was discovered
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SeniorContact:
    """Decision maker or senior contact at a company"""
    name: str
    role: str
    public_profile_url: Optional[str] = None  # LinkedIn, GitHub, etc.
    source_url: str = ""  # Where this contact was found
    role_score: int = 0  # 0-100, based on ROLE_SCORES
    verification_score: int = 0  # 0-100, overall confidence
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class JobPosting:
    """Job posting information"""
    title: str
    url: str
    role_matched: str  # Which target role matched
    posted_date: Optional[str] = None
    source: str = ""  # Where found (LinkedIn, Lever, etc.)
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Company:
    """Main company data structure"""
    company_name: str
    website: Optional[str] = None
    linkedin_url: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None  # e.g., "50-100", "1000+"
    location: Optional[str] = None
    jobs: List[JobPosting] = field(default_factory=list)
    public_emails: List[PublicEmail] = field(default_factory=list)
    contacts: List[SeniorContact] = field(default_factory=list)
    email_patterns: List[EmailPattern] = field(default_factory=list)
    score: int = 0  # Final composite score 0-100
    score_breakdown: Dict[str, int] = field(default_factory=dict)  # Component scores
    discovered_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source_urls: List[str] = field(default_factory=list)  # All sources we found
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        # Convert dataclass fields
        data['jobs'] = [j.to_dict() for j in self.jobs]
        data['public_emails'] = [e.to_dict() for e in self.public_emails]
        data['contacts'] = [c.to_dict() for c in self.contacts]
        data['email_patterns'] = [p.to_dict() for p in self.email_patterns]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Company':
        """Create from dictionary"""
        jobs = [JobPosting(**j) for j in data.get('jobs', [])]
        public_emails = [PublicEmail(**e) for e in data.get('public_emails', [])]
        contacts = [SeniorContact(**c) for c in data.get('contacts', [])]
        email_patterns = [EmailPattern(**p) for p in data.get('email_patterns', [])]
        
        data_copy = data.copy()
        data_copy['jobs'] = jobs
        data_copy['public_emails'] = public_emails
        data_copy['contacts'] = contacts
        data_copy['email_patterns'] = email_patterns
        
        return cls(**data_copy)


@dataclass
class DiscoveryResult:
    """Result of discovering a single company"""
    company: Company
    status: str  # "success", "partial", "failed"
    errors: List[str] = field(default_factory=list)
    processing_time: float = 0  # seconds
    
    def to_dict(self) -> Dict:
        return {
            'company': self.company.to_dict(),
            'status': self.status,
            'errors': self.errors,
            'processing_time': self.processing_time
        }


@dataclass
class PipelineStats:
    """Statistics for a pipeline run"""
    total_companies_discovered: int = 0
    companies_with_contacts: int = 0
    companies_with_emails: int = 0
    avg_processing_time: float = 0
    total_emails_verified: int = 0
    errors_count: int = 0
    duration: float = 0  # Total runtime in seconds
