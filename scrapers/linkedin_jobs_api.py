from __future__ import annotations

import csv
import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence

import requests


LINKEDIN_DEFAULT_API_BASE = "https://api.linkedin.com/rest"
LINKEDIN_DEFAULT_VERSION = "202603"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_MAX_BATCH_SIZE = 100


class LinkedInAPIError(RuntimeError):
    pass


def _now_millis() -> int:
    return int(time.time() * 1000)


def _chunked(items: Sequence[Dict[str, Any]], size: int) -> Iterator[List[Dict[str, Any]]]:
    for index in range(0, len(items), size):
        yield list(items[index : index + size])


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_header_name(value: Any) -> str:
    text = _clean(value).lower()
    return "".join(ch for ch in text if ch.isalnum())


def _normalize_location(value: str) -> str:
    return " ".join(value.split()).strip()


def build_external_job_id(job: Dict[str, Any]) -> str:
    source = "|".join(
        [
            _clean(job.get("job_id")),
            _clean(job.get("job_title")),
            _clean(job.get("company")),
            _clean(job.get("location")),
            _clean(job.get("description")),
        ]
    )
    digest = hashlib.sha1(source.encode("utf-8")).hexdigest()
    return f"job-{digest[:20]}"


def _guess_workplace_types(location: str) -> Optional[List[str]]:
    text = location.lower()
    if any(token in text for token in ("remote", "remoto", "remota")):
        return ["remote"]
    if any(token in text for token in ("hybrid", "hibrido", "híbrido")):
        return ["hybrid"]
    return None


