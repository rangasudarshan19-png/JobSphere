# JobSphere - Project Documentation

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.1.0 | Feb 16, 2026 | Reviews system, AI prompt upgrades, OpenRouter fallbacks |
| 2.0.0 | Feb 8, 2026 | CSS design system v2, app.js v2, XSS fixes, comprehensive testing |
| 1.0.0 | Jan 2026 | Initial release with all core features |

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────┐
│                  Frontend (Vanilla JS)               │
│  14 HTML Pages + app.js v2.0 + Design System CSS     │
├─────────────────────────────────────────────────────┤
│                FastAPI Backend (Python 3.13+)         │
│  10 Routers │ 18 Services │ 6 Models │ Middleware     │
├─────────────────────────────────────────────────────┤
│              SQLite Database (Development)            │
│  7 Tables: users, applications, reviews, etc.         │
├─────────────────────────────────────────────────────┤
│              External Services                        │
│  7 AI Providers │ 5 Job APIs │ SMTP Email             │
└─────────────────────────────────────────────────────┘
```

### Backend Architecture

**Routers (10):**
| Router | Prefix | Purpose |
|--------|--------|---------|
| auth.py | /api/auth | Authentication, registration, profile |
| applications.py | /api/applications | Job application CRUD |
| jobs.py | /api/jobs | Multi-source job search |
| ai_features.py | /api/ai | AI-powered features (resume, interview, cover letter) |
| resume.py | /api/resume | Resume upload, parsing, export |
| analytics.py | /api/analytics | Application statistics & trends |
| admin.py | /api/admin | Admin panel management |
| reviews.py | /api/reviews | User reviews CRUD |
| job_matching.py | /api/job-matching | Resume-job matching |
| scraper.py | /api/scraper | Job scraping |

**Services (18):**
| Service | Purpose |
|---------|---------|
| interview_generator.py | AI question generation & answer evaluation |
| resume_generator.py | AI resume generation with company research |
| resume_analyzer.py | Resume analysis & scoring |
| resume_parser.py | Resume file parsing (PDF, DOCX) |
| resume_export.py | Resume export (PDF, DOCX) |
| multi_ai_service.py | AI provider orchestration |
| job_matcher.py | Job-resume matching engine |
| skills_gap_analyzer.py | Skills gap identification |
| multi_search_service.py | Multi-source job aggregation |
| job_search_service.py | Job search coordination |
| job_search_aggregator.py | Search result aggregation |
| job_scraper.py | Web scraping for jobs |
| adzuna_service.py | Adzuna API integration |
| remotive_service.py | Remotive API integration |
| themuse_service.py | The Muse API integration |
| email_service.py | Email notifications (SMTP) |
| notification_service.py | In-app notifications |
| otp_service.py | OTP verification |

**Models (6):**
| Model | Table | Key Fields |
|-------|-------|------------|
| User | users | id, email, full_name, hashed_password, is_admin |
| Application | applications | id, user_id, job_title, company, status, applied_date |
| Review | reviews | id, user_id, rating (1-5), title, content, reviewer_name |
| Notification | notifications | id, user_id, type, message, is_read |
| AdminAuditLog | admin_audit_logs | id, admin_id, action, target |
| EnhancedResume | enhanced_resumes | id, user_id, resume_data, format |

---

## Database Schema

### Reviews Table (Added v2.1.0)
```sql
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    reviewer_name VARCHAR(100) NOT NULL,
    is_approved INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX idx_reviews_user ON reviews(user_id);
