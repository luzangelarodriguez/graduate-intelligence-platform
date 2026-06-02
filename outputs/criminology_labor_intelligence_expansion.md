# Criminology Labor Intelligence Expansion

- Generated at: 2026-06-01 23:16:01Z
- Platform decision: reuses the existing labor acquisition platform, `StructuredConnectorCrawler`, `BaseJobConnector`, and the current bronze/silver/gold observatory feed path.
- New engines created: none.
- Extraction contract: role title, employer, skills, competencies, requirements, certifications, responsibilities.
- Feed targets: skills_master, skills_alias, semantic_role_graph, curriculum_gap_observatory, recommendation_observatory.

## New Sources

- Interpol Careers (`interpol`): https://www.interpol.int/en/What-you-can-do/Careers | employer: INTERPOL | priority: alta | crawl paths: https://www.interpol.int/en/What-you-can-do/Careers, https://www.interpol.int/en/What-you-can-do/Careers/Secondments
- Europol Careers (`europol`): https://www.europol.europa.eu/work-with-us/careers | employer: Europol | priority: alta | crawl paths: https://www.europol.europa.eu/work-with-us/careers, https://www.europol.europa.eu/work-with-us/careers/open-vacancies
- UN Careers (`un_careers`): https://careers.un.org/jobs?language=en | employer: United Nations | priority: alta | crawl paths: https://careers.un.org/jobs?language=en
- UNODC Careers (`unodc`): https://www.unodc.org/unodc/en/about-unodc/employment-opportunities.html | employer: UNODC | priority: alta | crawl paths: https://www.unodc.org/unodc/en/about-unodc/employment-opportunities.html, https://careers.un.org/jobs?language=en&department=UNODC
- Securitas Colombia Careers (`securitas`): https://www.securitas.com.co/trabaja-con-nosotros/ | employer: Securitas | priority: media | crawl paths: https://www.securitas.com.co/trabaja-con-nosotros/, https://jobs.securitas.es/ssia/pais/colombia/3
- G4S Colombia Careers (`g4s`): https://www.g4s.com/es-co/trabaje-con-nosotros | employer: G4S | priority: media | crawl paths: https://www.g4s.com/es-co/trabaje-con-nosotros
- Prosegur Colombia Careers (`prosegur`): https://careers.prosegur.com/co/ | employer: Prosegur | priority: media | crawl paths: https://careers.prosegur.com/co/
- Fiscalia Colombia Convocatorias (`fiscalia_colombia`): https://www.fiscalia.gov.co/colombia/la-entidad/ofertas-de-empleo/concurso-area-de-policia-judicial/ | employer: Fiscalia General de la Nacion | priority: alta | crawl paths: https://www.fiscalia.gov.co/colombia/la-entidad/ofertas-de-empleo/concurso-area-de-policia-judicial/
- Policia Nacional Colombia Convocatorias (`policia_colombia`): https://www.policia.gov.co/tipo-de-contrato/convocatoria | employer: Policia Nacional de Colombia | priority: alta | crawl paths: https://www.policia.gov.co/tipo-de-contrato/convocatoria
- INPEC Convocatorias (`inpec`): https://www.inpec.gov.co/web/guest/convocatorias | employer: INPEC | priority: alta | crawl paths: https://www.inpec.gov.co/web/guest/convocatorias, https://epn.inpec.gov.co/convocatorias-de-empleo
- Procuraduria Concursos (`procuraduria`): https://www.procuraduria.gov.co/procuraduria/concurso/Pages/default.aspx | employer: Procuraduria General de la Nacion | priority: alta | crawl paths: https://www.procuraduria.gov.co/procuraduria/concurso/Pages/default.aspx
- Defensoria Convocatorias (`defensoria`): https://www.defensoria.gov.co/convocatorias | employer: Defensoria del Pueblo | priority: alta | crawl paths: https://www.defensoria.gov.co/convocatorias

## New Roles

- Analista Criminal
- Analista de Cumplimiento
- Analista de Derechos Humanos
- Analista de Inteligencia Criminal
- Analista de Tratamiento Penitenciario
- Anti-Corruption Specialist
- Asesor de Victimas
- Cash Risk Operator
- Compliance Analyst
- Control Room Operator
- Crime Prevention Officer
- Crime Prevention and Criminal Justice Officer
- Criminal Intelligence Analyst
- Cybercrime Investigator
- Cybercrime Specialist
- Defensor Publico
- Dragoneante
- Drug Control and Crime Prevention Officer
- Economic Crime Analyst
- Financial Crime Specialist
- Forensic Analyst
- Investigador Disciplinario
- Investigador Judicial
- Investigador Policia Judicial
- Profesional Penitenciario
- Profesional de Control Disciplinario
- Profesional en Justicia Penal
- Public Security Advisor
- Risk Analyst
- Rule of Law Officer
- Security Analyst
- Security Coordination Officer
- Security Guard
- Security Operations Coordinator
- Security Supervisor
- Security Technology Specialist
- Specialist - EU Organised Crime
- Tecnico Investigador Criminalistico
- Victim Assistance Specialist

