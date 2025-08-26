"""
Vercel API endpoints for TFT Webapp
Provides REST API for HTMX frontend
"""

from flask import Flask, request, jsonify, render_template_string
import os
import json
import logging
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Import TFT query system
try:
    from simple_database import SimpleTFTQuery as TFTQuery, test_connection, get_match_stats
    DATABASE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Database import failed: {e}")
    DATABASE_AVAILABLE = False
    
    # Fallback class
    class TFTQuery:
        def __init__(self, *args, **kwargs):
            pass
        def add_unit(self, *args, **kwargs):
            return self
        def get_stats(self):
            return {"error": "Database not available", "play_count": 0, "avg_placement": 0, "winrate": 0, "top4_rate": 0}
    
    def test_connection():
        return False
    
    def get_match_stats():
        return {'matches': 0, 'participants': 0}

@app.route('/')
def index():
    """Serve the main HTML page"""
    with open('index.html', 'r') as f:
        return f.read()

@app.route('/api/status')
def get_status():
    """Get database connection status"""
    if not DATABASE_AVAILABLE:
        return """
        <div class="bg-red-50 border border-red-200 rounded-lg p-4">
            <div class="flex">
                <div class="flex-shrink-0">
                    <span class="text-red-400">❌</span>
                </div>
                <div class="ml-3">
                    <h3 class="text-sm font-medium text-red-800">Database Unavailable</h3>
                    <p class="text-sm text-red-700">Database connection modules not available</p>
                </div>
            </div>
        </div>
        """
    
    connection_ok = test_connection()
    
    if connection_ok:
        return """
        <div class="bg-green-50 border border-green-200 rounded-lg p-4">
            <div class="flex">
                <div class="flex-shrink-0">
                    <span class="text-green-400">✅</span>
                </div>
                <div class="ml-3">
                    <h3 class="text-sm font-medium text-green-800">Database Connected</h3>
                    <p class="text-sm text-green-700">Connection to TFT match database successful</p>
                </div>
            </div>
        </div>
        """
    else:
        return """
        <div class="bg-red-50 border border-red-200 rounded-lg p-4">
            <div class="flex">
                <div class="flex-shrink-0">
                    <span class="text-red-400">❌</span>
                </div>
                <div class="ml-3">
                    <h3 class="text-sm font-medium text-red-800">Connection Failed</h3>
                    <p class="text-sm text-red-700">Unable to connect to database - check network and credentials</p>
                </div>
            </div>
        </div>
        """

@app.route('/api/stats')
def get_stats():
    """Get database statistics"""
    try:
        stats = get_match_stats()
        
        html = f"""
        <div class="bg-white p-6 rounded-lg shadow">
            <h3 class="text-lg font-medium mb-2">Total Matches</h3>
            <p class="text-3xl font-bold text-blue-600">{stats['matches']:,}</p>
        </div>
        <div class="bg-white p-6 rounded-lg shadow">
            <h3 class="text-lg font-medium mb-2">Total Participants</h3>
            <p class="text-3xl font-bold text-green-600">{stats['participants']:,}</p>
        </div>
        <div class="bg-white p-6 rounded-lg shadow">
            <h3 class="text-lg font-medium mb-2">Avg Players/Match</h3>
            <p class="text-3xl font-bold text-purple-600">{(stats['participants'] / stats['matches'] if stats['matches'] > 0 else 0):.1f}</p>
        </div>
        """
        
        return html
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return """
        <div class="bg-white p-6 rounded-lg shadow">
            <h3 class="text-lg font-medium mb-2 text-red-600">Error</h3>
            <p class="text-sm text-red-500">Unable to load statistics</p>
        </div>
        """

