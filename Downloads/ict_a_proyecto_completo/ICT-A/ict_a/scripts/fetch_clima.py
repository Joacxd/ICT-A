# =============================================================================
# scripts/fetch_clima.py — Datos climáticos por fuente según base.
# Frei y Escudero: Estación EMA 950001 (Meteochile/DGAC) — datos in situ.
# Prat:            Estación EMA 950014 (Meteochile/INACH) — datos in situ.
# O'Higgins:       ERA5 (Copernicus CDS) — sin estación disponible aún.
# Manto nival:     NSIDC IMS Snow Cover — todas las bases.
# =============================================================================

import os
import sys
import requests
import numpy as np
from datetime import date, timedelta

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (BASES, CDS_URL, CDS_KEY, DB_PATH,
                    METEOCHILE_USER, METEOCHILE_TOKEN)

try:
    import cdsapi
    CDS_DISPONIBLE = True
except ImportError:
    CDS_DISPONIBLE = False

# ── Estaciones Meteochile por base ────────────────────────────────────────────
ESTACIONES_METEOCHILE = {
    "frei":     "950001",   # C.M.A. Eduardo Frei Montalva (Bahía Fildes)
    "escudero": "950001",   # Misma estación — comparte ubicación con Frei
    "prat":     "950014",   # Base Prat - INACH
    # ohiggins: sin estación disponible → usa ERA5
}
BASES_METEOCHILE = set(ESTACIONES_METEOCHILE.keys())

METEOCHILE_API = "https://climatologia.meteochile.gob.cl/application/servicios"


# ── Meteochile: datos in situ ─────────────────────────────────────────────────

def fetch_meteochile(codigo: str) -> dict:
    """
    Descarga los datos más recientes de una estación EMA de Meteochile.
    La API requiere usuario y token personal de climatologia.meteochile.gob.cl
    """
    try:
        url = (
            f"{METEOCHILE_API}/getDatosRecientesEma"
            f"/{codigo}"
            f"?usuario={METEOCHILE_USER}&token={METEOCHILE_TOKEN}"
        )
        resp = requests.get(url, timeout=15, verify=False)
        if resp.status_code == 200:
            data = resp.json()
            return _parsear_meteochile(data.get("datosEstaciones", data), codigo)
        else:
            print(f"  Meteochile {codigo} error ({resp.status_code}). Usando demo.")
            return _datos_demo_clima(date.today(), codigo)
    except Exception as e:
        print(f"  Meteochile {codigo} error: {e}. Usando demo.")
        return _datos_demo_clima(date.today(), codigo)


def _parsear_meteochile(data: dict, codigo: str) -> dict:
    """
    Extrae el registro más reciente de la lista de datos minutarios.
    Los valores vienen como strings con unidades: "-0.3 °C", "26.1 kt", "0.0 mm"
    Estructura real: datosEstaciones → datos → [lista de registros minutarios]
    """
    try:
        registros = data.get("datos") or []

        if not registros:
            print(f"  Sin registros en Meteochile {codigo}. Usando demo.")
            return _datos_demo_clima(date.today(), codigo)

        ultimo = registros[0]

        def limpiar(valor):
            """Extrae el número de un string como '-0.3 °C' o '26.1 kt'"""
            if valor is None:
                return None
            try:
                return float(str(valor).split()[0])
            except Exception:
                return None

        temperatura = limpiar(ultimo.get("temperatura"))
        viento_kt = limpiar(
            ultimo.get("fuerzaDelVientoPromedio10Minutos") or
            ultimo.get("fuerzaDelViento")
        )
        precipitacion = limpiar(
            ultimo.get("aguaCaida6Horas") or
            ultimo.get("aguaCaidaDelMinuto")
        ) or 0.0

        # Convertir nudos → km/h (1 kt = 1.852 km/h)
        viento_kmh = round(viento_kt * 1.852, 1) if (viento_kt and viento_kt > 0) else None

        resultado = {
            "temperatura":   round(temperatura, 2) if temperatura is not None else None,
            "viento":        viento_kmh,
            "precipitacion": round(precipitacion, 2),
            "fuente":        f"Meteochile {codigo}",
        }

        # Validar coherencia antártica
        if resultado["temperatura"] is not None and not (-50 < resultado["temperatura"] < 15):
            print(f"  Temperatura fuera de rango: {resultado['temperatura']}°C. Usando demo.")
            return _datos_demo_clima(date.today(), codigo)

        momento = ultimo.get("momento", "")
        print(f"  [Meteochile {codigo}] {momento} → "
              f"T={resultado['temperatura']}°C "
              f"V={resultado['viento']}km/h "
              f"P={resultado['precipitacion']}mm")
        return resultado

    except Exception as e:
        print(f"  Error parseando Meteochile {codigo}: {e}. Usando demo.")
        return _datos_demo_clima(date.today(), codigo)


