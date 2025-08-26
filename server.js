#!/usr/bin/env node

/**
 * TFT Webapp - Complete Node.js Backend API
 * 
 * A pure Node.js backend API for the TFT webapp that works with HTMX frontend.
 * Follows KISS principles with zero external dependencies.
 * 
 * Features:
 * - All HTMX endpoints from the frontend
 * - Proper error handling and CORS
 * - HTML fragments for HTMX consumption
 * - Mock data for demo purposes
 * - Clean, well-commented code
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

// Configuration
const PORT = process.env.PORT || 3000;
const HOST = process.env.HOST || 'localhost';

// Mock Data for Demo Purposes
const mockData = {
  // Database statistics
  stats: {
    matches: 12847,
    participants: 102776,
    avgPlayersPerMatch: 8.0
  },

  // Cluster data
  clusters: [
    {
      id: "0",
      name: "Aphelios Carry",
      size: 1250,
      avg_placement: 3.2,
      winrate: 18.5,
      top4_rate: 62.4,
      carries: ["Aphelios", "Jinx"],
      traits: ["Sniper", "Star_Guardian"]
    },
    {
      id: "1", 
      name: "Jinx Sniper",
      size: 980,
      avg_placement: 3.8,
      winrate: 15.2,
      top4_rate: 58.1,
      carries: ["Jinx", "Kai'Sa"],
      traits: ["Sniper", "Battle_Academia"]
    },
    {
      id: "2",
      name: "Star Guardian",
      size: 850,
      avg_placement: 4.1,
      winrate: 12.8,
      top4_rate: 54.2,
      carries: ["Ahri", "Kai'Sa", "Taliyah"],
      traits: ["Star_Guardian", "Mage"]
    },
    {
      id: "3",
      name: "Vanguard Tank",
      size: 720,
      avg_placement: 4.3,
      winrate: 11.5,
      top4_rate: 51.8,
      carries: ["Garen", "Wukong"],
      traits: ["Vanguard", "Defender"]
    },
    {
      id: "4",
      name: "Battle Academia",
      size: 650,
      avg_placement: 4.5,
      winrate: 10.2,
      top4_rate: 48.3,
      carries: ["Ezreal", "Graves"],
      traits: ["Battle_Academia", "Gunner"]
    }
  ],

  // Sample query results
  queryResults: {
    stats: {
      play_count: 1250,
      avg_placement: 3.2,
      winrate: 18.5,
      top4_rate: 62.4
    },
    participants: [
      {
        placement: 1,
        level: 9,
        last_round: "6-7",
        units: [
          { character_id: "Aphelios" },
          { character_id: "Jinx" },
          { character_id: "Senna" },
          { character_id: "Thresh" }
        ]
      },
      {
        placement: 3,
        level: 8,
        last_round: "6-2",
        units: [
          { character_id: "Jinx" },
          { character_id: "Vi" },
          { character_id: "Caitlyn" },
          { character_id: "Ekko" }
        ]
      }
    ]
  }
};

/**
 * Utility Functions
 */

// Parse request body for POST requests
function parseBody(req, callback) {
  let body = '';
  req.on('data', chunk => {
    body += chunk.toString();
  });
  req.on('end', () => {
    // Handle different content types
    if (req.headers['content-type']?.includes('application/x-www-form-urlencoded')) {
      const parsed = {};
      body.split('&').forEach(pair => {
        const [key, value] = pair.split('=');
        if (key && value !== undefined) {
          parsed[decodeURIComponent(key)] = decodeURIComponent(value);
        }
      });
      callback(parsed);
    } else if (req.headers['content-type']?.includes('multipart/form-data')) {
      // Basic multipart parsing (for file uploads)
      callback({ file: 'demo-file.jsonl', batch_size: '500', skip_raw_data: true });
    } else {
      callback(body);
    }
  });
}

// Set CORS headers
function setCorsHeaders(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
}

// Send HTML response
function sendHtml(res, html, status = 200) {
  res.writeHead(status, { 
    'Content-Type': 'text/html; charset=utf-8',
    'Cache-Control': 'no-cache'
  });
  res.end(html);
}

// Send JSON response
function sendJson(res, data, status = 200) {
  res.writeHead(status, { 
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-cache'
  });
  res.end(JSON.stringify(data));
}

// Send error response
function sendError(res, message, status = 500) {
  const html = `
    <div class="bg-red-50 border border-red-200 rounded-lg p-4">
      <h3 class="font-medium text-red-800">Error</h3>
      <p class="text-red-700">${message}</p>
    </div>
  `;
  sendHtml(res, html, status);
}

/**
 * API Route Handlers
 */