CREATE INDEX idx_reviews_approved ON reviews(is_approved);
```

### Key Constraints
- **One review per user** - Enforced at API level (409 Conflict on duplicate)
- **Rating range** - CHECK constraint ensures 1-5
- **Cascade delete** - Reviews deleted when user account is deleted

---

## AI Integration

### Provider Configuration

All AI features use a multi-provider fallback system. If the primary provider fails, the system automatically tries the next available provider.

### Model: `gemini-2.0-flash`
- Used across all Gemini-powered features
- Fixed from deprecated `gemini-2.0-flash-exp` in v2.1.0
- Updated in 6 files, 14 occurrences

### OpenRouter Fallback (Added v2.1.0)
OpenRouter (`deepseek/deepseek-chat`) was added as a fallback to all major AI generation methods:

| Method | Primary | Fallback |
|--------|---------|----------|
| `generate_questions()` | OpenRouter → Gemini → Groq → ... | Full chain |
| `generate_answer()` | Gemini | OpenRouter fallback |
| `generate_cover_letter()` | Gemini | OpenRouter fallback |
| `analyze_resume()` | Gemini | OpenRouter fallback |
| `generate_improved_resume()` | Gemini | OpenRouter fallback |
| Job Matching | Gemini | OpenRouter fallback |
| Skills Gap Analysis | Gemini | OpenRouter fallback |

### AI Prompt Quality (Upgraded v2.1.0)
All 19 AI prompts across 7 files were upgraded to:
- Include explicit output format specification (JSON structure)
- Add role-specific technical depth requirements
- Request actionable, specific content (no generic advice)
- Include difficulty calibration and industry context
- Remove all hardcoded template answers from interview generator

### Hardcoded Template Removal (v2.1.0)
Removed 200+ lines of hardcoded sample answers from `interview_generator.py`. The AI now generates all answers dynamically, preventing users from seeing identical template responses.

---

## Reviews System (v2.1.0)

### Overview
Users can write, edit, and delete reviews of the JobSphere platform. Reviews are displayed publicly on the landing page and managed from the user's profile page.

### Architecture
- **Backend:** `reviews.py` router with full CRUD, Pydantic validation
- **Database:** `reviews` table with FK to users, rating constraint (1-5)
- **Landing Page (index.html):** Read-only display of all approved reviews
- **Profile Page (profile.html):** Full review management (write/edit/delete)
- **Dashboard (dashboard.html):** Quick action link to profile review section

### API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | /api/reviews | No | Get all approved reviews + avg rating |
| POST | /api/reviews | Yes | Submit new review (one per user) |
| GET | /api/reviews/mine | Yes | Get current user's review |
| PUT | /api/reviews/{id} | Yes | Update own review |
| DELETE | /api/reviews/{id} | Yes | Delete own review |

### Frontend Flow
1. **Landing page** shows all reviews in a card grid with star ratings, summary bar (avg rating + count)
2. **Profile page** has "My Review" section:
   - Empty state with "Write a Review" button if no review exists
   - Existing review display with Edit and Delete buttons
   - Modal form with interactive star rating, title, content, display name
   - Delete confirmation modal
3. **Dashboard** has "Write a Review" quick action linking to `profile.html#my-review`

### Security
- One review per user (409 Conflict if duplicate attempted)
- Users can only edit/delete their own reviews (ownership check via user_id)
- XSS prevention via `escapeHtml()` / `Toast.escape()` on all user content
- Cascade delete when user account is removed

---

## Frontend Architecture

### Pages (14)

| Page | Auth Required | Purpose |
|------|---------------|---------|
| index.html | No | Landing page, public reviews display |
| signup.html | No | User registration |
| login.html | No | User login |
| dashboard.html | Yes | Main dashboard, stats, quick actions |
| kanban-tracker.html | Yes | Kanban board (drag & drop) |
| job-tracker.html | Yes | List view with filters |
| job-search.html | Yes | Multi-source job search |
| ai-resume-builder.html | Yes | AI resume generation |
| cover-letter.html | Yes | AI cover letter generation |
| interview-prep.html | Yes | AI interview practice |
| job-matching.html | Yes | Resume-job matching |
| analytics.html | Yes | Charts and statistics |
| profile.html | Yes | User settings + review management |
| admin.html | Admin | Admin panel |

### Design System
- **Theme:** Dark mode with indigo accent (`#6366f1`)
- **CSS:** `main.css` (variables, layout, forms) + `components.css` (modals, toasts, cards)
- **JS:** `app.js` v2.0 with `Auth`, `Toast`, `Modal`, `Loading`, `Utils` modules
- **No framework dependencies** - Pure vanilla HTML/CSS/JS

