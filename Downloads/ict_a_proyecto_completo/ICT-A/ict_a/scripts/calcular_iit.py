# =============================================================================
# scripts/calcular_iit.py — Núcleo matemático del sistema ICT-A.
# Aplica normalización min-max → suma ponderada WLC → semáforo → SQLite.
# =============================================================================

import os
import sys
import sqlite3
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import PESOS, RANGOS_HIST, SEMAFORO, FACTOR_ESTACIONAL, DB_PATH, BASES


# ── Paso 1: Normalización min-max ─────────────────────────────────────────────

def normalizar(variable: str, valor: float) -> float:
    """
    Transforma un valor crudo al rango [0, 100] usando min-max histórico.
    """
    if valor is None:
        return 0.0

    rango = RANGOS_HIST.get(variable)
    if not rango:
        # Variable binaria (nidificación): ya viene en 0 o 1
        return float(valor) * 100

    vmin, vmax = rango["min"], rango["max"]
    if vmax == vmin:
        return 0.0

    norm = (valor - vmin) / (vmax - vmin) * 100
    return round(min(100.0, max(0.0, norm)), 2)


# ── Paso 2: Ajuste estacional de pesos ───────────────────────────────────────

def pesos_ajustados(nidificacion_activa: bool) -> dict:
    """
    Durante nidificación (nov-feb), incrementa pesos de D2 en FACTOR_ESTACIONAL
    y reduce D1 proporcionalmente, manteniendo suma total = 1.0.
    """
    pesos = dict(PESOS)
    if not nidificacion_activa:
        return pesos

    d2_vars = ["fauna", "algas", "nidificacion"]
    d1_vars = ["temperatura", "manto_nival", "viento", "precipitacion"]

    incremento_total  = sum(pesos[v] * (FACTOR_ESTACIONAL - 1) for v in d2_vars)
    reduccion_por_var = incremento_total / len(d1_vars)

    for v in d2_vars:
        pesos[v] = round(pesos[v] * FACTOR_ESTACIONAL, 4)
    for v in d1_vars:
        pesos[v] = round(max(0, pesos[v] - reduccion_por_var), 4)

    return pesos


# ── Paso 3: Cálculo WLC (Weighted Linear Combination) ────────────────────────

def calcular_iit(variables_norm: dict, nidificacion_activa: bool) -> dict:
    """
    Aplica la fórmula:  ICT-A = Σᵢ (wᵢ × xᵢ_norm)
    Devuelve dict con puntajes por dimensión y resultado final.
    """
    pesos = pesos_ajustados(nidificacion_activa)

    d1 = (
        pesos["temperatura"]   * variables_norm.get("t_temperatura",   0) +
        pesos["manto_nival"]   * variables_norm.get("t_manto_nival",   0) +
        pesos["viento"]        * variables_norm.get("t_viento",        0) +
        pesos["precipitacion"] * variables_norm.get("t_precipitacion", 0)
    )
    d2 = (
        pesos["fauna"]         * variables_norm.get("t_fauna",         0) +
        pesos["algas"]         * variables_norm.get("t_algas",         0) +
        pesos["nidificacion"]  * variables_norm.get("t_nidificacion",  0)
    )
    d3 = (
        pesos["turistas"]      * variables_norm.get("t_turistas",      0) +
        pesos["buques"]        * variables_norm.get("t_buques",        0) +
        pesos["dias_consec"]   * variables_norm.get("t_dias_consec",   0)
    )

    ict_a = round(d1 + d2 + d3, 2)

    # Clasificar semáforo
    estado = "verde"
    for nombre, rango in SEMAFORO.items():
        if rango["min"] <= ict_a <= rango["max"]:
            estado = nombre
            break

    return {
        "d1_climatica": round(d1, 2),
        "d2_ecologica": round(d2, 2),
        "d3_humana":    round(d3, 2),
        "ict_a":        ict_a,
        "estado":       estado,
        "ajuste_estacion": int(nidificacion_activa),
    }


# ── Paso 4: Guardar en SQLite ─────────────────────────────────────────────────

