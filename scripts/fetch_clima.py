# =============================================================================
# scripts/fetch_clima.py — Datos climáticos por fuente según base.
# Frei y Escudero: Estación EMA 950001 (Meteochile/DMC) — datos in situ.
# Prat:            Estación EMA 950014 (Meteochile/DMC) — datos in situ.
# O'Higgins:       ERA5 (Copernicus CDS) — sin estación disponible aún.
# =============================================================================

import os
import sys
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import numpy as np
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (BASES, CDS_URL, CDS_KEY, DB_PATH,
                    METEOCHILE_USER, METEOCHILE_TOKEN)

try:
    import cdsapi
    CDS_DISPONIBLE = True
except ImportError:
    CDS_DISPONIBLE = False

# Estaciones Meteochile por base
ESTACIONES_METEOCHILE = {
    "frei":     "950001",  # C.M.A. Eduardo Frei Montalva
    "escudero": "950001",  # Misma estación (Bahía Fildes)
    "prat":     "950014",  # Base Prat - INACH
}
BASES_METEOCHILE = set(ESTACIONES_METEOCHILE.keys())

METEOCHILE_API = "https://climatologia.meteochile.gob.cl/application/servicios"


# ── Meteochile: datos in situ ─────────────────────────────────────────────────

def fetch_meteochile(codigo: str) -> dict:
    """
    Descarga los datos más recientes de una estación EMA de Meteochile.
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
    Los valores vienen como strings con unidades: "-0.3 °C", "15.2 kt", "0.0 mm"
    """
    try:
        registros = data.get("datos") or []

        if not registros:
            print(f"  Sin registros en Meteochile {codigo}. Usando demo.")
            return _datos_demo_clima(date.today(), codigo)

        ultimo = registros[0]

        def limpiar(valor):
            if valor is None:
                return None
            try:
                return float(str(valor).split()[0])
            except Exception:
                return None

        temperatura   = limpiar(ultimo.get("temperatura"))
        viento_kt     = limpiar(
            ultimo.get("fuerzaDelVientoPromedio10Minutos") or
            ultimo.get("fuerzaDelViento")
        )
        precipitacion = limpiar(
            ultimo.get("aguaCaida6Horas") or
            ultimo.get("aguaCaidaDelMinuto")
        ) or 0.0

        # Convertir kt → km/h (1 kt = 1.852 km/h)
        viento_kmh = round(viento_kt * 1.852, 1) if viento_kt and viento_kt > 0 else None

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
    """Demo realista cuando Meteochile no está disponible."""
    import random
    random.seed(fecha.toordinal() + int(codigo))
    mes = fecha.month
    temp_base = {11: -3, 12: -1, 1: 0, 2: -1, 3: -4,
                 4: -7, 5: -10, 6: -13, 7: -14, 8: -12, 9: -8, 10: -5}
    return {
        "temperatura":   round(temp_base.get(mes, -7) + random.uniform(-2, 2), 2),
        "viento":        round(random.uniform(10, 46), 1),
        "precipitacion": round(random.uniform(0, 8), 2),
        "fuente":        "demo",
    }


# ── ERA5: Copernicus (solo O'Higgins) ─────────────────────────────────────────

