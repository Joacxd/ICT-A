# =============================================================================
# api/app.py — API REST con Flask.
# Sirve los datos del IIT-A al dashboard web.
# Ejecutar: python api/app.py
# =============================================================================

import os
import sys
import sqlite3
from datetime import date, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import DB_PATH, BASES, SEMAFORO
from scripts.actualizar import actualizar_todo

app = Flask(__name__)
CORS(app)  # permite que el dashboard HTML acceda a la API


import os as _os

def get_conn():
    db_url = _os.environ.get("DATABASE_URL")
    if db_url:
        import psycopg2, psycopg2.extras
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        con = psycopg2.connect(db_url)
        return con, "pg"
    else:
        import sqlite3
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        return con, "sqlite"

def query(sql: str, params=(), one=False):
    con, tipo = get_conn()
    if tipo == "pg":
        import psycopg2.extras
        sql = sql.replace("?", "%s")
        cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cur = con.cursor()
    cur.execute(sql, params)
    filas = cur.fetchall()
    con.close()
    resultado = [dict(f) for f in filas]
    if one:
        return resultado[0] if resultado else None
    return resultado


# ── GET /api/estado ───────────────────────────────────────────────────────────

@app.route("/api/estado")
def estado_actual():
    # Actualizar datos de Meteochile en tiempo real antes de responder
    try:
        from scripts.fetch_clima import fetch_meteochile
        from scripts.calcular_iit import normalizar
        import sqlite3
        from datetime import date

        datos_mc = fetch_meteochile()
        if datos_mc.get("temperatura") is not None:
            fecha_hoy = date.today().isoformat()
            con = sqlite3.connect(DB_PATH)
            cur = con.cursor()
            for base_id in ["frei", "escudero"]:
                cur.execute("""
                    UPDATE variables_raw
                    SET temperatura=?, viento=?, precipitacion=?
                    WHERE base_id=? AND fecha=?
                """, (
                    datos_mc["temperatura"],
                    datos_mc["viento"],
                    datos_mc["precipitacion"],
                    base_id, fecha_hoy
                ))
            con.commit()
            con.close()
    except Exception as e:
        print(f"  Meteochile tiempo real: {e}")
    """
    Estado IIT-A más reciente de todas las bases.
    Responde: [{base_id, nombre, iit_a, estado, fecha, d1, d2, d3, ...}]
    """
    resultado = []
    for base_id, base in BASES.items():
        fila = query("""
            SELECT i.*, v.temperatura, v.manto_nival, v.viento, v.precipitacion,
                   v.fauna, v.algas, v.nidificacion, v.turistas, v.buques, v.dias_consec
            FROM iit_calculado i
            JOIN variables_raw v ON i.base_id = v.base_id AND i.fecha = v.fecha
            WHERE i.base_id = ?
            ORDER BY i.fecha DESC LIMIT 1
        """, (base_id,), one=True)

        if fila:
            resultado.append({
                "base_id":  base_id,
                "nombre":   base["nombre"],
                "lat":      base["lat"],
                "lon":      base["lon"],
                "iit_a":    fila["iit_a"],
                "estado":   fila["estado"],
                "color":    SEMAFORO[fila["estado"]]["color"],
                "label":    SEMAFORO[fila["estado"]]["label"],
                "fecha":    fila["fecha"],
                "d1_climatica": fila["d1_climatica"],
                "d2_ecologica": fila["d2_ecologica"],
                "d3_humana":    fila["d3_humana"],
                "variables": {
                    "temperatura":   fila["temperatura"],
                    "manto_nival":   fila["manto_nival"],
                    "viento":        fila["viento"],
                    "precipitacion": fila["precipitacion"],
                    "fauna":         fila["fauna"],
                    "algas":         fila["algas"],
                    "nidificacion":  fila["nidificacion"],
                    "turistas":      fila["turistas"],
                    "buques":        fila["buques"],
                    "dias_consec":   fila["dias_consec"],
                },
                "norm": {
                    "temperatura":   fila["t_temperatura"],
                    "manto_nival":   fila["t_manto_nival"],
                    "viento":        fila["t_viento"],
                    "precipitacion": fila["t_precipitacion"],
                    "fauna":         fila["t_fauna"],
                    "algas":         fila["t_algas"],
                    "nidificacion":  fila["t_nidificacion"],
                    "turistas":      fila["t_turistas"],
                    "buques":        fila["t_buques"],
                    "dias_consec":   fila["t_dias_consec"],
                }
            })
        else:
            # Sin datos aún: devolver base con IIT-A nulo
            resultado.append({
                "base_id": base_id,
                "nombre":  base["nombre"],
                "iit_a":   None,
                "estado":  "sin_datos",
                "fecha":   None,
            })

    return jsonify(resultado)