def read_jobs_csv(file_path: str) -> List[Dict[str, str]]:
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    text = path.read_text(encoding="utf-8-sig")
    sample = text[:4096]
    delimiter = ","
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=";,\t|").delimiter
    except csv.Error:
        pass
    reader = csv.DictReader(text.splitlines(), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError("CSV file does not contain headers.")
    required = {"jobtitle", "company", "description", "location"}
    normalized = {_normalize_header_name(name): name for name in reader.fieldnames}
    missing = [field for field in required if field not in normalized]
    if missing:
        raise ValueError("CSV file is missing required columns: " + ", ".join(sorted(missing)))
    jobs: List[Dict[str, str]] = []
    for row in reader:
        job = {
            "job_title": _clean(row.get(normalized["jobtitle"])),
            "company": _clean(row.get(normalized["company"])),
            "description": _clean(row.get(normalized["description"])),
            "location": _clean(row.get(normalized["location"])),
            "date": _clean(row.get(normalized.get("date", ""), "")),
            "source": _clean(row.get(normalized.get("source", ""), "")) or path.stem,
            "job_id": _clean(row.get(normalized.get("jobid", ""), "")),
        }
        if not all(job[field] for field in ("job_title", "company", "description", "location")):
            continue
        jobs.append(job)
    return jobs


@dataclass
class LinkedInConfig:
    client_id: str
    client_secret: str
    access_token: Optional[str] = None
    api_base: str = LINKEDIN_DEFAULT_API_BASE
    api_version: str = LINKEDIN_DEFAULT_VERSION


class LinkedInJobsClient:
    def __init__(self, config: LinkedInConfig) -> None:
        self.config = config
        self._token: Optional[str] = config.access_token or None
        self._token_expires_at: float = 0.0

    @classmethod
    def from_values(
        cls,
        *,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        api_base: Optional[str] = None,
        api_version: Optional[str] = None,
        allow_missing_credentials: bool = False,
    ) -> "LinkedInJobsClient":
        client_id = _clean(client_id) or os.getenv("LINKEDIN_CLIENT_ID", "").strip()
        client_secret = _clean(client_secret) or os.getenv("LINKEDIN_CLIENT_SECRET", "").strip()
        access_token = _clean(access_token) or os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip() or None
        api_base = _clean(api_base) or os.getenv("LINKEDIN_API_BASE", LINKEDIN_DEFAULT_API_BASE).strip() or LINKEDIN_DEFAULT_API_BASE
        api_version = _clean(api_version) or os.getenv("LINKEDIN_API_VERSION", LINKEDIN_DEFAULT_VERSION).strip() or LINKEDIN_DEFAULT_VERSION
        has_token = bool(access_token)
        if (not client_id or not client_secret) and not has_token:
            if allow_missing_credentials:
                return cls(
                    LinkedInConfig(
                        client_id=client_id,
                        client_secret=client_secret,
                        access_token=access_token,
                        api_base=api_base.rstrip("/"),
                        api_version=api_version,
                    )
                )
            raise LinkedInAPIError(
                "Missing LinkedIn credentials. Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET."
            )
        return cls(
            LinkedInConfig(
                client_id=client_id,
                client_secret=client_secret,
                access_token=access_token,
                api_base=api_base.rstrip("/"),
                api_version=api_version,
            )
        )

    @classmethod
    def from_env(cls, *, allow_missing_credentials: bool = False) -> "LinkedInJobsClient":
        return cls.from_values(allow_missing_credentials=allow_missing_credentials)

    def _get_access_token(self) -> str:
        if self._token and time.time() < self._token_expires_at:
            return self._token
        if self._token and self._token_expires_at == 0:
            self._token_expires_at = time.time() + 60 * 25
            return self._token

        response = requests.post(
            LINKEDIN_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
            },
            timeout=30,
        )
        if response.status_code >= 400:
            detail = response.text.strip()
            try:
                payload = response.json()
                if payload.get("error") == "access_denied":
                    detail = (
                        f"{detail} "
                        "(LinkedIn rejected application tokens for this app. "
                        "The app likely needs partner access or application-token permissions.)"
                    )
            except Exception:
                pass
            raise LinkedInAPIError(
                f"LinkedIn token request failed ({response.status_code}): {detail}"
            )
        payload = response.json()
        token = _clean(payload.get("access_token"))
        expires_in = int(payload.get("expires_in") or 1800)
        if not token:
            raise LinkedInAPIError("LinkedIn token response did not include access_token.")
        self._token = token
        self._token_expires_at = time.time() + max(60, expires_in - 120)
        return token

    def _headers(self, method: str) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Linkedin-Version": self.config.api_version,
            "X-Restli-Protocol-Version": "2.0.0",
        }
        if method.upper() == "POST":
            headers["X-Restli-Method"] = "batch_create"
        return headers

    def _build_element(
        self,
        job: Dict[str, Any],
        *,
        listing_type: str = "BASIC",
        operation: str = "CREATE",
        integration_context: Optional[str] = None,
        company_urn: Optional[str] = None,
        company_apply_url: Optional[str] = None,
        contract_urn: Optional[str] = None,
        poster_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        title = _clean(job.get("job_title"))
        description = _clean(job.get("description"))
        location = _normalize_location(_clean(job.get("location")))
        if not title or not description or not location:
            raise LinkedInAPIError("Each job must include job_title, description and location.")

        element: Dict[str, Any] = {
            "externalJobPostingId": _clean(job.get("job_id")) or build_external_job_id(job),
            "listingType": listing_type.upper(),
            "title": title[:200],
            "description": description,
            "listedAt": int(job.get("listed_at") or job.get("listedAt") or _now_millis()),
            "jobPostingOperationType": operation.upper(),
            "location": location,
        }

        apply_url = _clean(job.get("company_apply_url")) or _clean(company_apply_url)
        if apply_url:
            element["companyApplyUrl"] = apply_url
        elif operation.upper() == "CREATE":
            raise LinkedInAPIError(
                "LinkedIn Job Posting API requires companyApplyUrl for CREATE operations. "
                "Provide --company-apply-url or a company_apply_url column."
            )

        if integration_context:
            element["integrationContext"] = integration_context
        if company_urn:
            element["company"] = company_urn
        if contract_urn:
            element["contract"] = contract_urn
        if poster_email:
            element["posterEmail"] = poster_email

        workplace_types = job.get("workplace_types") or job.get("workplaceTypes")
        if isinstance(workplace_types, str):
            parsed = [item.strip() for item in workplace_types.split(",") if item.strip()]
            if parsed:
                element["workplaceTypes"] = parsed
        elif isinstance(workplace_types, list) and workplace_types:
            element["workplaceTypes"] = [str(item).strip() for item in workplace_types if str(item).strip()]
        else:
            inferred = _guess_workplace_types(location)
            if inferred:
                element["workplaceTypes"] = inferred

        employment_status = _clean(job.get("employment_status") or job.get("employmentStatus"))
        if employment_status:
            element["employmentStatus"] = employment_status.upper().replace(" ", "_")

        categories = job.get("categories")
        if isinstance(categories, list) and categories:
            element["categories"] = [str(item).strip() for item in categories if str(item).strip()]

        skills_description = _clean(job.get("skills_description") or job.get("skillsDescription"))
        if skills_description:
            element["skillsDescription"] = skills_description

        return element

    def batch_sync(
        self,
        jobs: Sequence[Dict[str, Any]],
        *,
        listing_type: str = "BASIC",
        operation: str = "CREATE",
        integration_context: Optional[str] = None,
        company_urn: Optional[str] = None,
        company_apply_url: Optional[str] = None,
        contract_urn: Optional[str] = None,
        poster_email: Optional[str] = None,
        dry_run: bool = False,
    ) -> List[Dict[str, Any]]:
        payloads: List[Dict[str, Any]] = []
        for job in jobs:
            payloads.append(
                self._build_element(
                    job,
                    listing_type=listing_type,
                    operation=operation,
                    integration_context=integration_context,
                    company_urn=company_urn,
                    company_apply_url=company_apply_url,
                    contract_urn=contract_urn,
                    poster_email=poster_email,
                )
            )

        if dry_run:
            return [{"dry_run": True, "elements": payloads}]

        results: List[Dict[str, Any]] = []
        for batch_index, batch in enumerate(_chunked(payloads, LINKEDIN_MAX_BATCH_SIZE), start=1):
            response = requests.post(
                f"{self.config.api_base}/simpleJobPostings",
                headers=self._headers("POST"),
                json={"elements": batch},
                timeout=60,
            )
            body: Any
            try:
                body = response.json()
            except Exception:
                body = response.text
            if response.status_code >= 400:
                raise LinkedInAPIError(
                    f"LinkedIn job sync failed for batch {batch_index} ({response.status_code}): {body}"
                )
            results.append(
                {
                    "batch": batch_index,
                    "submitted": len(batch),
                    "status_code": response.status_code,
                    "response": body,
                }
            )
        return results

    def get_status(self, external_ids: Sequence[str]) -> Dict[str, Any]:
        ids = [str(item).strip() for item in external_ids if str(item).strip()]
        if not ids:
            raise LinkedInAPIError("At least one external job posting id is required.")
        response = requests.get(
            f"{self.config.api_base}/jobPostingStatus",
            headers=self._headers("GET"),
            params=[("ids", item) for item in ids],
            timeout=60,
        )
        try:
            body: Any = response.json()
        except Exception:
            body = response.text
        if response.status_code >= 400:
            raise LinkedInAPIError(f"LinkedIn job status lookup failed ({response.status_code}): {body}")
        return {"status_code": response.status_code, "response": body}


def load_config_json(path: str) -> Dict[str, Any]:
    config_path = Path(path).expanduser().resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    payload = json.loads(config_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("LinkedIn config file must contain a JSON object.")
    return payload


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))