@app.route('/api/clusters/list')
def get_clusters_list():
    """Get list of available clusters"""
    try:
        # Mock data for now - in production this would query the database
        clusters = [
            {"id": "0", "name": "Aphelios Carry"},
            {"id": "1", "name": "Jinx Sniper"},
            {"id": "2", "name": "Star Guardian"},
            {"id": "3", "name": "Vanguard Tank"},
            {"id": "4", "name": "Battle Academia"},
        ]
        
        return jsonify({"clusters": clusters})
        
    except Exception as e:
        logger.error(f"Clusters list error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/clusters/details')
def get_cluster_details():
    """Get details for a specific cluster"""
    cluster_id = request.args.get('cluster-select')
    
    if not cluster_id:
        return '<p class="text-gray-500">Select a cluster to view details</p>'
    
    try:
        # Mock cluster details - in production this would query the database
        details = {
            "0": {
                "name": "Aphelios Carry",
                "size": 1250,
                "avg_placement": 3.2,
                "winrate": 18.5,
                "top4_rate": 62.4,
                "carries": ["Aphelios", "Jinx"],
                "traits": ["Sniper", "Star_Guardian"]
            },
            "1": {
                "name": "Jinx Sniper", 
                "size": 980,
                "avg_placement": 3.8,
                "winrate": 15.2,
                "top4_rate": 58.1,
                "carries": ["Jinx", "Kai'Sa"],
                "traits": ["Sniper", "Battle_Academia"]
            }
        }.get(cluster_id, {
            "name": f"Cluster {cluster_id}",
            "size": 500,
            "avg_placement": 4.0,
            "winrate": 12.5,
            "top4_rate": 50.0,
            "carries": ["Unknown"],
            "traits": ["Unknown"]
        })
        
        html = f"""
        <h3 class="text-xl font-semibold mb-4">Cluster {cluster_id}: {details['name']}</h3>
        
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div class="bg-gray-50 p-4 rounded">
                <h4 class="text-sm font-medium text-gray-600">Compositions</h4>
                <p class="text-2xl font-bold">{details['size']:,}</p>
            </div>
            <div class="bg-gray-50 p-4 rounded">
                <h4 class="text-sm font-medium text-gray-600">Avg Placement</h4>
                <p class="text-2xl font-bold">{details['avg_placement']}</p>
            </div>
            <div class="bg-gray-50 p-4 rounded">
                <h4 class="text-sm font-medium text-gray-600">Win Rate</h4>
                <p class="text-2xl font-bold">{details['winrate']}%</p>
            </div>
            <div class="bg-gray-50 p-4 rounded">
                <h4 class="text-sm font-medium text-gray-600">Top 4 Rate</h4>
                <p class="text-2xl font-bold">{details['top4_rate']}%</p>
            </div>
        </div>
        
        <div class="space-y-4">
            <div>
                <h4 class="font-medium text-gray-700 mb-2">Carry Units</h4>
                <div class="flex flex-wrap gap-2">
                    {' '.join([f'<span class="px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm">{carry}</span>' for carry in details['carries']])}
                </div>
            </div>
            <div>
                <h4 class="font-medium text-gray-700 mb-2">Common Traits</h4>
                <div class="flex flex-wrap gap-2">
                    {' '.join([f'<span class="px-2 py-1 bg-green-100 text-green-800 rounded text-sm">{trait}</span>' for trait in details['traits']])}
                </div>
            </div>
        </div>
        """
        
        return html
        
    except Exception as e:
        logger.error(f"Cluster details error: {e}")
        return f'<p class="text-red-500">Error loading cluster details: {str(e)}</p>'

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
    
    try:
        # Validate and execute query
        if not query_text.startswith('TFTQuery()') and not query_text.startswith('SimpleTFTQuery()'):
            return """
            <div class="bg-red-50 border border-red-200 rounded-lg p-4">
                <p class="text-red-800">Query must start with TFTQuery() or SimpleTFTQuery()</p>
            </div>
            """
        
        # Replace with correct class name
        safe_query = query_text.replace('SimpleTFTQuery()', 'TFTQuery()').replace('TFTQuery()', 'TFTQuery()')
        
        # Execute in safe environment
        local_vars = {'TFTQuery': TFTQuery}
        result = eval(safe_query, {"__builtins__": {}}, local_vars)
        
        if isinstance(result, dict):
            if "error" in result:
                return f"""
                <div class="bg-red-50 border border-red-200 rounded-lg p-4">
                    <h3 class="font-medium text-red-800">Query Error</h3>
                    <p class="text-red-700">{result['error']}</p>
                </div>
                """
            else:
                # Display stats result
                html = f"""
                <div class="bg-white p-6 rounded-lg shadow">
                    <h3 class="text-lg font-medium mb-4">Query Results</h3>
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div class="bg-gray-50 p-4 rounded">
                            <h4 class="text-sm font-medium text-gray-600">Play Count</h4>
                            <p class="text-2xl font-bold">{result.get('play_count', 0):,}</p>
                        </div>
                        <div class="bg-gray-50 p-4 rounded">
                            <h4 class="text-sm font-medium text-gray-600">Avg Placement</h4>
                            <p class="text-2xl font-bold">{result.get('avg_placement', 0)}</p>
                        </div>
                        <div class="bg-gray-50 p-4 rounded">
                            <h4 class="text-sm font-medium text-gray-600">Win Rate</h4>
                            <p class="text-2xl font-bold">{result.get('winrate', 0)}%</p>
                        </div>
                        <div class="bg-gray-50 p-4 rounded">
                            <h4 class="text-sm font-medium text-gray-600">Top 4 Rate</h4>
                            <p class="text-2xl font-bold">{result.get('top4_rate', 0)}%</p>
                        </div>
                    </div>
                </div>
                """
                return html
        elif isinstance(result, list):
            # Display participant results
            html = f"""
            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-lg font-medium mb-4">Query Results</h3>
                <p class="text-gray-600 mb-4">Found {len(result):,} matching compositions</p>
                
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
            """
            
            for i, p in enumerate(result[:20]):  # Limit to 20 results
                units = ', '.join([u.get('character_id', 'Unknown') for u in p.get('units', [])[:5]])
                if len(p.get('units', [])) > 5:
                    units += '...'
                
                html += f"""
                <tr>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{p.get('placement', 'N/A')}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{p.get('level', 'N/A')}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{p.get('last_round', 'N/A')}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{units}</td>
                </tr>
                """
            
            html += """
                        </tbody>
                    </table>
                </div>
            </div>
            """
            
            return html
        else:
            return f"""
            <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 class="font-medium text-blue-800">Query Result</h3>
                <pre class="text-blue-700 mt-2">{str(result)}</pre>
            </div>
            """
            
    except Exception as e:
        logger.error(f"Query execution error: {e}")
        return f"""
        <div class="bg-red-50 border border-red-200 rounded-lg p-4">
            <h3 class="font-medium text-red-800">Query Error</h3>
            <p class="text-red-700">{str(e)}</p>
        </div>
        """

@app.route('/api/upload', methods=['POST'])
def upload_data():
    """Handle data upload"""
    return """
    <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <h3 class="font-medium text-yellow-800">Upload Feature</h3>
        <p class="text-yellow-700">File upload functionality requires database connection and is not implemented in this demo version.</p>
    </div>
    """

@app.route('/api/db-status')
def get_db_status():
    """Get database status for upload tab"""
    try:
        stats = get_match_stats()
        
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
        <p class="text-sm text-gray-600 mt-4">Connected to TFT match database</p>
        """
        
        return html
        
    except Exception as e:
        return """
        <div class="text-red-500">
            <p>Database connection unavailable</p>
        </div>
        """

# Vercel serverless function handler
def handler(request):
    return app(request.environ, lambda status, headers: None)

if __name__ == '__main__':
    app.run(debug=True)