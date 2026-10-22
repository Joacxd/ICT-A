# ICT-A — Índice Compuesto para el Turismo Antártico
## Feria Antártica Escolar INACH 2026

---

## Estructura del proyecto

```
iit_antartico/
├── config.py               ← CREDENCIALES Y CONSTANTES (editar aquí)
├── requirements.txt
├── actualizar.bat           ← Ejecutar para actualizar datos
├── scripts/
│   ├── __init__.py
│   ├── init_db.py          ← Crear BD (ejecutar una vez)
│   ├── fetch_clima.py      ← Meteochile EMA + ERA5 + manto nival
│   ├── fetch_eco.py        ← GBIF/SCAR fauna, algas, nidificación
│   ├── fetch_buques.py     ← aisstream.io WebSocket AIS
│   ├── calcular_iit.py     ← Normalización WLC + semáforo + SQLite
│   └── actualizar.py       ← Orquestador completo
├── api/
│   └── app.py              ← Flask API REST (puerto 5000)
├── dashboard/
│   ├── index.html          ← Dashboard polar (abrir en navegador)
│   ├── logo.png            ← Logo PNG del proyecto (colocar aquí)
│   └── loading.gif         ← GIF de carga (colocar aquí)
└── data/
    └── ict_a.db            ← Base de datos SQLite (se crea automáticamente)
```

---

## Instalación (una vez)

```cmd
cd iit_antartico
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe scripts/init_db.py
```

---

## Credenciales a configurar en config.py

1. **Meteochile DGAC** — Crear cuenta en climatologia.meteochile.gob.cl
   - `METEOCHILE_USER` = tu correo
   - `METEOCHILE_TOKEN` = token de tu perfil

2. **Copernicus CDS (ERA5)** — Cuenta en cds.climate.copernicus.eu
   - `CDS_URL` = https://cds.climate.copernicus.eu/api
   - `CDS_KEY` = UID:API_KEY
   - Crear archivo `~/.cdsapirc` con url y key

3. **aisstream.io (buques AIS)** — Cuenta gratuita en aisstream.io
   - `AISSTREAM_KEY` = tu API key

---

## Uso diario

**Terminal 1 — Iniciar la API:**
```cmd
venv\Scripts\python.exe api/app.py
```

**Terminal 2 — Actualizar datos:**
```cmd
actualizar.bat
```

**Navegador:**
Abrir `dashboard/index.html` directamente (doble clic).

---

## Poblar historial de demostración (para la feria)

```cmd
venv\Scripts\python.exe scripts/actualizar.py --demo
```

Genera 30 días de datos realistas sin necesitar APIs externas.

---

## Fuentes de datos

| Base     | Temperatura | Viento          | Precipitación   | Manto nival |
|----------|-------------|-----------------|-----------------|-------------|
| Frei     | Meteochile 950001 (RT) | Meteochile 950001 (km/h) | Meteochile 950001 | ERA5 snow_depth |
| Escudero | Meteochile 950001 (RT) | Meteochile 950001 (km/h) | Meteochile 950001 | ERA5 snow_depth |
| Prat     | Meteochile 950014 (RT) | Demo estacional*        | Meteochile 950014 | ERA5 snow_depth |
| O'Higgins| ERA5 (8 días latencia) | ERA5 (km/h)             | ERA5 / Open-Meteo | ERA5 snow_depth |

*La EMA 950014 de Base Prat aún no transmite viento.
Cuando lo haga, el sistema lo integrará automáticamente.