## New Skills

- criminal investigation
- victimology
- forensic analysis
- cybercrime
- criminal intelligence
- compliance
- risk analysis
- chain of custody
- organized crime
- financial crime
- public safety
- criminal profiling
- criminal policy
- crime prevention
- public security
- criminal analysis
- penitentiary systems
- Criminal Policy

## New Graph Edges

- Forensic Analyst -> Criminal Intelligence Analyst: shared skills = forensic analysis, chain of custody, criminal intelligence
- Criminal Intelligence Analyst -> Cybercrime Investigator: shared skills = criminal intelligence, cybercrime, risk analysis
- Cybercrime Investigator -> Financial Crime Specialist: shared skills = cybercrime, financial crime, chain of custody
- Compliance Analyst -> Risk Analyst: shared skills = compliance, risk analysis, financial crime
- Victim Assistance Specialist -> Public Security Advisor: shared skills = victimology, public safety, crime prevention
- Investigador Policia Judicial -> Analista Criminal: shared skills = criminal investigation, criminal analysis, chain of custody
- Profesional Penitenciario -> Public Security Advisor: shared skills = penitentiary systems, public safety, risk analysis

## New Benchmark Coverage

- Reference program: Benchmark de criminología y seguridad
- Benchmark institutions covered: 9
- Core competencies covered: análisis de evidencia, métodos de investigación criminal, victimología y atención a víctimas, prevención del delito, análisis criminal, cadena de custodia, criminal intelligence, seguridad pública, crimen organizado, crimen financiero, Criminal Investigation, Victimology, Criminal Profiling, Criminal Policy, Crime Prevention, Public Safety, Public Security, Cybercrime, Forensic Analysis, Chain of Custody, Risk Analysis, Compliance
- Priority skills covered: criminal investigation, victimology, criminal profiling, criminal intelligence, crime prevention, public safety, public security, cybercrime, forensic analysis, chain of custody, risk analysis, compliance, Criminal Policy
- Market signals covered: forensic, investigation, public safety, security analyst, risk analyst, cybercrime, victim services, Criminal Investigation, Victimology, Criminal Profiling, Criminal Intelligence, Criminal Policy, Crime Prevention, Public Security, Forensic Analysis, Chain of Custody, Risk Analysis, Compliance

## Feed Mapping

- `skills_master`: adds canonical criminology, forensic, cybercrime, risk, compliance, public safety, organized crime, and financial crime skills.
- `skills_alias`: maps Spanish and English aliases such as investigacion criminal, victimologia, criminalistica, ciberdelito, cadena de custodia, lavado de activos, seguridad publica, and public safety.
- `semantic_role_graph`: adds role transitions for forensic, investigative, cybercrime, compliance, penitentiary, victim assistance, and public safety profiles.
- `curriculum_gap_observatory`: compares program 108 coverage against the expanded criminology benchmark and new labor evidence.
- `recommendation_observatory`: prioritizes modules and career-path recommendations around evidence handling, cybercrime, victimology, intelligence analysis, risk, compliance, and public safety.

## Impact On Program 108

- Program 108 is treated as `criminology`, preserving its domain identity and avoiding analytics-only contamination.
- The labor benchmark now observes international law-enforcement, multilateral, Colombian public-sector, and private security demand signals.
- Expected curriculum pressure increases around cybercrime, forensic analysis, chain of custody, criminal intelligence, financial crime, organized crime, risk analysis, compliance, and victimology.
- The expanded connector set improves employability evidence for roles such as Criminal Intelligence Analyst, Cybercrime Investigator, Forensic Analyst, Victim Assistance Specialist, Public Security Advisor, Compliance Analyst, Tecnico Investigador Criminalistico, Investigador Judicial, and Profesional Penitenciario.
- Recommendations for program 108 can now be grounded in institutional labor evidence from Interpol, Europol, UN Careers, UNODC, Fiscalia Colombia, Policia Nacional Colombia, INPEC, Procuraduria, Defensoria, Securitas, G4S, and Prosegur.

## Deep Harvest Result

- Latest deep-pagination run: `lap-f5cceaa8f3754261`
- Unique results in the latest run: 98
- Real job postings in the latest run: 97
- Persisted Bronze rows in the latest run: 98
- Persisted Silver rows in the latest run: 98
- Europol archive jobs now stored in warehouse verification: 164
- Total jobs in warehouse verification after the deep harvest: 423
- Program 108 intelligence was refreshed independently with the new evidence.
