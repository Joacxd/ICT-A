# =============================================================================
# scripts/fetch_eco.py — Datos ecológicos: fauna, algas y nidificación.
# Fuentes: SCAR BIOTAS (biodiversity.aq / GBIF API) + calendario estacional.
# =============================================================================

import os
import sys
import math
import requests
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import BASES

# API GBIF (compatible con biodiversity.aq) — completamente pública, sin key
GBIF_API = "https://api.gbif.org/v1"

# Especies antárticas clave monitoreadas
ESPECIES_SENSIBLES = [
    "Pygoscelis antarcticus",   # Pingüino de barbijo
    "Pygoscelis papua",          # Pingüino papúa
    "Mirounga leonina",          # Elefante marino del sur
    "Arctocephalus gazella",     # Lobo fino antártico
    "Macronectes giganteus",     # Petrel gigante
    "Sterna vittata",            # Gaviotín antártico
    "Catharacta maccormicki",    # Skúa antártico
]

# ── Fauna: registros GBIF en área de cada base ───────────────────────────────

def fetch_fauna(base_id: str, base: dict, fecha: date) -> float:
    """
    Consulta GBIF por registros de fauna sensible cerca de la base.
    Devuelve un índice de presencia 0-100.
    """
    try:
        year = fecha.year
        lat, lon = base["lat"], base["lon"]
        radio_grados = base["radio_km"] / 111.0  # aprox km → grados

        total_registros = 0
        for especie in ESPECIES_SENSIBLES[:4]:  # limitar llamadas API
            params = {
                "scientificName": especie,
                "decimalLatitude": f"{lat - radio_grados},{lat + radio_grados}",
                "decimalLongitude": f"{lon - radio_grados},{lon + radio_grados}",
                "year": f"{year-1},{year}",
                "hasCoordinate": "true",
                "limit": 1,
            }
            resp = requests.get(
                f"{GBIF_API}/occurrence/search",
                params=params,
                timeout=10
            )
            if resp.status_code == 200:
                total_registros += resp.json().get("count", 0)

        # Normalizar: 0 registros → 0, ≥20 registros → 100
        indice = min(100, total_registros * 5)
        return round(float(indice), 1)

    except Exception as e:
        print(f"  GBIF error ({base_id}): {e}. Usando demo.")
        return _fauna_demo(base_id, fecha)


def _fauna_demo(base_id: str, fecha: date) -> float:
    """Datos de demostración basados en estacionalidad real."""
    import random
    random.seed(fecha.toordinal() + hash(base_id) % 1000)
    mes = fecha.month
    # Mayor actividad de fauna en verano austral (oct-mar)
    fauna_base = {10: 60, 11: 75, 12: 80, 1: 85, 2: 80, 3: 70,
                  4: 40, 5: 20, 6: 10, 7: 10, 8: 15, 9: 35}
    base_val = fauna_base.get(mes, 30)
    return round(min(100, max(0, base_val + random.uniform(-10, 10))), 1)


# ── Algas: índice de cobertura algal estimada ────────────────────────────────

def fetch_algas(base_id: str, fecha: date) -> float:
    """
    Estima cobertura de algas (Prasiola crispa y algas verdes) en playas.
    En producción real: procesamiento de imágenes Sentinel-2 con índice NDVI.
    Para la feria: modelo estacional basado en temperatura y luz.
    """
    # Modelo simplificado: algas aumentan con temperaturas > -2°C en verano
    mes = fecha.month
    # Las algas proliferan en verano austral cuando hay deshielo
    algas_estacional = {
        10: 15, 11: 30, 12: 45, 1: 50, 2: 45, 3: 30,
        4: 15,  5: 5,  6: 2,   7: 2,  8: 5,  9: 10
    }
    base_val = algas_estacional.get(mes, 10)
    import random
    random.seed(fecha.toordinal() + hash(base_id) % 2000 + 500)
    return round(min(100, max(0, base_val + random.uniform(-8, 8))), 1)


# ── Nidificación: variable binaria por calendario ────────────────────────────

def calcular_nidificacion(fecha: date) -> int:
    """
    Determina si la fecha cae en período de nidificación activa (nov-feb).
    Devuelve 1 (activo) o 0 (fuera de temporada).
    Basado en literatura: Trathan et al. (2008), IAATO (2023).
    """
    mes = fecha.month
    # Nidificación activa: noviembre, diciembre, enero, febrero
    return 1 if mes in [11, 12, 1, 2] else 0


# ── Función principal ─────────────────────────────────────────────────────────

def recolectar_eco(fecha: date = None) -> dict:
    """
    Recolecta datos ecológicos para todas las bases.
    Devuelve dict: {base_id: {fauna, algas, nidificacion}}
    """
    if fecha is None:
        fecha = date.today()

    print(f"[fetch_eco] Consultando datos ecológicos para {fecha.isoformat()}...")
    nidificacion = calcular_nidificacion(fecha)

    resultado = {}
    for base_id, base in BASES.items():
        fauna  = fetch_fauna(base_id, base, fecha)
        algas  = fetch_algas(base_id, fecha)
        resultado[base_id] = {
            "fauna":        fauna,
            "algas":        algas,
            "nidificacion": nidificacion,
        }
        print(f"  {base_id}: fauna={fauna}, algas={algas}, nidificación={nidificacion}")

    return resultado


if __name__ == "__main__":
    datos = recolectar_eco()
    for base, vals in datos.items():
        print(f"  {base}: {vals}")