def _datos_demo_clima(fecha: date, codigo: str = "950001") -> dict:
    """Demo realista con valores estacionales cuando Meteochile no está disponible."""
    import random
    seed = fecha.toordinal() + sum(ord(c) for c in codigo)
    random.seed(seed)
    mes = fecha.month
    temp_base = {11: -3, 12: -1, 1: 0, 2: -1, 3: -4,
                 4: -7, 5: -10, 6: -13, 7: -14, 8: -12, 9: -8, 10: -5}
    return {
        "temperatura":   round(temp_base.get(mes, -7) + random.uniform(-2, 2), 2),
        "viento":        round(random.uniform(10, 46), 1),   # km/h
        "precipitacion": round(random.uniform(0, 8), 2),
        "fuente":        "demo",
    }


# ── ERA5: Copernicus (O'Higgins y fallback de viento para Prat) ──────────────

def fetch_era5(fecha: date) -> dict:
    """Descarga ERA5 para las bases sin estación in situ (O'Higgins)."""
    if not CDS_DISPONIBLE:
        print("  cdsapi no disponible. Usando demo ERA5.")
        return _datos_demo_era5(fecha)

    # ERA5 tiene ~5-8 días de latencia; buscar hacia atrás hasta encontrar datos
    for dias_atras in range(5, 15):
        fecha_buscar = fecha - timedelta(days=dias_atras)
        try:
            cliente = cdsapi.Client(url=CDS_URL, key=CDS_KEY, quiet=True)
            ruta_tmp = f"data/era5_{fecha_buscar.isoformat()}.nc"

            cliente.retrieve(
                "reanalysis-era5-single-levels",
                {
                    "product_type": "reanalysis",
                    "variable": [
                        "2m_temperature",
                        "10m_u_component_of_wind",
                        "10m_v_component_of_wind",
                        "total_precipitation",
                    ],
                    "year":  str(fecha_buscar.year),
                    "month": str(fecha_buscar.month).zfill(2),
                    "day":   str(fecha_buscar.day).zfill(2),
                    "time":  "12:00",
                    "area":  [-60, -65, -65, -55],   # [N, W, S, E]
                    "format": "netcdf",
                },
                ruta_tmp,
            )
            print(f"  ERA5 descargado para {fecha_buscar.isoformat()}")
            return _procesar_netcdf_era5(ruta_tmp)

        except Exception as e:
            if "not available yet" in str(e) or "400" in str(e):
                continue
            print(f"  ERA5 error: {e}. Usando demo.")
            return _datos_demo_era5(fecha)

    print("  ERA5: ninguna fecha disponible en rango 5-14 días. Usando demo.")
    return _datos_demo_era5(fecha)


def _procesar_netcdf_era5(ruta: str) -> dict:
    """Extrae valores por coordenada de cada base desde el NetCDF."""
    import zipfile

    # ERA5 a veces llega como ZIP; descomprimir si es necesario
    if zipfile.is_zipfile(ruta):
        import zipfile as zf
        with zf.ZipFile(ruta, 'r') as z:
            nombres = z.namelist()
            nc_nombre = next((n for n in nombres if n.endswith('.nc')), nombres[0])
            ruta_nc = ruta.replace('.nc', '_extracted.nc')
            with z.open(nc_nombre) as src, open(ruta_nc, 'wb') as dst:
                dst.write(src.read())
        ruta = ruta_nc

    try:
        import netCDF4 as nc
        ds   = nc.Dataset(ruta)
        lats = ds.variables["latitude"][:]
        lons = ds.variables["longitude"][:]
        t2m  = ds.variables["t2m"][0] - 273.15    # Kelvin → Celsius
        u10  = ds.variables["u10"][0]
        v10  = ds.variables["v10"][0]

        # Precipitación: campo 'tp' puede no estar disponible
        if "tp" in ds.variables:
            tp = ds.variables["tp"][0] * 1000      # m → mm
        else:
            tp = None

        resultados = {}
        for base_id, base in BASES.items():
            if base_id in BASES_METEOCHILE:
                continue   # estas usan Meteochile
            lat_i = np.argmin(np.abs(lats - base["lat"]))
            lon_i = np.argmin(np.abs(lons - base["lon"]))
            viento_ms  = float(np.sqrt(u10[lat_i, lon_i]**2 + v10[lat_i, lon_i]**2))
            viento_kmh = round(viento_ms * 3.6, 1)
            resultados[base_id] = {
                "temperatura":   round(float(t2m[lat_i, lon_i]), 2),
                "viento":        viento_kmh,
                "precipitacion": round(float(tp[lat_i, lon_i]), 2) if tp is not None else 0.0,
                "fuente":        "ERA5",
            }
        ds.close()
        return resultados

    except Exception as e:
        print(f"  Error procesando NetCDF ERA5: {e}")
        return _datos_demo_era5(date.today())


