---
noteId: "6aa69190824911f09c8005f6366662c3"
tags: []

---

# TFT Webapp HTMX Frontend

Modern web frontend for TFT composition analysis using HTMX and Tailwind CSS, deployable on Vercel.

## Features

- **Modern UI**: Clean, responsive design with Tailwind CSS
- **Interactive**: HTMX-powered dynamic content loading
- **Fast**: Server-side rendering with minimal JavaScript
- **Scalable**: Vercel serverless deployment

## Architecture

### Frontend (`index.html`)
- Single-page application with tab-based navigation
- HTMX for dynamic content loading
- Tailwind CSS for styling
- Minimal vanilla JavaScript for tab switching

### Backend (`api/index.py`)
- Flask-based REST API
- Serverless functions for Vercel
- Reuses existing database connection logic
- Returns HTML fragments for HTMX

### Database Integration
- Uses existing `simple_database.py` module
- Graceful fallback when database unavailable
- Same query interface as Streamlit version

## Deployment to Vercel

### Prerequisites
```bash
npm install -g vercel
```

### Deploy
```bash
vercel --prod
```

### Environment Variables
Set in Vercel dashboard:
- `DATABASE_URL` - PostgreSQL connection string

## Local Development

### Setup
```bash
pip install -r requirements-vercel.txt
python api/index.py
```

### Access
- Open `http://localhost:5000`
- API endpoints at `/api/*`

## File Structure

```
├── index.html           # Main HTML page
├── api/
│   └── index.py        # Flask API endpoints
├── vercel.json         # Vercel configuration
├── requirements-vercel.txt  # Python dependencies
├── simple_database.py  # Database connection (reused)
└── querying.py         # Query system (reused)
```

## API Endpoints

- `GET /` - Main HTML page
- `GET /api/status` - Database connection status
- `GET /api/stats` - Database statistics
- `GET /api/clusters/list` - Available clusters
- `GET /api/clusters/details` - Cluster details
- `POST /api/query` - Execute TFT query
- `POST /api/upload` - Data upload (placeholder)
- `GET /api/db-status` - Database status for upload tab

## Features Implemented

### ✅ Complete
- Overview tab with database status and statistics
- Query interface with documentation
- Responsive design
- Error handling
- HTMX integration

### ⚠️ Partial (Mock Data)
- Cluster analysis (uses mock data, needs database tables)
- Upload functionality (placeholder implementation)

### 🔄 Extensible
- Can add more query types
- Can integrate with existing clustering system
- Can add real-time features with WebSockets

## Advantages over Streamlit

1. **Performance**: Faster loading, no Python runtime on client
2. **Deployment**: Native Vercel support, better CDN integration
3. **Customization**: Full control over UI/UX
4. **Cost**: More cost-effective for high traffic
5. **SEO**: Better search engine optimization
6. **Mobile**: Better mobile experience

## Migration Notes

- All core query functionality preserved
- Same database backend
- Similar user interface
- Added mock data for demo purposes
- Ready for production with database connection