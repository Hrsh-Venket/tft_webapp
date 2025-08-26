---
noteId: "7c9afb70825811f09c8005f6366662c3"
tags: []

---

# TFT Webapp - Node.js Backend API

A complete, pure Node.js backend API for the TFT (Teamfight Tactics) Composition Analysis webapp. Built with zero external dependencies following KISS principles, designed to work seamlessly with the existing HTMX frontend.

## 🚀 Features

- **Zero Dependencies**: Pure Node.js implementation with no external packages
- **HTMX Compatible**: Returns HTML fragments for seamless frontend integration
- **Complete API**: All endpoints needed for the TFT webapp
- **Mock Data**: Comprehensive demo data for testing and development
- **CORS Support**: Proper cross-origin request handling
- **Error Handling**: Robust error responses and logging
- **Clean Code**: Well-commented, maintainable codebase

## 📡 API Endpoints

### GET Endpoints
- `GET /` - Main HTML page (serves index.html)
- `GET /api/status` - Database connection status (HTML fragment)
- `GET /api/stats` - Statistics cards (HTML fragment)
- `GET /api/clusters/list` - Available clusters (JSON)
- `GET /api/clusters/details?cluster-select=ID` - Cluster details (HTML fragment)
- `GET /api/db-status` - Database status for upload tab (HTML fragment)

### POST Endpoints
- `POST /api/query` - Execute TFT query (HTML fragment)
- `POST /api/upload` - File upload simulation (HTML fragment)

## 🛠 Quick Start

### Prerequisites
- Node.js 14 or higher
- The `index.html` file in the same directory

### Installation & Run
```bash
# No dependencies to install!
npm test          # Verify server loads correctly
npm start         # Start the server
# or
node server.js    # Direct execution
```

### Development
```bash
npm run dev       # Same as start, for development
```

The server will start on `http://localhost:3000` by default.

## 🎯 Usage Examples

### Basic Usage
```javascript
// The server handles all HTMX requests automatically
// Just point your HTMX frontend to the running server
```

### Environment Configuration
```bash
# Optional environment variables
PORT=3000          # Server port (default: 3000)
HOST=localhost     # Server host (default: localhost)
NODE_ENV=production # Environment mode
```

### Testing Endpoints
```bash
# Test status endpoint
curl http://localhost:3000/api/status

# Test stats endpoint  
curl http://localhost:3000/api/stats

# Test clusters list
curl http://localhost:3000/api/clusters/list

# Test query endpoint
curl -X POST -d "query=SimpleTFTQuery().add_unit('Aphelios').get_stats()" \
     http://localhost:3000/api/query
```

## 📊 Mock Data Structure

The API includes comprehensive mock data for demonstration:

### Statistics
- Total matches: 12,847
- Total participants: 102,776
- Average players per match: 8.0

### Clusters (5 samples)
- Aphelios Carry (1,250 compositions)
- Jinx Sniper (980 compositions)  
- Star Guardian (850 compositions)
- Vanguard Tank (720 compositions)
- Battle Academia (650 compositions)

### Query Results
- Statistics responses (play count, placement, winrates)
- Participant data with units and match details

## 🔧 Architecture

### Code Structure
```
server.js           # Main server file
├── Mock Data       # Sample data for all endpoints
├── Utility Functions # Request parsing, CORS, responses
├── Route Handlers  # Individual endpoint logic
├── Request Router  # URL routing and method handling
└── Server Init     # Startup and shutdown logic
```

### Design Principles
- **KISS**: Keep it simple and straightforward
- **Zero Dependencies**: Only uses Node.js built-in modules
- **HTMX First**: Optimized for HTMX frontend consumption
- **Error Resilient**: Comprehensive error handling
- **Logging**: Console logging for debugging and monitoring

## 🎮 TFT Query System

The API supports TFT query simulation with these formats:

### Statistics Queries
```javascript
SimpleTFTQuery().add_unit('Aphelios').get_stats()
TFTQuery().add_trait('Sniper', 2).get_stats()
```

### Participant Queries
```javascript
SimpleTFTQuery().add_unit('Jinx').get_participants()
TFTQuery().add_player_level(8, 10).get_participants()
```

### Supported Methods
- `add_unit(unit_name)` - Filter by unit presence
- `add_trait(trait_name, tier)` - Filter by trait tier
- `add_player_level(min, max)` - Filter by player level
- `get_stats()` - Return aggregated statistics
- `get_participants()` - Return individual match data

## 🔄 HTMX Integration

The API is specifically designed for HTMX:

- Returns HTML fragments, not full pages
- Proper content-type headers (`text/html`)
- HTMX-friendly error messages
- No-cache headers for dynamic content
- CORS headers for cross-origin requests

## 📈 Production Considerations

### Database Integration
Replace mock data with real database calls:

```javascript
// Replace mockData.stats with:
const stats = await database.getMatchStatistics();

// Replace mockData.clusters with:
const clusters = await database.getClusters();
```

### Environment Variables
```bash
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
API_KEY=your-api-key
```

### Performance
- Add request logging middleware
- Implement caching for expensive operations
- Add rate limiting for public APIs
- Use connection pooling for database operations

### Security
- Add request validation
- Implement authentication/authorization
- Sanitize user inputs
- Add HTTPS in production

## 🐛 Error Handling

The API provides consistent error responses:

```html
<div class="bg-red-50 border border-red-200 rounded-lg p-4">
  <h3 class="font-medium text-red-800">Error</h3>
  <p class="text-red-700">Error message here</p>
</div>
```

## 📝 Logging

Console logging includes:
- Request method and URL
- Endpoint-specific actions
- Query processing details
- Error messages with context

## 🚀 Deployment

### Local Development
```bash
node server.js
# Server starts on http://localhost:3000
```

### Production Deployment
- Works with any Node.js hosting platform
- No build step required
- Zero dependencies to install
- Scales horizontally with load balancers

### Docker Support
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]
```

## 🤝 Contributing

The codebase follows these conventions:
- ESLint standard configuration
- Detailed commenting for all functions
- Consistent error handling patterns
- HTMX-first response design

## 📄 License

MIT License - see LICENSE file for details.

---

**Built with ⚔️ for TFT composition analysis**

This API replaces the Python Flask backend with a clean, efficient Node.js implementation while maintaining full compatibility with the existing HTMX frontend.