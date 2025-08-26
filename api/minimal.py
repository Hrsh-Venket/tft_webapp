"""
Minimal Vercel API for TFT Webapp Demo
No database dependencies - uses mock data for demonstration
"""

from flask import Flask, request, jsonify
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Mock data for demonstration
MOCK_STATS = {
    'matches': 12500,
    'participants': 100000
}

MOCK_CLUSTERS = [
    {"id": "0", "name": "Aphelios Carry", "size": 1250, "avg_placement": 3.2, "winrate": 18.5, "top4_rate": 62.4},
    {"id": "1", "name": "Jinx Sniper", "size": 980, "avg_placement": 3.8, "winrate": 15.2, "top4_rate": 58.1},
    {"id": "2", "name": "Star Guardian", "size": 850, "avg_placement": 4.1, "winrate": 12.8, "top4_rate": 54.2},
    {"id": "3", "name": "Vanguard Tank", "size": 720, "avg_placement": 4.3, "winrate": 11.5, "top4_rate": 51.8},
    {"id": "4", "name": "Battle Academia", "size": 650, "avg_placement": 4.5, "winrate": 10.2, "top4_rate": 48.9},
]

@app.route('/')
def index():
    """Serve the main HTML page"""
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return """
        <!DOCTYPE html>
        <html>
        <head><title>TFT Webapp</title></head>
        <body>
        <h1>TFT Webapp Demo</h1>
        <p>This is a demo version. The main index.html file should be deployed alongside this API.</p>
        <p><a href="/api/status">Check API Status</a></p>
        </body>
        </html>
        """

@app.route('/api/status')
def get_status():
    """Get database connection status"""
    return """
    <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div class="flex">
            <div class="flex-shrink-0">
                <span class="text-yellow-400">⚠️</span>
            </div>
            <div class="ml-3">
                <h3 class="text-sm font-medium text-yellow-800">Demo Mode</h3>
                <p class="text-sm text-yellow-700">Using mock data for demonstration. Connect DATABASE_URL for live data.</p>
            </div>
        </div>
    </div>
    """

@app.route('/api/stats')
def get_stats():
    """Get database statistics"""
    stats = MOCK_STATS
    
    html = f"""
    <div class="bg-white p-6 rounded-lg shadow">
        <h3 class="text-lg font-medium mb-2">Total Matches</h3>
        <p class="text-3xl font-bold text-blue-600">{stats['matches']:,}</p>
        <p class="text-sm text-gray-500">Demo data</p>
    </div>
    <div class="bg-white p-6 rounded-lg shadow">
        <h3 class="text-lg font-medium mb-2">Total Participants</h3>
        <p class="text-3xl font-bold text-green-600">{stats['participants']:,}</p>
        <p class="text-sm text-gray-500">Demo data</p>
    </div>
    <div class="bg-white p-6 rounded-lg shadow">
        <h3 class="text-lg font-medium mb-2">Avg Players/Match</h3>
        <p class="text-3xl font-bold text-purple-600">{(stats['participants'] / stats['matches']):.1f}</p>
        <p class="text-sm text-gray-500">Demo data</p>
    </div>
    """
    
    return html

@app.route('/api/clusters/list')
def get_clusters_list():
    """Get list of available clusters"""
    clusters = [{"id": c["id"], "name": c["name"]} for c in MOCK_CLUSTERS]
    return jsonify({"clusters": clusters})