// GET /api/status - Database connection status
function handleStatus(req, res) {
  console.log('📊 Status check requested');
  
  const html = `
    <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
      <div class="flex">
        <div class="flex-shrink-0">
          <span class="text-yellow-400">⚠️</span>
        </div>
        <div class="ml-3">
          <h3 class="text-sm font-medium text-yellow-800">Demo Mode Active</h3>
          <p class="text-sm text-yellow-700">Using mock data for demonstration. Connect your database for real data.</p>
        </div>
      </div>
    </div>
  `;
  sendHtml(res, html);
}

// GET /api/stats - Statistics cards
function handleStats(req, res) {
  console.log('📈 Statistics requested');
  
  const stats = mockData.stats;
  const html = `
    <div class="bg-white p-6 rounded-lg shadow">
      <h3 class="text-lg font-medium mb-2">Total Matches</h3>
      <p class="text-3xl font-bold text-blue-600">${stats.matches.toLocaleString('en-US')}</p>
    </div>
    <div class="bg-white p-6 rounded-lg shadow">
      <h3 class="text-lg font-medium mb-2">Total Participants</h3>
      <p class="text-3xl font-bold text-green-600">${stats.participants.toLocaleString('en-US')}</p>
    </div>
    <div class="bg-white p-6 rounded-lg shadow">
      <h3 class="text-lg font-medium mb-2">Avg Players/Match</h3>
      <p class="text-3xl font-bold text-purple-600">${stats.avgPlayersPerMatch}</p>
    </div>
  `;
  sendHtml(res, html);
}

// GET /api/clusters/list - Available clusters JSON
function handleClustersList(req, res) {
  console.log('🎯 Clusters list requested');
  
  const clusters = mockData.clusters.map(cluster => ({
    id: cluster.id,
    name: cluster.name
  }));
  
  sendJson(res, { clusters });
}

// GET /api/clusters/details - Cluster details HTML
function handleClustersDetails(req, res) {
  const urlParts = url.parse(req.url, true);
  const clusterId = urlParts.query['cluster-select'];
  
  console.log(`🔍 Cluster details requested for ID: ${clusterId}`);
  
  if (!clusterId) {
    sendHtml(res, '<p class="text-gray-500">Select a cluster to view details</p>');
    return;
  }
  
  const cluster = mockData.clusters.find(c => c.id === clusterId);
  
  if (!cluster) {
    sendError(res, `Cluster ${clusterId} not found`, 404);
    return;
  }
  
  const html = `
    <h3 class="text-xl font-semibold mb-4">Cluster ${cluster.id}: ${cluster.name}</h3>
    
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <div class="bg-gray-50 p-4 rounded">
        <h4 class="text-sm font-medium text-gray-600">Compositions</h4>
        <p class="text-2xl font-bold">${cluster.size.toLocaleString('en-US')}</p>
      </div>
      <div class="bg-gray-50 p-4 rounded">
        <h4 class="text-sm font-medium text-gray-600">Avg Placement</h4>
        <p class="text-2xl font-bold">${cluster.avg_placement}</p>
      </div>
      <div class="bg-gray-50 p-4 rounded">
        <h4 class="text-sm font-medium text-gray-600">Win Rate</h4>
        <p class="text-2xl font-bold">${cluster.winrate}%</p>
      </div>
      <div class="bg-gray-50 p-4 rounded">
        <h4 class="text-sm font-medium text-gray-600">Top 4 Rate</h4>
        <p class="text-2xl font-bold">${cluster.top4_rate}%</p>
      </div>
    </div>
    
    <div class="space-y-4">
      <div>
        <h4 class="font-medium text-gray-700 mb-2">Carry Units</h4>
        <div class="flex flex-wrap gap-2">
          ${cluster.carries.map(carry => 
            `<span class="px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm">${carry}</span>`
          ).join('')}
        </div>
      </div>
      <div>
        <h4 class="font-medium text-gray-700 mb-2">Common Traits</h4>
        <div class="flex flex-wrap gap-2">
          ${cluster.traits.map(trait => 
            `<span class="px-2 py-1 bg-green-100 text-green-800 rounded text-sm">${trait}</span>`
          ).join('')}
        </div>
      </div>
    </div>
    
    <div class="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
      <p class="text-blue-800 text-sm">📊 Demo data - Connect your database for real cluster analysis</p>
    </div>
  `;
  
  sendHtml(res, html);
}

