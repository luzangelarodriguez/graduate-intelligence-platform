# LinkedIn Access Review

Current status:

- The app returned `access_denied` when requesting a token with `client_credentials`.
- LinkedIn said the application is not allowed to create application tokens.
- The official Job Posting API is restricted to approved developers.
- LinkedIn documentation says new Job Posting partnerships are not currently being accepted and access should be requested through Apply Connect.

What is still needed for the official integration:

1. A LinkedIn-approved app for `client_credentials` authentication.
2. Partner or Apply Connect access enabled by LinkedIn Talent Solutions.
3. Valid credentials and permission to use `simpleJobPostings` and `jobPostingStatus`.
4. `companyApplyUrl` and, depending on the job type, `integrationContext`, `company_urn`, or `contract_urn`.

Useful files:

- `linkedin_sync.py` to sync real jobs into LinkedIn.
- `linkedin_access_check.py` to diagnose access.
- `public_jobs_scraper.py` to keep extracting public jobs from open portals.

