import netCDF4 as nc, numpy as np

ds = nc.Dataset('data/nieve_2026-05-28.nc')
lats = ds.variables['latitude'][:]
lons  = ds.variables['longitude'][:]
sd   = ds.variables['sd'][0]

bases = {
    'frei':     (-62.192, -58.980),
    'prat':     (-62.479, -59.664),
    'ohiggins': (-63.317, -57.900),
    'escudero': (-62.200, -58.957),
}

for nombre, (lat, lon) in bases.items():
    lat_i = np.argmin(np.abs(lats - lat))
    lon_i = np.argmin(np.abs(lons - lon))
    print(f"{nombre}: lat={float(lats[lat_i]):.2f} lon={float(lons[lon_i]):.2f} sd={float(sd[lat_i, lon_i]):.6f}")

ds.close()