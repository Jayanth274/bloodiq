const express = require('express');
const router = express.Router();
const fetch = require('node-fetch');

// Fallback logic function
function getFallbackResponse(text) {
  const queryText = text || '';
  if (/O[-\s]?negative|O-/i.test(queryText)) {
    return "O- is the rarest blood type. Critical shortage risk is highest for O-. Check availability in your city immediately.";
  }
  if (/critical|emergency|urgent/i.test(queryText)) {
    return "Showing critical alerts: Multiple banks are at high risk. Check the forecast map for real-time severity scores.";
  }
  if (/donor|donate/i.test(queryText)) {
    return "To find donors, specify blood type. Example: donors?blood_type=O%2B";
  }
  if (/shortage|low|depleted/i.test(queryText)) {
    return "Blood shortage prediction runs 72 hours ahead. Red markers on the map indicate critical banks.";
  }
  return "I can help with blood availability, shortage forecasts, and donor information. Try asking about a specific blood type or city.";
}

// POST /api/query
router.post('/', async (req, res) => {
  try {
    const { text } = req.body;

    if (!text) {
      return res.status(400).json({
        success: false,
        data: null,
        error: 'text is a required body parameter',
        timestamp: new Date().toISOString()
      });
    }

    const apiKey = process.env.GEMINI_API_KEY;
    if (apiKey && apiKey !== 'your_key_here') {
      try {
        const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`;
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            contents: [{
              parts: [{
                text: "You are BloodIQ assistant. Answer questions about blood bank availability, shortage risks, and donor information for Indian cities. Be concise and direct. Question: " + text
              }]
            }]
          })
        });

        if (response.ok) {
          const data = await response.json();
          if (data && data.candidates && data.candidates[0] && data.candidates[0].content && data.candidates[0].content.parts && data.candidates[0].content.parts[0]) {
            const answer = data.candidates[0].content.parts[0].text;
            return res.status(200).json({
              success: true,
              data: { answer, source: 'gemini' },
              error: null,
              timestamp: new Date().toISOString()
            });
          }
        } else {
          const errText = await response.text();
          console.warn(`Gemini API request failed with status ${response.status}: ${errText}`);
        }
      } catch (geminiErr) {
        console.error('Error querying Gemini API:', geminiErr.message);
      }
    }

    // Fallback response
    const answer = getFallbackResponse(text);
    res.status(200).json({
      success: true,
      data: { answer, source: 'fallback' },
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
