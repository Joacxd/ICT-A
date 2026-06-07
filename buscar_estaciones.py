import requests
import json

usuario = "joacofloresgarate@gmail.com"
token   = "fc1a91830c9a8bc6d42d4541"

url = f"https://climatologia.meteochile.gob.cl/application/servicios/getDatosRecientesRedEma?usuario={usuario}&token={token}"
r = requests.get(url, verify=False)
data = r.json()

for e in data.get("datosEstaciones", []):
    est = e["estacion"]
    lat = float(est.get("latitud", 0))
    if lat < -55:
        print(est["codigoNacional"], "|", est["nombreEstacion"], "|", est["latitud"])