def fetch_era5(fecha: date) -> dict:
    """Descarga ERA5 para O'Higgins y respaldo de Prat."""
    if not CDS_DISPONIBLE:
        print("  cdsapi no disponible. Usando demo ERA5.")
        return _datos_demo_era5(fecha)

    # Intentar con fechas retroactivas hasta encontrar una disponible
    for dias_atras in range(5, 15):
        fecha_intento = date.today() - timedelta(days=dias_atras)
        try:
            cliente = cdsapi.Client(url=CDS_URL, key=CDS_KEY, quiet=True)
            ruta_tmp = f"data/era5_{fecha_intento.isoformat()}.nc"

            # Eliminar archivo si existe (evitar caché corrupto)
            import os
            if os.path.exists(ruta_tmp):
                os.remove(ruta_tmp)

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
                    "year":  str(fecha_intento.year),
                    "month": str(fecha_intento.month).zfill(2),
                    "day":   str(fecha_intento.day).zfill(2),
                    "time":  "12:00",
                    "area":  [-60, -65, -65, -55],
                    "format": "netcdf",
                },
                ruta_tmp,
            )
            # Descomprimir si llegó como ZIP
            import zipfile, os
            if zipfile.is_zipfile(ruta_tmp):
                print(f"  ERA5 llegó comprimido, descomprimiendo...")
                with zipfile.ZipFile(ruta_tmp, 'r') as z:
                    nombres = z.namelist()
                    nc_dentro = [n for n in nombres if n.endswith('.nc')][0]
                    ruta_nc = ruta_tmp.replace('.nc', '_real.nc')
                    with z.open(nc_dentro) as src, open(ruta_nc, 'wb') as dst:
                        dst.write(src.read())
                os.remove(ruta_tmp)
                os.rename(ruta_nc, ruta_tmp)
                print(f"  ERA5 descomprimido correctamente")

            print(f"  ERA5 descargado para {fecha_intento.isoformat()}")
            return _procesar_netcdf_era5(ruta_tmp)

        except Exception as e:
            if "400" in str(e) or "not available" in str(e):
                print(f"  ERA5 {fecha_intento.isoformat()} no disponible, probando día anterior...")
                continue
            else:
                print(f"  ERA5 error inesperado: {e}. Usando demo.")
                return _datos_demo_era5(fecha)

    print("  ERA5 sin datos disponibles en rango. Usando demo.")
    return _datos_demo_era5(fecha)


def _procesar_netcdf_era5(ruta: str) -> dict:
    try:
        import netCDF4 as nc, os
        if os.path.getsize(ruta) < 10000:
            os.remove(ruta)
            raise Exception(f"Archivo ERA5 corrupto: {ruta}")
        with open(ruta, 'rb') as f:
            header = f.read(4)
        print(f"  ERA5 header bytes: {header}")
        ds = nc.Dataset(ruta)
        print(f"  ERA5 variables: {list(ds.variables.keys())}")
        lats = ds.variables["latitude"][:]
        lons = ds.variables["longitude"][:]
        t2m  = ds.variables["t2m"][0] - 273.15
        u10  = ds.variables["u10"][0]
        v10  = ds.variables["v10"][0]
        # Precipitación: puede llamarse 'tp' o 'mtpr' según versión
        # Precipitación opcional según versión de la API
        if "tp" in ds.variables:
            tp = ds.variables["tp"][0] * 1000
        elif "mtpr" in ds.variables:
            tp = ds.variables["mtpr"][0] * 1000
        else:
            print("  ERA5: precipitación no disponible, consultando Open-Meteo...")
            tp = np.zeros_like(t2m)
            # Rellenar con Open-Meteo para cada base
            try:
                import json
                for base_id, base in BASES.items():
                    url_om = (
                        f"https://api.open-meteo.com/v1/forecast"
                        f"?latitude={base['lat']}&longitude={base['lon']}"
                        f"&daily=precipitation_sum"
                        f"&past_days=10&forecast_days=1"
                        f"&timezone=UTC"
                    )
                    r_om = requests.get(url_om, timeout=10)
                    if r_om.status_code == 200:
                        d_om = r_om.json()
                        precip_list = d_om.get("daily", {}).get("precipitation_sum", [])
                        # Tomar el valor más reciente no nulo
                        precip_val = next((v for v in reversed(precip_list) if v is not None), 0.0)
                        lat_i = np.argmin(np.abs(lats - base["lat"]))
                        lon_i = np.argmin(np.abs(lons - base["lon"]))
                        tp[lat_i, lon_i] = float(precip_val)
                        print(f"  Open-Meteo {base_id}: precip={precip_val}mm")
            except Exception as e_om:
                print(f"  Open-Meteo error: {e_om}. Precipitación = 0")
        resultados = {}
        for base_id, base in BASES.items():
            if base_id in BASES_METEOCHILE and base_id != "prat":
                continue
            lat_i  = np.argmin(np.abs(lats - base["lat"]))
            lon_i  = np.argmin(np.abs(lons - base["lon"]))
            viento_ms  = float(np.sqrt(u10[lat_i, lon_i]**2 + v10[lat_i, lon_i]**2))
            viento_kmh = round(viento_ms * 3.6, 1)
            resultados[base_id] = {
                "temperatura":   round(float(t2m[lat_i, lon_i]), 2),
                "viento":        viento_kmh,
                "precipitacion": round(float(tp[lat_i, lon_i]), 2),
                "fuente":        "ERA5",
            }
        ds.close()
        return resultados
    except Exception as e:
        print(f"  Error procesando NetCDF: {e}")
        return _datos_demo_era5(date.today())