@app.route('/api/clusters/details')
def get_cluster_details():
    """Get details for a specific cluster"""
    cluster_id = request.args.get('cluster-select')
    
    if not cluster_id:
        return '<p class="text-gray-500">Select a cluster to view details</p>'
    
    # Find cluster data
    cluster_data = next((c for c in MOCK_CLUSTERS if c["id"] == cluster_id), None)
    
    if not cluster_data:
        return f'<p class="text-red-500">Cluster {cluster_id} not found</p>'
    
    html = f"""
    <h3 class="text-xl font-semibold mb-4">Cluster {cluster_id}: {cluster_data['name']}</h3>
    
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-gray-50 p-4 rounded">
            <h4 class="text-sm font-medium text-gray-600">Compositions</h4>
            <p class="text-2xl font-bold">{cluster_data['size']:,}</p>
        </div>
        <div class="bg-gray-50 p-4 rounded">
            <h4 class="text-sm font-medium text-gray-600">Avg Placement</h4>
            <p class="text-2xl font-bold">{cluster_data['avg_placement']}</p>
        </div>
        <div class="bg-gray-50 p-4 rounded">
            <h4 class="text-sm font-medium text-gray-600">Win Rate</h4>
            <p class="text-2xl font-bold">{cluster_data['winrate']}%</p>
        </div>
        <div class="bg-gray-50 p-4 rounded">
            <h4 class="text-sm font-medium text-gray-600">Top 4 Rate</h4>
            <p class="text-2xl font-bold">{cluster_data['top4_rate']}%</p>
        </div>
    </div>
    
    <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p class="text-yellow-800 text-sm">📊 Demo data - Connect your database for real cluster analysis</p>
    </div>
    """
    
    return html

@app.route('/api/query', methods=['POST'])
def execute_query():
    """Execute a TFT query"""
    query_text = request.form.get('query', '').strip()
    
    if not query_text:
        return """
        <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p class="text-yellow-800">Please enter a query</p>
        </div>
        """
    
    # Mock query results
    mock_result = {
        'play_count': 1250,
        'avg_placement': 3.2,
        'winrate': 18.5,
        'top4_rate': 62.4
    }
    
    html = f"""
    <div class="bg-white p-6 rounded-lg shadow">
        <h3 class="text-lg font-medium mb-4">Query Results</h3>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div class="bg-gray-50 p-4 rounded">
                <h4 class="text-sm font-medium text-gray-600">Play Count</h4>
                <p class="text-2xl font-bold">{mock_result['play_count']:,}</p>
            </div>
            <div class="bg-gray-50 p-4 rounded">
                <h4 class="text-sm font-medium text-gray-600">Avg Placement</h4>
                <p class="text-2xl font-bold">{mock_result['avg_placement']}</p>
            </div>
            <div class="bg-gray-50 p-4 rounded">
                <h4 class="text-sm font-medium text-gray-600">Win Rate</h4>
                <p class="text-2xl font-bold">{mock_result['winrate']}%</p>
            </div>
            <div class="bg-gray-50 p-4 rounded">
                <h4 class="text-sm font-medium text-gray-600">Top 4 Rate</h4>
                <p class="text-2xl font-bold">{mock_result['top4_rate']}%</p>
            </div>
        </div>
        <div class="mt-4 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p class="text-yellow-800 text-sm">📊 Demo results - Connect your database for real query execution</p>
            <p class="text-yellow-700 text-xs mt-1">Query: {query_text}</p>
        </div>
    </div>
    """
    
    return html

@app.route('/api/upload', methods=['POST'])
def upload_data():
    """Handle data upload"""
    return """
    <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 class="font-medium text-blue-800">Demo Mode</h3>
        <p class="text-blue-700">File upload requires database connection. This is a demonstration version.</p>
    </div>
    """

@app.route('/api/db-status')
def get_db_status():
    """Get database status for upload tab"""
    stats = MOCK_STATS
    
    html = f"""
    <div class="grid grid-cols-2 gap-4">
        <div class="bg-gray-50 p-4 rounded">
            <h4 class="text-sm font-medium text-gray-600">Total Matches</h4>
            <p class="text-2xl font-bold">{stats['matches']:,}</p>
        </div>
        <div class="bg-gray-50 p-4 rounded">
            <h4 class="text-sm font-medium text-gray-600">Total Participants</h4>
            <p class="text-2xl font-bold">{stats['participants']:,}</p>
        </div>
    </div>
    <p class="text-sm text-yellow-600 mt-4">⚠️ Demo mode - using mock data</p>
    """
    
    return html

# Vercel serverless function handler
def handler(request):
    return app(request.environ, lambda status, headers: None)

if __name__ == '__main__':
    app.run(debug=True)