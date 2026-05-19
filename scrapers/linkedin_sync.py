from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from linkedin_jobs_api import (
    LinkedInAPIError,
    LinkedInJobsClient,
    build_external_job_id,
    load_config_json,
    print_json,
    read_jobs_csv,
)


def load_jobs(file_path: str) -> List[Dict[str, str]]:
    return read_jobs_csv(file_path)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sync real job records to LinkedIn via the official Job Posting API."
    )
    parser.add_argument("--input", required=True, help="CSV with job_title, company, description, location.")
    parser.add_argument(
        "--config",
        help="Optional JSON config file with LinkedIn settings like company_urn, integration_context and company_apply_url.",
    )
    parser.add_argument("--operation", default="CREATE", choices=["CREATE", "UPDATE", "RENEW", "CLOSE"])
    parser.add_argument("--listing-type", default="BASIC", choices=["BASIC", "PREMIUM"])
    parser.add_argument("--company-apply-url", default=None, help="Fallback apply URL for all jobs.")
    parser.add_argument("--integration-context", default=None, help='LinkedIn organization URN, e.g. urn:li:organization:1234')
    parser.add_argument("--company-urn", default=None, help='LinkedIn company URN, e.g. urn:li:company:1234')
    parser.add_argument("--contract-urn", default=None, help='LinkedIn contract URN for premium jobs, e.g. urn:li:contract:1234')
    parser.add_argument("--poster-email", default=None, help="Optional poster email for promoted jobs.")
    parser.add_argument("--client-id", default=None, help="LinkedIn OAuth client id.")
    parser.add_argument("--client-secret", default=None, help="LinkedIn OAuth client secret.")
    parser.add_argument("--access-token", default=None, help="Optional pre-issued LinkedIn access token.")
    parser.add_argument("--api-base", default=None, help="LinkedIn API base URL.")
    parser.add_argument("--api-version", default=None, help="LinkedIn API version header.")
    parser.add_argument("--status", action="store_true", help="Fetch status after syncing using external job ids.")
    parser.add_argument("--status-only", action="store_true", help="Only fetch status for job ids found in the CSV.")
    parser.add_argument("--dry-run", action="store_true", help="Build the payloads and print them without calling LinkedIn.")
    parser.add_argument("--output", default="linkedin_sync_results.json", help="Write the API result to JSON.")
    args = parser.parse_args(argv)

    config: Dict[str, Any] = {}
    if args.config:
        config = load_config_json(args.config)

    jobs = load_jobs(args.input)
    if not jobs:
        raise LinkedInAPIError("No valid jobs found in the CSV input.")

    company_apply_url = args.company_apply_url or config.get("company_apply_url")
    integration_context = args.integration_context or config.get("integration_context")
    company_urn = args.company_urn or config.get("company_urn")
    contract_urn = args.contract_urn or config.get("contract_urn")
    poster_email = args.poster_email or config.get("poster_email")
    client_id = args.client_id or config.get("client_id")
    client_secret = args.client_secret or config.get("client_secret")
    access_token = args.access_token or config.get("access_token")
    api_base = args.api_base or config.get("api_base")
    api_version = args.api_version or config.get("api_version")

    client = LinkedInJobsClient.from_values(
        client_id=client_id,
        client_secret=client_secret,
        access_token=access_token,
        api_base=api_base,
        api_version=api_version,
        allow_missing_credentials=args.dry_run,
    )

    result: Dict[str, Any] = {
        "loaded_jobs": len(jobs),
        "operation": args.operation.upper(),
        "listing_type": args.listing_type.upper(),
    }

    if args.status_only:
        external_ids = [job.get("job_id") or build_external_job_id(job) for job in jobs]
        result["status"] = client.get_status(external_ids)
        print_json(result)
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return 0

    sync_result = client.batch_sync(
        jobs,
        listing_type=args.listing_type,
        operation=args.operation,
        integration_context=integration_context,
        company_urn=company_urn,
        company_apply_url=company_apply_url,
        contract_urn=contract_urn,
        poster_email=poster_email,
        dry_run=args.dry_run,
    )
    result["sync"] = sync_result

    if args.status:
        external_ids = [job.get("job_id") or build_external_job_id(job) for job in jobs]
        result["status"] = client.get_status(external_ids)

    print_json(result)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
