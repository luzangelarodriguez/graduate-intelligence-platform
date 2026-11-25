"""
Estudios de referencia por programa — datos estructurados y verificados.

Regla de contenido:
  - texto      : paráfrasis propia (sin comillas, no es cita textual)
  - fuente     : nombre de la publicación o institución
  - url        : enlace real al documento; nunca construido ni inventado
  - fecha      : YYYY-MM o YYYY según lo que conste en la fuente
  - verificada : True solo si se abrió y leyó la página directamente

PROGRAM_STUDIES mapea program_id → dict con claves:
  resumen, hallazgos, habilidades_al_alza, pierde_peso, evidencia
"""
from __future__ import annotations

from typing import Any


ALLOWED_VERIFIED_DOMAINS = {
    "weforum.org",
    "pmi.org",
    "hai.stanford.edu",
    "gartner.com",
    "brandwatch.com",
    "govtech.com",
    "elsalvador.com",
}


def _h(
    texto: str,
    fuente: str,
    url: str,
    fecha: str,
    verificada: bool = False,
) -> dict[str, Any]:
    return {
        "texto": texto,
        "fuente": fuente,
        "url": url,
        "fecha": fecha,
        "verificada": verificada,
    }


# Hallazgo BID compartido entre todos los programas con evidencia de mercado
_BID_VACANTES_IA = _h(
    texto=(
        "Alrededor del 7 % de las vacantes de América Latina mencionaban "
        "IA en junio de 2025, y la IA es el área de habilidades de más rápido "
        "crecimiento en las vacantes de la región, según un informe del BID "
        "reseñado por la prensa."
    ),
    fuente="BID (informe macroeconómico 2026), vía elsalvador.com",
    url="https://www.elsalvador.com/?p=1282233",
    fecha="2025-06",
    verificada=True,
)


