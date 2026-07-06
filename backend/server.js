require('dotenv').config();
const express = require('express');
const cors = require('cors');

const availabilityRouter = require('./routes/availability');
const forecastRouter = require('./routes/forecast');
const donorsRouter = require('./routes/donors');
const queryRouter = require('./routes/query');

const app = express();
const PORT = process.env.PORT || 3001;

// Enable CORS for all origins
app.use(cors());

// Parse JSON body
app.use(express.json());

// Mount routes
app.use('/api/availability', availabilityRouter);
app.use('/api/forecast', forecastRouter);
app.use('/api/donors', donorsRouter);
app.use('/api/query', queryRouter);

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({
    status: 'ok',
    timestamp: new Date().toISOString()
  });
});

app.listen(PORT, () => {
  console.log(`BloodIQ backend running on port ${PORT}`);
});
