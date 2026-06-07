# =============================================================================
# scripts/calcular_iit.py — Núcleo matemático del sistema ICT-A.
# Compatible con SQLite (local) y PostgreSQL (Render).
# =============================================================================

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import PESOS, RANGOS_HIST, SEMAFORO, FACTOR_ESTACIONAL, BASES

def get_conn():
    from scripts.init_db import get_conn as _get_conn
    return _get_conn()

# ── Normalización min-max ────────────────────────────────────────────────────
def normalizar(variable: str, valor: float) -> float:
    if valor is None:
        return 0.0
    rango = RANGOS_HIST.get(variable)
    if not rango:
        return float(valor) * 100
    vmin, vmax = rango["min"], rango["max"]
    if vmax == vmin:
        return 0.0
    norm = (valor - vmin) / (vmax - vmin) * 100
    return round(min(100.0, max(0.0, norm)), 2)

# ── Ajuste estacional ────────────────────────────────────────────────────────
def pesos_ajustados(nidificacion_activa: bool) -> dict:
    pesos = dict(PESOS)
    if not nidificacion_activa:
        return pesos
    d2_vars = ["fauna", "algas", "nidificacion"]
    d1_vars = ["temperatura", "manto_nival", "viento", "precipitacion"]
    incremento_total = sum(pesos[v] * (FACTOR_ESTACIONAL - 1) for v in d2_vars)
    reduccion_por_var = incremento_total / len(d1_vars)
    for v in d2_vars:
        pesos[v] = round(pesos[v] * FACTOR_ESTACIONAL, 4)
    for v in d1_vars:
        pesos[v] = round(max(0, pesos[v] - reduccion_por_var), 4)
    return pesos

# ── Cálculo WLC ──────────────────────────────────────────────────────────────
def calcular_iit(variables_norm: dict, nidificacion_activa: bool) -> dict:
    pesos = pesos_ajustados(nidificacion_activa)
    d1 = (pesos["temperatura"]   * variables_norm.get("t_temperatura",   0) +
          pesos["manto_nival"]   * variables_norm.get("t_manto_nival",   0) +
          pesos["viento"]        * variables_norm.get("t_viento",        0) +
          pesos["precipitacion"] * variables_norm.get("t_precipitacion", 0))
    d2 = (pesos["fauna"]         * variables_norm.get("t_fauna",         0) +
          pesos["algas"]         * variables_norm.get("t_algas",         0) +
          pesos["nidificacion"]  * variables_norm.get("t_nidificacion",  0))
    d3 = (pesos["turistas"]      * variables_norm.get("t_turistas",      0) +
          pesos["buques"]        * variables_norm.get("t_buques",        0) +
          pesos["dias_consec"]   * variables_norm.get("t_dias_consec",   0))
    iit_a = round(d1 + d2 + d3, 2)
    estado = "verde"
    for nombre, rango in SEMAFORO.items():
        if rango["min"] <= iit_a <= rango["max"]:
            estado = nombre
            break
    return {"d1_climatica": round(d1,2), "d2_ecologica": round(d2,2),
            "d3_humana": round(d3,2), "iit_a": iit_a, "estado": estado,
            "ajuste_estacion": int(nidificacion_activa)}