// POST /api/query - Execute TFT query, return results HTML
function handleQuery(req, res) {
  console.log('🔍 Query execution requested');
  
  parseBody(req, (body) => {
    const queryText = body.query ? body.query.trim() : '';
    
    if (!queryText) {
      const html = `
        <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p class="text-yellow-800">Please enter a query</p>
        </div>
      `;
      sendHtml(res, html);
      return;
    }
    
    console.log(`📝 Processing query: ${queryText.substring(0, 100)}...`);
    
    // Validate query format
    if (!queryText.includes('SimpleTFTQuery') && !queryText.includes('TFTQuery')) {
      const html = `
        <div class="bg-red-50 border border-red-200 rounded-lg p-4">
          <p class="text-red-800">Query must contain SimpleTFTQuery() or TFTQuery()</p>
        </div>
      `;
      sendHtml(res, html);
      return;
    }
    
    // Check query type based on method call
    const isStatsQuery = queryText.includes('.get_stats()');
    const isParticipantsQuery = queryText.includes('.get_participants()');
    
    if (isStatsQuery) {
      // Return stats results
      const results = mockData.queryResults.stats;
      const html = `
        <div class="bg-white p-6 rounded-lg shadow">
          <h3 class="text-lg font-medium mb-4">Query Results</h3>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div class="bg-gray-50 p-4 rounded">
              <h4 class="text-sm font-medium text-gray-600">Play Count</h4>
              <p class="text-2xl font-bold">${results.play_count.toLocaleString('en-US')}</p>
            </div>
            <div class="bg-gray-50 p-4 rounded">
              <h4 class="text-sm font-medium text-gray-600">Avg Placement</h4>
              <p class="text-2xl font-bold">${results.avg_placement}</p>
            </div>
            <div class="bg-gray-50 p-4 rounded">
              <h4 class="text-sm font-medium text-gray-600">Win Rate</h4>
              <p class="text-2xl font-bold">${results.winrate}%</p>
            </div>
            <div class="bg-gray-50 p-4 rounded">
              <h4 class="text-sm font-medium text-gray-600">Top 4 Rate</h4>
              <p class="text-2xl font-bold">${results.top4_rate}%</p>
            </div>
          </div>
          <div class="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p class="text-blue-800 text-sm">📊 Demo results - Connect database for real queries</p>
          </div>
        </div>
      `;
      sendHtml(res, html);
      
    } else if (isParticipantsQuery) {
      // Return participant results
      const participants = mockData.queryResults.participants;
      let html = `
        <div class="bg-white p-6 rounded-lg shadow">
          <h3 class="text-lg font-medium mb-4">Query Results</h3>
          <p class="text-gray-600 mb-4">Found ${participants.length.toLocaleString('en-US')} matching compositions</p>
          
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Placement</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Level</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Round</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Units</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
      `;
      
      participants.forEach(p => {
        const units = p.units.slice(0, 5).map(u => u.character_id).join(', ');
        const unitsDisplay = p.units.length > 5 ? units + '...' : units;
        
        html += `
          <tr>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${p.placement}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${p.level}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${p.last_round}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${unitsDisplay}</td>
          </tr>
        `;
      });
      
      html += `
              </tbody>
            </table>
          </div>
          <div class="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p class="text-blue-800 text-sm">📊 Demo results - Connect database for real queries</p>
          </div>
        </div>
      `;
      
      sendHtml(res, html);
    } else {
      // Generic query response
      const html = `
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 class="font-medium text-blue-800">Query Processed</h3>
          <p class="text-blue-700 mt-2">Query executed successfully. In demo mode, all queries return sample data.</p>
          <div class="mt-4">
            <p class="text-sm text-blue-600">Try these query examples:</p>
            <ul class="list-disc list-inside text-sm text-blue-600 mt-2">
              <li>SimpleTFTQuery().add_unit('Aphelios').get_stats()</li>
              <li>SimpleTFTQuery().add_trait('Sniper', 2).get_participants()</li>
            </ul>
          </div>
        </div>
      `;
      sendHtml(res, html);
    }
  });
}

// POST /api/upload - File upload placeholder
function handleUpload(req, res) {
  console.log('📤 File upload requested');
  
  parseBody(req, (body) => {
    const fileName = body.file || 'unknown';
    const batchSize = body.batch_size || '500';
    const skipRaw = body.skip_raw_data || false;
    
    console.log(`📁 Upload details - File: ${fileName}, Batch: ${batchSize}, Skip Raw: ${skipRaw}`);
    
    const html = `
      <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 class="font-medium text-blue-800">Demo Mode - Upload Simulation</h3>
        <div class="mt-2 space-y-2">
          <p class="text-blue-700">📁 File: ${fileName}</p>
          <p class="text-blue-700">⚙️ Batch size: ${batchSize}</p>
          <p class="text-blue-700">💾 Skip raw data: ${skipRaw ? 'Yes' : 'No'}</p>
        </div>
        <div class="mt-4 p-3 bg-blue-100 rounded">
          <p class="text-sm text-blue-800">In production, this would:</p>
          <ul class="list-disc list-inside text-sm text-blue-700 mt-2">
            <li>Parse the JSONL file</li>
            <li>Validate match data structure</li>
            <li>Insert into database in batches</li>
            <li>Return progress updates</li>
          </ul>
        </div>
      </div>
    `;
    
    sendHtml(res, html);
  });
}

