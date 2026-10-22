# =============================================================================
# api/app.py — API REST con Flask.
# Sirve los datos del ICT-A al dashboard web.
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
CORS(app)


def query(sql: str, params=(), one=False):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(sql, params)
    filas = cur.fetchall()
    con.close()
    if one:
        return dict(filas[0]) if filas else None
    return [dict(f) for f in filas]


# ── GET /api/estado ───────────────────────────────────────────────────────────
@app.route("/api/estado")
def estado_actual():
    resultado = []
    for base_id, base in BASES.items():
        fila = query("""
            SELECT i.*, v.temperatura, v.manto_nival, v.viento, v.precipitacion,
                   v.fauna, v.algas, v.nidificacion, v.turistas, v.buques, v.dias_consec
            FROM ict_calculado i
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
                # iit_a e ict_a devuelven el mismo valor
                # (iit_a es el nombre que usa el dashboard anterior)
                "ict_a":    fila["ict_a"],
                "iit_a":    fila["ict_a"],
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
            resultado.append({
                "base_id": base_id,
                "nombre":  base["nombre"],
                "lat":     base["lat"],
                "lon":     base["lon"],
                "ict_a":   None,
                "iit_a":   None,
                "estado":  "sin_datos",
                "fecha":   None,
            })

    return jsonify(resultado)


# ── GET /api/historial/<base_id> ──────────────────────────────────────────────
@app.route("/api/historial/<base_id>")
def historial(base_id: str):
    if base_id not in BASES:
        return jsonify({"error": "Base no encontrada"}), 404

    dias = int(request.args.get("dias", 30))
    desde = (date.today() - timedelta(days=dias)).isoformat()

    filas = query("""
        SELECT fecha, ict_a, ict_a as iit_a, estado,
               d1_climatica, d2_ecologica, d3_humana
        FROM ict_calculado
        WHERE base_id=? AND fecha >= ?
        ORDER BY fecha ASC
    """, (base_id, desde))

    return jsonify(filas)


# ── GET /api/bases ────────────────────────────────────────────────────────────
@app.route("/api/bases")
def listar_bases():
    return jsonify([
        {"base_id": bid, **{k: v for k, v in b.items() if k != "radio_km"}}
        for bid, b in BASES.items()
    ])


# ── GET /api/alertas ──────────────────────────────────────────────────────────
@app.route("/api/alertas")
def alertas():
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
            "buques":   int(datos.get("buques",   0)),
        }
    }

    try:
        resultado = actualizar_todo(fecha, datos_manuales)
        res_base  = resultado.get(base_id, {})
        val = res_base.get("ict_a")
        return jsonify({
            "ok":      True,
            "base_id": base_id,
            "fecha":   fecha_str,
            "ict_a":   val,
            "iit_a":   val,
            "estado":  res_base.get("estado"),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── POST /api/actualizar ──────────────────────────────────────────────────────
@app.route("/api/actualizar", methods=["POST"])
def forzar_actualizacion():
    try:
        resultados = actualizar_todo(date.today())
        return jsonify({
            "ok": True,
            "bases": {
                bid: {"ict_a": r["ict_a"], "iit_a": r["ict_a"], "estado": r["estado"]}
                for bid, r in resultados.items()
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("ICT-A API iniciada en http://localhost:5000")
    app.run(debug=True, port=5000)
