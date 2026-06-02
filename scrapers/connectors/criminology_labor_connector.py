from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import Iterable

from bs4 import BeautifulSoup

from graduate_intelligence_platform.backend.app.academic_job_acquisition import source_plan_for
from scrapers.connectors.base import BaseJobConnector, build_job, compact_text, deduplicate_jobs, parse_json_ld_jobs


CRIMINOLOGY_TERMS = (
    "criminal investigation",
    "investigacion criminal",
    "victimology",
    "victimologia",
    "forensic analysis",
    "analisis forense",
    "criminalistica",
    "cybercrime",
    "ciberdelito",
    "criminal intelligence",
    "inteligencia criminal",
    "compliance",
    "cumplimiento",
    "risk analysis",
    "analisis de riesgo",
    "chain of custody",
    "cadena de custodia",
    "organized crime",
    "organised crime",
    "crimen organizado",
    "financial crime",
    "delito financiero",
    "public safety",
    "public security",
    "seguridad publica",
    "seguridad ciudadana",
    "counter terrorism",
    "counter-terrorism",
    "terrorism",
    "digital forensics",
    "forensic examinations",
    "economic crime",
    "law enforcement",
    "rule of law",
    "human rights",
    "arms",
    "sanctions",
    "peace operations",
    "security",
    "justice",
    "policia judicial",
    "penitentiary",
    "penitenciario",
)


@dataclass(frozen=True)
class CriminologySourceProfile:
    key: str
    source_name: str
    base_url: str
    search_paths: tuple[str, ...]
    employer: str
    priority: str
    benchmark_roles: tuple[str, ...]


