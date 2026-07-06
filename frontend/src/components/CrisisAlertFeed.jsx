import React, { useState } from 'react';

export default function CrisisAlertFeed({ banks, onAlertClick }) {
  const [isOpen, setIsOpen] = useState(false);

  // 1. Filter banks at CRITICAL severity (score >= 75)
  const criticalRecords = banks.filter((b) => b.current_score >= 75);

  // 2. Group by bank name + city combination to aggregate affected blood types
  const groupedBanksMap = new Map();
  for (const record of criticalRecords) {
    const key = `${record.bank_name || ''}_${record.city || ''}`;
    if (!groupedBanksMap.has(key)) {
      groupedBanksMap.set(key, {
        bank_id: record.bank_id,
        bank_name: record.bank_name,
        city: record.city,
        state: record.state,
        latitude: record.latitude,
        longitude: record.longitude,
        severity: record.severity,
        max_score: record.current_score,
        min_days_of_supply: record.days_of_supply !== null ? record.days_of_supply : 99,
        affected_types: [record.blood_type],
        // Save the full record to pass on click
        full_record: record
      });
    } else {
      const existing = groupedBanksMap.get(key);
      existing.affected_types.push(record.blood_type);
      if (record.current_score > existing.max_score) {
        existing.max_score = record.current_score;
      }
      if (record.days_of_supply !== null && record.days_of_supply < existing.min_days_of_supply) {
        existing.min_days_of_supply = record.days_of_supply;
      }
    }
  }

  // 3. Convert to list and sort by max score descending
  const sortedAlerts = Array.from(groupedBanksMap.values()).sort(
    (a, b) => b.max_score - a.max_score
  );

  const toggleFeed = () => setIsOpen(!isOpen);

  return (
    <>
      {/* Floating Toggle Button */}
      <button
        onClick={toggleFeed}
        className="absolute top-4 right-4 z-[1000] bg-slate-900/90 backdrop-blur-md border border-red-500 hover:border-red-400 text-white px-4 py-2.5 rounded-lg shadow-lg flex items-center gap-2 transition duration-200 focus:outline-none select-none font-medium hover:bg-slate-850"
      >
        <span className="relative flex h-2.5 w-2.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
        </span>
        🚨 Crisis Feed ({sortedAlerts.length})
      </button>

      {/* Slide-out Sidebar Panel */}
      {isOpen && (
        <div className="absolute top-0 right-0 z-[1001] w-[320px] bg-slate-900/95 backdrop-blur-md text-white h-full overflow-hidden border-l border-slate-800 shadow-2xl flex flex-col select-none">
          {/* Header */}
          <div className="bg-slate-950 p-4 border-b border-slate-800 flex justify-between items-center">
            <div>
              <h2 className="text-md font-bold text-red-500 flex items-center gap-1.5">
                🚨 Crisis Alert Feed
              </h2>
              <p className="text-[10px] text-gray-400 mt-0.5">
                Banks at CRITICAL severity (score &ge; 75)
              </p>
            </div>
            <button
              onClick={toggleFeed}
              className="text-gray-400 hover:text-white transition duration-150 font-bold text-lg focus:outline-none p-1"
              aria-label="Close feed"
            >
              &#x2715;
            </button>
          </div>

          {/* List Container */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {sortedAlerts.length === 0 ? (
              <div className="text-center text-gray-500 py-8 text-sm">
                No active critical alerts.
              </div>
            ) : (
              sortedAlerts.map((alert, idx) => (
                <div
                  key={idx}
                  onClick={() => {
                    if (onAlertClick) {
                      onAlertClick(alert.full_record);
                    }
                  }}
                  className="bg-slate-850/80 hover:bg-slate-800/90 border border-slate-800 hover:border-red-900/40 rounded-xl p-3.5 cursor-pointer transition duration-150 shadow-md flex flex-col gap-2"
                >
                  {/* Bank & City Info */}
                  <div className="flex justify-between items-start gap-2">
                    <div className="min-w-0">
                      <h3 className="font-bold text-sm text-white truncate" title={alert.bank_name}>
                        {alert.bank_name}
                      </h3>
                      <p className="text-[11px] text-gray-400 mt-0.5">
                        {alert.city}{alert.state ? `, ${alert.state}` : ''}
                      </p>
                    </div>
                    {/* Score Badge */}
                    <div className="bg-red-950/80 border border-red-900/40 px-2.5 py-1 rounded-lg text-center flex flex-col shrink-0 min-w-[40px]">
                      <span className="text-red-400 font-extrabold text-sm leading-none">
                        {alert.max_score}
                      </span>
                      <span className="text-[8px] text-red-500/70 font-semibold tracking-wider uppercase mt-0.5">
                        Score
                      </span>
                    </div>
                  </div>

                  {/* Affected Blood Types */}
                  <div className="flex flex-wrap items-center gap-1.5 mt-1">
                    <span className="text-[10px] text-gray-500 font-bold uppercase mr-1">
                      Critical:
                    </span>
                    {alert.affected_types.map((type) => (
                      <span
                        key={type}
                        className="bg-red-900/40 text-red-300 text-[10px] font-bold px-2 py-0.5 rounded border border-red-900/30"
                      >
                        {type}
                      </span>
                    ))}
                  </div>

                  {/* Supply Information */}
                  <div className="flex justify-between items-center text-xs mt-1 text-gray-400 pt-2 border-t border-slate-800/60">
                    <span className="flex items-center gap-1">
                      ⏳ Supply:
                    </span>
                    <span className="font-bold text-red-400">
                      {alert.min_days_of_supply === 99 ? 'N/A' : `${alert.min_days_of_supply} days`}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </>
  );
}
