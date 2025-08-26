---
noteId: "149d5890734111f095e8a9866d35445a"
tags: []

---

# Hugging Face Spaces Deployment Guide

## Why Hugging Face Spaces?
- **Completely FREE** - No payment information required
- **Easy deployment** - Git-based like GitHub Pages
- **Built for ML apps** - Perfect for Streamlit
- **Great performance** - Good for your TFT analysis app

## Deployment Steps

### 1. Create Account
1. Go to [huggingface.co](https://huggingface.co)
2. Sign up (free account)
3. Verify your email

### 2. Create a New Space
1. Go to [huggingface.co/new-space](https://huggingface.co/new-space)
2. Choose:
   - **Space name**: `tft-match-analysis` (or whatever you prefer)
   - **License**: Apache 2.0 (or MIT)
   - **SDK**: Streamlit
   - **Hardware**: CPU basic (free)
   - **Visibility**: Public (for free tier)

### 3. Required Files for HF Spaces
You need these specific files:

**`app.py`** (renamed from streamlit_app.py)
**`requirements.txt`** (you already have this)
**`README.md`** (auto-generated, you can customize)

### 4. Environment Variables
Set in Space Settings > Variables:
- `DATABASE_URL`: Your Supabase connection string
- `ENVIRONMENT`: production

### 5. Deploy Options

**Option A: Git Push (Recommended)**
```bash
# Clone your space repository
git clone https://huggingface.co/spaces/YOUR_USERNAME/tft-match-analysis
cd tft-match-analysis

# Copy your files (I'll help create the right structure)
# Push to HF
git add .
git commit -m "Initial deployment"
git push
```

**Option B: File Upload**
- Upload files directly through the web interface

## Limitations to Consider
- **Compute limits**: May time out on very large operations
- **Memory limits**: 16GB RAM on free tier
- **No background jobs**: Can't run continuous data collection
- **Cold starts**: App sleeps after inactivity

## Would you like me to create the HF-specific files?