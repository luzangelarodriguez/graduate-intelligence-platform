# Acquisition worker

Runs `scripts/run_daily_labor_acquisition.sh` for the daily market-driven acquisition job.

Recommended Railway cron schedule:

- `0 7 * * *` UTC

If the Railway service is configured with `America/Bogota` as its execution timezone, use:

- `0 2 * * *`

Command:

```sh
bash scripts/run_daily_labor_acquisition.sh
```
