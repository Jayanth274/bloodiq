import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import BloodMap from './components/BloodMap';
import BankPanel from './components/BankPanel';
import L from 'leaflet';

// Fix default leaflet marker icons issues
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

export default function App() {
  const [selectedBloodType, setSelectedBloodType] = useState(null);
  const [selectedCity, setSelectedCity] = useState('');
  const [banks, setBanks] = useState([]);
  const [forecasts, setForecasts] = useState([]);
  const [selectedBank, setSelectedBank] = useState(null);
  const [mapCenter, setMapCenter] = useState(null);

  useEffect(() => {
    if (selectedCity && selectedCity.trim().length >= 3) {
      const cityLower = selectedCity.trim().toLowerCase();
      const matched = banks.find((b) => (b.city || '').toLowerCase().includes(cityLower));
      if (matched && matched.latitude && matched.longitude) {
        setMapCenter([Number(matched.latitude), Number(matched.longitude)]);
      }
    }
  }, [selectedCity, banks]);

  useEffect(() => {
    const apiBase = process.env.REACT_APP_API_URL || 'http://localhost:3001';

    // Fetch availability on mount
    fetch(`${apiBase}/api/availability`)
      .then((res) => res.json())
      .then((resData) => {
        if (resData.success && Array.isArray(resData.data)) {
          setBanks(resData.data);
        }
      })
      .catch((err) => console.error('Failed to fetch availability:', err));

    // Fetch forecast on mount
    fetch(`${apiBase}/api/forecast`)
      .then((res) => res.json())
      .then((resData) => {
        if (resData.success && Array.isArray(resData.data)) {
          setForecasts(resData.data);
        }
      })
      .catch((err) => console.error('Failed to fetch forecast:', err));
  }, []);

  // Filter banks by blood type and city (case-insensitive)
  const filteredBanks = banks.filter((bank) => {
    const matchesBloodType = !selectedBloodType || bank.blood_type === selectedBloodType;
    const matchesCity = !selectedCity.trim() || 
      (bank.city || '').toLowerCase().includes(selectedCity.trim().toLowerCase());
    return matchesBloodType && matchesCity;
  });

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#0f172a' }}>
      <Sidebar
        bloodType={selectedBloodType}
        setBloodType={setSelectedBloodType}
        city={selectedCity}
        setCity={setSelectedCity}
        banks={filteredBanks}
        forecasts={forecasts}
        onAlertClick={(bank) => {
          if (bank.latitude && bank.longitude) {
            setMapCenter([Number(bank.latitude), Number(bank.longitude)]);
          }
          setSelectedBank(bank);
        }}
      />
      <div style={{ flex: 1, position: 'relative' }}>
        <BloodMap
          banks={filteredBanks}
          forecasts={forecasts}
          selectedBloodType={selectedBloodType}
          onBankSelect={setSelectedBank}
          mapCenter={mapCenter}
        />
      </div>
      {selectedBank && (
        <BankPanel
          bank={selectedBank}
          onClose={() => setSelectedBank(null)}
          forecasts={forecasts}
        />
      )}
    </div>
  );
}