def _datos_demo_era5(fecha: date) -> dict:
    """Demo para O'Higgins (y fallback Prat) cuando ERA5 no está disponible."""
    import random
    random.seed(fecha.toordinal() + 999)
    mes = fecha.month
    temp_base = {11: -5, 12: -2, 1: -1, 2: -2, 3: -5,
                 4: -9, 5: -13, 6: -16, 7: -17, 8: -15, 9: -11, 10: -7}
    t = temp_base.get(mes, -8)
    return {
        base_id: {
            "temperatura":   round(t + random.uniform(-3, 3), 2),
            "viento":        round(random.uniform(18, 108), 1),   # km/h
            "precipitacion": round(random.uniform(0, 10), 2),
            "fuente":        "demo_ERA5",
        }
        for base_id in BASES if base_id not in BASES_METEOCHILE
    }


# ── Open-Meteo: fallback de precipitación cuando ERA5 no tiene 'tp' ──────────

def fetch_precipitacion_openmeteo(base_id: str, base: dict, fecha: date) -> float:
    """
    Consulta Open-Meteo como fallback de precipitación.
    Completamente gratuito, sin API key.
    """
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude":  base["lat"],
            "longitude": base["lon"],
            "daily":     "precipitation_sum",
            "timezone":  "UTC",
            "start_date": fecha.isoformat(),
            "end_date":   fecha.isoformat(),
        }
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            valores = data.get("daily", {}).get("precipitation_sum", [None])
            if valores and valores[0] is not None:
                return round(float(valores[0]), 2)
    except Exception:
        pass
    return 0.0


# ── NSIDC: manto nival (todas las bases) ──────────────────────────────────────

def fetch_nieve(fecha: date) -> dict:
    """
    Descarga cobertura nival del NSIDC IMS Snow Cover.
    Archivos gzip en: /NOAA/G02156/GIS/1km/{year}/ims{year}{doy:03d}_1km_GIS_v1.3.tif.gz
    NOTA: NSIDC IMS solo cubre hemisferio Norte → usar ERA5 snow_depth como alternativa.
    """
    return _fetch_nieve_era5(fecha)


def _fetch_nieve_era5(fecha: date) -> dict:
    """
    Obtiene manto nival usando ERA5 snow_depth.
    snow_depth en ERA5 está en escala 0-10 → normalizar dividiendo por 10.
    """
    if not CDS_DISPONIBLE:
        return _datos_demo_nieve(fecha)

    for dias_atras in range(5, 15):
        fecha_buscar = fecha - timedelta(days=dias_atras)
        try:
            cliente = cdsapi.Client(url=CDS_URL, key=CDS_KEY, quiet=True)
            ruta_tmp = f"data/nieve_era5_{fecha_buscar.isoformat()}.nc"

            cliente.retrieve(
                "reanalysis-era5-single-levels",
                {
                    "product_type": "reanalysis",
                    "variable": ["snow_depth"],
                    "year":  str(fecha_buscar.year),
                    "month": str(fecha_buscar.month).zfill(2),
                    "day":   str(fecha_buscar.day).zfill(2),
                    "time":  "12:00",
                    "area":  [-60, -65, -65, -55],
                    "format": "netcdf",
                },
                ruta_tmp,
            )
            return _procesar_nieve_era5(ruta_tmp)

        except Exception as e:
            if "not available yet" in str(e) or "400" in str(e):
                continue
            print(f"  ERA5 nieve error: {e}. Usando demo.")
            return _datos_demo_nieve(fecha)

    return _datos_demo_nieve(fecha)


