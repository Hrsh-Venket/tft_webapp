#!/usr/bin/env node

/**
 * TFT Webapp API Test Suite
 * 
 * Simple test script to verify all API endpoints work correctly.
 * Tests both the server functionality and HTMX compatibility.
 */

const http = require('http');
const { URL } = require('url');

// Test configuration
const BASE_URL = 'http://localhost:3000';
const TEST_PORT = 3001; // Use different port for testing

// Start test server
const server = require('./server.js');
let testServer;

// Test utilities
function makeRequest(method, path, data = null) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, `http://localhost:${TEST_PORT}`);
    
    const headers = {};
    if (method === 'POST') {
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

// Test cases
const tests = [
  {
    name: 'GET /api/status',
    method: 'GET',
    path: '/api/status',
    expect: {
      status: 200,
      contentType: 'text/html',
      contains: ['Demo Mode', 'mock data']
    }
  },
  {
    name: 'GET /api/stats',
    method: 'GET', 
    path: '/api/stats',
    expect: {
      status: 200,
      contentType: 'text/html',
      contains: ['Total Matches', '12,847', '102,776']
    }
  },
  {
    name: 'GET /api/clusters/list',
    method: 'GET',
    path: '/api/clusters/list', 
    expect: {
      status: 200,
      contentType: 'application/json',
      contains: ['Aphelios Carry', 'clusters']
    }
  },
  {
    name: 'GET /api/clusters/details',
    method: 'GET',
    path: '/api/clusters/details?cluster-select=0',
    expect: {
      status: 200,
      contentType: 'text/html',
      contains: ['Aphelios Carry', 'Compositions', 'Win Rate']
    }
  },
  {
    name: 'POST /api/query (stats)',
    method: 'POST',
    path: '/api/query',
    data: { query: 'SimpleTFTQuery().add_unit("Aphelios").get_stats()' },
    expect: {
      status: 200,
      contentType: 'text/html',
      contains: ['Query Results', 'Play Count', '1,250']
    }
  },
  {
    name: 'POST /api/query (participants)',
    method: 'POST',
    path: '/api/query',
    data: { query: 'SimpleTFTQuery().add_unit("Jinx").get_participants()' },
    expect: {
      status: 200,
      contentType: 'text/html',
      contains: ['Query Results', 'Placement', 'Level']
    }
  },
  {
    name: 'POST /api/upload',
    method: 'POST',
    path: '/api/upload',
    data: { file: 'test.jsonl', batch_size: '500', skip_raw_data: 'true' },
    expect: {
      status: 200,
      contentType: 'text/html',
      contains: ['Demo Mode', 'Upload Simulation', 'test.jsonl']
    }
  },
  {
    name: 'GET /api/db-status',
    method: 'GET',
    path: '/api/db-status',
    expect: {
      status: 200,
      contentType: 'text/html',
      contains: ['Total Matches', 'Total Participants', 'Demo mode']
    }
  }
];

// Run tests
async function runTests() {
  console.log('🧪 TFT Webapp API Test Suite');
  console.log('=' .repeat(50));
  
  // Start test server
  process.env.PORT = TEST_PORT;
  testServer = http.createServer(server.handleRequest);
  
  await new Promise((resolve) => {
    testServer.listen(TEST_PORT, () => {
      console.log(`🚀 Test server started on port ${TEST_PORT}`);
      resolve();
    });
  });
  
  let passed = 0;
  let failed = 0;
  
  for (const test of tests) {
    try {
      console.log(`\n📋 Testing: ${test.name}`);
      
      const response = await makeRequest(test.method, test.path, test.data);
      
      // Check status code
      if (response.status !== test.expect.status) {
        throw new Error(`Expected status ${test.expect.status}, got ${response.status}`);
      }
      
      // Check content type
      const contentType = response.headers['content-type'];
      if (!contentType.includes(test.expect.contentType)) {
        throw new Error(`Expected content-type to include ${test.expect.contentType}, got ${contentType}`);
      }
      
      // Check response contains expected strings
      for (const expectedString of test.expect.contains) {
        if (!response.body.includes(expectedString)) {
          throw new Error(`Response body does not contain: ${expectedString}`);
        }
      }
      
      console.log(`   ✅ PASSED`);
      passed++;
      
    } catch (error) {
      console.log(`   ❌ FAILED: ${error.message}`);
      failed++;
    }
  }
  
  // Test summary
  console.log('\n' + '='.repeat(50));
  console.log(`📊 Test Results: ${passed} passed, ${failed} failed`);
  
  if (failed === 0) {
    console.log('🎉 All tests passed! The API is working correctly.');
  } else {
    console.log('⚠️  Some tests failed. Check the output above for details.');
  }
  
  // Cleanup
  testServer.close();
  process.exit(failed > 0 ? 1 : 0);
}

// Handle errors
process.on('unhandledRejection', (reason, promise) => {
  console.error('❌ Unhandled Rejection:', reason);
  if (testServer) testServer.close();
  process.exit(1);
});

// Run the tests
if (require.main === module) {
  runTests().catch(error => {
    console.error('❌ Test runner error:', error);
    if (testServer) testServer.close();
    process.exit(1);
  });
}

module.exports = { runTests };