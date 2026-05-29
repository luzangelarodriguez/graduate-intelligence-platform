from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from microcurriculum_engine.matching.market_matching import MarketComparison


@dataclass(frozen=True)
class CurriculumRecommendation:
    recommendation_type: str
    title: str
    recommendation_text: str
    confidence_score: float
    evidence: dict[str, Any]
    gap_detectado: str
    evidencia_curricular: str
    evidencia_laboral: str
    asignatura_o_modulo_sugerido: str
    accion_curricular: str
    prioridad: str
    justificacion: str
    nivel_impacto: str
    confidence: float
    explanation: str
    subdomain: str


TEMPLATE_CATALOG: dict[str, dict[str, dict[str, str]]] = {
    "analitica/inteligencia_artificial": {
        "python": {
            "module": "Laboratorio aplicado de Python para aprendizaje automatico",
            "action": "Incorporar practicas guiadas de preparacion de datos, entrenamiento de modelos y evaluacion usando Python.",
            "justification": "Python es el lenguaje dominante para prototipado y experimentacion reproducible en inteligencia artificial.",
            "impact": "alto",
        },
        "scikit-learn": {
            "module": "Modelado supervisado con scikit-learn",
            "action": "Agregar ejercicios de regresion, clasificacion, validacion cruzada y ajuste de hiperparametros con scikit-learn.",
            "justification": "El microcurriculo cubre algoritmos, pero requiere evidencia practica con una libreria estandar de implementacion.",
            "impact": "alto",
        },
        "mlops": {
            "module": "MLOps y ciclo de vida de modelos",
            "action": "Incorporar versionamiento, monitoreo, despliegue, trazabilidad y evaluacion continua de modelos de machine learning.",
            "justification": "La pertinencia laboral en IA exige operar modelos despues del entrenamiento, no solo construirlos en aula.",
            "impact": "alto",
        },
        "notebooks": {
            "module": "Notebooks reproducibles para experimentacion en IA",
            "action": "Usar notebooks como evidencia evaluable de exploracion, entrenamiento y comunicacion de resultados.",
            "justification": "Los notebooks facilitan reproducibilidad, trazabilidad academica y portafolio profesional del estudiante.",
            "impact": "medio",
        },
        "visual analytics": {
            "module": "Visualizacion y explicabilidad de modelos",
            "action": "Incluir visualizacion de errores, matriz de confusion, curvas ROC/AUC y comunicacion ejecutiva de resultados.",
            "justification": "La toma de decisiones con modelos requiere interpretar desempeno, error y riesgo.",
            "impact": "medio",
        },
        "power bi": {
            "module": "Storytelling analitico para resultados de IA",
            "action": "Conectar resultados de modelos a tableros ejecutivos para interpretar hallazgos y seguimiento.",
            "justification": "La empleabilidad en analitica valora traducir modelos en evidencia accionable para negocio.",
            "impact": "medio",
        },
        "sql": {
            "module": "Gestion de datos para machine learning",
            "action": "Agregar consultas SQL para extraccion, segmentacion y preparacion de datasets de entrenamiento.",
            "justification": "La calidad del modelo depende de pipelines de datos confiables antes de entrenar.",
            "impact": "alto",
        },
        "big data": {
            "module": "Escalamiento de datos para IA",
            "action": "Incorporar criterios para manejar volumen, variedad y procesamiento distribuido en problemas de aprendizaje automatico.",
            "justification": "Los casos reales de IA suelen requerir datos masivos o integracion de multiples fuentes.",
            "impact": "medio",
        },
    },
    "management/innovacion": {
        "vigilancia tecnologica": {
            "module": "Vigilancia tecnologica e inteligencia de entorno",
            "action": "Formalizar un modulo de vigilancia tecnologica con fuentes, indicadores, radar de tendencias y analisis de senales.",
            "justification": "El diseno de proyectos de innovacion necesita evidencia sistematica antes de priorizar iniciativas.",
            "impact": "alto",
        },
        "inteligencia competitiva": {
            "module": "Inteligencia competitiva para portafolios de innovacion",
            "action": "Incluir benchmarking competitivo, analisis de sustitutos, patentes, actores y posicionamiento de mercado.",
            "justification": "La innovacion requiere comparar oportunidades frente al mercado y no solo generar ideas internas.",
            "impact": "alto",
        },
        "gestion de proyectos": {
            "module": "Gestion de portafolios de innovacion",
            "action": "Agregar priorizacion de iniciativas, criterios de seleccion, gestion de riesgos y seguimiento por etapas.",
            "justification": "El documento aborda proyectos; el siguiente nivel es gestionar un portafolio con indicadores.",
            "impact": "alto",
        },
        "design thinking": {
            "module": "Design thinking y validacion temprana",
            "action": "Incorporar empatia, ideacion, prototipado rapido y validacion con usuarios antes del caso final.",
            "justification": "La innovacion mejora cuando el problema se valida con usuarios y evidencia antes de invertir.",
            "impact": "medio",
        },
        "kpi": {
            "module": "Metricas de innovacion",
            "action": "Definir KPIs de entrada, proceso, salida e impacto para medir avance del proyecto innovador.",
            "justification": "Un comite academico necesita evidencia cuantificable del aprendizaje y del impacto esperado.",
            "impact": "medio",
        },
        "liderazgo": {
            "module": "Liderazgo para cultura de innovacion",
            "action": "Integrar practicas de facilitacion, gestion del cambio y movilizacion de equipos interdisciplinarios.",
            "justification": "La innovacion falla sin capacidades de adopcion, comunicacion y gestion cultural.",
            "impact": "medio",
        },
        "agile": {
            "module": "Experimentacion agil para innovacion",
            "action": "Usar ciclos cortos de hipotesis, prototipo, prueba y aprendizaje para madurar iniciativas.",
            "justification": "La gestion de innovacion se beneficia de aprendizaje iterativo y validacion temprana.",
            "impact": "medio",
        },
        "scrum": {
            "module": "Ejecucion iterativa de proyectos de innovacion",
            "action": "Aplicar ceremonias y artefactos ligeros para coordinar entregables, backlog y retrospectivas.",
            "justification": "La ejecucion por iteraciones ayuda a convertir ideas en prototipos evaluables.",
            "impact": "medio",
        },
    },
    "management/finanzas": {
        "excel avanzado": {
            "module": "Excel avanzado para decisiones financieras",
            "action": "Incorporar modelacion con tablas de datos, escenarios, Solver, funciones financieras y controles de sensibilidad.",
            "justification": "El microcurriculo cita Excel; conviene convertirlo en evidencia practica evaluable de modelacion financiera.",
            "impact": "alto",
        },
        "power bi financiero": {
            "module": "Dashboards financieros ejecutivos",
            "action": "Agregar un entregable de tablero financiero con KPIs, flujo de caja, rentabilidad, riesgo y alertas.",
            "justification": "Los comites y empresas demandan lectura ejecutiva de indicadores financieros en tableros.",
            "impact": "alto",
        },
        "modelacion financiera": {
            "module": "Modelacion financiera y valoracion",
            "action": "Fortalecer VAN, TIR, WACC, CAPM y valoracion de inversiones con casos empresariales integrados.",
            "justification": "La asignatura contiene fundamentos; la recomendacion eleva el componente aplicado y trazable.",
            "impact": "alto",
        },
        "analisis de escenarios": {
            "module": "Analisis de sensibilidad y escenarios",
            "action": "Incluir simulacion de escenarios, supuestos criticos y comparacion de decisiones bajo incertidumbre.",
            "justification": "La toma de decisiones financieras requiere evaluar sensibilidad y riesgo ante cambios de mercado.",
            "impact": "alto",
        },
        "indicadores financieros": {
            "module": "Indicadores financieros para seguimiento gerencial",
            "action": "Definir y calcular indicadores de liquidez, rentabilidad, endeudamiento, riesgo y creacion de valor.",
            "justification": "Los indicadores conectan el analisis financiero con decisiones de direccion y seguimiento.",
            "impact": "medio",
        },
        "gestion de proyectos": {
            "module": "Evaluacion financiera de proyectos",
            "action": "Vincular gestion de proyectos con evaluacion financiera, flujos de caja, payback y criterios de inversion.",
            "justification": "El enfoque financiero gana pertinencia cuando se integra con decisiones de inversion reales.",
            "impact": "medio",
        },
        "liderazgo": {
            "module": "Comunicacion financiera para direccion",
            "action": "Agregar sustentacion ejecutiva de decisiones financieras ante comite, con riesgos y alternativas.",
            "justification": "El liderazgo financiero requiere comunicar escenarios, supuestos y decisiones con claridad.",
            "impact": "medio",
        },
    },
    "ti/ingenieria_software": {
        "devops": {
            "module": "DevOps para ciclo de vida de software",
            "action": "Incorporar practicas de integracion, entrega, observabilidad y operacion de software.",
            "justification": "La industria espera que el egresado conecte desarrollo con despliegue y operacion.",
            "impact": "alto",
        },
        "ci cd": {
            "module": "CI/CD y automatizacion de entrega",
            "action": "Agregar pipelines con pruebas, analisis estatico, build, versionamiento y despliegue.",
            "justification": "La entrega continua reduce riesgo y evidencia madurez en ingenieria de software.",
            "impact": "alto",
        },
        "docker": {
            "module": "Contenedores para ambientes reproducibles",
            "action": "Usar Docker para empaquetar servicios, dependencias y ambientes de laboratorio.",
            "justification": "La reproducibilidad de ambientes es una competencia clave en equipos modernos.",
            "impact": "alto",
        },
        "cloud": {
            "module": "Arquitectura cloud aplicada",
            "action": "Disenar y desplegar una arquitectura basica en nube con seguridad, escalabilidad y costos.",
            "justification": "La empleabilidad en software exige comprender despliegue cloud y arquitectura operable.",
            "impact": "alto",
        },
        "api": {
            "module": "Diseno de APIs y contratos de integracion",
            "action": "Incorporar versionamiento, documentacion OpenAPI, autenticacion, pruebas y contratos.",
            "justification": "Las APIs son el punto de integracion principal entre productos digitales.",
            "impact": "alto",
        },
        "react": {
            "module": "Frontend moderno basado en componentes",
            "action": "Agregar una practica de interfaz con componentes, estado, consumo de API y pruebas basicas.",
            "justification": "El frontend moderno complementa backend y fortalece perfil fullstack.",
            "impact": "medio",
        },
    },
}

