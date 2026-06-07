# =============================================================================
# scripts/actualizar.py — Orquestador del ciclo completo de actualización.
# Ejecutar manualmente o programar con cron cada 24 horas.
# Uso: python scripts/actualizar.py [--fecha YYYY-MM-DD] [--demo]
# =============================================================================

import os
import sys
import argparse
import sqlite3
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import DB_PATH, BASES

from scripts.init_db       import init_db
from scripts.fetch_clima   import recolectar_clima
from scripts.fetch_eco     import recolectar_eco
from scripts.fetch_buques  import recolectar_buques
from scripts.calcular_iit  import procesar_base


def obtener_dias_consecutivos(base_id: str, fecha: date) -> int:
    """
    Calcula cuántos días consecutivos lleva recibiendo visitas la base.
    Lee los últimos 14 registros de la BD para contarlos.
    """
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""
            SELECT fecha, turistas FROM variables_raw
            WHERE base_id=? AND fecha <= ?
            ORDER BY fecha DESC LIMIT 14
        """, (base_id, fecha.isoformat()))
        filas = cur.fetchall()
        con.close()

        consecutivos = 0
        for _, turistas in filas:
            if turistas and turistas > 0:
                consecutivos += 1
            else:
                break
        return consecutivos
    except Exception:
        return 0


def actualizar_todo(fecha: date, datos_manuales: dict = None) -> dict:
    """
    Pipeline completo de actualización para todas las bases.
    datos_manuales: {base_id: {turistas, buques}} — ingresado por formulario web.
    """
    print(f"\n{'='*55}")
    print(f"  IIT-A — Actualización del {fecha.isoformat()}")
    print(f"{'='*55}")

    # Asegurar que la BD existe
    init_db()

    # ── 1. Recolectar datos automáticos ──────────────────────────────────────
    print("\n[1/4] Recolectando datos climáticos...")
    clima  = recolectar_clima(fecha)

    print("\n[2/4] Recolectando datos ecológicos...")
    eco    = recolectar_eco(fecha)

    print("\n[3/4] Recolectando datos AIS (buques)...")
    buques = recolectar_buques(fecha)

    # ── 2. Combinar y calcular IIT-A por base ────────────────────────────────
    print("\n[4/4] Calculando IIT-A...")
    resultados = {}

    for base_id in BASES:
        datos = {
            **clima.get(base_id, {}),
            **eco.get(base_id, {}),
            **buques.get(base_id, {}),
        }

        # Inyectar datos manuales si los hay (turistas viene del formulario)
        if datos_manuales and base_id in datos_manuales:
            manuales = datos_manuales[base_id]
            datos.update(manuales)
            datos["ingreso_manual"] = 1
        else:
            # Si no hay dato manual, usar último valor conocido de la BD
            datos.setdefault("turistas", _ultimo_valor(base_id, "turistas") or 0)
            datos.setdefault("ingreso_manual", 0)

        # Calcular días consecutivos automáticamente
        datos["dias_consec"] = obtener_dias_consecutivos(base_id, fecha)

        resultado = procesar_base(base_id, fecha, datos)
        resultados[base_id] = {
            "iit_a":  resultado["iit_a"],
            "estado": resultado["estado"],
            "datos":  datos,
        }

    print(f"\n{'='*55}")
    print("  Actualización completada.")
    for base_id, res in resultados.items():
        print(f"  {base_id:12} → IIT-A {res['iit_a']:5.1f}  [{res['estado'].upper()}]")
    print(f"{'='*55}\n")

    return resultados


def _ultimo_valor(base_id: str, campo: str):
    """Lee el último valor conocido de un campo desde la BD."""
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute(f"""
            SELECT {campo} FROM variables_raw
            WHERE base_id=? AND {campo} IS NOT NULL
            ORDER BY fecha DESC LIMIT 1
        """, (base_id,))
        fila = cur.fetchone()
        con.close()
        return fila[0] if fila else None
    except Exception:
        return None


def poblar_historico(dias: int = 30):
    """
    Genera un historial de los últimos N días para demostración.
    Útil para la feria: pobla la BD con datos realistas sin APIs externas.
    """
    print(f"\nPoblando historial de {dias} días con datos de demostración...")
    hoy = date.today()
    for i in range(dias, 0, -1):
        fecha = hoy - timedelta(days=i)
        actualizar_todo(fecha)
    print(f"Historial poblado desde {hoy - timedelta(days=dias)} hasta {hoy}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Actualizador IIT-A")
    parser.add_argument("--fecha", type=str, help="Fecha YYYY-MM-DD (default: hoy)")
    parser.add_argument("--demo",  action="store_true", help="Poblar 30 días de historial demo")
    args = parser.parse_args()

    if args.demo:
        poblar_historico(30)
    else:
        fecha = date.fromisoformat(args.fecha) if args.fecha else date.today()
        actualizar_todo(fecha)
