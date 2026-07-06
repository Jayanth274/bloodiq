const express = require('express');
const router = express.Router();
const fs = require('fs').promises;
const path = require('path');
const Papa = require('papaparse');

// GET /api/donors
router.get('/', async (req, res) => {
  try {
    const { blood_type, city } = req.query;

    if (!blood_type) {
      return res.status(400).json({
        success: false,
        data: null,
        error: 'blood_type is a required query parameter',
        timestamp: new Date().toISOString()
      });
    }

    const filePath = path.join(__dirname, '../../data/mobilized_donors.csv');
    const csvData = await fs.readFile(filePath, 'utf8');
    const parsed = Papa.parse(csvData, { header: true, skipEmptyLines: true });

    let results = parsed.data;

    // Filter by blood_type (exact match)
    const targetBloodType = blood_type.trim();
    results = results.filter(row => (row.blood_type || '').trim() === targetBloodType);

    // If city provided, filter by city case-insensitive (checking both donor city and matched bank city)
    if (city) {
      const cityLower = city.trim().toLowerCase();
      results = results.filter(row => 
        (row.city || '').trim().toLowerCase() === cityLower ||
        (row.matched_bank_city || '').trim().toLowerCase() === cityLower
      );
    }

    // Map fields
    const mapped = results.map(row => {
      return {
        donor_id: row.donor_id || '',
        blood_type: row.blood_type || '',
        city: row.city || '',
        last_donation_days_ago: Number(row.last_donation_days_ago) || 0,
        contact: row.contact || '',
        matched_bank_city: row.matched_bank_city || '',
        priority_rank: Number(row.priority_rank) || 0
      };
    });

    // Sort by last_donation_days_ago DESC
    mapped.sort((a, b) => b.last_donation_days_ago - a.last_donation_days_ago);

    // Return top 20 results
    const top20 = mapped.slice(0, 20);

    res.status(200).json({
      success: true,
      data: top20,
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
