# =============================================================================
# scripts/init_db.py — Crea la base de datos SQLite con todas sus tablas.
# Ejecutar una sola vez: python scripts/init_db.py
# =============================================================================

import sqlite3
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import DB_PATH


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # ── Tabla 1: variables crudas (una fila por base + fecha) ──────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS variables_raw (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            base_id       TEXT NOT NULL,
            fecha         TEXT NOT NULL,
            temperatura   REAL,
            manto_nival   REAL,
            viento        REAL,
            precipitacion REAL,
            fauna         REAL,
            algas         REAL,
            nidificacion  INTEGER,
            turistas      INTEGER,
            buques        INTEGER,
            dias_consec   INTEGER,
            fuente_clima  TEXT,
            fuente_eco    TEXT,
            ingreso_manual INTEGER DEFAULT 0,
            created_at    TEXT DEFAULT (datetime('now')),
            UNIQUE(base_id, fecha)
        )
    """)

    # ── Tabla 2: ICT-A calculado (resultado final por base + fecha) ─────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ict_calculado (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            base_id         TEXT NOT NULL,
            fecha           TEXT NOT NULL,
            t_temperatura   REAL,
            t_manto_nival   REAL,
            t_viento        REAL,
            t_precipitacion REAL,
            t_fauna         REAL,
            t_algas         REAL,
            t_nidificacion  REAL,
            t_turistas      REAL,
            t_buques        REAL,
            t_dias_consec   REAL,
            d1_climatica    REAL,
            d2_ecologica    REAL,
            d3_humana       REAL,
            ict_a           REAL NOT NULL,
            estado          TEXT NOT NULL,
            ajuste_estacion INTEGER DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now')),
            UNIQUE(base_id, fecha)
        )
    """)

    # ── Tabla 3: alertas generadas ──────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alertas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            base_id     TEXT NOT NULL,
            fecha       TEXT NOT NULL,
            tipo        TEXT NOT NULL,
            variable    TEXT,
            valor_ict   REAL,
            estado_prev TEXT,
            estado_nuevo TEXT,
            mensaje     TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    con.commit()
    con.close()
    print(f"Base de datos inicializada en: {DB_PATH}")
    print("Tablas creadas: variables_raw, ict_calculado, alertas")


if __name__ == "__main__":
    init_db()
