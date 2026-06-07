# Sistema IIT-A — Monitor de Impacto Turístico Antártico
Propuesta FAE 2026 · INACH

## Requisitos
- Python 3.10 o superior
- Conexión a internet

## Instalación (una sola vez)

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Crear la base de datos
python scripts/init_db.py

# 3. Poblar 30 días de historial de demostración (sin APIs externas)
python scripts/actualizar.py --demo
```

## Uso diario

```bash
# Ventana 1: iniciar la API
python api/app.py

# Ventana 2: actualizar datos del día
python scripts/actualizar.py

# Luego abrir dashboard/index.html en el navegador
```

## Ingreso manual de turistas
Abrir el dashboard → pestaña "Ingreso manual" → ingresar turistas y buques del día.

## Configurar APIs reales (opcional)
Editar config.py y completar:
- NASA_USER / NASA_PASS  →  urs.earthdata.nasa.gov
- CDS_KEY               →  cds.climate.copernicus.eu
- MARINE_API_KEY        →  marinetraffic.com/en/ais/api

Sin configurar, el sistema usa datos de demostración realistas.

## Estructura del proyecto
```
iit_antartico/
├── config.py              # Parámetros, pesos y umbrales del IIT-A
├── requirements.txt
├── scripts/
│   ├── init_db.py         # Crea la base de datos SQLite
│   ├── fetch_clima.py     # ERA5 + NSIDC (temperatura, viento, nieve)
│   ├── fetch_eco.py       # GBIF/SCAR (fauna, algas, nidificación)
│   ├── fetch_buques.py    # MarineTraffic AIS (buques en zona)
│   ├── calcular_iit.py    # Normalización + WLC + semáforo
│   └── actualizar.py      # Orquestador del ciclo completo
├── api/
│   └── app.py             # API REST Flask (5 endpoints)
├── dashboard/
│   └── index.html         # Dashboard web completo
└── data/
    └── iit_antartico.db   # Base de datos SQLite (se crea automáticamente)
```