def _datos_demo_era5(fecha: date) -> dict:
    import random
    random.seed(fecha.toordinal() + 999)
    mes = fecha.month
    temp_base = {11: -5, 12: -2, 1: -1, 2: -2, 3: -5,
                 4: -9, 5: -13, 6: -16, 7: -17, 8: -15, 9: -11, 10: -7}
    t = temp_base.get(mes, -8)
    return {
        base_id: {
            "temperatura":   round(t + random.uniform(-3, 3), 2),
            "viento":        round(random.uniform(18, 108), 1),
            "precipitacion": round(random.uniform(0, 10), 2),
            "fuente":        "demo_ERA5",
        }
        for base_id in BASES
    }

# ── ERA5: cobertura nival ────────────────────────────────────────────────────

def fetch_nieve(fecha: date) -> dict:
    """
    Obtiene cobertura nival desde ERA5 (snow_depth).
    ERA5 cubre todo el planeta incluyendo la Antártica.
    """
    if not CDS_DISPONIBLE:
        return _datos_demo_nieve(fecha)

    try:
        cliente = cdsapi.Client(url=CDS_URL, key=CDS_KEY, quiet=True)
        ruta_tmp = f"data/nieve_{fecha.isoformat()}.nc"

        cliente.retrieve(
            "reanalysis-era5-single-levels",
            {
                "product_type": "reanalysis",
                "variable": ["snow_depth"],
                "year":  str(fecha.year),
                "month": str(fecha.month).zfill(2),
                "day":   str(fecha.day).zfill(2),
                "time":  "12:00",
                "area":  [-60, -65, -65, -55],
                "format": "netcdf",
            },
            ruta_tmp,
        )

        import netCDF4 as nc
        ds   = nc.Dataset(ruta_tmp)
        lats = ds.variables["latitude"][:]
        lons = ds.variables["longitude"][:]
        sd   = ds.variables["sd"][0]  # snow depth en metros

        resultados = {}
        for base_id, base in BASES.items():
            lat_i = np.argmin(np.abs(lats - base["lat"]))
            lon_i = np.argmin(np.abs(lons - base["lon"]))
            # Convertir metros de nieve a porcentaje 0-100
            # ERA5: 0 = sin nieve, ~1m = máximo típico antártico
            valor_m = float(sd[lat_i, lon_i])
            # ERA5 snow_depth: escala 0-10 en esta región
            pct = min(100.0, round((valor_m / 10.0) * 100, 1))
            resultados[base_id] = {"manto_nival": pct}
        ds.close()
        print(f"  Nieve ERA5 OK: {resultados}")
        return resultados

    except Exception as e:
        print(f"  Nieve ERA5 error: {e}. Usando demo.")
        return _datos_demo_nieve(fecha)


def _procesar_nieve_tif(ruta: str) -> dict:
    try:
        import rasterio
        from rasterio.warp import transform

        resultados = {}
        with rasterio.open(ruta) as ds:
            datos = ds.read(1)
            crs_tif = ds.crs  # proyección polar del archivo

            for base_id, base in BASES.items():
                # Convertir lat/lon a las coordenadas del TIF
                xs, ys = transform(
                    "EPSG:4326",   # desde lat/lon
                    crs_tif,       # al sistema del TIF
                    [base["lon"]], # longitud
                    [base["lat"]]  # latitud
                )
                # Convertir coordenadas proyectadas a fila/columna del raster
                row, col = ds.index(xs[0], ys[0])

                # Ventana 10x10 píxeles alrededor de la base
                r0 = max(0, row - 5)
                r1 = min(datos.shape[0], row + 5)
                c0 = max(0, col - 5)
                c1 = min(datos.shape[1], col + 5)
                ventana = datos[r0:r1, c0:c1]

                # Valor 4 = nieve en tierra según IMS
                pct = float(np.mean(ventana == 4)) * 100
                resultados[base_id] = {"manto_nival": round(pct, 1)}
                print(f"  {base_id}: manto_nival={round(pct,1)}%")

        return resultados

    except Exception as e:
        print(f"  Error procesando TIF nieve: {e}")
        return _datos_demo_nieve(date.today())