def guardar_variables(base_id: str, fecha: date, datos_crudos: dict,
                      datos_norm: dict, resultado: dict):
    """Persiste variables crudas y resultado ICT-A en la base de datos."""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Guardar variables crudas
    cur.execute("""
        INSERT OR REPLACE INTO variables_raw
        (base_id, fecha, temperatura, manto_nival, viento, precipitacion,
         fauna, algas, nidificacion, turistas, buques, dias_consec,
         fuente_clima, fuente_eco, ingreso_manual)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        base_id, fecha.isoformat(),
        datos_crudos.get("temperatura"),
        datos_crudos.get("manto_nival"),
        datos_crudos.get("viento"),
        datos_crudos.get("precipitacion"),
        datos_crudos.get("fauna"),
        datos_crudos.get("algas"),
        datos_crudos.get("nidificacion"),
        datos_crudos.get("turistas"),
        datos_crudos.get("buques"),
        datos_crudos.get("dias_consec"),
        "Meteochile+ERA5", "GBIF/SCAR",
        datos_crudos.get("ingreso_manual", 0),
    ))

    # Guardar ICT-A calculado
    cur.execute("""
        INSERT OR REPLACE INTO ict_calculado
        (base_id, fecha,
         t_temperatura, t_manto_nival, t_viento, t_precipitacion,
         t_fauna, t_algas, t_nidificacion,
         t_turistas, t_buques, t_dias_consec,
         d1_climatica, d2_ecologica, d3_humana,
         ict_a, estado, ajuste_estacion)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        base_id, fecha.isoformat(),
        datos_norm.get("t_temperatura"),
        datos_norm.get("t_manto_nival"),
        datos_norm.get("t_viento"),
        datos_norm.get("t_precipitacion"),
        datos_norm.get("t_fauna"),
        datos_norm.get("t_algas"),
        datos_norm.get("t_nidificacion"),
        datos_norm.get("t_turistas"),
        datos_norm.get("t_buques"),
        datos_norm.get("t_dias_consec"),
        resultado["d1_climatica"],
        resultado["d2_ecologica"],
        resultado["d3_humana"],
        resultado["ict_a"],
        resultado["estado"],
        resultado["ajuste_estacion"],
    ))

    # Generar alerta si el estado cambió
    _generar_alerta(cur, base_id, fecha, resultado)

    con.commit()
    con.close()


def _generar_alerta(cur, base_id, fecha, resultado):
    """Registra una alerta si el ICT-A cambió de estado."""
    cur.execute("""
        SELECT estado FROM ict_calculado
        WHERE base_id=? AND fecha < ?
        ORDER BY fecha DESC LIMIT 1
    """, (base_id, fecha.isoformat()))
    fila = cur.fetchone()
    estado_prev = fila[0] if fila else None

    if resultado["estado"] != estado_prev:
        cur.execute("""
            INSERT INTO alertas (base_id, fecha, tipo, valor_ict, estado_prev, estado_nuevo, mensaje)
            VALUES (?,?,?,?,?,?,?)
        """, (
            base_id, fecha.isoformat(), "cambio_estado",
            resultado["ict_a"], estado_prev, resultado["estado"],
            f"ICT-A cambió de {estado_prev} a {resultado['estado']} "
            f"(valor: {resultado['ict_a']})"
        ))


# ── Función principal ─────────────────────────────────────────────────────────

def procesar_base(base_id: str, fecha: date, datos_crudos: dict) -> dict:
    """
    Pipeline completo para una base:
    crudos → normalización → WLC → semáforo → SQLite → resultado
    """
    nidif_activa = bool(datos_crudos.get("nidificacion", 0))

    # Normalizar todas las variables
    vars_map = {
        "t_temperatura":   "temperatura",
        "t_manto_nival":   "manto_nival",
        "t_viento":        "viento",
        "t_precipitacion": "precipitacion",
        "t_fauna":         "fauna",
        "t_algas":         "algas",
        "t_nidificacion":  "nidificacion",
        "t_turistas":      "turistas",
        "t_buques":        "buques",
        "t_dias_consec":   "dias_consec",
    }
    datos_norm = {
        t_key: normalizar(var, datos_crudos.get(var))
        for t_key, var in vars_map.items()
    }

    # Calcular ICT-A
    resultado = calcular_iit(datos_norm, nidif_activa)

    # Persistir
    guardar_variables(base_id, fecha, datos_crudos, datos_norm, resultado)

    print(f"  [{base_id}] ICT-A={resultado['ict_a']} → {resultado['estado'].upper()}")
    return {**datos_norm, **resultado}


if __name__ == "__main__":
    from scripts.init_db import init_db
    init_db()
    ejemplo = {
        "temperatura": -4.0, "manto_nival": 30.0, "viento": 50.0,
        "precipitacion": 3.0, "fauna": 75.0, "algas": 20.0,
        "nidificacion": 1, "turistas": 147, "buques": 3, "dias_consec": 6,
    }
    res = procesar_base("frei", date.today(), ejemplo)
    print(res)
