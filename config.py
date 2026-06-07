# =============================================================================
# config.py — Configuración central del sistema IIT-A
# Todas las constantes del proyecto viven aquí.
# =============================================================================

# ── Bases antárticas monitoreadas ────────────────────────────────────────────
BASES = {
    "frei": {
        "nombre": "Base Pres. Eduardo Frei Montalva",
        "lat": -62.2,
        "lon": -58.97,
        "radio_km": 5,
        "ecosistema": "Pastizales costeros, pingüinera",
        "organismo": "FACH / Armada de Chile",
        "temporada_inicio": 11,  # noviembre
        "temporada_fin": 3,      # marzo
    },
    "prat": {
        "nombre": "Base Naval Arturo Prat",
        "lat": -62.5,
        "lon": -59.68,
        "radio_km": 5,
        "ecosistema": "Tundra antártica, marisma costera",
        "organismo": "Armada de Chile",
        "temporada_inicio": 11,
        "temporada_fin": 3,
    },
    "ohiggins": {
        "nombre": "Base Gral. Bernardo O'Higgins",
        "lat": -63.32,
        "lon": -57.9,
        "radio_km": 5,
        "ecosistema": "Glaciares costeros, roca expuesta",
        "organismo": "Ejército de Chile",
        "temporada_inicio": 11,
        "temporada_fin": 2,
    },
    "escudero": {
        "nombre": "Base Cient. Prof. Julio Escudero (INACH)",
        "lat": -62.2,
        "lon": -58.95,
        "radio_km": 3,
        "ecosistema": "Tundra y litoral rocoso, laguna costera",
        "organismo": "INACH",
        "temporada_inicio": 11,
        "temporada_fin": 3,
    },
}

# ── Pesos del IIT-A (deben sumar 1.00) ───────────────────────────────────────
# Dimensión climática (D1): peso total 0.30
PESOS = {
    "temperatura":   0.10,
    "manto_nival":   0.10,
    "viento":        0.05,
    "precipitacion": 0.05,
    # Dimensión ecológica (D2): peso total 0.40
    "fauna":         0.15,
    "algas":         0.10,
    "nidificacion":  0.15,
    # Dimensión presión humana (D3): peso total 0.30
    "turistas":      0.15,
    "buques":        0.08,
    "dias_consec":   0.07,
}

# Factor de ajuste estacional (nov-feb: nidificación activa)
# Incrementa D2 y reduce D1 proporcionalmente, manteniendo suma = 1.0
FACTOR_ESTACIONAL = 1.3

# ── Umbrales críticos por variable (valor normalizado que dispara alerta) ────
UMBRALES = {
    "temperatura":   65,   # T_s > 0°C sostenida → riesgo deshielo
    "manto_nival":   60,   # reducción > 20% respecto media histórica
    "viento": 64,   # V_w > 50 kt (≈ 93 km/h)
    "precipitacion": 70,   # P > 15 mm/día
    "fauna":         75,   # colonias activas < 500 m del sitio
    "algas":         70,   # cobertura algal > 10% de playa
    "nidificacion":  100,  # variable binaria: 0 o 100
    "turistas":      73,   # T_a > 200 personas/día  (200/300*100 ≈ 73)
    "buques":        50,   # B_s > 5 buques         (5/10*100 = 50)
    "dias_consec":   71,   # D_c ≥ 5 días           (5/7*100 ≈ 71)
}

# ── Rangos históricos para normalización min-max (período 2010-2023) ─────────
RANGOS_HIST = {
    "temperatura":   {"min": -25.0, "max": 5.0},     # °C
    "viento": {"min": 0.0, "max": 145.0},    # km/h (78 kt ≈ 145 km/h)
    "precipitacion": {"min": 0.0,   "max": 30.0},     # mm/día
    "manto_nival":   {"min": 0.0,   "max": 100.0},    # % cobertura
    "fauna":         {"min": 0.0,   "max": 100.0},    # índice 0-100
    "algas":         {"min": 0.0,   "max": 100.0},    # % cobertura
    "turistas":      {"min": 0,     "max": 300},      # personas/día
    "buques":        {"min": 0,     "max": 10},       # número
    "dias_consec":   {"min": 0,     "max": 14},       # días
}

# ── Clasificación semáforo ────────────────────────────────────────────────────
SEMAFORO = {
    "verde":    {"min": 0,  "max": 44,  "label": "Operación normal",   "color": "#639922"},
    "amarillo": {"min": 45, "max": 69,  "label": "Alerta moderada",    "color": "#EF9F27"},
    "rojo":     {"min": 70, "max": 100, "label": "Cierre territorial", "color": "#E24B4A"},
}

# ── Credenciales API (completar antes de ejecutar) ───────────────────────────
# NASA Earthdata: crear cuenta en https://urs.earthdata.nasa.gov
NASA_USER = "iita"
NASA_PASS = "AndiperlaWillinki2026#"

# Copernicus CDS (ERA5): crear cuenta en https://cds.climate.copernicus.eu
# Guardar también en ~/.cdsapirc  (el instalador lo pide automáticamente)
CDS_URL  = "https://cds.climate.copernicus.eu/api"
CDS_KEY  = "9b17fa0d-76c7-4d64-801a-1d6d88c3b1ab"

# MarineTraffic AIS: cuenta gratuita en https://www.marinetraffic.com/en/ais/api
MARINE_API_KEY = ""

# AISTREAM API: cuenta gratuita en https://aistream.antarctica.ac.uk/signup
AISSTREAM_KEY = "40400ad205aa9d53c9f35f4ce7fcf30613fd1c78"

METEOCHILE_USER  = "joacofloresgarate@gmail.com"
METEOCHILE_TOKEN = "fc1a91830c9a8bc6d42d4541"

# Ruta de la base de datos SQLite
DB_PATH = "data/iit_antartico.db"
