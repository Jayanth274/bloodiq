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
    const isOpenRouter = apiKey && apiKey.startsWith('sk-or-');
    const modelStr = isOpenRouter ? 'google/gemini-2.5-flash' : 'gemini-2.0-flash';
    const requestUrl = isOpenRouter 
      ? 'https://openrouter.ai/api/v1/chat/completions' 
      : `https://generativelanguage.googleapis.com/v1beta/models/${modelStr}:generateContent?key=${apiKey ? '***KEY_PRESENT***' : '***MISSING***'}`;

    let apiKeyExists = !!apiKey;
    let apiKeyLength = apiKey ? apiKey.length : 0;
    let googleStatus = 'N/A';
    let googleResponse = 'N/A';
    let errorMessage = 'N/A';
    let fallbackReason = 'N/A';

    console.log(`\n========================\nIncoming prompt:\n${text}\n`);

    if (!apiKey) {
      fallbackReason = 'apiKey missing';
    } else if (apiKey === 'your_key_here') {
      fallbackReason = 'apiKey == "your_key_here"';
    } else {
      try {
        const fetchUrl = isOpenRouter 
          ? 'https://openrouter.ai/api/v1/chat/completions' 
          : `https://generativelanguage.googleapis.com/v1beta/models/${modelStr}:generateContent?key=${apiKey}`;

        const fetchHeaders = {
          'Content-Type': 'application/json'
        };
        if (isOpenRouter) {
          fetchHeaders['Authorization'] = `Bearer ${apiKey}`;
        }

        const fetchBody = isOpenRouter ? {
          model: modelStr,
          max_tokens: 1000,
          messages: [{
            role: 'user',
            content: "You are BloodIQ assistant. Answer questions about blood bank availability, shortage risks, and donor information for Indian cities. Be concise and direct. Question: " + text
          }]
        } : {
          contents: [{
            parts: [{
              text: "You are BloodIQ assistant. Answer questions about blood bank availability, shortage risks, and donor information for Indian cities. Be concise and direct. Question: " + text
            }]
          }]
        };

        const response = await fetch(fetchUrl, {
          method: 'POST',
          headers: fetchHeaders,
          body: JSON.stringify(fetchBody)
        });

        googleStatus = response.status;
        const rawBody = await response.text();
        googleResponse = rawBody;

        if (response.ok) {
          let data;
          try {
            data = JSON.parse(rawBody);
          } catch (e) {
            fallbackReason = 'response parsing failed';
            throw e;
          }

          let answer = '';
          if (isOpenRouter) {
            if (data && data.choices && data.choices[0] && data.choices[0].message) {
              answer = data.choices[0].message.content;
            } else {
              fallbackReason = 'OpenRouter choices missing';
            }
          } else {
            if (data && data.candidates && data.candidates[0] && data.candidates[0].content && data.candidates[0].content.parts && data.candidates[0].content.parts[0]) {
              answer = data.candidates[0].content.parts[0].text;
            } else {
              fallbackReason = 'Gemini candidates missing';
            }
          }

          if (answer) {
            console.log("GEMINI_API_KEY EXISTS:\n" + apiKeyExists);
            console.log("\nAPI KEY LENGTH:\n" + apiKeyLength);
            console.log("\nMODEL:\n" + modelStr);
            console.log("\nREQUEST URL:\n" + requestUrl);
            console.log("\nGOOGLE HTTP STATUS:\n" + googleStatus);
            console.log("\nGOOGLE RESPONSE:\n" + googleResponse);
            console.log("\nERROR:\n" + errorMessage);
            console.log("\nFALLBACK REASON:\nNone (Gemini Success)");
            console.log("\n========================\n");

            return res.status(200).json({
              success: true,
              data: { answer, source: 'gemini' },
              error: null,
              timestamp: new Date().toISOString()
            });
          }
        } else {
          if (response.status === 401) {
            fallbackReason = 'Google/OpenRouter 401';
          } else if (response.status === 402) {
            fallbackReason = 'OpenRouter 402 (payment required/no credits)';
          } else if (response.status === 403) {
            fallbackReason = 'Google/OpenRouter 403';
          } else if (response.status === 404) {
            fallbackReason = 'Google/OpenRouter 404';
          } else if (response.status === 429) {
            fallbackReason = 'quota exceeded';
          } else {
            fallbackReason = `Google/OpenRouter HTTP error (${response.status})`;
          }
        }
      } catch (geminiErr) {
        errorMessage = geminiErr.message;
        if (fallbackReason === 'N/A') {
          fallbackReason = 'exception thrown';
        }
      }
    }

    console.log("GEMINI_API_KEY EXISTS:\n" + apiKeyExists);
    console.log("\nAPI KEY LENGTH:\n" + apiKeyLength);
    console.log("\nMODEL:\n" + modelStr);
    console.log("\nREQUEST URL:\n" + requestUrl);
    console.log("\nGOOGLE HTTP STATUS:\n" + googleStatus);
    console.log("\nGOOGLE RESPONSE:\n" + googleResponse);
    console.log("\nERROR:\n" + errorMessage);
    console.log("\nFALLBACK REASON:\n" + fallbackReason);
    console.log("\n========================\n");

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
