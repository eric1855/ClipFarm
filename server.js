#!/usr/bin/env node

const express = require('express');
const path = require('path');
const axios = require('axios');
const fs = require('fs');
const FormData = require('form-data');
const multer = require('multer');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3000;

// API base URL
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Expose generated videos for playback/download
const OUTPUT_DIR = path.join(__dirname, 'output_videos');
const CANDIDATE_DIR = path.join(__dirname, 'candidate_videos');
app.use('/media/output', express.static(OUTPUT_DIR));
app.use('/media/candidates', express.static(CANDIDATE_DIR));

// Configure multer for file uploads
const upload = multer({
  dest: 'uploads/',
  limits: {
    fileSize: 500 * 1024 * 1024 // 500MB limit
  },
  fileFilter: (req, file, cb) => {
    const allowedTypes = ['video/mp4', 'video/avi', 'video/mov', 'video/mkv', 
                         'audio/wav', 'audio/mp3', 'audio/m4a', 'audio/flac', 'audio/ogg'];
    if (allowedTypes.includes(file.mimetype)) {
      cb(null, true);
    } else {
      cb(new Error('Invalid file type. Please upload a video or audio file.'), false);
    }
  }
});

// Routes
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// API proxy endpoints
app.post('/api/upload', upload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    // Allow up to 10 minutes for full pipeline (transcribe + GPT + FFmpeg)
    req.setTimeout(600000);
    res.setTimeout(600000);

    // Build backend multipart form
    const form = new FormData();
    form.append('file', fs.createReadStream(req.file.path), req.file.originalname);

    // Append legacy extraction params to trigger backend extraction
    const params = new URLSearchParams({
      model: req.body.model || 'small',
      compute_type: req.body.compute_type || 'int8',
      beam_size: String(req.body.beam_size || '5'),
      vad: String(req.body.vad || 'false'),
    });
    if (req.body.language) params.append('language', req.body.language);

    // Optional user instructions from the UI
    if (req.body.instructions) {
      form.append('instructions', req.body.instructions);
    }

    const url = `${API_BASE_URL}/upload?${params.toString()}`;
    const response = await axios.post(url, form, {
      headers: form.getHeaders(),
      timeout: 600000,
      maxContentLength: Infinity,
      maxBodyLength: Infinity,
    });
    res.json(response.data);
  } catch (error) {
    console.error('Upload error:', error.response?.data || error.message);
    res.status(500).json({
      error: 'Upload failed',
      details: error.response?.data?.detail || error.message
    });
  } finally {
    if (req.file) fs.unlink(req.file.path, () => {});
  }
});

app.get('/api/download/:jobId/:filename', async (req, res) => {
  try {
    const { jobId, filename } = req.params;
    const response = await axios.get(
      `${API_BASE_URL}/download/${jobId}/${filename}`,
      { responseType: 'stream' }
    );

    res.setHeader('Content-Type', response.headers['content-type']);
    res.setHeader('Content-Disposition', response.headers['content-disposition']);
    
    response.data.pipe(res);
  } catch (error) {
    console.error('Download error:', error.response?.data || error.message);
    res.status(500).json({ 
      error: 'Download failed', 
      details: error.response?.data?.detail || error.message 
    });
  }
});

app.get('/api/jobs/:jobId', async (req, res) => {
  try {
    const { jobId } = req.params;
    const response = await axios.get(`${API_BASE_URL}/jobs/${jobId}`);
    res.json(response.data);
  } catch (error) {
    console.error('Job status error:', error.response?.data || error.message);
    res.status(500).json({ 
      error: 'Failed to get job status', 
      details: error.response?.data?.detail || error.message 
    });
  }
});

app.get('/api/health', async (req, res) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/health`);
    res.json(response.data);
  } catch (error) {
    res.status(500).json({ 
      error: 'Backend not available', 
      details: error.message 
    });
  }
});

// Error handling middleware
app.use((error, req, res, next) => {
  if (error instanceof multer.MulterError) {
    if (error.code === 'LIMIT_FILE_SIZE') {
      return res.status(400).json({ error: 'File too large. Maximum size is 500MB.' });
    }
  }
  
  console.error('Server error:', error);
  res.status(500).json({ error: 'Internal server error' });
});

// Start server
app.listen(PORT, () => {
  console.log(`Frontend server running on http://localhost:${PORT}`);
  console.log(`Backend API: ${API_BASE_URL}`);
  console.log(`Health check: http://localhost:${PORT}/api/health`);
});

module.exports = app;
