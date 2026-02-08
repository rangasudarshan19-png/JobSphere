"""
Resume Parser Service
Extract structured information from resumes in PDF, DOCX, or TXT format
"""
import re
from typing import Dict, List, Optional
import PyPDF2
from docx import Document
from io import BytesIO


class ResumeParser:
    """Parse resumes and extract structured information"""
    
    def __init__(self):
        # Common skills to look for
        self.skills_keywords = {
            'programming_languages': [
                'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby',
                'go', 'rust', 'php', 'swift', 'kotlin', 'scala', 'r', 'matlab'
            ],
            'web_frameworks': [
                'react', 'angular', 'vue', 'django', 'flask', 'fastapi', 'express',
                'spring', 'laravel', 'rails', 'nextjs', 'nuxt', 'svelte'
            ],
            'databases': [
                'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
                'cassandra', 'dynamodb', 'oracle', 'sql server', 'sqlite'
            ],
            'cloud_platforms': [
                'aws', 'azure', 'gcp', 'google cloud', 'heroku', 'digitalocean',
                'linode', 'firebase', 'cloudflare'
            ],
            'devops_tools': [
                'docker', 'kubernetes', 'jenkins', 'gitlab', 'github actions',
                'terraform', 'ansible', 'chef', 'puppet', 'circleci', 'travis'
            ],
            'tools': [
                'git', 'jira', 'confluence', 'slack', 'vs code', 'intellij',
                'postman', 'swagger', 'figma', 'sketch'
            ],
            'methodologies': [
                'agile', 'scrum', 'kanban', 'tdd', 'bdd', 'ci/cd', 'devops',
                'microservices', 'rest api', 'graphql'
            ]
        }
        
        # Education keywords
        self.education_keywords = [
            'bachelor', 'master', 'phd', 'doctorate', 'diploma', 'degree',
            'b.tech', 'b.e', 'm.tech', 'mba', 'mca', 'bca', 'b.sc', 'm.sc'
        ]
        
        # Experience section headers
        self.experience_headers = [
            'experience', 'work experience', 'employment', 'work history',
            'professional experience', 'career history'
        ]
        
        # Project section headers
        self.project_headers = [
            'projects', 'key projects', 'academic projects', 'personal projects'
        ]
        
        # Certification keywords
        self.certification_keywords = [
            'certified', 'certification', 'certificate', 'aws certified',
            'microsoft certified', 'google certified', 'oracle certified'
        ]
    
    def parse(self, file_content: bytes, filename: str) -> Dict:
        """
        Parse resume and extract information
        
        Args:
            file_content: Binary content of the file
            filename: Name of the file (to determine type)
        
        Returns:
            Dict containing extracted information
        """
        # Extract text based on file type
        text = self._extract_text(file_content, filename)
        
        if not text:
            return {'error': 'Could not extract text from file'}
        
        # Parse different sections
        result = {
            'raw_text': text,
            'personal_info': self._extract_personal_info(text),
            'skills': self._extract_skills(text),
            'education': self._extract_education(text),
            'experience': self._extract_experience(text),
            'projects': self._extract_projects(text),
            'certifications': self._extract_certifications(text),
            'summary': self._generate_summary(text)
        }
        
        return result
    
    def _extract_text(self, file_content: bytes, filename: str) -> str:
        """Extract text from different file formats"""
        filename_lower = filename.lower()
        
        try:
            if filename_lower.endswith('.pdf'):
                return self._extract_from_pdf(file_content)
            elif filename_lower.endswith('.docx'):
                return self._extract_from_docx(file_content)
            elif filename_lower.endswith('.txt'):
                return file_content.decode('utf-8', errors='ignore')
            else:
                return ""
        except Exception as e:
            print(f"Error extracting text: {e}")
            return ""
    
    def _extract_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF"""
        try:
            pdf_file = BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""
    
    def _extract_from_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX"""
        try:
            docx_file = BytesIO(file_content)
            doc = Document(docx_file)
            
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            return text
        except Exception as e:
            print(f"Error reading DOCX: {e}")
            return ""
    
    def _extract_personal_info(self, text: str) -> Dict:
        """Extract personal information"""
        info = {}
        
        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            info['email'] = emails[0]
        
        # Extract phone
        phone_pattern = r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,5}[-\s\.]?[0-9]{1,5}'
        phones = re.findall(phone_pattern, text)
        if phones:
            info['phone'] = phones[0]
        
        # Extract name (usually first line)
        lines = text.strip().split('\n')
        if lines:
            first_line = lines[0].strip()
            if len(first_line.split()) <= 4 and len(first_line) < 50:
                info['name'] = first_line
        
        # Extract LinkedIn
        linkedin_pattern = r'linkedin\.com/in/[\w-]+'
        linkedin = re.findall(linkedin_pattern, text.lower())
        if linkedin:
            info['linkedin'] = linkedin[0]
        
        # Extract GitHub
        github_pattern = r'github\.com/[\w-]+'
        github = re.findall(github_pattern, text.lower())
        if github:
            info['github'] = gith[CHAR]
        
        return info
    
    def _extract_skills(self, text: str) -> Dict[str, List[str]]:
        """Extract skills from resume"""
        text_lower = text.lower()
        found_skills = {}
        
        for category, keywords in self.skills_keywords.items():
            found = []
            for skill in keywords:
                # Use word boundaries to avoid partial matches
                pattern = r'\b' + re.escape(skill) + r'\b'
                if re.search(pattern, text_lower):
                    found.append(skill.title())
            
            if found:
                found_skills[category] = found
        
        return found_skills
    
    def _extract_education(self, text: str) -> List[Dict]:
        """Extract education information"""
        education = []
        text_lower = text.lower()
        
        # Find education section
        for keyword in self.education_keywords:
            pattern = r'\b' + re.escape(keyword) + r'\b[^\.]*'
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            
            for match in matches:
                # Try to extract year
                year_pattern = r'\b(19|20)\d{2}\b'
                years = re.findall(year_pattern, match)
                
                education.append({
                    'degree': match.strip()[:100],
                    'year': years[0] if years else None
                })
        
        return education[:5]  # Limit to 5 entries
    
    def _extract_experience(self, text: str) -> List[str]:
        """Extract work experience"""
        experiences = []
        lines = text.split('\n')
        
        in_experience_section = False
        current_experience = []
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Check if we're entering experience section
            if any(header in line_lower for header in self.experience_headers):
                in_experience_section = True
                continue
            
            # Check if we're leaving experience section
            if in_experience_section and any(header in line_lower for header in self.project_headers + ['education', 'skills']):
                in_experience_section = False
                if current_experience:
                    experiences.append(' '.join(current_experience))
                    current_experience = []
                continue
            
            # Collect experience lines
            if in_experience_section and line.strip():
                current_experience.append(line.strip())
                
                # If line looks like a new job (contains year), start new entry
                if re.search(r'\b(19|20)\d{2}\b', line):
                    if len(current_experience) > 1:
                        experiences.append(' '.join(current_experience[:-1]))
                        current_experience = [current_experience[-1]]
        
        # Add last experience
        if current_experience:
            experiences.append(' '.join(current_experience))
        
        return experiences[:5]  # Limit to 5 experiences
    
    def _extract_projects(self, text: str) -> List[str]:
        """Extract project information"""
        projects = []
        lines = text.split('\n')
        
        in_project_section = False
        current_project = []
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Check if we're entering project section
            if any(header in line_lower for header in self.project_headers):
                in_project_section = True
                continue
            
            # Check if we're leaving project section
            if in_project_section and any(header in line_lower for header in self.experience_headers + ['education', 'certification']):
                in_project_section = False
                if current_project:
                    projects.append(' '.join(current_project))
                    current_project = []
                continue
            
            # Collect project lines
            if in_project_section and line.strip():
                current_project.append(line.strip())
                
                # If we have enough info, start new project
                if len(current_project) > 3:
                    projects.append(' '.join(current_project))
                    current_project = []
        
        # Add last project
        if current_project:
            projects.append(' '.join(current_project))
        
        return projects[:5]  # Limit to 5 projects
    
    def _extract_certifications(self, text: str) -> List[str]:
        """Extract certifications"""
        certifications = []
        text_lower = text.lower()
        
        for keyword in self.certification_keywords:
            pattern = r'\b' + re.escape(keyword) + r'[^\n]*'
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            certifications.extend([m.strip() for m in matches if len(m.strip()) > 10])
        
        return list(set(certifications))[:10]  # Unique, limit to 10
    
    def _generate_summary(self, text: str) -> Dict:
        """Generate summary statistics"""
        words = text.split()
        lines = text.split('\n')
        
        return {
            'total_words': len(words),
            'total_lines': len(lines),
            'estimated_pages': len(words) // 300 + 1
        }