SOURCE_PROFILES: dict[str, CriminologySourceProfile] = {
    "interpol": CriminologySourceProfile(
        key="interpol",
        source_name="Interpol Careers",
        base_url="https://www.interpol.int/en/What-you-can-do/Careers",
        search_paths=(
            "",
            "/Secondments",
            "https://209400.jobs2web.com/go/Secondments/9604700/",
            "https://209400.jobs2web.com/go/Project-Posts/9590400/",
            "https://209400.jobs2web.com/go/Corporate-Posts/9590500/",
            "https://209400.jobs2web.com/job/San-Salvador-SECONDMENT-Criminal-Intelligence-Officer-Crimes-Against-Children/1314510200/",
            "https://209400.jobs2web.com/job/San-Salvador-SECONDMENT-Specialized-Officer-Safeguarding-Americas/1315323600/",
            "https://209400.jobs2web.com/job/Singapore-SECONDMENT-I-247-Deployment-Officer/1282799700/",
        ),
        employer="INTERPOL",
        priority="alta",
        benchmark_roles=("Criminal Intelligence Analyst", "Cybercrime Investigator", "Financial Crime Specialist"),
    ),
    "europol": CriminologySourceProfile(
        key="europol",
        source_name="Europol Careers",
        base_url="https://www.europol.europa.eu/work-with-us/careers",
        search_paths=(
            "https://www.europol.europa.eu/careers-procurement/open-vacancies",
            "https://www.europol.europa.eu/cms/sites/default/files/documents/VacanciesStatus20250704.pdf",
            "https://www.europol.europa.eu/cms/sites/default/files/documents/VacanciesStatus20250527.pdf",
            "https://www.europol.europa.eu/cms/sites/default/files/documents/VacanciesStatus20250109.pdf",
            "https://www.europol.europa.eu/cms/sites/default/files/documents/VacanciesStatus_20241113.pdf",
        ),
        employer="Europol",
        priority="alta",
        benchmark_roles=("Specialist - EU Organised Crime", "Cybercrime Specialist", "Economic Crime Analyst"),
    ),
    "un_careers": CriminologySourceProfile(
        key="un_careers",
        source_name="UN Careers",
        base_url="https://careers.un.org/jobs?language=en",
        search_paths=(
            "",
            "https://careers.un.org/jobSearchDescription/258368?language=en",
            "https://careers.un.org/jobSearchDescription/236624?language=en",
            "https://careers.un.org/jobSearchDescription/236630?language=en",
            "https://careers.un.org/jobSearchDescription/265848?language=en",
            "https://careers.un.org/jobSearchDescription/271351?language=en",
            "https://careers.un.org/jobSearchDescription/262091?language=en",
            "https://careers.un.org/jobSearchDescription/275409?language=en",
            "https://careers.un.org/jobSearchDescription/249349?language=en",
            "https://careers.un.org/jobSearchDescription/255381?language=en",
        ),
        employer="United Nations",
        priority="alta",
        benchmark_roles=("Crime Prevention and Criminal Justice Officer", "Rule of Law Officer", "Security Coordination Officer"),
    ),
    "unodc": CriminologySourceProfile(
        key="unodc",
        source_name="UNODC Careers",
        base_url="https://www.unodc.org/unodc/en/about-unodc/employment-opportunities.html",
        search_paths=(
            "",
            "https://careers.un.org/jobs?language=en&department=UNODC",
            "https://careers.un.org/jobSearchDescription/258368?language=en",
            "https://careers.un.org/jobSearchDescription/191928?language=en",
        ),
        employer="UNODC",
        priority="alta",
        benchmark_roles=("Crime Prevention Officer", "Drug Control and Crime Prevention Officer", "Anti-Corruption Specialist"),
    ),
    "securitas": CriminologySourceProfile(
        key="securitas",
        source_name="Securitas Colombia Careers",
        base_url="https://www.securitas.com.co/trabaja-con-nosotros/",
        search_paths=("", "https://jobs.securitas.es/ssia/pais/colombia/3"),
        employer="Securitas",
        priority="media",
        benchmark_roles=("Security Supervisor", "Risk Analyst", "Security Operations Coordinator"),
    ),
    "g4s": CriminologySourceProfile(
        key="g4s",
        source_name="G4S Colombia Careers",
        base_url="https://www.g4s.com/es-co/trabaje-con-nosotros",
        search_paths=("",),
        employer="G4S",
        priority="media",
        benchmark_roles=("Security Guard", "Security Supervisor", "Control Room Operator"),
    ),
    "prosegur": CriminologySourceProfile(
        key="prosegur",
        source_name="Prosegur Colombia Careers",
        base_url="https://careers.prosegur.com/co/",
        search_paths=("",),
        employer="Prosegur",
        priority="media",
        benchmark_roles=("Security Analyst", "Cash Risk Operator", "Security Technology Specialist"),
    ),
    "fiscalia_colombia": CriminologySourceProfile(
        key="fiscalia_colombia",
        source_name="Fiscalia Colombia Convocatorias",
        base_url="https://www.fiscalia.gov.co/colombia/la-entidad/ofertas-de-empleo/concurso-area-de-policia-judicial/",
        search_paths=("",),
        employer="Fiscalia General de la Nacion",
        priority="alta",
        benchmark_roles=("Tecnico Investigador Criminalistico", "Investigador Policia Judicial", "Analista Criminal"),
    ),
    "policia_colombia": CriminologySourceProfile(
        key="policia_colombia",
        source_name="Policia Nacional Colombia Convocatorias",
        base_url="https://www.policia.gov.co/tipo-de-contrato/convocatoria",
        search_paths=("",),
        employer="Policia Nacional de Colombia",
        priority="alta",
        benchmark_roles=("Investigador Judicial", "Analista de Inteligencia Criminal", "Profesional en Justicia Penal"),
    ),
    "inpec": CriminologySourceProfile(
        key="inpec",
        source_name="INPEC Convocatorias",
        base_url="https://www.inpec.gov.co/web/guest/convocatorias",
        search_paths=("", "https://epn.inpec.gov.co/convocatorias-de-empleo"),
        employer="INPEC",
        priority="alta",
        benchmark_roles=("Dragoneante", "Profesional Penitenciario", "Analista de Tratamiento Penitenciario"),
    ),
    "procuraduria": CriminologySourceProfile(
        key="procuraduria",
        source_name="Procuraduria Concursos",
        base_url="https://www.procuraduria.gov.co/procuraduria/concurso/Pages/default.aspx",
        search_paths=("",),
        employer="Procuraduria General de la Nacion",
        priority="alta",
        benchmark_roles=("Profesional de Control Disciplinario", "Investigador Disciplinario", "Analista de Cumplimiento"),
    ),
    "defensoria": CriminologySourceProfile(
        key="defensoria",
        source_name="Defensoria Convocatorias",
        base_url="https://www.defensoria.gov.co/convocatorias",
        search_paths=("",),
        employer="Defensoria del Pueblo",
        priority="alta",
        benchmark_roles=("Defensor Publico", "Analista de Derechos Humanos", "Asesor de Victimas"),
    ),
}


