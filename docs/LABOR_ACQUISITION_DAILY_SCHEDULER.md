# Daily Labor Acquisition Scheduler

This scheduler runs the academic-driven labor acquisition stack once per day.

## Execution script

- `scripts/run_daily_labor_acquisition.py`
- Linux/Railway wrapper: `scripts/run_daily_labor_acquisition.sh`
- Windows wrapper: `scripts/run_daily_labor_acquisition.ps1`

## Sequence

1. Generate academic source plans with `graduate_intelligence_platform.backend.app.academic_job_acquisition`.
2. Run `pipelines.run_labor_acquisition_platform.run_labor_acquisition(...)`.
3. Persist jobs and skills through the existing warehouse path.
4. Materialize metrics and reports.
5. Record the execution manifest and summary artifacts.

## Railway configuration

Use the `railway/acquisition-worker` service with this command:

```sh
bash scripts/run_daily_labor_acquisition.sh
```

Schedule:

- `0 7 * * *` if Railway evaluates cron in UTC.
- `0 2 * * *` if the service is pinned to `America/Bogota`.

Recommended environment variables:

- `DATABASE_URL`
- `DB_SSLMODE=require`
- `PLAYWRIGHT_HEADLESS=true`
- `LOG_LEVEL=INFO`

## GitHub Actions configuration

Workflow:

- `.github/workflows/labor-acquisition-daily.yml`

Schedule:

- `0 7 * * *`

The workflow installs dependencies, installs Chromium for Playwright, and runs the same shell wrapper used by Railway.

## Windows Task Scheduler configuration

Use this command to create the task:

```powershell
schtasks /Create /F /SC DAILY /ST 02:00 /TN "Daily Labor Acquisition" /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Users\SoporteTI\Desktop\SOFTWARE\scripts\run_daily_labor_acquisition.ps1"
```

If the task should run under a different account, set `/RU` and `/RP` explicitly in the same command.

## Error handling

- The scheduler retries the full run automatically.
- Retries default to 2 attempts after the initial run.
- Each failure is logged with the exception stack trace.
- A failed run still writes a summary JSON with the captured error.

## Logs

- `logs/daily_labor_acquisition_YYYYMMDDTHHMMSSZ.log`
- `outputs/labor_acquisition_source_plans.json`
- `outputs/daily_labor_acquisition_summary.json`
- Existing pipeline outputs from `run_labor_acquisition_platform.py`

## Notes

- No new tables are introduced.
- Existing acquisition, jobs, and job_skills persistence paths remain unchanged.
- The scheduler reuses the academic intelligence module as the single source of search plans.