BLOCKED_BY_SUBDOMAIN = {
    "management/innovacion": {"react", "docker", "kubernetes", "devops", "backend", "frontend", "api", "cloud"},
    "management/finanzas": {"react", "docker", "kubernetes", "devops", "backend", "frontend", "api", "cloud"},
}


def infer_subdomain(domain: str, comparison: MarketComparison) -> str:
    signals = set(comparison.shared_skills) | set(comparison.obsolete_skills) | set(comparison.market_skills) | set(comparison.missing_skills)
    if domain == "finanzas":
        return "management/finanzas"
    if domain == "analitica" and signals & {"ia", "machine learning", "mlops", "scikit-learn", "notebooks"}:
        return "analitica/inteligencia_artificial"
    if domain == "management" and signals & {"innovacion", "vigilancia tecnologica", "inteligencia competitiva", "design thinking"}:
        return "management/innovacion"
    if domain == "ti":
        return "ti/ingenieria_software"
    return domain


def template_for(subdomain: str, skill: str) -> dict[str, str]:
    catalog = TEMPLATE_CATALOG.get(subdomain, {})
    if skill in catalog:
        return catalog[skill]
    if subdomain == "analitica/inteligencia_artificial":
        return {
            "module": "Laboratorio integrador de inteligencia artificial aplicada",
            "action": f"Integrar {skill} en un caso aplicado con datos, evaluacion, interpretacion y evidencia reproducible.",
            "justification": f"{skill} complementa el ciclo de aprendizaje automatico y fortalece la aplicacion profesional.",
            "impact": "medio",
        }
    if subdomain == "management/innovacion":
        return {
            "module": "Proyecto integrador de innovacion estrategica",
            "action": f"Conectar {skill} con la formulacion, priorizacion y evaluacion de proyectos de innovacion.",
            "justification": f"{skill} aporta estructura para convertir oportunidades en iniciativas evaluables.",
            "impact": "medio",
        }
    if subdomain == "management/finanzas":
        return {
            "module": "Caso aplicado de direccion financiera",
            "action": f"Incorporar {skill} como evidencia aplicada dentro de decisiones de inversion, riesgo o valoracion.",
            "justification": f"{skill} fortalece la capacidad de justificar decisiones financieras con evidencia.",
            "impact": "medio",
        }
    if subdomain == "ti/ingenieria_software":
        return {
            "module": "Proyecto aplicado de ingenieria de software",
            "action": f"Incorporar {skill} en una practica integradora con codigo, pruebas, despliegue y documentacion.",
            "justification": f"{skill} incrementa pertinencia frente a roles modernos de ingenieria de software.",
            "impact": "medio",
        }
    return {
        "module": "Modulo de actualizacion curricular basada en evidencia",
        "action": f"Incorporar {skill} mediante una actividad aplicada con rubrica y evidencia verificable.",
        "justification": f"{skill} aparece como brecha frente a la senal laboral disponible para el dominio {subdomain}.",
        "impact": "medio",
    }


