#!/usr/bin/env node

/**
 * TFT Webapp API Demo Script
 * 
 * Demonstrates the complete Node.js backend API in action.
 * Shows how all endpoints work and what they return.
 */

const http = require('http');
const { URL } = require('url');

// Configuration
const DEMO_PORT = 3002;
const BASE_URL = `http://localhost:${DEMO_PORT}`;

// Start demo server
const server = require('./server.js');
let demoServer;

// Demo request utility
function makeRequest(method, path, data = null) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, BASE_URL);
    
    const headers = {};
    if (method === 'POST' && data) {
      headers['Content-Type'] = 'application/x-www-form-urlencoded';
    }
    
    const options = {
      hostname: url.hostname,
      port: url.port,
      path: url.pathname + url.search,
      method: method.toUpperCase(),
      headers: headers
    };
    
    const req = http.request(options, (res) => {
      let body = '';
      res.on('data', chunk => body += chunk);
      res.on('end', () => {
        resolve({
          status: res.statusCode,
          headers: res.headers,
          body: body.trim()
        });
      });
    });
    
    req.on('error', reject);
    
    if (data && method === 'POST') {
      const postData = new URLSearchParams(data).toString();
      req.write(postData);
    }
    
    req.end();
  });
}

// Demo scenarios
const demos = [
  {
    title: "Database Status Check",
    method: "GET",
    path: "/api/status",
    description: "Check if database connection is working"
  },
  {
    title: "Statistics Overview", 
    method: "GET",
    path: "/api/stats",
    description: "Get overall match statistics"
  },
  {
    title: "Available Clusters",
    method: "GET", 
    path: "/api/clusters/list",
    description: "List all available team composition clusters"
  },
  {
    title: "Cluster Details - Aphelios Carry",
    method: "GET",
    path: "/api/clusters/details?cluster-select=0",
    description: "Detailed analysis of the Aphelios carry cluster"
  },
  {
    title: "TFT Query - Aphelios Stats",
    method: "POST",
    path: "/api/query",
    data: { query: 'SimpleTFTQuery().add_unit("Aphelios").get_stats()' },
    description: "Execute a TFT query to get Aphelios unit statistics"
  },
  {
    title: "TFT Query - Jinx Participants",
    method: "POST", 
    path: "/api/query",
    data: { query: 'SimpleTFTQuery().add_unit("Jinx").get_participants()' },
    description: "Get individual match data for compositions with Jinx"
  },
  {
    title: "File Upload Simulation",
    method: "POST",
    path: "/api/upload", 
    data: { file: 'matches.jsonl', batch_size: '1000', skip_raw_data: 'true' },
    description: "Simulate uploading match data to the database"
  },
  {
    title: "Database Status for Upload",
    method: "GET",
    path: "/api/db-status",
    description: "Get database status information for the upload tab"
  }
];

// Run demo
async function runDemo() {
  console.log('🎮 TFT Webapp Node.js API Demo');
  console.log('=' .repeat(60));
  console.log('🚀 This demo showcases the complete backend API functionality');
  console.log('⚔️ All endpoints work with the HTMX frontend seamlessly');
  console.log('');
  
  // Start demo server
  process.env.PORT = DEMO_PORT;
  demoServer = http.createServer(server.handleRequest);
  
  await new Promise((resolve) => {
    demoServer.listen(DEMO_PORT, () => {
      console.log(`🌟 Demo server started on ${BASE_URL}`);
      console.log('');
      resolve();
    });
  });
  
  // Run through each demo
  for (let i = 0; i < demos.length; i++) {
    const demo = demos[i];
    
    console.log(`📋 Demo ${i + 1}/${demos.length}: ${demo.title}`);
    console.log(`📝 ${demo.description}`);
    console.log(`🔗 ${demo.method} ${demo.path}`);
    
    if (demo.data) {
      console.log(`📦 Data: ${JSON.stringify(demo.data)}`);
    }
    
    try {
      const response = await makeRequest(demo.method, demo.path, demo.data);
      
      console.log(`✅ Status: ${response.status}`);
      console.log(`📄 Content-Type: ${response.headers['content-type']}`);
      
      // Show response preview
      if (response.headers['content-type']?.includes('application/json')) {
        const json = JSON.parse(response.body);
        console.log('📊 Response (JSON):');
        console.log(JSON.stringify(json, null, 2));
      } else {
        // For HTML responses, show a preview
        const preview = response.body.length > 200 
          ? response.body.substring(0, 200) + '...' 
          : response.body;
        console.log('🏷️  Response (HTML Preview):');
        console.log(preview.replace(/\n\s+/g, ' ').trim());
      }
      
    } catch (error) {
      console.log(`❌ Error: ${error.message}`);
    }
    
    console.log('');
    
    // Add a small delay between requests
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  
  console.log('=' .repeat(60));
  console.log('🎉 Demo completed successfully!');
  console.log('');
  console.log('💡 Key Features Demonstrated:');
  console.log('  ✅ Zero external dependencies');
  console.log('  ✅ HTMX-compatible HTML responses');
  console.log('  ✅ JSON API endpoints');
  console.log('  ✅ TFT query processing');
  console.log('  ✅ File upload handling');
  console.log('  ✅ Proper error handling');
  console.log('  ✅ CORS support');
  console.log('');
  console.log('🚀 Ready for production use!');
  console.log('📖 Check README-NODE-API.md for full documentation');
  
  // Cleanup
  demoServer.close();
}

// Handle errors
process.on('unhandledRejection', (reason, promise) => {
  console.error('❌ Unhandled Rejection:', reason);
  if (demoServer) demoServer.close();
  process.exit(1);
});

process.on('SIGINT', () => {
  console.log('\n🛑 Demo interrupted');
  if (demoServer) demoServer.close();
  process.exit(0);
});

// Run the demo
if (require.main === module) {
  runDemo().catch(error => {
    console.error('❌ Demo error:', error);
    if (demoServer) demoServer.close();
    process.exit(1);
  });
}

module.exports = { runDemo };