def _datos_demo_nieve(fecha: date) -> dict:
    import random
    random.seed(fecha.toordinal() + 1000)
    mes = fecha.month
    nb  = {11: 40, 12: 20, 1: 15, 2: 20, 3: 45,
           4: 65, 5: 80, 6: 90, 7: 95, 8: 90, 9: 75, 10: 55}.get(mes, 60)
    return {
        base_id: {"manto_nival": round(min(100, max(0, nb + random.uniform(-10, 10))), 1)}
        for base_id in BASES
    }


# ── Función principal ─────────────────────────────────────────────────────────

def recolectar_clima(fecha: date = None) -> dict:
    """
    Combina Meteochile (Frei/Escudero/Prat) + ERA5 (O'Higgins) + ERA5 (todas).
    """
    if fecha is None:
        fecha = date.today() - timedelta(days=10)

    print(f"[fetch_clima] Descargando datos para {fecha.isoformat()}...")

    # 1. Meteochile: una consulta por cada código único de estación
    codigos_unicos = {}
    for base_id, codigo in ESTACIONES_METEOCHILE.items():
        if codigo not in codigos_unicos:
            codigos_unicos[codigo] = []
        codigos_unicos[codigo].append(base_id)

    datos_por_codigo = {}
    for codigo, bases_usando in codigos_unicos.items():
        print(f"  Consultando Meteochile EMA {codigo} ({', '.join(bases_usando)})...")
        datos_por_codigo[codigo] = fetch_meteochile(codigo)

   # 2. ERA5 para O'Higgins y como respaldo de viento para Prat
    print("  Descargando ERA5 para O'Higgins y respaldo Prat...")
    datos_era5 = fetch_era5(fecha)

    # 3. Cobertura nival para todas las bases
    print("  Descargando cobertura nival ERA5...")
    from datetime import timedelta
    datos_nieve = fetch_nieve(fecha - timedelta(days=8))
    # 4. Combinar todo con fallback a ERA5 cuando Meteochile no entrega viento
    resultado = {}
    for base_id in BASES:
        if base_id in BASES_METEOCHILE:
            codigo = ESTACIONES_METEOCHILE[base_id]
            mc     = datos_por_codigo[codigo]
            era_fb = datos_era5.get(base_id, {})
            _viento_mc = mc.get("viento")
            _viento_era = era_fb.get("viento")
            if _viento_mc is not None and _viento_mc > 0:
                _viento_final = _viento_mc
            elif _viento_era is not None and _viento_era > 0:
                _viento_final = _viento_era
            else:
                demo = _datos_demo_era5(fecha)
                _viento_final = round(demo.get(base_id, demo.get("prat", {})).get("viento", 25.0), 1)

            clima = {
                "temperatura": mc.get("temperatura") if mc.get("temperatura") is not None
                               else era_fb.get("temperatura"),
                "viento": _viento_final,
                "precipitacion": mc.get("precipitacion") if mc.get("precipitacion") is not None
                               else era_fb.get("precipitacion"),
            }
        resultado[base_id] = {
            **clima,
            **datos_nieve.get(base_id, {}),
        }

    print(f"[fetch_clima] Listo.")
    for base_id, vals in resultado.items():
        fuente = "Meteochile" if base_id in BASES_METEOCHILE else "ERA5"
        print(f"  {base_id}: T={vals.get('temperatura')}°C "
              f"V={vals.get('viento')}km/h [{fuente}]")
    return resultado


if __name__ == "__main__":
    datos = recolectar_clima(date.today())
