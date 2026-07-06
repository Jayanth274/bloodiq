const express = require('express');
const router = express.Router();
const fs = require('fs').promises;
const path = require('path');
const Papa = require('papaparse');

// GET /api/forecast
router.get('/', async (req, res) => {
  try {
    const { city } = req.query;

    const filePath = path.join(__dirname, '../../data/bloodiq_forecasts.csv');
    const csvData = await fs.readFile(filePath, 'utf8');
    const parsed = Papa.parse(csvData, { header: true, skipEmptyLines: true });

    let results = parsed.data;

    if (city) {
      const cityLower = city.trim().toLowerCase();
      results = results.filter(row => (row.city || '').trim().toLowerCase() === cityLower);
    }

    // Map to required structure first
    const mapped = results.map(row => {
      const bankId = row.bank_id;
      return {
        bank_id: Number(bankId) || bankId,
        bank_name: row.bank_name || '',
        city: row.city || '',
        blood_type: row.blood_type || '',
        current_score: Number(row.current_score) || 0,
        projected_score_72h: Number(row.projected_score_72h) || 0,
        severity: row.severity || '',
        forecast_severity: row.forecast_severity || '',
        days_of_supply: row.days_of_supply !== undefined ? Number(row.days_of_supply) : null
      };
    });

    // Sort by projected_score_72h DESC
    mapped.sort((a, b) => b.projected_score_72h - a.projected_score_72h);

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