PROGRAM_STUDIES: dict[int, dict[str, Any]] = {
    # ── 13 · Visual Analytics y Big Data ─────────────────────────────────────
    13: {
        "resumen": (
            "El especialista en big data es el empleo de mayor crecimiento porcentual "
            "hasta 2030 y la combinación IA y big data lidera las habilidades en alza "
            "globalmente (WEF). Hacia 2029, las decisiones modeladas explícitamente "
            "serán cinco veces más confiables y el streaming de datos para IA pasará "
            "de menos del 15 % en 2025 a más del 60 % en 2028 (Gartner). En América "
            "Latina, alrededor del 7 % de las vacantes de la región mencionaba IA "
            "(BID, jun 2025)."
        ),
        "hallazgos": [
            _h(
                texto=(
                    "El especialista en big data es el empleo de mayor crecimiento "
                    "porcentual hasta 2030; la habilidad compuesta IA y big data lidera "
                    "la lista de competencias en alza; el pensamiento analítico es la "
                    "habilidad básica más demandada."
                ),
                fuente="WEF – Future of Jobs Report 2025 (digest)",
                url="https://www.weforum.org/publications/the-future-of-jobs-report-2025/digest/",
                fecha="2025",
                verificada=True,
            ),
            _h(
                texto=(
                    "Las decisiones de negocio modeladas explícitamente serán cinco veces "
                    "más confiables y un 80 % más rápidas hacia 2029. El streaming de "
                    "datos para aplicaciones de IA pasará de menos del 15 % en 2025 a "
                    "más del 60 % en 2028."
                ),
                fuente="Gartner – Top Trends for Data & Analytics 2026",
                url="https://www.gartner.com/en/newsroom/press-releases/2026-06-16-gartner-identifies-the-top-trends-for-data-and-analytics",
                fecha="2026-06",
                verificada=True,
            ),
            _BID_VACANTES_IA,
        ],
        "habilidades_al_alza": [
            "gobierno y explicabilidad de decisiones automatizadas",
            "datos en streaming para IA",
            "capa semántica y grafos de conocimiento",
            "gestión de datos asistida por agentes",
        ],
        "pierde_peso": {
            "texto": "preparación manual y rutinaria de datos",
            "lectura_propia": True,
        },
        "evidencia": "industria",
    },

    # ── 146 · Marketing y Publicidad ─────────────────────────────────────────
    146: {
        "resumen": (
            "La IA redefine el rol del profesional de marketing: según Gartner, "
            "dos de cada tres CMO anticipan cambios drásticos en sus funciones. "
            "Una encuesta amplia de Brandwatch confirma que IA y automatización "
            "son ya las habilidades más valoradas del sector."
        ),
        "hallazgos": [
            _h(
                texto=(
                    "El 65 % de los CMO encuestados en 2025 cree que la IA cambiará "
                    "drásticamente su rol en los próximos dos años."
                ),
                fuente="Gartner – Marketing Predictions 2026",
                url="https://www.gartner.com/en/marketing/research/marketing-predictions/unlocked",
                fecha="2025",
                verificada=True,
            ),
            _h(
                texto=(
                    "En una encuesta a 1.028 profesionales del marketing (marzo 2026), "
                    "el 84 % considera que IA y automatización son las habilidades más "
                    "importantes para el año."
                ),
                fuente="Brandwatch – The Marketer Report 2026",
                url="https://www.brandwatch.com/reports/marketer/view/",
                fecha="2026-03",
                verificada=True,
            ),
            _h(
                texto=(
                    "La demanda de habilidades en datos, IA y automatización en el sector "
                    "de marketing supera la oferta disponible; los directores de marketing "
                    "deberán invertir en recapacitación de sus equipos."
                ),
                fuente="Deloitte Digital – Marketing Trends 2026",
                url="https://www.deloittedigital.com/nl/en/insights/perspective/marketing-trends-2026.html",
                fecha="2026",
                verificada=False,
            ),
            _h(
                texto=(
                    "Según un analista de Gartner citado por el medio, pocos profesionales "
                    "de marketing comprenden cómo los modelos de IA interpretan y "
                    "recomiendan productos."
                ),
                fuente="MediaPost – Marketers vs Machines: What the Skills Gap Means",
                url="https://www.mediapost.com/publications/article/410066/marketers-vs-machines-what-the-skills-gap-means.html",
                fecha="2025",
                verificada=False,
            ),
            _h(
                texto=(
                    "La construcción de marca regresa como prioridad competitiva para los "
                    "equipos de marketing en 2026."
                ),
                fuente="CIM – Top Three Skills Marketers Need to Succeed in 2026",
                url="https://cim.co.uk/content-insights/articles/top-three-skills-marketers-need-to-succeed-in-2026",
                fecha="2026",
                verificada=False,
            ),
            _BID_VACANTES_IA,
        ],
        "habilidades_al_alza": [
            "uso estratégico de IA generativa",
            "analítica y medición de campañas",
            "automatización de flujos de marketing",
            "estrategia de marca y posicionamiento",
            "visibilidad en búsquedas conversacionales",
        ],
        "pierde_peso": {
            "texto": "producción manual de contenido genérico",
            "lectura_propia": True,
        },
        "evidencia": "industria",
    },

    # ── 9 · Dirección y Gestión de Proyectos ─────────────────────────────────
    9: {
        "resumen": (
            "PMI anticipa hasta 30 millones de nuevos profesionales de proyectos para 2035, "
            "pero el rol evoluciona: los proyectos son más complejos y la IA ya asiste en "
            "investigación, documentación e identificación de riesgos. Una encuesta citada "
            "por PMI indica que el 48 % de las empresas no tiene roles claros para gestionar "
            "agentes de IA."
        ),
        "hallazgos": [
            _h(
                texto=(
                    "Se proyectan hasta 30 millones de profesionales de proyectos adicionales "
                    "para 2035. El 81 % reporta que sus proyectos son más complejos. "
                    "Los profesionales ya usan IA para investigación y análisis (77 %), "
                    "documentación y entregables (69 %) e identificación de riesgos (53 %). "
                    "Solo el 19 % teme ser reemplazado."
                ),
                fuente="PMI – comunicado oct 2026",
                url="https://www.pmi.org/about/press-media/2026/project-management-institute-helps-a-growing-profession-deliver-greater-value",
                fecha="2026-10",
                verificada=True,
            ),
            _h(
                texto=(
                    "Una encuesta citada en el mismo comunicado PMI indica que el 98 % de "
                    "las empresas desplegó o planea desplegar agentes de IA, pero solo "
                    "el 17 % monitorea su desempeño y el 48 % no tiene roles claros "
                    "para gestionarlos."
                ),
                fuente="PMI – comunicado oct 2026 (encuesta citada)",
                url="https://www.pmi.org/about/press-media/2026/project-management-institute-helps-a-growing-profession-deliver-greater-value",
                fecha="2026-10",
                verificada=True,
            ),
            _h(
                texto=(
                    "El PMI Pulse of the Profession 2025 presenta el criterio de negocio "
                    "como el principal diferenciador del éxito en la gestión de proyectos."
                ),
                fuente="PMI – Pulse of the Profession 2025",
                url="https://www.pmi.org/pulse",
                fecha="2025",
                verificada=False,
            ),
            _BID_VACANTES_IA,
        ],
        "habilidades_al_alza": [
            "gobierno de agentes de IA en proyectos",
            "navegación y gestión de complejidad",
            "criterio de negocio y toma de decisiones",
            "gestión del cambio organizacional",
        ],
        "pierde_peso": {
            "texto": "elaboración manual de documentación y reportes rutinarios",
            "lectura_propia": True,
        },
        "evidencia": "industria",
    },

    # ── 109 · Ingeniería Informática ─────────────────────────────────────────
    109: {
        "resumen": (
            "En entrevistas con 54 profesionales, ninguno propuso abandonar los fundamentos "
            "de programación. Una encuesta a 400 líderes de ingeniería mostró que el 71 % "
            "considera que la IA dificultó evaluar habilidades técnicas de candidatos."
        ),
        "hallazgos": [
            _h(
                texto=(
                    "En entrevistas con 54 profesionales, ninguno propuso abandonar los "
                    "fundamentos de programación. Una encuesta a 400 líderes de ingeniería "
                    "(enero 2026) mostró que el 71 % considera que la IA dificultó evaluar "
                    "habilidades técnicas de candidatos."
                ),
                fuente="GovTech – AI Is Changing What Employers Want from Entry-Level Tech Workers",
                url="https://www.govtech.com/education/higher-ed/ai-is-changing-what-employers-want-from-entry-level-tech-workers",
                fecha="2026-11",
                verificada=True,
            ),
            _h(
                texto=(
                    "El WEF ubica a los desarrolladores de software entre los cuatro empleos "
                    "de mayor crecimiento hasta 2030, con redes y ciberseguridad como "
                    "segunda habilidad en alza."
                ),
                fuente="WEF – Future of Jobs Report 2025, sección Jobs Outlook",
                url="https://www.weforum.org/publications/the-future-of-jobs-report-2025/in-full/2-jobs-outlook/",
                fecha="2025",
                verificada=False,
            ),
            _h(
                texto=(
                    "Dos mesas de expertos en 2026 concluyen que verificar y validar software "
                    "será la habilidad central para los ingenieros cuando los agentes "
                    "autónomos escriban la mayor parte del código."
                ),
                fuente="alphaxiv 2606.21894 – verificación y validación en la era de agentes",
                url="https://www.alphaxiv.org/abs/2606.21894",
                fecha="2026",
                verificada=False,
            ),
            _h(
                texto=(
                    "Una propuesta académica plantea reestructurar los cuatro años de "
                    "formación en computación sobre el estándar CS2023 para preparar a los "
                    "ingenieros en un entorno donde los agentes asisten en la escritura de código."
                ),
                fuente="NUS-Google – arxiv 2606.07545, reestructuración curricular CS2023",
                url="https://arxiv.org/html/2606.07545v1",
                fecha="2026",
                verificada=False,
            ),
            _BID_VACANTES_IA,
        ],
        "habilidades_al_alza": [
            "verificación y validación de software",
            "diseño de sistemas y arquitectura",
            "seguridad y ciberseguridad",
            "IA responsable y gobernanza",
            "alfabetización de datos",
        ],
        "pierde_peso": {
            "texto": "implementación rutinaria y escritura de código repetitivo",
            "lectura_propia": True,
        },
        "evidencia": "mixta",
    },

    # ── 11 · Inteligencia Artificial ─────────────────────────────────────────
    11: {
        "resumen": (
            "Los especialistas en IA y aprendizaje automático son el tercer empleo de mayor "
            "crecimiento según el WEF, y Gartner recomienda gobernanza de decisiones "
            "automatizadas."
        ),
        "hallazgos": [
            _h(
                texto=(
                    "La IA generativa llegó al 53 % de adopción en tres años. "
                    "OSWorld —benchmark de agentes autónomos en entornos de escritorio— "
                    "subió de cerca del 5 % en 2024 al 66,3 % en 2025, frente al 72,35 % "
                    "de referencia humana. Se reportaron 362 incidentes de IA en 2025."
                ),
                fuente="Stanford HAI – AI Index Report 2026",
                url="https://hai.stanford.edu/ai-index/2026-ai-index-report",
                fecha="2026",
                verificada=True,
            ),
            _h(
                texto=(
                    "Los especialistas en IA y aprendizaje automático ocupan el tercer lugar "
                    "entre los empleos de mayor crecimiento hasta 2030. Dos tercios de los "
                    "empleadores planean contratar talento con habilidades de IA."
                ),
                fuente="WEF – Future of Jobs Report 2025 (digest)",
                url="https://www.weforum.org/publications/the-future-of-jobs-report-2025/digest/",
                fecha="2025",
                verificada=True,
            ),
            _h(
                texto=(
                    "Más del 10 % de las empresas será AI-first hacia 2030, con gobernanza "
                    "de decisiones explicables y auditables como requisito central."
                ),
                fuente="Gartner – Top Trends for Data & Analytics 2026",
                url="https://www.gartner.com/en/newsroom/press-releases/2026-06-16-gartner-identifies-the-top-trends-for-data-and-analytics",
                fecha="2026-06",
                verificada=True,
            ),
            _BID_VACANTES_IA,
        ],
        "habilidades_al_alza": [
            "ingeniería y operacionalización de IA",
            "evaluación y seguridad de modelos y agentes",
            "gobernanza y auditoría de decisiones automatizadas",
            "datos en tiempo real para sistemas de IA",
        ],
        "pierde_peso": {
            "texto": (
                "las fuentes consultadas no identifican una habilidad en declive claro "
                "para este programa; el perfil evoluciona más que se sustituye"
            ),
            "lectura_propia": True,
        },
        "evidencia": "industria",
    },

    # ── 20 · Neuropsicología y Educación ─────────────────────────────────────
    20: {
        "resumen": (
            "La literatura reciente, no verificada aquí abriendo cada fuente, apunta a "
            "evaluación digital y remota, con advertencias sobre sesgo algorítmico y privacidad."
        ),
        "hallazgos": [
            _h(
                texto=(
                    "Una propuesta publicada en Frontiers in Psychology plantea integrar "
                    "herramientas de evaluación asistidas por IA dentro de los marcos "
                    "clínicos tradicionales; advierte riesgos de sesgo algorítmico y de "
                    "privacidad de datos, y señala que el neuropsicólogo necesitará "
                    "competencias nuevas para validar e interpretar estos resultados."
                ),
                fuente="Frontiers in Psychology 2025 – integración de IA en evaluación neuropsicológica",
                url="https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2025.1537368/abstract",
                fecha="2025",
                verificada=False,
            ),
            _h(
                texto=(
                    "Un editorial sobre teleneuropsicología revisa el avance del campo: "
                    "revisiones y metaanálisis respaldan la aplicabilidad diagnóstica de la "
                    "evaluación remota frente a la presencial, y aparecen los primeros "
                    "estudios sobre tamizaje digital autoadministrado."
                ),
                fuente="Frontiers in Psychology – editorial teleneuropsicología, dic 2025",
                url="https://www.frontiersin.org/articles/10.3389/fpsyg.2025.1745809/full",
                fecha="2025-12",
                verificada=False,
            ),
            _h(
                texto=(
                    "Una revisión publicada en JoVE examina qué efecto tiene la ausencia "
                    "de contacto humano directo en evaluaciones digitales sin supervisión, "
                    "un factor aún sin consenso en la literatura."
                ),
                fuente="JoVE – revisión sobre evaluación digital sin supervisión",
                url="https://www.jove.com/v/70431",
                fecha="2026-04",
                verificada=False,
            ),
            _h(
                texto=(
                    "La OCDE señala que la IA generativa mejora el aprendizaje solo cuando "
                    "existe un propósito pedagógico claro; delegar tareas cognitivas a "
                    "chatbots genera riesgo de pereza metacognitiva en los estudiantes."
                ),
                fuente="OCDE – Digital Education Outlook 2026",
                url="https://www.oecd.org/en/publications/oecd-digital-education-outlook-2026_062a7394-en.html",
                fecha="2026",
                verificada=False,
            ),
            _h(
                texto=(
                    "Un artículo de revisión atribuye el progreso limitado de la neuroeducación "
                    "a varios factores y propone mejorar la alfabetización neurocientífica de "
                    "los educadores como condición para trasladar los hallazgos de laboratorio "
                    "al aula."
                ),
                fuente="PMC – revisión sobre neuroeducación y alfabetización neurocientífica (2021)",
                url="https://pmc.ncbi.nlm.nih.gov/articles/PMC8678470",
                fecha="2021",
                verificada=False,
            ),
            _h(
                texto=(
                    "La UNESCO-IBE presenta la neuroeducación como conocimiento usable para "
                    "la Agenda de Educación 2030, resaltando su potencial para orientar "
                    "políticas educativas basadas en evidencia."
                ),
                fuente="UNESCO-IBE – neuroeducación y Agenda de Educación 2030",
                url="https://solportal.ibe-unesco.org/?p=640",
                fecha="2023",
                verificada=False,
            ),
        ],
        "habilidades_al_alza": [
            "evaluación digital y remota",
            "interpretación crítica de resultados asistidos por IA",
            "ética de datos clínicos",
            "diseño pedagógico con IA",
            "alfabetización neurocientífica",
        ],
        "pierde_peso": {
            "texto": "aplicación manual y únicamente presencial de baterías largas",
            "lectura_propia": True,
        },
        "evidencia": "academica",
    },
}
