"""
Frontend Tests: Feature Gating
Tests verify that unimplemented features show proper messages
"""


async def test_job_matching_not_implemented(page):
    """Job matching should show 'Feature Not Yet Implemented'"""
    await page.goto("http://localhost:8000/job-matching.html")
    
    # Check for not implemented message
    message = await page.locator("text=Feature Not Yet Implemented").is_visible()
    assert message, "Job matching should show 'Feature Not Yet Implemented'"
    
    # Verify no search results
    results = await page.locator(".job-listing, .job-item").count()
    assert results == 0, "Job matching should not show any results"


async def test_cover_letter_not_implemented(page):
    """Cover letter should show 'under development'"""
    await page.goto("http://localhost:8000/cover-letter.html")
    
    # Check for under development message
    message = await page.locator("text=/under development|not yet implemented/i").is_visible()
    assert message, "Cover letter should show development message"
    
    # Verify generate button is disabled or hidden
    generate_btn = await page.locator("button:has-text('Generate')").first
    if generate_btn:
        is_disabled = await generate_btn.is_disabled()
        is_hidden = not await generate_btn.is_visible()
        assert is_disabled or is_hidden, "Generate button should be disabled or hidden"


async def test_dashboard_no_duplicate_job_search(page):
    """Dashboard should not have duplicate 'Search Jobs' option"""
    await page.goto("http://localhost:8000/dashboard.html")
    
    # Count "Search Jobs" or "Find Matching Jobs" buttons
    search_buttons = await page.locator("text=/Search Jobs|Find Matching Jobs/i").count()
    
    # Should have only "Find Matching Jobs", not duplicate
    assert search_buttons <= 2, "Should not have duplicate job search options"


async def test_branding_jobsphere(page):
    """UI should use JobSphere branding"""
    await page.goto("http://localhost:8000/")
    
    # Check for JobSphere branding
    branding = await page.locator("text=JobSphere").is_visible()
    assert branding, "Page should display JobSphere branding"


if __name__ == "__main__":
    print("Frontend E2E tests defined. Run with: pytest testing/frontend/ -v")
