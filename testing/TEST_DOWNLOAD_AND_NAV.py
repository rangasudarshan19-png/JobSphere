#!/usr/bin/env python3
"""
Test PDF/DOCX download and navigation fixes
"""

import requests
import json
import time

API_BASE = "http://127.0.0.1:8000"

print("=" * 60)
print("TEST: PDF/DOCX DOWNLOAD WITH CONTENT")
print("=" * 60)

# Sample resume data
resume_data = {
    "contact": {
        "full_name": "John Developer",
        "email": "john.dev@example.com",
        "phone": "6303323781",
        "location": "Hyderabad",
        "linkedin": "https://www.linkedin.com/in/john-dev",
        "profile_picture": None
    },
    "professional_summary": "Results-driven Software Engineer with 5 years of experience in manual and automation testing, specializing in GWPC projects. Demonstrated ability to balance full-time professional responsibilities while pursuing a degree, leading to extensive hands-on experience and recognition for outstanding performance in diverse technical environments.",
    "experience": [
        {
            "title": "Software Engineer",
            "company": "HCLtech",
            "start_date": "2022",
            "end_date": "Present",
            "description": [
                "Led the testing and implementation phases, ensuring compliance with project specifications.",
                "Collaborated with cross-functional teams to enhance automation testing processes."
            ],
            "achievements": ["Testing implementation", "Team collaboration"]
        },
        {
            "title": "QA Tester",
            "company": "Previous Company",
            "start_date": "2019",
            "end_date": "2022",
            "description": ["Manual and automation testing"],
            "achievements": []
        }
    ],
    "education": [
        {
            "degree": "Bachelor's Degree",
            "institution": "University Name",
            "graduation_date": "2023",
            "field": "Computer Science"
        }
    ],
    "skills": [
        "Manual Testing",
        "Automation Testing",
        "Python",
        "Java",
        "SQL",
        "Qtest",
        "Jira",
        "SQL Squirrel",
        "GEN AI"
    ],
    "projects": [
        {
            "name": "GWPC Project 1",
            "description": "Led the testing and implementation phases, ensuring compliance with project specifications.",
            "technologies": []
        },
        {
            "name": "GWPC Project 2",
            "description": "Collaborated with cross-functional teams to enhance automation testing processes.",
            "technologies": []
        }
    ],
    "certifications": []
}

# Test 1: PDF Download
print("\n📄 TEST #1: PDF Download")
print("-" * 60)

try:
    response = requests.post(
        f"{API_BASE}/api/resume/download",
        json={
            "resume_data": resume_data,
            "format": "pdf",
            "template_style": "Professional"
        }
    )
    
    if response.status_code == 200:
        size = len(response.content)
        print(f"✅ PDF Download SUCCESS")
        print(f"   Status: {response.status_code}")
        print(f"   Size: {size} bytes")
        print(f"   Content-Type: {response.headers.get('Content-Type')}")
        
        # Save to file
        with open("c:\\Users\\Chait\\OneDrive\\Desktop\\Project\\test_download.pdf", "wb") as f:
            f.write(response.content)
        print(f"   Saved to: test_download.pdf")
        
        # Check if PDF has content (PDF files start with %PDF)
        if response.content.startswith(b'%PDF'):
            print(f"   ✅ Valid PDF format detected")
        else:
            print(f"   ❌ Invalid PDF format (doesn't start with %PDF)")
            
    else:
        print(f"❌ PDF Download FAILED")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        
except Exception as e:
    print(f"❌ PDF Download ERROR: {str(e)}")

# Test 2: DOCX Download
print("\n📄 TEST #2: DOCX Download")
print("-" * 60)

try:
    response = requests.post(
        f"{API_BASE}/api/resume/download",
        json={
            "resume_data": resume_data,
            "format": "docx",
            "template_style": "Professional"
        }
    )
    
    if response.status_code == 200:
        size = len(response.content)
        print(f"✅ DOCX Download SUCCESS")
        print(f"   Status: {response.status_code}")
        print(f"   Size: {size} bytes")
        print(f"   Content-Type: {response.headers.get('Content-Type')}")
        
        # Save to file
        with open("c:\\Users\\Chait\\OneDrive\\Desktop\\Project\\test_download.docx", "wb") as f:
            f.write(response.content)
        print(f"   Saved to: test_download.docx")
        
        # Check if DOCX has content (DOCX files are ZIP, start with PK)
        if response.content.startswith(b'PK'):
            print(f"   ✅ Valid DOCX format detected (ZIP archive)")
        else:
            print(f"   ❌ Invalid DOCX format (doesn't start with PK)")
            
    else:
        print(f"❌ DOCX Download FAILED")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        
except Exception as e:
    print(f"❌ DOCX Download ERROR: {str(e)}")

print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
print("""
If PDFs and DOCX files are successfully generated with content:
✅ PDF/DOCX export is FIXED

For navigation testing:
- The frontend now directly redirects to:
  - cover-letter.html
  - interview-prep.html
  - job-search.html
  
- Without checking /api/resume/actions endpoint
- Navigation data is stored in sessionStorage for the pages to access

Test by clicking the buttons in the resume preview section.
""")
