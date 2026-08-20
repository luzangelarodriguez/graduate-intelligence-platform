"""
Registra la Especialización en Dirección y Gestión de Proyectos (UNIR Colombia)
en la base de datos y carga su microcurrículo.

Uso:
    python scripts/register_project_management_program.py

Requiere .env.local con las credenciales de DB.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env.local")

from backend.database_config import get_connection_parameters
import psycopg2

config = get_connection_parameters()
conn = psycopg2.connect(
    host=config["host"],
    port=config["port"],
    dbname=config["database"],
    user=config["user"],
    password=config["password"],
    sslmode=config["sslmode"],
    connect_timeout=config["connect_timeout"],
)
conn.autocommit = False
cur = conn.cursor()

# ── Paso 1: Verificar o crear el programa ──────────────────────────────────────
cur.execute("""
    SELECT id FROM especializaciones
    WHERE nombre ILIKE '%gerencia%proyect%'
       OR nombre ILIKE '%direcci%proyect%'
       OR nombre ILIKE '%gesti%proyect%'
""")
row = cur.fetchone()
if row:
    prog_id = row[0]
    print(f"El programa ya existe: id={prog_id}")
else:
    cur.execute("""
        INSERT INTO especializaciones (nombre, dominio, snies)
        VALUES (%s, %s, %s) RETURNING id
    """, (
        "Especialización en Dirección y Gestión de Proyectos",
        "project_management",
        "109155",
    ))
    prog_id = cur.fetchone()[0]
    print(f"Programa creado: id={prog_id}")

# ── Paso 2: Insertar asignaturas ──────────────────────────────────────────────
ASIGNATURAS = [
    ("Diseño y Gestión de Proyectos",                  1, 3),
    ("Diseño y Planificación de Proyectos",            2, 3),
    ("Planificación y Gestión de Presupuesto y Recursos", 3, 3),
    ("Gestión de la Calidad, Riesgos y Evaluación",   4, 3),
    ("Diseño de Proyectos Orientados a la Innovación",5, 3),
    ("Electiva",                                       6, 3),
    ("Caso Práctico",                                  7, 3),
    ("Preparación para la Certificación PMP",         8, 3),
]

SKILLS_POR_ASIGNATURA: dict[str, list[str]] = {
    "Diseño y Gestión de Proyectos": [
        "gestion de proyectos", "pmbok", "ciclo de vida", "integracion", "alcance",
    ],
    "Diseño y Planificación de Proyectos": [
        "planificacion", "cronograma", "ms project", "estructura desglose trabajo",
        "scrum", "agile",
    ],
    "Planificación y Gestión de Presupuesto y Recursos": [
        "presupuesto", "gestion financiera", "recursos humanos", "costos", "valor ganado",
    ],
    "Gestión de la Calidad, Riesgos y Evaluación": [
        "gestion de riesgos", "iso 9001", "iso 31000", "calidad", "auditoria", "indicadores",
    ],
    "Diseño de Proyectos Orientados a la Innovación": [
        "innovacion", "design thinking", "proyectos tecnologicos",
        "transformacion digital", "vuca",
    ],
    "Caso Práctico": [
        "direccion de proyectos", "liderazgo", "comunicacion", "negociacion",
        "resolucion de conflictos",
    ],
    "Preparación para la Certificación PMP": [
        "pmp", "pmi", "prince2", "ipma", "iso 21500", "certificacion",
    ],
    "Electiva": [],
}

# ── Paso 2b: Obtener o crear el registro en microcurriculos ───────────────────
cur.execute("SELECT id FROM microcurriculos WHERE specialization_id = %s", (prog_id,))
mc_row = cur.fetchone()
if mc_row:
    mc_id = mc_row[0]
    print(f"Microcurrículo ya existe: id={mc_id}")
else:
    cur.execute(
        "INSERT INTO microcurriculos (specialization_id) VALUES (%s) RETURNING id",
        (prog_id,),
    )
    mc_id = cur.fetchone()[0]
    print(f"Microcurrículo creado: id={mc_id}")

for nombre, orden, creditos in ASIGNATURAS:
    cur.execute("""
        SELECT ma.id
        FROM microcurriculo_asignaturas ma
        JOIN microcurriculos m ON ma.microcurriculo_id = m.id
        WHERE m.specialization_id = %s AND ma.nombre = %s
    """, (prog_id, nombre))
    existing = cur.fetchone()
    if existing:
        asig_id = existing[0]
        print(f"  Asignatura ya existe: {nombre} (id={asig_id})")
    else:
        cur.execute("""
            INSERT INTO microcurriculo_asignaturas
                (microcurriculo_id, nombre, orden, creditos)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (mc_id, nombre, orden, creditos))
        asig_id = cur.fetchone()[0]
        print(f"  Asignatura creada: {nombre} (id={asig_id})")

    for skill in SKILLS_POR_ASIGNATURA.get(nombre, []):
        cur.execute("""
            INSERT INTO microcurriculo_skills (asignatura_id, skill)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """, (asig_id, skill))

conn.commit()
conn.close()
print(f"\nListo. ID del programa: {prog_id}")
print(f"Actualiza el frontend: reemplaza id: 0 por id: {prog_id} en ObservatorioStorytelling.tsx")
