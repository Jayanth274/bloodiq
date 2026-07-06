import React, { useState, useEffect } from 'react';

export default function BankPanel({ bank, onClose, forecasts = [] }) {
  const [donorResults, setDonorResults] = useState(null);
  const [surplusBank, setSurplusBank] = useState(null);
  const [donorsLoading, setDonorsLoading] = useState(false);
  const [surplusLoading, setSurplusLoading] = useState(false);

  // Reset results on bank change
  useEffect(() => {
    setDonorResults(null);
    setSurplusBank(null);
    setDonorsLoading(false);
    setSurplusLoading(false);
  }, [bank]);

  if (!bank) return null;

  // Find matching forecast details for this bank and blood type
  const forecast = forecasts.find(
    (f) => String(f.bank_id) === String(bank.bank_id) && f.blood_type === bank.blood_type
  ) || {};

  const score = bank.current_score || 0;
  const projectedScore = forecast.projected_score_72h !== undefined ? forecast.projected_score_72h : score;

  // Score color helper
  const getScoreColorClass = (val) => {
    if (val >= 75) return 'text-red-400';
    if (val >= 40) return 'text-yellow-400';
    return 'text-green-400';
  };

  // Severity style helper
  const getSeverityBadgeClass = (sev) => {
    const s = String(sev).toUpperCase();
    if (s.includes('CRITICAL')) return 'bg-red-900 text-red-300';
    if (s.includes('LOW')) return 'bg-yellow-900 text-yellow-300';
    return 'bg-green-900 text-green-300';
  };

  // Days of supply logic
  const rawDays = bank.days_of_supply !== undefined && bank.days_of_supply !== null
    ? bank.days_of_supply 
    : (forecast.days_of_supply !== undefined && forecast.days_of_supply !== null ? forecast.days_of_supply : null);

  const daysOfSupply = rawDays !== null && !isNaN(Number(rawDays)) ? Number(rawDays) : null;

  let daysFillColor = 'bg-red-500';
  let daysPercent = 0;
  if (daysOfSupply !== null) {
    if (daysOfSupply > 7) {
      daysFillColor = 'bg-green-500';
    } else if (daysOfSupply >= 2) {
      daysFillColor = 'bg-yellow-500';
    } else {
      daysFillColor = 'bg-red-500';
    }
    // Scale against 10 days of supply for full capacity representation
    daysPercent = Math.min(100, (daysOfSupply / 10) * 100);
  }

  // Find Donors Click handler
  const handleFindDonors = async () => {
    if (donorsLoading) return;
    setDonorsLoading(true);
    setDonorResults(null);

    const apiBase = process.env.REACT_APP_API_URL || 'http://localhost:3001';
    try {
      const response = await fetch(
        `${apiBase}/api/donors?blood_type=${encodeURIComponent(bank.blood_type)}&city=${encodeURIComponent(bank.city)}`
      );
      if (!response.ok) throw new Error('API request failed');
      const resData = await response.json();
      if (resData.success && Array.isArray(resData.data)) {
        setDonorResults(resData.data);
      } else {
        setDonorResults([]);
      }
    } catch (err) {
      console.error(err);
      setDonorResults([]);
    } finally {
      setDonorsLoading(false);
    }
  };

  // Find Surplus Click handler
  const handleFindSurplus = async () => {
    if (surplusLoading) return;
    setSurplusLoading(true);
    setSurplusBank(null);

    const apiBase = process.env.REACT_APP_API_URL || 'http://localhost:3001';
    try {
      const response = await fetch(
        `${apiBase}/api/forecast?city=${encodeURIComponent(bank.city)}`
      );
      if (!response.ok) throw new Error('API request failed');
      const resData = await response.json();
      if (resData.success && Array.isArray(resData.data)) {
        // Filter by same blood type, excluding current bank if possible
        const sameType = resData.data.filter(
          (f) =>
            f.blood_type === bank.blood_type &&
            String(f.bank_id) !== String(bank.bank_id)
        );

        if (sameType.length > 0) {
          // Sort by projected_score_72h ascending (lowest score = safest/most surplus)
          sameType.sort((a, b) => (a.projected_score_72h || 0) - (b.projected_score_72h || 0));
          setSurplusBank(sameType[0]);
        } else {
          setSurplusBank('none');
        }
      } else {
        setSurplusBank('none');
      }
    } catch (err) {
      console.error(err);
      setSurplusBank('none');
    } finally {
      setSurplusLoading(false);
    }
  };

  return (
    <div className="w-[340px] bg-slate-800 text-white h-full overflow-y-auto border-l border-slate-700 shadow-2xl flex flex-col relative select-none">
      
      {/* Header section */}
      <div className="bg-slate-900 p-4 border-b border-slate-700 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-white transition duration-150 font-bold text-lg focus:outline-none"
          aria-label="Close panel"
        >
          &#x2715;
        </button>
        <h2 className="text-lg font-bold text-white truncate pr-6 mb-0.5" title={bank.bank_name}>
          {bank.bank_name}
        </h2>
        <p className="text-sm text-gray-400">
          {bank.city}{bank.state ? `, ${bank.state}` : ''}
        </p>
        <span className="bg-red-900 text-red-300 text-xs px-2 py-0.5 rounded-full inline-block mt-1 font-semibold uppercase">
          {bank.blood_type}
        </span>
      </div>

      {/* Score section */}
      <div className="p-4 bg-slate-850 mx-4 mt-4 rounded-xl border border-slate-750 flex flex-col items-center">
        <span className="text-xs text-gray-500 tracking-widest mb-1 font-bold uppercase">
          CRITICALITY SCORE
        </span>
        <div className={`text-7xl font-black ${getScoreColorClass(score)} leading-none mb-3`}>
          {score}
        </div>
        <span className={`px-3 py-1 rounded-full text-sm font-semibold uppercase ${getSeverityBadgeClass(bank.severity)}`}>
          {bank.severity || 'SAFE'}
        </span>
      </div>

      {/* 72h Forecast section */}
      <div className="px-4 mt-4">
        <div className="flex justify-between items-center mb-1.5">
          <span className="text-xs text-gray-500 tracking-widest font-bold uppercase">
            72H FORECAST
          </span>
          {forecast.forecast_severity && (
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${getSeverityBadgeClass(forecast.forecast_severity)}`}>
              {forecast.forecast_severity.replace('FORECAST_', '')}
            </span>
          )}
        </div>
        <div className="flex items-baseline gap-2">
          <div className={`text-4xl font-bold ${getScoreColorClass(projectedScore)}`}>
            {projectedScore}
          </div>
          <span className="text-xs text-gray-500 font-medium">projected score</span>
        </div>
        <p className="text-xs text-gray-500 mt-0.5">
          Projected criticality in 72 hours
        </p>
      </div>

      {/* Warning banner */}
      {forecast.forecast_severity === 'FORECAST_CRITICAL' && (
        <div className="px-4 mt-3">
          <div className="bg-red-950 border border-red-800 rounded-lg p-3">
            <span className="text-red-400 font-semibold text-sm flex items-center gap-1">
              ⚠ Critical shortage predicted in 72 hours
            </span>
            <p className="text-red-300 text-xs mt-1 leading-relaxed">
              This bank requires immediate donor mobilization or surplus transfer.
            </p>
          </div>
        </div>
      )}

      {/* Days of supply section */}
      {daysOfSupply !== null && (
        <div className="px-4 mt-4">
          <div className="flex justify-between items-center mb-1.5">
            <span className="text-xs text-gray-500 tracking-widest font-bold uppercase">
              DAYS OF SUPPLY
            </span>
            <span className="text-sm font-extrabold text-gray-200">
              {daysOfSupply} {daysOfSupply === 1 ? 'day' : 'days'} remaining
            </span>
          </div>
          <div className="bg-slate-700 rounded-full h-3 w-full overflow-hidden mb-1 relative">
            <div
              className={`h-full ${daysFillColor} rounded-full transition-all duration-500`}
              style={{ width: `${daysPercent}%` }}
            />
          </div>
          <div className="text-[11px] text-gray-400">
            Estimated supply remaining based on daily demand
          </div>
        </div>
      )}

      {/* Action triggers output (donors/surplus list) */}
      <div className="px-4 mt-4">
        
        {/* Finding/Loading state */}
        {(donorsLoading || surplusLoading) && (
          <div className="text-center py-2 text-xs text-gray-400 italic">
            Finding...
          </div>
        )}

        {/* Donors list */}
        {donorResults !== null && (
          <div>
            {donorResults.length > 0 ? (
              <div className="space-y-2">
                {donorResults.slice(0, 3).map((donor) => (
                  <div key={donor.donor_id} className="bg-slate-700 rounded-lg p-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-red-300 font-bold">{donor.blood_type}</span>
                      <span className="text-gray-400">{donor.last_donation_days_ago} days ago</span>
                    </div>
                    <div className="text-gray-300 mt-1">
                      {donor.city} • {donor.contact}
                    </div>
                  </div>
                ))}
                <p className="text-gray-505 text-center text-[10px] uppercase font-bold text-gray-500 mt-1">
                  {donorResults.length} donors available
                </p>
              </div>
            ) : (
              <div className="text-center py-3 bg-slate-750 rounded-lg text-xs text-gray-450 border border-slate-700 text-gray-400">
                {bank.severity === 'SAFE' || bank.severity === 'LOW'
                  ? `No mobilization needed — ${bank.blood_type} supply is ${bank.severity} in this area`
                  : "No donors found in this area"}
              </div>
            )}
          </div>
        )}

        {/* Surplus bank recommendation */}
        {surplusBank !== null && (
          <div>
            {surplusBank !== 'none' ? (
              <div className="bg-green-950 border border-green-800 rounded-lg p-3">
                <p className="text-green-400 text-xs font-semibold">
                  Nearest Surplus Bank
                </p>
                <p className="text-white text-sm font-bold mt-1 leading-snug">
                  {surplusBank.bank_name}
                </p>
                <p className="text-gray-400 text-xs mt-0.5">
                  {surplusBank.city} • Score: {surplusBank.projected_score_72h}
                </p>
                <p className="text-green-300 text-xs mt-1">
                  Status: {surplusBank.forecast_severity ? surplusBank.forecast_severity.replace('FORECAST_', '') : 'SAFE'}
                </p>
              </div>
            ) : (
              <div className="text-center py-3 bg-slate-750 rounded-lg text-xs text-gray-450 border border-slate-700 text-gray-400">
                No surplus banks found nearby
              </div>
            )}
          </div>
        )}

      </div>

      {/* Action row */}
      <div className="px-4 mt-6 pb-6 flex gap-3 mt-auto">
        <button
          onClick={() => {
            window._donorQuery = bank.blood_type;
            handleFindDonors();
          }}
          className="flex-1 bg-red-600 hover:bg-red-700 text-white text-sm font-semibold px-4 py-2.5 rounded-lg transition duration-150 active:scale-95 focus:outline-none"
        >
          {donorsLoading ? 'Finding...' : 'Find Donors'}
        </button>
        <button
          onClick={handleFindSurplus}
          className="flex-1 bg-slate-600 hover:bg-slate-500 text-white text-sm font-semibold px-4 py-2.5 rounded-lg transition duration-150 active:scale-95 focus:outline-none"
        >
          {surplusLoading ? 'Finding...' : 'Find Surplus'}
        </button>
      </div>

    </div>
  );
}