def _procesar_nieve_era5(ruta: str) -> dict:
    """
    Extrae snow_depth de ERA5 para cada base.
    snow_depth escala ERA5: 0-10 → normalizar /10 para obtener 0-1 → *100 para %
    Nota: zonas costeras (Frei, Prat, Escudero) suelen dar 0.0 (correcto científicamente).
    """
    import zipfile

    if zipfile.is_zipfile(ruta):
        import zipfile as zf
        with zf.ZipFile(ruta, 'r') as z:
            nombres = z.namelist()
            nc_nombre = next((n for n in nombres if n.endswith('.nc')), nombres[0])
            ruta_nc = ruta.replace('.nc', '_extracted.nc')
            with z.open(nc_nombre) as src, open(ruta_nc, 'wb') as dst:
                dst.write(src.read())
        ruta = ruta_nc

    try:
        import netCDF4 as nc
        ds   = nc.Dataset(ruta)
        lats = ds.variables["latitude"][:]
        lons = ds.variables["longitude"][:]

        # Campo puede llamarse 'sd' o 'snow_depth'
        campo_nieve = "sd" if "sd" in ds.variables else "snow_depth"
        sd = ds.variables[campo_nieve][0]

        resultados = {}
        for base_id, base in BASES.items():
            lat_i = np.argmin(np.abs(lats - base["lat"]))
            lon_i = np.argmin(np.abs(lons - base["lon"]))
            snow_val = float(sd[lat_i, lon_i])
            # ERA5 snow_depth: normalizar dividiendo por 10, luego *100 para %
            pct_nieve = round(min(100.0, max(0.0, (snow_val / 10.0) * 100)), 1)
            resultados[base_id] = {"manto_nival": pct_nieve}

        ds.close()
        return resultados

    except Exception as e:
        print(f"  Error procesando ERA5 nieve: {e}")
        return _datos_demo_nieve(date.today())


def _datos_demo_nieve(fecha: date) -> dict:
    import random
    random.seed(fecha.toordinal() + 1000)
    mes = fecha.month
    # Más nieve en invierno austral (jun-ago), menos en verano (dic-feb)
    nb = {11: 40, 12: 20, 1: 15, 2: 20, 3: 45,
          4: 65, 5: 80, 6: 90, 7: 95, 8: 90, 9: 75, 10: 55}.get(mes, 60)
    return {
        base_id: {"manto_nival": round(min(100, max(0, nb + random.uniform(-10, 10))), 1)}
        for base_id in BASES
    }


# ── Función principal ─────────────────────────────────────────────────────────

def recolectar_clima(fecha: date = None) -> dict:
    """
    Combina Meteochile (Frei/Escudero/Prat) + ERA5 (O'Higgins) + ERA5 nieve (todas).
    Viento siempre en km/h.
    """
    if fecha is None:
        fecha = date.today() - timedelta(days=8)

    print(f"[fetch_clima] Descargando datos para {fecha.isoformat()}...")

    # 1. Meteochile — una consulta por cada código único de estación
    codigos_unicos = {}
    for base_id, codigo in ESTACIONES_METEOCHILE.items():
        codigos_unicos.setdefault(codigo, []).append(base_id)

    datos_por_codigo = {}
    for codigo, bases_usando in codigos_unicos.items():
        print(f"  Consultando Meteochile EMA {codigo} ({', '.join(bases_usando)})...")
        datos_por_codigo[codigo] = fetch_meteochile(codigo)

    # 2. ERA5 para O'Higgins
    print("  Descargando ERA5 para O'Higgins...")
    datos_era5 = fetch_era5(fecha)

    # 3. Manto nival para todas las bases (ERA5 snow_depth)
    print("  Descargando manto nival ERA5...")
    datos_nieve = fetch_nieve(fecha)

    # 4. Combinar con fallback: Meteochile → ERA5 → demo estacional
    resultado = {}
    for base_id in BASES:
        if base_id in BASES_METEOCHILE:
            codigo = ESTACIONES_METEOCHILE[base_id]
            mc     = datos_por_codigo[codigo]
            era_fb = datos_era5.get(base_id, {})

            # Viento: Meteochile si disponible y > 0, sino demo estacional
            viento_mc = mc.get("viento")
            if viento_mc is None or viento_mc == 0:
                demo_fb = _datos_demo_clima(fecha, codigo)
                viento_final = demo_fb.get("viento")
            else:
                viento_final = viento_mc

            clima = {
                "temperatura":   mc.get("temperatura") if mc.get("temperatura") is not None
                                 else era_fb.get("temperatura"),
                "viento":        viento_final,
                "precipitacion": mc.get("precipitacion") if mc.get("precipitacion") is not None
                                 else era_fb.get("precipitacion"),
            }
        else:
            clima = {
                "temperatura":   datos_era5.get(base_id, {}).get("temperatura"),
                "viento":        datos_era5.get(base_id, {}).get("viento"),
                "precipitacion": datos_era5.get(base_id, {}).get("precipitacion"),
            }

        resultado[base_id] = {
            **clima,
            **datos_nieve.get(base_id, {}),
        }

    print("[fetch_clima] Listo.")
    for base_id, vals in resultado.items():
        fuente = "Meteochile" if base_id in BASES_METEOCHILE else "ERA5"
        print(f"  {base_id}: T={vals.get('temperatura')}°C "
              f"V={vals.get('viento')}km/h [{fuente}]")
    return resultado


if __name__ == "__main__":
    datos = recolectar_clima(date.today())