# ── GET /api/historial/<base_id> ──────────────────────────────────────────────
@app.route("/api/historial/<base_id>")
def historial(base_id: str):
    """
    Historial IIT-A de una base. Query param: dias (default 30).
    Responde: [{fecha, iit_a, estado, d1, d2, d3}]
    """
    if base_id not in BASES:
        return jsonify({"error": "Base no encontrada"}), 404

    dias = int(request.args.get("dias", 30))
    desde = (date.today() - timedelta(days=dias)).isoformat()

    filas = query("""
        SELECT fecha, iit_a, estado, d1_climatica, d2_ecologica, d3_humana
        FROM iit_calculado
        WHERE base_id=? AND fecha >= ?
        ORDER BY fecha ASC
    """, (base_id, desde))

    return jsonify(filas)


# ── GET /api/bases ────────────────────────────────────────────────────────────
@app.route("/api/bases")
def listar_bases():
    """Devuelve la lista de bases con metadata."""
    return jsonify([
        {"base_id": bid, **{k: v for k, v in b.items() if k != "radio_km"}}
        for bid, b in BASES.items()
    ])


# ── GET /api/alertas ──────────────────────────────────────────────────────────
@app.route("/api/alertas")
def alertas():
    """Últimas 20 alertas generadas por el sistema."""
    filas = query("""
        SELECT * FROM alertas
        ORDER BY created_at DESC LIMIT 20
    """)
    for f in filas:
        f["base_nombre"] = BASES.get(f["base_id"], {}).get("nombre", f["base_id"])
    return jsonify(filas)


# ── POST /api/manual ──────────────────────────────────────────────────────────
@app.route("/api/manual", methods=["POST"])
def ingreso_manual():
    """
    Recibe datos ingresados manualmente desde el formulario del dashboard.
    Body JSON: {base_id, turistas, buques, fecha (opcional)}
    """
    datos = request.get_json()
    if not datos or "base_id" not in datos:
        return jsonify({"error": "Datos inválidos"}), 400

    base_id = datos["base_id"]
    if base_id not in BASES:
        return jsonify({"error": "Base no encontrada"}), 404

    fecha_str = datos.get("fecha", date.today().isoformat())
    fecha = date.fromisoformat(fecha_str)

    datos_manuales = {
        base_id: {
            "turistas": int(datos.get("turistas", 0)),
            "buques":   int(datos.get("buques", 0)),
        }
    }

    try:
        resultado = actualizar_todo(fecha, datos_manuales)
        res_base  = resultado.get(base_id, {})
        return jsonify({
            "ok":     True,
            "base_id": base_id,
            "fecha":   fecha_str,
            "iit_a":   res_base.get("iit_a"),
            "estado":  res_base.get("estado"),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── GET /api/actualizar ───────────────────────────────────────────────────────
@app.route("/api/actualizar", methods=["POST"])
def forzar_actualizacion():
    """
    Fuerza una actualización inmediata de todos los datos.
    Útil para demostración en la feria.
    """
    try:
        resultados = actualizar_todo(date.today())
        return jsonify({
            "ok": True,
            "bases": {
                bid: {"iit_a": r["iit_a"], "estado": r["estado"]}
                for bid, r in resultados.items()
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