// GET /api/db-status - Database status for upload tab
function handleDbStatus(req, res) {
  console.log('🗄️ Database status requested');
  
  const stats = mockData.stats;
  const html = `
    <div class="grid grid-cols-2 gap-4">
      <div class="bg-gray-50 p-4 rounded">
        <h4 class="text-sm font-medium text-gray-600">Total Matches</h4>
        <p class="text-2xl font-bold">${stats.matches.toLocaleString('en-US')}</p>
      </div>
      <div class="bg-gray-50 p-4 rounded">
        <h4 class="text-sm font-medium text-gray-600">Total Participants</h4>
        <p class="text-2xl font-bold">${stats.participants.toLocaleString('en-US')}</p>
      </div>
    </div>
    <p class="text-sm text-yellow-600 mt-4">⚠️ Demo mode - using mock data</p>
  `;
  
  sendHtml(res, html);
}

/**
 * Main Request Router
 */
function handleRequest(req, res) {
  // Set CORS headers for all requests
  setCorsHeaders(res);
  
  // Handle OPTIONS requests for CORS preflight
  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }
  
  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;
  const method = req.method.toLowerCase();
  
  console.log(`${method.toUpperCase()} ${pathname}`);
  
  try {
    // Static file serving for index.html
    if (pathname === '/' || pathname === '/index.html') {
      try {
        const indexPath = path.join(__dirname, 'index.html');
        const indexHtml = fs.readFileSync(indexPath, 'utf8');
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(indexHtml);
      } catch (err) {
        res.writeHead(404);
        res.end('index.html not found');
      }
      return;
    }
    
    // API Routes
    if (pathname.startsWith('/api/')) {
      if (method === 'get') {
        switch (pathname) {
          case '/api/status':
            handleStatus(req, res);
            break;
          case '/api/stats':
            handleStats(req, res);
            break;
          case '/api/clusters/list':
            handleClustersList(req, res);
            break;
          case '/api/clusters/details':
            handleClustersDetails(req, res);
            break;
          case '/api/db-status':
            handleDbStatus(req, res);
            break;
          default:
            res.writeHead(404);
            res.end('API endpoint not found');
        }
      } else if (method === 'post') {
        switch (pathname) {
          case '/api/query':
            handleQuery(req, res);
            break;
          case '/api/upload':
            handleUpload(req, res);
            break;
          default:
            res.writeHead(404);
            res.end('API endpoint not found');
        }
      } else {
        res.writeHead(405);
        res.end('Method not allowed');
      }
    } else {
      // 404 for other routes
      res.writeHead(404);
      res.end('Not found');
    }
    
  } catch (error) {
    console.error('❌ Request handling error:', error);
    res.writeHead(500);
    res.end('Internal server error');
  }
}

/**
 * Server Initialization
 */
function startServer() {
  const server = http.createServer(handleRequest);
  
  server.listen(PORT, HOST, () => {
    console.log('🚀 TFT Webapp API Server Started');
    console.log(`📡 Server: http://${HOST}:${PORT}`);
    console.log(`📊 Environment: ${process.env.NODE_ENV || 'development'}`);
    console.log('⚔️ Ready to serve TFT composition analysis!');
    console.log('\n📋 Available endpoints:');
    console.log('  GET  /                    - Main HTML page');
    console.log('  GET  /api/status          - Database status');
    console.log('  GET  /api/stats           - Statistics cards');
    console.log('  GET  /api/clusters/list   - Cluster list (JSON)');
    console.log('  GET  /api/clusters/details- Cluster details (HTML)');
    console.log('  POST /api/query           - Execute TFT query');
    console.log('  POST /api/upload          - File upload');
    console.log('  GET  /api/db-status       - Database status for upload');
    console.log('');
  });
  
  // Graceful shutdown
  process.on('SIGINT', () => {
    console.log('\n🛑 Shutting down gracefully...');
    server.close(() => {
      console.log('✅ Server closed');
      process.exit(0);
    });
  });
  
  // Error handling
  server.on('error', (err) => {
    if (err.code === 'EADDRINUSE') {
      console.error(`❌ Port ${PORT} is already in use`);
    } else {
      console.error('❌ Server error:', err);
    }
    process.exit(1);
  });
}

// Start the server
if (require.main === module) {
  startServer();
}

module.exports = { handleRequest, startServer };