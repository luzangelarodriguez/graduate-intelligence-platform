from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from linkedin_jobs_api import LinkedInAPIError, LinkedInJobsClient


def _mask(value: Optional[str]) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}***{value[-4:]}"


def build_report(client_id: Optional[str], client_secret: Optional[str], access_token: Optional[str]) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "has_client_id": bool(client_id),
        "has_client_secret": bool(client_secret),
        "has_access_token": bool(access_token),
        "client_id_preview": _mask(client_id),
        "access_token_preview": _mask(access_token),
        "status": "unknown",
        "notes": [],
        "next_steps": [],
    }

    if not client_id or not client_secret:
        report["status"] = "missing_credentials"
        report["notes"].append("Faltan LINKEDIN_CLIENT_ID y/o LINKEDIN_CLIENT_SECRET.")
        report["next_steps"].append("Carga las credenciales desde variables de entorno o usa --client-id/--client-secret.")
        return report

    client = LinkedInJobsClient.from_values(
        client_id=client_id,
        client_secret=client_secret,
        access_token=access_token,
        allow_missing_credentials=True,
    )

    try:
        token = client._get_access_token()
        report["status"] = "authorized"
        report["token_length"] = len(token)
        report["notes"].append("LinkedIn issued a valid access token.")
        report["next_steps"].append("Ya puedes intentar POST a /simpleJobPostings o GET a /jobPostingStatus.")
    except LinkedInAPIError as exc:
        message = str(exc)
        report["status"] = "denied"
        report["error"] = message
        if "access_denied" in message or "application tokens" in message:
            report["notes"].append(
                "LinkedIn did not authorize application tokens for this app. "
                "The Job Posting API is restricted to approved developers."
            )
            report["next_steps"].append(
                "Request partner or Apply Connect access from LinkedIn Talent Solutions."
            )
            report["next_steps"].append(
                "Confirm with LinkedIn that the app is allowed to use Client Credentials."
            )
        else:
            report["notes"].append("Authentication failed for another reason; review the error detail.")
            report["next_steps"].append("Review the LinkedIn error and validate the credentials.")

    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnose LinkedIn Job Posting API access.")
    parser.add_argument("--client-id", default=None)
    parser.add_argument("--client-secret", default=None)
    parser.add_argument("--access-token", default=None)
    parser.add_argument("--output", default=None, help="Optional JSON file to write the report.")
    args = parser.parse_args(argv)

    client_id = args.client_id or os.getenv("LINKEDIN_CLIENT_ID")
    client_secret = args.client_secret or os.getenv("LINKEDIN_CLIENT_SECRET")
    access_token = args.access_token or os.getenv("LINKEDIN_ACCESS_TOKEN")
    report = build_report(
        client_id=client_id,
        client_secret=client_secret,
        access_token=access_token,
    )

    payload = json.dumps(report, ensure_ascii=False, indent=2, default=str)
    print(payload)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
