import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, CircleMarker, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

// Sub-component to control map behaviors (auto-zooming)
function MapController({ mapCenter }) {
  const map = useMap();
  useEffect(() => {
    if (mapCenter) {
      map.flyTo(mapCenter, 11, {
        animate: true,
        duration: 1.5
      });
    }
  }, [mapCenter, map]);
  return null;
}

export default function BloodMap({ banks, forecasts = [], selectedBloodType, onBankSelect, mapCenter }) {
  console.log('Banks received in map:', banks?.length);
  const [mapMode, setMapMode] = useState('current');

  // Filter banks by bounds and blood type
  const filteredBanks = banks.filter((bank) => {
    const lat = Number(bank.latitude);
    const lng = Number(bank.longitude);

    // Check latitude between 8 and 37, longitude between 68 and 97
    if (!lat || isNaN(lat) || lat < 8 || lat > 37) return false;
    if (!lng || isNaN(lng) || lng < 68 || lng > 97) return false;

    // Filter by selectedBloodType if set
    if (selectedBloodType && bank.blood_type !== selectedBloodType) {
      return false;
    }

    return true;
  });

  const getPathOptions = (severity) => {
    switch (String(severity).toUpperCase()) {
      case 'CRITICAL':
        return { color: '#ef4444', fillColor: '#ef4444', fillOpacity: 0.8, weight: 1 };
      case 'LOW':
        return { color: '#eab308', fillColor: '#eab308', fillOpacity: 0.8, weight: 1 };
      case 'SAFE':
      default:
        return { color: '#22c55e', fillColor: '#22c55e', fillOpacity: 0.8, weight: 1 };
    }
  };

  return (
    <div style={{ height: '100%', width: '100%', position: 'relative' }}>
      {/* Map Mode Toggle Switch */}
      <div className="absolute top-4 left-14 z-[1000] flex flex-col items-center">
        <div className="bg-slate-900/95 backdrop-blur-md border border-slate-700 p-1.5 rounded-lg shadow-lg flex items-center gap-1 select-none">
          <button
            onClick={() => setMapMode('current')}
            className={`px-4 py-2 rounded font-extrabold text-sm transition duration-150 focus:outline-none flex items-center gap-2 ${
              mapMode === 'current'
                ? 'bg-red-600 text-white shadow-md'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <span className={`h-2.5 w-2.5 rounded-full ${mapMode === 'current' ? 'bg-white' : 'bg-red-500 animate-pulse'}`}></span>
            Current State
          </button>
          <button
            onClick={() => setMapMode('forecast')}
            className={`px-4 py-2 rounded font-extrabold text-sm transition duration-150 focus:outline-none flex items-center gap-2 ${
              mapMode === 'forecast'
                ? 'bg-blue-600 text-white shadow-md'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <span className={`h-2.5 w-2.5 rounded-full ${mapMode === 'forecast' ? 'bg-white' : 'bg-blue-400 animate-pulse'}`}></span>
            72h Forecast
          </button>
        </div>
        <div className="bg-slate-900/90 backdrop-blur-sm border border-slate-750 px-2.5 py-1 rounded text-[10px] text-gray-300 font-bold mt-1.5 shadow-md">
          {mapMode === 'forecast'
            ? "Showing predicted severity in 72 hours"
            : "Showing current supply severity"}
        </div>
      </div>

      <MapContainer
        center={[20.5937, 78.9629]}
        zoom={5}
        scrollWheelZoom={true}
        style={{ height: '100%', width: '100%' }}
      >
        <MapController mapCenter={mapCenter} />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {filteredBanks.map((bank, index) => {
          const lat = Number(bank.latitude);
          const lng = Number(bank.longitude);

          // Calculate severity based on mode
          let severity = bank.severity;
          if (mapMode === 'forecast') {
            const f = forecasts.find(
              (x) => String(x.bank_id) === String(bank.bank_id) && x.blood_type === bank.blood_type
            );
            if (f && f.forecast_severity) {
              // Convert FORECAST_CRITICAL -> CRITICAL, FORECAST_LOW -> LOW, FORECAST_SAFE -> SAFE
              severity = f.forecast_severity.replace('FORECAST_', '');
            }
          }

          return (
            <CircleMarker
              key={`${bank.bank_id}-${bank.blood_type}-${index}`}
              center={[lat, lng]}
              radius={8}
              pathOptions={getPathOptions(severity)}
              eventHandlers={{
                click: () => {
                  if (onBankSelect) {
                    onBankSelect(bank);
                  }
                },
              }}
            />
          );
        })}
      </MapContainer>
    </div>
  );
}
