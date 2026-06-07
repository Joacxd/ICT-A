import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def get_conn():
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        import psycopg2
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return psycopg2.connect(db_url), "pg"
    else:
        import sqlite3
        from config import DB_PATH
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        return sqlite3.connect(DB_PATH), "sqlite"

def init_db():
    con, tipo = get_conn()
    cur = con.cursor()
    serial = "SERIAL" if tipo == "pg" else "INTEGER"
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS variables_raw (
            id            {serial} PRIMARY KEY,
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
            created_at    TEXT DEFAULT {'current_timestamp' if tipo == 'pg' else "datetime('now')"},
            UNIQUE(base_id, fecha)
        )
    """)
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS iit_calculado (
            id              {serial} PRIMARY KEY,
            base_id         TEXT NOT NULL,
            fecha           TEXT NOT NULL,
            t_temperatura   REAL, t_manto_nival REAL,
            t_viento        REAL, t_precipitacion REAL,
            t_fauna         REAL, t_algas REAL,
            t_nidificacion  REAL, t_turistas REAL,
            t_buques        REAL, t_dias_consec REAL,
            d1_climatica    REAL, d2_ecologica REAL, d3_humana REAL,
            iit_a           REAL NOT NULL,
            estado          TEXT NOT NULL,
            ajuste_estacion INTEGER DEFAULT 0,
            created_at      TEXT DEFAULT {'current_timestamp' if tipo == 'pg' else "datetime('now')"},
            UNIQUE(base_id, fecha)
        )
    """)
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS alertas (
            id           {serial} PRIMARY KEY,
            base_id      TEXT NOT NULL,
            fecha        TEXT NOT NULL,
            tipo         TEXT NOT NULL,
            variable     TEXT,
            valor_iit    REAL,
            estado_prev  TEXT,
            estado_nuevo TEXT,
            mensaje      TEXT,
            created_at   TEXT DEFAULT {'current_timestamp' if tipo == 'pg' else "datetime('now')"}
        )
    """)
    con.commit()
    con.close()
    print(f"Base de datos inicializada ({tipo})")

if __name__ == "__main__":
    init_db()