def priority_for(skill: str, demand: int, impact: str) -> str:
    if impact == "alto" or demand >= 3:
        return "alta"
    if demand == 2:
        return "media"
    return "media"


def build_recommendation(
    *,
    skill: str,
    subdomain: str,
    domain: str,
    comparison: MarketComparison,
    recommendation_type: str,
    max_evidence_jobs: int = 3,
) -> CurriculumRecommendation | None:
    if skill in BLOCKED_BY_SUBDOMAIN.get(subdomain, set()):
        return None
    template = template_for(subdomain, skill)
    demand = comparison.demand_counts.get(skill, 1)
    confidence = round(min(0.94, 0.72 + 0.04 * demand + (0.04 if template["impact"] == "alto" else 0)), 4)
    gap = f"Brecha curricular en {skill}"
    evidence_curricular = (
        f"El microcurriculo no evidencia suficiente cobertura aplicada de {skill}."
        if skill in comparison.missing_skills
        else f"{skill} aparece en el microcurriculo, pero requiere mayor trazabilidad aplicada o evidencia de evaluacion."
    )
    evidence_laboral = (
        f"Senal laboral registrada para {skill} en el dominio {domain}; demanda observada: {demand}."
    )
    title = f"{template['module']} ({skill})"
    text = (
        f"{template['action']} Justificacion: {template['justification']} "
        f"Evidencia: {evidence_laboral}"
    )
    return CurriculumRecommendation(
        recommendation_type=recommendation_type,
        title=title,
        recommendation_text=text,
        confidence_score=confidence,
        evidence={
            "skill": skill,
            "domain": domain,
            "subdomain": subdomain,
            "demand_count": demand,
            "evidence_jobs": comparison.evidence_jobs[:max_evidence_jobs],
            "curricular_signal": evidence_curricular,
        },
        gap_detectado=gap,
        evidencia_curricular=evidence_curricular,
        evidencia_laboral=evidence_laboral,
        asignatura_o_modulo_sugerido=template["module"],
        accion_curricular=template["action"],
        prioridad=priority_for(skill, demand, template["impact"]),
        justificacion=template["justification"],
        nivel_impacto=template["impact"],
        confidence=confidence,
        explanation=(
            f"Recomendacion generada para {subdomain}: conecta el gap `{skill}` con una accion curricular "
            "evaluable, evidencia laboral y pertinencia disciplinar."
        ),
        subdomain=subdomain,
    )


