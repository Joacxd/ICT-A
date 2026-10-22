# =============================================================================
# scripts/fetch_buques.py — Buques activos en zona de cada base.
# Fuente: aisstream.io (WebSocket AIS abierto y gratuito).
# =============================================================================

import os
import sys
import json
import asyncio
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import BASES, AISSTREAM_KEY

AISSTREAM_WS = "wss://stream.aisstream.io/v0/stream"


async def _fetch_aisstream(base_id: str, base: dict, timeout_seg: int = 8) -> int:
    """
    Conecta al WebSocket de aisstream.io y cuenta buques en el radio de la base.
    Escucha durante timeout_seg segundos y cuenta mensajes AIS únicos (por MMSI).
    """
    try:
        import websockets

        lat, lon = base["lat"], base["lon"]
        radio_grados = base["radio_km"] / 111.0

        mensaje_suscripcion = json.dumps({
            "APIKey": AISSTREAM_KEY,
            "BoundingBoxes": [[
                [lat - radio_grados, lon - radio_grados],
                [lat + radio_grados, lon + radio_grados]
            ]],
            "FilterMessageTypes": ["PositionReport"]
        })

        mmsis_vistos = set()
        async with websockets.connect(AISSTREAM_WS) as ws:
            await ws.send(mensaje_suscripcion)
            try:
                async with asyncio.timeout(timeout_seg):
                    async for mensaje in ws:
                        data = json.loads(mensaje)
                        mmsi = (data.get("Message", {})
                                    .get("PositionReport", {})
                                    .get("UserID"))
                        if mmsi:
                            mmsis_vistos.add(mmsi)
            except asyncio.TimeoutError:
                pass

        return len(mmsis_vistos)

    except ImportError:
        print(f"  websockets no instalado. Usar: pip install websockets")
        return _buques_demo(base_id)
    except Exception as e:
        print(f"  aisstream error ({base_id}): {e}. Usando demo.")
        return _buques_demo(base_id)


def fetch_buques_base(base_id: str, base: dict) -> int:
    """Wrapper síncrono para el WebSocket async."""
    if AISSTREAM_KEY == "TU_API_KEY_AISSTREAM":
        return _buques_demo(base_id)
    try:
        return asyncio.run(_fetch_aisstream(base_id, base))
    except Exception as e:
        print(f"  Error ejecutando aisstream ({base_id}): {e}. Usando demo.")
        return _buques_demo(base_id)


def _buques_demo(base_id: str) -> int:
    """Datos de demostración basados en temporada turística real."""
    import random
    mes = date.today().month
    trafico_base = {
        11: 2, 12: 3, 1: 4, 2: 3, 3: 2,
        4: 0,  5: 0,  6: 0, 7: 0, 8: 0, 9: 0, 10: 1
    }
    base_val = trafico_base.get(mes, 0)
    if base_id == "escudero":
        base_val = max(0, base_val - 1)   # Escudero tiene menos tráfico turístico
    return max(0, base_val + random.randint(-1, 1))


def recolectar_buques(fecha: date = None) -> dict:
    """
    Recolecta conteo de buques para todas las bases.
    Devuelve dict: {base_id: {buques: int}}
    """
    if fecha is None:
        fecha = date.today()

    print(f"[fetch_buques] Consultando AIS para {fecha.isoformat()}...")
    resultado = {}
    for base_id, base in BASES.items():
        n_buques = fetch_buques_base(base_id, base)
        resultado[base_id] = {"buques": n_buques}
        print(f"  {base_id}: {n_buques} buques en zona")

    return resultado


if __name__ == "__main__":
    datos = recolectar_buques()
    for base, vals in datos.items():
        print(f"  {base}: {vals}")