### Key JS Patterns
```javascript
// API base URL auto-detection
const API_BASE = (() => {
    const h = window.location.hostname;
    return (!h || h === 'localhost' || h === '127.0.0.1')
        ? 'http://127.0.0.1:8000' : window.location.origin;
})();

// Authenticated fetch
Auth.fetchWithAuth(`${API_BASE}/api/endpoint`, { method: 'GET' });

// Token management
Auth.getToken();     // Get JWT from sessionStorage
Auth.requireAuth();  // Redirect to login if not authenticated

// Toast notifications
Toast.show('Success!', 'success');
Toast.show('Error occurred', 'error');

// XSS prevention
Toast.escape(userInput);
```

---

## Security Features

### Authentication
- JWT tokens with configurable expiration
- Bcrypt password hashing (12 rounds)
- Session management via sessionStorage
- Protected API endpoints via `get_current_user` dependency

### Middleware
- **Security Headers** - X-Content-Type-Options, X-Frame-Options, CSP
- **Request Tracking** - Unique request IDs for log correlation
- **CORS** - Configurable allowed origins

### XSS Prevention
- All user-generated content escaped before rendering
- `Toast.escape()` in authenticated pages
- `escapeHtml()` in public pages
- No `innerHTML` with unsanitized data

### Input Validation
- Pydantic field validators on all API inputs
- Client-side validation with min/max length checks
- SQL injection prevention via SQLAlchemy ORM

---

## Testing

### Quick Start
```bash
cd backend/python-service
python -m pytest tests/ -v --tb=short
```

### Current Results
- **51/51 tests passing**
- **32.8% code coverage** (30% threshold met)
- Tests cover: auth, applications, analytics, email, integration workflows

### Test Credentials
| Role | Email | Password |
|------|-------|----------|
| User | rangasudarshan19@gmail.com | Sudarshan@1 |
| Admin | admin@jobtracker.com | admin123 |

See [TESTING_GUIDE.md](guides/TESTING_GUIDE.md) for comprehensive testing documentation.

---

## Deployment

### Development
```bash
cd backend/python-service
python main.py
# Server: http://127.0.0.1:8000
# Frontend: http://127.0.0.1:8000/frontend/index.html
```

### Windows Quick Launch
- `LAUNCH_JOBSPHERE.bat` - Start server + open browser
- `CHECK_SERVER.bat` - Verify server status

### Required Environment Variables
```env
SECRET_KEY=your-jwt-secret
GEMINI_API_KEY=your-gemini-key
OPENROUTER_API_KEY=your-openrouter-key
```

### Optional Environment Variables
```env
GROQ_API_KEY=your-groq-key
JSEARCH_API_KEY=your-jsearch-key
ADZUNA_APP_ID=your-adzuna-id
ADZUNA_API_KEY=your-adzuna-key
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

---

## Changelog (v2.1.0 - February 16, 2026)

### New Features
- **Reviews System** - Full CRUD for user reviews with star ratings
  - Backend: `review.py` model + `reviews.py` router (5 endpoints)
  - Frontend: Public display on landing page, management in profile
  - Database: `reviews` table with constraints and indexes

### Improvements
- **AI Prompts Upgraded** - All 19 prompts across 7 files enhanced for better output quality
- **OpenRouter Fallback** - Added to `generate_answer`, `generate_cover_letter`, `analyze_resume`, `generate_improved_resume`
- **Gemini Model Fixed** - Updated from deprecated `gemini-2.0-flash-exp` to `gemini-2.0-flash` (14 occurrences, 6 files)
- **Template Answers Removed** - Eliminated 200+ lines of hardcoded interview answers

### Bug Fixes
- Fixed XSS vulnerabilities in user content rendering
- Fixed CSS design system inconsistencies across pages
- Fixed app.js v2.0 module loading issues

---

**Last Updated:** February 16, 2026  
**Version:** 2.1.0  
**Developer:** Sudarshan Ranga | BITS Pilani | 2025-2026
