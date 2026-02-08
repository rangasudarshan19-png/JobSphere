"""
Job Scraper Service
Extracts job details from URLs and formats them for easy application creation
"""
import re
from typing import Dict, Optional
from datetime import datetime


class JobScraper:
    """
    Service to parse and extract job information from various sources
    Currently supports: LinkedIn, Indeed, and generic job posting URLs
    """
    
    def __init__(self):
        self.platforms = {
            'linkedin': self._parse_linkedin,
            'indeed': self._parse_indeed,
            'generic': self._parse_generic
        }
    
    def detect_platform(self, url: str) -> str:
        """Detect which job platform the URL is from"""
        url_lower = url.lower()
        
        if 'linkedin.com' in url_lower:
            return 'linkedin'
        elif 'indeed.com' in url_lower:
            return 'indeed'
        else:
            return 'generic'
    
    def extract_job_info(self, url: str, html_content: Optional[str] = None) -> Dict:
        """
        Extract job information from URL
        
        Args:
            url: Job posting URL
            html_content: Optional HTML content if already fetched
            
        Returns:
            Dictionary with extracted job details
        """
        platform = self.detect_platform(url)
        
        # Basic URL parsing
        job_info = {
            'url': url,
            'platform': platform,
            'job_title': '',
            'company_name': '',
            'location': '',
            'job_description': '',
            'salary': '',
            'job_type': '',
            'scraped_at': datetime.utcnow().isoformat()
        }
        
        # Platform-specific parsing
        if platform in self.platforms:
            extracted = self.platforms[platform](url, html_content)
            job_info.update(extracted)
        
        return job_info
    
    def _parse_linkedin(self, url: str, html_content: Optional[str]) -> Dict:
        """Parse LinkedIn job posting"""
        info = {}
        
        # Extract job ID from URL
        job_id_match = re.search(r'/jobs/view/(\d+)', url)
        if job_id_match:
            info['external_job_id'] = job_id_match.group(1)
            info['platform'] = 'LinkedIn'
            # Don't set job_title yet - let user fill it or parse from HTML
        
        # Try to extract company from URL patterns
        company_match = re.search(r'/company/([^/]+)', url)
        if company_match:
            info['company_name'] = company_match.group(1).replace('-', ' ').title()
        
        # If HTML content provided, parse it (basic parsing)
        if html_content:
            # Extract title
            title_match = re.search(r'<title>(.*?)\s*\|\s*LinkedIn</title>', html_content, re.IGNORECASE)
            if title_match:
                info['job_title'] = title_match.group(1).strip()
            
            # Extract company
            company_match = re.search(r'<a[^>]*class="[^"]*topcard__org-name-link[^"]*"[^>]*>(.*?)</a>', html_content, re.IGNORECASE)
            if company_match:
                info['company_name'] = company_match.group(1).strip()
        
        info['platform'] = 'LinkedIn'
        return info
    
    def _parse_indeed(self, url: str, html_content: Optional[str]) -> Dict:
        """Parse Indeed job posting"""
        info = {}
        
        # Extract job key from URL
        job_key_match = re.search(r'[?&]jk=([^&]+)', url)
        if job_key_match:
            info['external_job_id'] = job_key_match.group(1)
            info['platform'] = 'Indeed'
            # Don't set job_title yet - let user fill it or parse from HTML
        
        # Try to extract company from URL query params
        company_match = re.search(r'[?&]q=([^&]+)', url)
        if company_match:
            # URL decode and clean
            company = company_match.group(1).replace('+', ' ').replace('%20', ' ')
            info['company_name'] = company.title()
        
        # If HTML content provided, parse it
        if html_content:
            # Extract title
            title_match = re.search(r'<h1[^>]*class="[^"]*jobsearch-JobInfoHeader-title[^"]*"[^>]*>(.*?)</h1>', html_content, re.IGNORECASE | re.DOTALL)
            if title_match:
                info['job_title'] = re.sub(r'<.*?>', '', title_match.group(1)).strip()
            
            # Extract company
            company_match = re.search(r'<div[^>]*class="[^"]*jobsearch-InlineCompanyRating[^"]*"[^>]*>.*?<a[^>]*>(.*?)</a>', html_content, re.IGNORECASE | re.DOTALL)
            if company_match:
                info['company_name'] = company_match.group(1).strip()
        
        info['platform'] = 'Indeed'
        return info
    
    def _parse_generic(self, url: str, html_content: Optional[str]) -> Dict:
        """Parse generic job posting URL"""
        info = {'platform': 'Other'}
        
        # Extract domain for company name guess
        domain_match = re.search(r'https?://([^/]+)', url)
        if domain_match:
            domain = domain_match.group(1).replace('www.', '').split('.')[0]
            # Only set company name if it seems valid
            if domain and domain not in ['jobs', 'careers', 'apply']:
                info['company_name'] = domain.title()
        
        if html_content:
            # Try to extract title from page title
            title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
                # Remove common suffixes
                title = re.sub(r'\s*[-|]\s*.*$', '', title)
                if title:
                    info['job_title'] = title
        
        return info
    
    def parse_manual_entry(self, job_data: Dict) -> Dict:
        """
        Parse and validate manually entered job data
        
        Args:
            job_data: Dictionary with job details
            
        Returns:
            Cleaned and validated job data
        """
        cleaned = {
            'job_title': job_data.get('job_title', '').strip(),
            'company_name': job_data.get('company_name', '').strip(),
            'location': job_data.get('location', '').strip(),
            'job_description': job_data.get('job_description', '').strip(),
            'salary': job_data.get('salary', '').strip(),
            'job_type': job_data.get('job_type', '').strip(),
            'url': job_data.get('url', '').strip(),
            'notes': job_data.get('notes', '').strip()
        }
        
        # Extract keywords from job description
        if cleaned['job_description']:
            cleaned['keywords'] = self.extract_keywords(cleaned['job_description'])
        
        return cleaned
    
    def extract_keywords(self, text: str) -> list:
        """Extract technical keywords from job description"""
        # Common tech keywords and skills
        tech_keywords = [
            'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue',
            'node', 'django', 'flask', 'fastapi', 'spring', 'docker', 'kubernetes',
            'aws', 'azure', 'gcp', 'sql', 'postgresql', 'mongodb', 'redis',
            'git', 'ci/cd', 'agile', 'scrum', 'rest', 'api', 'microservices',
            'machine learning', 'ai', 'data science', 'tensorflow', 'pytorch',
            'html', 'css', 'sass', 'webpack', 'babel', 'graphql', 'redis',
            'elasticsearch', 'kafka', 'rabbitmq', 'jenkins', 'terraform',
            'ansible', 'linux', 'unix', 'bash', 'shell', 'devops', 'sre'
        ]
        
        text_lower = text.lower()
        found_keywords = []
        
        for keyword in tech_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        return list(set(found_keywords))  # Remove duplicates
    
    def suggest_status(self, job_data: Dict) -> str:
        """
        Suggest initial application status based on job data
        
        Returns appropriate status from: 'applied', 'screening', 'interview_scheduled', 'interviewed', 'offer', 'rejected'
        """
        # If applied date exists, suggest 'applied'
        if job_data.get('applied_date'):
            return 'applied'
        
        # Default to 'applied' for imported jobs (they need to review before applying)
        return 'applied'
    
    def generate_application_notes(self, job_info: Dict) -> str:
        """Generate helpful notes for the application"""
        notes = []
        
        if job_info.get('platform'):
            notes.append(f"Source: {job_info['platform']}")
        
        if job_info.get('external_job_id'):
            notes.append(f"Job ID: {job_info['external_job_id']}")
        
        if job_info.get('keywords'):
            notes.append(f"Key Skills: {', '.join(job_info['keywords'][:5])}")
        
        if job_info.get('scraped_at'):
            notes.append(f"Scraped: {job_info['scraped_at']}")
        
        return '\n'.join(notes)
    
    def validate_url(self, url: str) -> bool:
        """Validate if URL format is correct"""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return url_pattern.match(url) is not None