# ── Guardar en BD (SQLite o PostgreSQL) ──────────────────────────────────────
def guardar_variables(base_id: str, fecha: date, datos_crudos: dict,
                      datos_norm: dict, resultado: dict):
    con, tipo = get_conn()
    cur = con.cursor()
    p = "%s" if tipo == "pg" else "?"

    if tipo == "pg":
        cur.execute(f"""
            INSERT INTO variables_raw
            (base_id,fecha,temperatura,manto_nival,viento,precipitacion,
             fauna,algas,nidificacion,turistas,buques,dias_consec,
             fuente_clima,fuente_eco,ingreso_manual)
            VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p})
            ON CONFLICT (base_id,fecha) DO UPDATE SET
            temperatura=EXCLUDED.temperatura, manto_nival=EXCLUDED.manto_nival,
            viento=EXCLUDED.viento, precipitacion=EXCLUDED.precipitacion,
            fauna=EXCLUDED.fauna, algas=EXCLUDED.algas,
            nidificacion=EXCLUDED.nidificacion, turistas=EXCLUDED.turistas,
            buques=EXCLUDED.buques, dias_consec=EXCLUDED.dias_consec,
            fuente_clima=EXCLUDED.fuente_clima, fuente_eco=EXCLUDED.fuente_eco,
            ingreso_manual=EXCLUDED.ingreso_manual
        """, (base_id, fecha.isoformat(),
              datos_crudos.get("temperatura"), datos_crudos.get("manto_nival"),
              datos_crudos.get("viento"), datos_crudos.get("precipitacion"),
              datos_crudos.get("fauna"), datos_crudos.get("algas"),
              datos_crudos.get("nidificacion"), datos_crudos.get("turistas"),
              datos_crudos.get("buques"), datos_crudos.get("dias_consec"),
              "ERA5+Meteochile", "GBIF/SCAR", datos_crudos.get("ingreso_manual", 0)))

        cur.execute(f"""
            INSERT INTO iit_calculado
            (base_id,fecha,t_temperatura,t_manto_nival,t_viento,t_precipitacion,
             t_fauna,t_algas,t_nidificacion,t_turistas,t_buques,t_dias_consec,
             d1_climatica,d2_ecologica,d3_humana,iit_a,estado,ajuste_estacion)
            VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p})
            ON CONFLICT (base_id,fecha) DO UPDATE SET
            t_temperatura=EXCLUDED.t_temperatura, t_manto_nival=EXCLUDED.t_manto_nival,
            t_viento=EXCLUDED.t_viento, t_precipitacion=EXCLUDED.t_precipitacion,
            t_fauna=EXCLUDED.t_fauna, t_algas=EXCLUDED.t_algas,
            t_nidificacion=EXCLUDED.t_nidificacion, t_turistas=EXCLUDED.t_turistas,
            t_buques=EXCLUDED.t_buques, t_dias_consec=EXCLUDED.t_dias_consec,
            d1_climatica=EXCLUDED.d1_climatica, d2_ecologica=EXCLUDED.d2_ecologica,
            d3_humana=EXCLUDED.d3_humana, iit_a=EXCLUDED.iit_a,
            estado=EXCLUDED.estado, ajuste_estacion=EXCLUDED.ajuste_estacion
        """, (base_id, fecha.isoformat(),
              datos_norm.get("t_temperatura"), datos_norm.get("t_manto_nival"),
              datos_norm.get("t_viento"), datos_norm.get("t_precipitacion"),
              datos_norm.get("t_fauna"), datos_norm.get("t_algas"),
              datos_norm.get("t_nidificacion"), datos_norm.get("t_turistas"),
              datos_norm.get("t_buques"), datos_norm.get("t_dias_consec"),
              resultado["d1_climatica"], resultado["d2_ecologica"],
              resultado["d3_humana"], resultado["iit_a"],
              resultado["estado"], resultado["ajuste_estacion"]))
    else:
        cur.execute("""
            INSERT OR REPLACE INTO variables_raw
            (base_id,fecha,temperatura,manto_nival,viento,precipitacion,
             fauna,algas,nidificacion,turistas,buques,dias_consec,
             fuente_clima,fuente_eco,ingreso_manual)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (base_id, fecha.isoformat(),
              datos_crudos.get("temperatura"), datos_crudos.get("manto_nival"),
              datos_crudos.get("viento"), datos_crudos.get("precipitacion"),
              datos_crudos.get("fauna"), datos_crudos.get("algas"),
              datos_crudos.get("nidificacion"), datos_crudos.get("turistas"),
              datos_crudos.get("buques"), datos_crudos.get("dias_consec"),
              "ERA5+Meteochile", "GBIF/SCAR", datos_crudos.get("ingreso_manual", 0)))

        cur.execute("""
            INSERT OR REPLACE INTO iit_calculado
            (base_id,fecha,t_temperatura,t_manto_nival,t_viento,t_precipitacion,
             t_fauna,t_algas,t_nidificacion,t_turistas,t_buques,t_dias_consec,
             d1_climatica,d2_ecologica,d3_humana,iit_a,estado,ajuste_estacion)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (base_id, fecha.isoformat(),
              datos_norm.get("t_temperatura"), datos_norm.get("t_manto_nival"),
              datos_norm.get("t_viento"), datos_norm.get("t_precipitacion"),
              datos_norm.get("t_fauna"), datos_norm.get("t_algas"),
              datos_norm.get("t_nidificacion"), datos_norm.get("t_turistas"),
              datos_norm.get("t_buques"), datos_norm.get("t_dias_consec"),
              resultado["d1_climatica"], resultado["d2_ecologica"],
              resultado["d3_humana"], resultado["iit_a"],
              resultado["estado"], resultado["ajuste_estacion"]))

    _generar_alerta(cur, base_id, fecha, resultado, tipo)
    con.commit()
    con.close()

def _generar_alerta(cur, base_id, fecha, resultado, tipo):
    p = "%s" if tipo == "pg" else "?"
    cur.execute(f"""
        SELECT estado FROM iit_calculado
        WHERE base_id={p} AND fecha < {p}
        ORDER BY fecha DESC LIMIT 1
    """, (base_id, fecha.isoformat()))
    fila = cur.fetchone()
    estado_prev = (fila[0] if isinstance(fila, tuple) else fila["estado"]) if fila else None
    if resultado["estado"] != estado_prev:
        cur.execute(f"""
            INSERT INTO alertas (base_id,fecha,tipo,valor_iit,estado_prev,estado_nuevo,mensaje)
            VALUES ({p},{p},{p},{p},{p},{p},{p})
        """, (base_id, fecha.isoformat(), "cambio_estado",
              resultado["iit_a"], estado_prev, resultado["estado"],
              f"ICT-A cambió de {estado_prev} a {resultado['estado']} (valor: {resultado['iit_a']})"))

# ── Pipeline principal ───────────────────────────────────────────────────────
def procesar_base(base_id: str, fecha: date, datos_crudos: dict) -> dict:
    nidif_activa = bool(datos_crudos.get("nidificacion", 0))
    vars_map = {
        "t_temperatura": "temperatura", "t_manto_nival": "manto_nival",
        "t_viento": "viento", "t_precipitacion": "precipitacion",
        "t_fauna": "fauna", "t_algas": "algas", "t_nidificacion": "nidificacion",
        "t_turistas": "turistas", "t_buques": "buques", "t_dias_consec": "dias_consec",
    }
    datos_norm = {t_key: normalizar(var, datos_crudos.get(var)) for t_key, var in vars_map.items()}
    resultado = calcular_iit(datos_norm, nidif_activa)
    guardar_variables(base_id, fecha, datos_crudos, datos_norm, resultado)
    print(f"  [{base_id}] ICT-A={resultado['iit_a']} → {resultado['estado'].upper()}")
    return {**datos_norm, **resultado}
