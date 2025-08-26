"""
Ultra-minimal Vercel API for TFT Webapp
Zero external dependencies - pure Python standard library
"""

import json
import urllib.parse
from http.server import BaseHTTPRequestHandler

# Mock data
MOCK_STATS = {'matches': 12500, 'participants': 100000}
MOCK_CLUSTERS = [
    {"id": "0", "name": "Aphelios Carry", "size": 1250, "avg_placement": 3.2, "winrate": 18.5, "top4_rate": 62.4},
    {"id": "1", "name": "Jinx Sniper", "size": 980, "avg_placement": 3.8, "winrate": 15.2, "top4_rate": 58.1},
]

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?')[0]
        
        if path == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html = '''<div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <h3 class="text-sm font-medium text-yellow-800">Demo Mode</h3>
                <p class="text-sm text-yellow-700">Using mock data for demonstration.</p>
            </div>'''
            self.wfile.write(html.encode())
            
        elif path == '/api/stats':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            stats = MOCK_STATS
            html = f'''<div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-lg font-medium mb-2">Total Matches</h3>
                <p class="text-3xl font-bold text-blue-600">{stats['matches']:,}</p>
            </div>
            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-lg font-medium mb-2">Total Participants</h3>
                <p class="text-3xl font-bold text-green-600">{stats['participants']:,}</p>
            </div>
            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-lg font-medium mb-2">Avg Players/Match</h3>
                <p class="text-3xl font-bold text-purple-600">{stats['participants']/stats['matches']:.1f}</p>
            </div>'''
            self.wfile.write(html.encode())
            
        elif path == '/api/clusters/list':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            clusters = [{"id": c["id"], "name": c["name"]} for c in MOCK_CLUSTERS]
            self.wfile.write(json.dumps({"clusters": clusters}).encode())
            
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/api/query':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html = '''<div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-lg font-medium mb-4">Query Results (Demo)</h3>
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
            </div>'''
            self.wfile.write(html.encode())
        else:
            self.send_response(404)
            self.end_headers()