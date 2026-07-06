const express = require('express');
const router = express.Router();
const fs = require('fs').promises;
const path = require('path');
const Papa = require('papaparse');

// Helper to load bank details mapping from clean_blood_banks.csv
let bankDetailsMap = null;
async function getBankDetailsMap() {
  if (bankDetailsMap) return bankDetailsMap;
  try {
    const filePath = path.join(__dirname, '../../data/clean_blood_banks.csv');
    const csvData = await fs.readFile(filePath, 'utf8');
    const parsed = Papa.parse(csvData, { header: true, skipEmptyLines: true });
    bankDetailsMap = new Map();
    for (const row of parsed.data) {
      const id = row.sr_no || row.bank_id;
      if (id) {
        bankDetailsMap.set(id.trim(), {
          state: (row.state || '').trim(),
          latitude: row.latitude ? Number(row.latitude) : null,
          longitude: row.longitude ? Number(row.longitude) : null
        });
      }
    }
  } catch (err) {
    console.error('Failed to load clean_blood_banks.csv:', err);
    bankDetailsMap = new Map();
  }
  return bankDetailsMap;
}

// GET /api/availability
router.get('/', async (req, res) => {
  try {
    const { city, blood_type } = req.query;

    const detailsMap = await getBankDetailsMap();
    const filePath = path.join(__dirname, '../../data/bloodiq_forecasts.csv');
    const csvData = await fs.readFile(filePath, 'utf8');
    const parsed = Papa.parse(csvData, { header: true, skipEmptyLines: true });

    let results = parsed.data;

    if (city) {
      const cityLower = city.trim().toLowerCase();
      results = results.filter(row => (row.city || '').trim().toLowerCase().includes(cityLower));
    }

    if (blood_type) {
      const btLower = blood_type.trim().toLowerCase();
      results = results.filter(row => (row.blood_type || '').trim().toLowerCase() === btLower);
    }

    const mapped = results.map(row => {
      const bankId = row.bank_id;
      const details = detailsMap.get(String(bankId).trim()) || {};
      return {
        bank_id: Number(bankId) || bankId,
        bank_name: row.bank_name || '',
        city: row.city || '',
        state: details.state || '',
        latitude: details.latitude,
        longitude: details.longitude,
        blood_type: row.blood_type || '',
        current_score: Number(row.current_score) || 0,
        severity: row.severity || '',
        days_of_supply: row.days_of_supply !== undefined ? Number(row.days_of_supply) : null,
        units_available: 0
      };
    });

    res.status(200).json({
      success: true,
      data: mapped,
      error: null,
      timestamp: new Date().toISOString()
    });
  } catch (err) {
    res.status(500).json({
      success: false,
      data: null,
      error: err.message,
      timestamp: new Date().toISOString()
    });
  }
});

module.exports = router;
