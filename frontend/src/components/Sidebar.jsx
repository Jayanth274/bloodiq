import React from 'react';
import ChatBox from './ChatBox';

export default function Sidebar({ bloodType, setBloodType, city, setCity, banks, forecasts = [], onAlertClick }) {
  const bloodTypes = [
    ['A+', 'A-', 'B+', 'B-'],
    ['O+', 'O-', 'AB+', 'AB-']
  ];

  // Calculate counts based on severity
  const criticalCount = banks.filter(b => b.severity === 'CRITICAL').length;
  const safeCount = banks.filter(b => b.severity === 'SAFE').length;

  const handleBloodTypeClick = (bt) => {
    if (bloodType === bt) {
      setBloodType(null); // Deselect if clicked again
    } else {
      setBloodType(bt);
    }
  };

  // Filter for sleeper crises: currently LOW/SAFE, forecast is FORECAST_CRITICAL
  const upcomingCrises = banks.filter(bank => {
    if (bank.severity !== 'LOW' && bank.severity !== 'SAFE') return false;
    const f = forecasts.find(x => String(x.bank_id) === String(bank.bank_id) && x.blood_type === bank.blood_type);
    return f && f.forecast_severity === 'FORECAST_CRITICAL';
  }).map(bank => {
    const f = forecasts.find(x => String(x.bank_id) === String(bank.bank_id) && x.blood_type === bank.blood_type);
    return {
      ...bank,
      projected_score_72h: f.projected_score_72h
    };
  });

  const displayCrises = upcomingCrises.slice(0, 5);

  return (
    <div className="w-[280px] bg-slate-900 border-r border-slate-850 p-6 flex flex-col h-screen select-none text-white overflow-hidden">
      {/* Header */}
      <div className="mb-4 shrink-0">
        <h1 className="text-2xl font-bold text-[#ef4444] tracking-tight">BloodIQ</h1>
        <p className="text-xs text-gray-400 font-medium">Blood Supply Intelligence</p>
      </div>

      {/* Benchmark Banner */}
      <div className="bg-yellow-900 border border-yellow-600 text-yellow-200 text-xs p-2.5 rounded mb-4 font-sans select-none leading-relaxed shrink-0">
        <div className="font-bold flex items-center gap-1.5 mb-0.5">
          <span>⚡</span> GPU Accelerated
        </div>
        <div>7,118,960 rows in 0.06s</div>
        <div className="font-semibold text-[11px] text-yellow-350">248.4x faster than CPU</div>
      </div>

      {/* Scrollable middle container to prevent overflow */}
      <div className="flex-1 overflow-y-auto pr-1 -mr-2 space-y-4 mb-4">
        {/* Blood Type Filter */}
        <div>
          <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider block mb-2">
            Blood Type Filter
          </label>
          <div className="flex flex-col gap-2">
            {bloodTypes.map((row, rowIdx) => (
              <div key={rowIdx} className="grid grid-cols-4 gap-2">
                {row.map((bt) => {
                  const isSelected = bloodType === bt;
                  return (
                    <button
                      key={bt}
                      onClick={() => handleBloodTypeClick(bt)}
                      className={`py-1.5 rounded font-bold text-sm transition-colors duration-205 ${
                        isSelected
                          ? 'bg-red-600 text-white shadow-md shadow-red-900/30'
                          : 'bg-slate-700 hover:bg-slate-650 text-gray-300'
                      }`}
                    >
                      {bt}
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
        </div>

        {/* City Search Input */}
        <div>
          <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider block mb-2">
            City Location
          </label>
          <input
            type="text"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            placeholder="Search city..."
            className="w-full bg-slate-800 border border-slate-650 text-white placeholder-gray-500 rounded px-3 py-2 text-sm focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500"
          />
        </div>

        {/* Stats Row */}
        <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-800">
          <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider block mb-2.5">
            Real-time Alerts
          </label>
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <div className="text-xl font-bold text-white">{banks.length}</div>
              <div className="text-[10px] text-gray-400 font-medium">Total</div>
            </div>
            <div>
              <div className="text-xl font-bold text-red-500">{criticalCount}</div>
              <div className="text-[10px] text-gray-400 font-medium">Critical</div>
            </div>
            <div>
              <div className="text-xl font-bold text-green-500">{safeCount}</div>
              <div className="text-[10px] text-gray-400 font-medium">Safe</div>
            </div>
          </div>
        </div>

        {/* Section "UPCOMING CRISES" */}
        <div>
          <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider block mb-2">
            UPCOMING CRISES
          </label>
          <div className="bg-slate-800/30 border border-slate-800 rounded-lg p-2 space-y-2">
            {displayCrises.length === 0 ? (
              <p className="text-[11px] text-gray-500 italic text-center py-2">
                No sleeper crises detected.
              </p>
            ) : (
              displayCrises.map((crisis, idx) => (
                <div
                  key={`${crisis.bank_id}-${crisis.blood_type}-${idx}`}
                  onClick={() => onAlertClick && onAlertClick(crisis)}
                  className="bg-slate-800 hover:bg-slate-700/80 border border-slate-700/50 rounded p-2 text-[11px] cursor-pointer transition duration-150 active:scale-[0.98]"
                >
                  <div className="flex justify-between items-start gap-1">
                    <div className="font-extrabold text-gray-200 truncate pr-1" title={crisis.bank_name}>
                      {crisis.bank_name}
                    </div>
                    <span className="bg-red-900/85 text-red-200 font-bold px-1 rounded text-[9px] shrink-0">
                      {crisis.blood_type}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-gray-400 mt-1 text-[9px]">
                    <span>{crisis.city}</span>
                    <span className="text-red-400 font-semibold">Proj Score: {crisis.projected_score_72h}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* ChatBox Component */}
      <div className="shrink-0 border-t border-slate-700 pt-4 mt-auto">
        <ChatBox />
      </div>
    </div>
  );
}