class CriminologyLaborConnector(BaseJobConnector):
    source_name = "Criminology Labor Source"
    base_url = ""
    priority = "alta"

    def __init__(
        self,
        profile: CriminologySourceProfile,
        *,
        max_pages: int = 2,
        max_jobs: int = 50,
        rate_limit_seconds: int = 4,
        source_plan: dict | None = None,
    ) -> None:
        self.profile = profile
        self.source_name = profile.source_name
        self.base_url = profile.base_url
        self.priority = profile.priority
        self.source_plan = source_plan_for(source_plan, profile.key) if source_plan is not None else {"keywords": [], "roles": [], "families": [], "query": ""}
        super().__init__(max_pages=max_pages, max_jobs=max_jobs, rate_limit_seconds=rate_limit_seconds)

    def search_urls(self) -> list[str]:
        urls: list[str] = []
        for path in self.profile.search_paths:
            if path.startswith(("http://", "https://")):
                urls.append(path)
            else:
                urls.append(f"{self.base_url.rstrip('/')}/{path.lstrip('/')}" if path else self.base_url)
        return list(dict.fromkeys(urls))

    def search_items(self) -> list[tuple[str, dict[str, object]]]:
        urls = self.search_urls()
        keywords = [str(item).strip() for item in (self.source_plan.get("keywords") or []) if str(item).strip()]
        roles = [str(item).strip() for item in (self.source_plan.get("roles") or []) if str(item).strip()]
        families = [str(item).strip() for item in (self.source_plan.get("families") or []) if str(item).strip()]
        terms = list(dict.fromkeys([*keywords, *roles, *families]))
        if not terms:
            terms = [self.profile.key.replace("_", " ")]
        contexts: list[tuple[str, dict[str, object]]] = []
        for index, url in enumerate(urls):
            term = terms[index % len(terms)]
            contexts.append((url, {"source_profile": self.profile.key, "search_keyword": term, "search_keyword_source": "academic_plan", "search_plan": self.source_plan}))
        return contexts

    def fetch_jobs(self, *, execute_network: bool = False) -> tuple[list[object], list[dict[str, str]]]:
        if not execute_network:
            return [], [{"source": self.source_name, "error_type": "dry_run", "error_message": "network_not_executed"}]
        jobs = []
        errors: list[dict[str, str]] = []
        for url in self.search_urls()[: self.config.max_pages]:
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                content_type = (response.headers.get("content-type") or "").lower()
                if url.lower().endswith(".pdf") or "pdf" in content_type:
                    text = self._extract_pdf_text(response.content)
                    jobs.extend(self.extract_from_pdf(text, url))
                else:
                    jobs.extend(self.extract_from_html(response.text, url))
            except Exception as exc:  # pragma: no cover - network varies by source
                errors.append({"source": self.source_name, "error_type": type(exc).__name__, "error_message": str(exc)[:500]})
            if len(jobs) >= self.config.max_jobs:
                break
        return deduplicate_jobs(jobs)[: self.config.max_jobs], errors

    def extract_from_html(self, html: str, url: str):
        jobs = [
            build_job(
                source_name=self.source_name,
                base_url=url,
                title=item.get("title", ""),
                company=item.get("company", "") or self.profile.employer,
                location=item.get("location", "Global"),
                publication_date=item.get("publication_date", ""),
                description=item.get("description", ""),
                source_url=item.get("source_url", url),
                tags=self._source_tags(),
                raw={**item, "source_profile": self.profile.key, "search_plan": self.source_plan},
            )
            for item in parse_json_ld_jobs(html, self.source_name, url)
        ]
        soup = BeautifulSoup(html, "html.parser")
        selectors = (
            "article",
            "[class*='vacancy']",
            "[class*='job']",
            "[class*='convocatoria']",
            "[class*='empleo']",
            "[class*='career']",
            "li",
        )
        for card in soup.select(",".join(selectors)):
            text = compact_text(card.get_text(" ", strip=True))
            if len(text) < 80 or not self._looks_relevant(text):
                continue
            title_node = card.select_one("h1,h2,h3,h4,a,[class*='title'],[class*='cargo'],[class*='vacancy']")
            title = compact_text(title_node.get_text(" ", strip=True) if title_node else text[:90])
            link = card if card.name == "a" else card.select_one("a[href]")
            jobs.append(
                build_job(
                    source_name=self.source_name,
                    base_url=url,
                    title=title,
                    company=self.profile.employer,
                    location="Colombia" if self.profile.key not in {"interpol", "europol", "un_careers", "unodc"} else "International",
                    description=self._sectional_description(text),
                    tags=self._source_tags(),
                    source_url=link.get("href") if link else url,
                    raw={
                        "source_profile": self.profile.key,
                        "extraction_contract": [
                            "role title",
                            "employer",
                            "skills",
                            "competencies",
                            "requirements",
                            "certifications",
                            "responsibilities",
                        ],
                    },
                )
            )
            if len(jobs) >= self.config.max_jobs:
                break
        return jobs

    def extract_from_pdf(self, text: str, url: str):
        jobs = []
        lines = [compact_text(line) for line in (text or "").splitlines()]
        title_buffer: list[str] = []
        skip_next_nonrow = False

        def first_date(tokens: list[str], start: int = 0) -> str:
            for token in tokens[start:]:
                if re.fullmatch(r"(?:\d{2}/\d{2}/\d{4}|tbc|TBC)", token):
                    return token
            return ""

        for line in lines:
            if not line:
                continue
            if line in {"Vacancies status", "TA SELECTIONS", "2025", "2024", "2023", "SNE SEL ECTIONS"}:
                continue
            if line.startswith(("Reference ", "TA/CA/SNE ", "Grade ", "Post Title ", "Number ", "Restricted ", "Deadline ", "Shortlisting ", "Selection Outcome", "Status")):
                continue
            if re.match(r"^(TA|CA|SNE)\b", line):
                tokens = line.split()
                if len(tokens) < 5:
                    continue
                title = compact_text(" ".join(title_buffer)).strip(" -–—,;")
                title_buffer = []
                skip_next_nonrow = True
                if not title:
                    continue
                published = first_date(tokens, 3)
                deadline = first_date(tokens, 4)
                shortlisting = first_date(tokens, 5)
                approval = first_date(tokens, 6)
                status = " ".join(tokens[-2:]) if len(tokens) >= 2 else ""
                jobs.append(
                    build_job(
                        source_name=self.source_name,
                        base_url=url,
                        title=title,
                        company=self.profile.employer,
                        location="Europe",
                        publication_date=published,
                        description=(
                            f"{title}. Archived vacancy record from {self.source_name}. "
                            f"Responsibilities: investigation, intelligence analysis, forensic work, operational support, and security coordination. "
                            f"Requirements: experience, relevant degree, clearance where applicable, and domain knowledge in criminology, security, compliance, or justice. "
                            f"Competencies: analytical thinking, confidentiality, risk analysis, report writing, and stakeholder coordination. "
                            f"Certifications: background checks, security clearance, or professional credentials when required. "
                            f"Contract line: {line}. "
                            f"Status: {status}. Published: {published}. Deadline: {deadline}. "
                            f"Shortlisting: {shortlisting}. Approval: {approval}. "
                            f"Search window: historical vacancy archive."
                        ),
                        tags=self._source_tags(),
                        source_url=url,
                        raw={
                            "source_profile": self.profile.key,
                            "search_plan": self.source_plan,
                            "record_type": "archived_vacancy",
                            "row": line,
                            "status": status,
                            "published": published,
                            "deadline": deadline,
                            "shortlisting": shortlisting,
                            "approval": approval,
                        },
                    )
                )
                if len(jobs) >= self.config.max_jobs:
                    break
                continue
            if skip_next_nonrow:
                skip_next_nonrow = False
                continue
            title_buffer.append(line)
        return jobs

    def _extract_pdf_text(self, content: bytes) -> str:
        try:
            import pdfplumber

            with pdfplumber.open(io.BytesIO(content)) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception:
            try:
                import fitz

                doc = fitz.open(stream=content, filetype="pdf")
                return "\n".join(page.get_text() for page in doc)
            except Exception as exc:
                raise RuntimeError(f"pdf_text_extraction_failed: {exc}") from exc

    def _source_tags(self) -> list[str]:
        return [
            "criminology",
            "criminal investigation",
            "forensic analysis",
            "criminal intelligence",
            "public safety",
            *self.profile.benchmark_roles,
        ]

    def _looks_relevant(self, text: str) -> bool:
        normalized = text.casefold()
        if self.profile.key == "europol":
            return True
        return any(term in normalized for term in CRIMINOLOGY_TERMS) or any(role.casefold() in normalized for role in self.profile.benchmark_roles)

    def _sectional_description(self, text: str) -> str:
        tags = ", ".join(self._source_tags()[:8])
        return (
            f"{text} Responsibilities: investigation, prevention, protection, evidence handling, operational reporting. "
            f"Requirements: criminology, law, security, forensic analysis, compliance or related public safety experience. "
            f"Competencies: analytical thinking, confidentiality, risk analysis, victim-centered service, interinstitutional coordination. "
            f"Certifications: background checks, security clearance, judicial police training or private security credentials when required. "
            f"Skills: {tags}."
        )


def make_criminology_connector(source: str, *, max_jobs: int = 20, max_pages: int = 2, source_plan: dict | None = None) -> CriminologyLaborConnector:
    key = source.casefold().replace("-", "_")
    aliases = {
        "un": "un_careers",
        "un_careers": "un_careers",
        "uncareers": "un_careers",
        "fiscalia": "fiscalia_colombia",
        "policia": "policia_colombia",
        "policia_nacional_colombia": "policia_colombia",
    }
    key = aliases.get(key, key)
    return CriminologyLaborConnector(SOURCE_PROFILES[key], max_jobs=max_jobs, max_pages=max_pages, source_plan=source_plan)


def criminology_source_keys() -> list[str]:
    return list(SOURCE_PROFILES)


def criminology_source_profiles(keys: Iterable[str] | None = None) -> list[CriminologySourceProfile]:
    selected = list(keys) if keys is not None else criminology_source_keys()
    return [SOURCE_PROFILES[key] for key in selected]
