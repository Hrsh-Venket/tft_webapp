// Ultra-minimal Node.js API for TFT Webapp
// Zero external dependencies

const mockStats = { matches: 12500, participants: 100000 };
const mockClusters = [
  { id: "0", name: "Aphelios Carry", size: 1250, avg_placement: 3.2, winrate: 18.5, top4_rate: 62.4 },
  { id: "1", name: "Jinx Sniper", size: 980, avg_placement: 3.8, winrate: 15.2, top4_rate: 58.1 },
  { id: "2", name: "Star Guardian", size: 850, avg_placement: 4.1, winrate: 12.8, top4_rate: 54.2 },
  { id: "3", name: "Vanguard Tank", size: 720, avg_placement: 4.3, winrate: 11.5, top4_rate: 51.8 },
];

export default function handler(req, res) {
  const { method, url } = req;
  const path = url.split('?')[0];

  // Set CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  if (method === 'GET') {
    if (path === '/api/status') {
      res.setHeader('Content-Type', 'text/html');
      res.status(200).send(`
        <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <h3 class="text-sm font-medium text-yellow-800">Demo Mode</h3>
          <p class="text-sm text-yellow-700">Using mock data for demonstration.</p>
        </div>
      `);
    } 
    else if (path === '/api/stats') {
      res.setHeader('Content-Type', 'text/html');
      res.status(200).send(`
        <div class="bg-white p-6 rounded-lg shadow">
          <h3 class="text-lg font-medium mb-2">Total Matches</h3>
          <p class="text-3xl font-bold text-blue-600">${mockStats.matches.toLocaleString()}</p>
        </div>
        <div class="bg-white p-6 rounded-lg shadow">
          <h3 class="text-lg font-medium mb-2">Total Participants</h3>
          <p class="text-3xl font-bold text-green-600">${mockStats.participants.toLocaleString()}</p>
        </div>
        <div class="bg-white p-6 rounded-lg shadow">
          <h3 class="text-lg font-medium mb-2">Avg Players/Match</h3>
          <p class="text-3xl font-bold text-purple-600">${(mockStats.participants / mockStats.matches).toFixed(1)}</p>
        </div>
      `);
    }
    else if (path === '/api/clusters/list') {
      res.setHeader('Content-Type', 'application/json');
      res.status(200).json({ 
        clusters: mockClusters.map(c => ({ id: c.id, name: c.name }))
      });
    }
    else if (path === '/api/clusters/details') {
      const clusterId = new URL(req.url, 'http://localhost').searchParams.get('cluster-select');
      const cluster = mockClusters.find(c => c.id === clusterId);
      
      if (!cluster) {
        res.setHeader('Content-Type', 'text/html');
        res.status(200).send('<p class="text-gray-500">Select a cluster to view details</p>');
        return;
      }

      res.setHeader('Content-Type', 'text/html');
      res.status(200).send(`
        <h3 class="text-xl font-semibold mb-4">Cluster ${cluster.id}: ${cluster.name}</h3>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div class="bg-gray-50 p-4 rounded">
            <h4 class="text-sm font-medium text-gray-600">Compositions</h4>
            <p class="text-2xl font-bold">${cluster.size.toLocaleString()}</p>
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
        <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p class="text-yellow-800 text-sm">📊 Demo data - Connect your database for real analysis</p>
        </div>
      `);
    }
    else if (path === '/api/db-status') {
      res.setHeader('Content-Type', 'text/html');
      res.status(200).send(`
        <div class="grid grid-cols-2 gap-4">
          <div class="bg-gray-50 p-4 rounded">
            <h4 class="text-sm font-medium text-gray-600">Total Matches</h4>
            <p class="text-2xl font-bold">${mockStats.matches.toLocaleString()}</p>
          </div>
          <div class="bg-gray-50 p-4 rounded">
            <h4 class="text-sm font-medium text-gray-600">Total Participants</h4>
            <p class="text-2xl font-bold">${mockStats.participants.toLocaleString()}</p>
          </div>
        </div>
        <p class="text-sm text-yellow-600 mt-4">⚠️ Demo mode - using mock data</p>
      `);
    }
    else {
      res.status(404).send('Not Found');
    }
  }
  else if (method === 'POST') {
    if (path === '/api/query') {
      res.setHeader('Content-Type', 'text/html');
      res.status(200).send(`
        <div class="bg-white p-6 rounded-lg shadow">
          <h3 class="text-lg font-medium mb-4">Query Results</h3>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div class="bg-gray-50 p-4 rounded">
              <h4 class="text-sm font-medium text-gray-600">Play Count</h4>
              <p class="text-2xl font-bold">1,250</p>
            </div>
            <div class="bg-gray-50 p-4 rounded">
              <h4 class="text-sm font-medium text-gray-600">Avg Placement</h4>
              <p class="text-2xl font-bold">3.2</p>
            </div>
            <div class="bg-gray-50 p-4 rounded">
              <h4 class="text-sm font-medium text-gray-600">Win Rate</h4>
              <p class="text-2xl font-bold">18.5%</p>
            </div>
            <div class="bg-gray-50 p-4 rounded">
              <h4 class="text-sm font-medium text-gray-600">Top 4 Rate</h4>
              <p class="text-2xl font-bold">62.4%</p>
            </div>
          </div>
          <div class="mt-4 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p class="text-yellow-800 text-sm">📊 Demo results - Connect database for real queries</p>
          </div>
        </div>
      `);
    }
    else if (path === '/api/upload') {
      res.setHeader('Content-Type', 'text/html');
      res.status(200).send(`
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 class="font-medium text-blue-800">Demo Mode</h3>
          <p class="text-blue-700">File upload requires database connection.</p>
        </div>
      `);
    }
    else {
      res.status(404).send('Not Found');
    }
  }
  else {
    res.status(405).send('Method Not Allowed');
  }
}