def candidate_gaps(subdomain: str, comparison: MarketComparison, max_items: int) -> list[tuple[str, str]]:
    preferred = list(TEMPLATE_CATALOG.get(subdomain, {}).keys())
    ordered: list[tuple[str, str]] = []
    for skill in comparison.missing_skills:
        ordered.append((skill, "missing_skill"))
    for skill in preferred:
        if skill in comparison.obsolete_skills or skill in comparison.shared_skills:
            ordered.append((skill, "strengthen_curricular_evidence"))
    for skill in preferred:
        if skill not in {item[0] for item in ordered}:
            ordered.append((skill, "strategic_curriculum_update"))
    seen: set[str] = set()
    result: list[tuple[str, str]] = []
    for skill, rec_type in ordered:
        if skill in seen:
            continue
        seen.add(skill)
        result.append((skill, rec_type))
        if len(result) >= max_items:
            break
    return result


def generate_recommendations(
    *,
    domain: str,
    comparison: MarketComparison,
    max_items: int = 6,
) -> list[dict[str, Any]]:
    subdomain = infer_subdomain(domain, comparison)
    recommendations: list[CurriculumRecommendation] = []
    for skill, recommendation_type in candidate_gaps(subdomain, comparison, max_items):
        recommendation = build_recommendation(
            skill=skill,
            subdomain=subdomain,
            domain=domain,
            comparison=comparison,
            recommendation_type=recommendation_type,
        )
        if recommendation is not None:
            recommendations.append(recommendation)
    if not recommendations:
        recommendations.append(
            CurriculumRecommendation(
                recommendation_type="maintain_alignment",
                title="Mantener vigilancia curricular basada en evidencia",
                recommendation_text=(
                    "Mantener revision periodica del microcurriculo con evidencia laboral Gold, "
                    "matriz de competencias y trazabilidad de resultados de aprendizaje."
                ),
                confidence_score=0.78,
                evidence={"coverage": comparison.coverage, "domain": domain, "subdomain": subdomain},
                gap_detectado="Sin brecha critica inmediata",
                evidencia_curricular="El microcurriculo presenta cobertura razonable frente a la senal disponible.",
                evidencia_laboral="No se identifico una brecha critica con la evidencia laboral actual.",
                asignatura_o_modulo_sugerido="Comite periodico de actualizacion curricular",
                accion_curricular="Programar revision semestral de evidencias laborales, desempeno y resultados de aprendizaje.",
                prioridad="baja",
                justificacion="La pertinencia debe mantenerse con monitoreo continuo aunque no exista brecha critica.",
                nivel_impacto="medio",
                confidence=0.78,
                explanation="Recomendacion de mantenimiento generada por cobertura curricular suficiente.",
                subdomain=subdomain,
            )
        )
    return [asdict(item) for item in recommendations[:max_items]]
