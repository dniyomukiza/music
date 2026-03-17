# Picture-Word Matching Game - Pre-Generated Images System

## Overview
This system generates 3 pictures daily using Gemini API and stores them locally for the picture-word matching game. This approach provides:

- **Fast Loading**: Instant game start (no 30-second API calls)
- **Cost Efficiency**: Only 3 API calls per day vs. multiple calls per user
- **Reliability**: Works even if Gemini API is temporarily down
- **Better UX**: No waiting time for users

## Files Structure

```
glconnect/
├── static/pictures/          # Generated images stored here
├── models.py                 # PictureGameItem model added
└── routes1.py               # Updated API endpoint

generate_daily_pictures.py    # Daily generation script
setup_daily_pictures.sh      # Cron job setup script
```

## Database Schema

```sql
CREATE TABLE picture_game_items (
    id SERIAL PRIMARY KEY,
    kinyarwanda_word VARCHAR(255) NOT NULL,
    english_meaning TEXT NOT NULL,
    image_filename VARCHAR(500) NOT NULL,  -- Path to static/pictures/
    word_id INTEGER REFERENCES words_data(id),
    created_at TIMESTAMP DEFAULT NOW(),
    used_count INTEGER DEFAULT 0,         -- Track usage for rotation
    is_active BOOLEAN DEFAULT TRUE,       -- Soft deletion
    last_used TIMESTAMP                   -- Track last usage
);
```

## Setup Instructions

### 1. Run Database Migration
```bash
FLASK_APP=run.py python -m flask db upgrade
```

### 2. Setup Daily Generation
```bash
# Make setup script executable
chmod +x setup_daily_pictures.sh

# Run setup (creates cron job for 6 AM daily)
./setup_daily_pictures.sh
```

### 3. Test Manual Generation
```bash
python generate_daily_pictures.py
```

## How It Works

### Daily Generation Process
1. **Script runs at 6 AM daily** (via cron job)
2. **Batch 1: Selects 3 random Kinyarwanda words** from database
3. **Generates images using Gemini API** (currently placeholder)
4. **Pauses for 1 minute** (respectful API usage)
5. **Batch 2: Selects 3 more random words** from database
6. **Generates 3 more images** using Gemini API
7. **Stores all 6 images in `static/pictures/`**
8. **Saves metadata to database**

### Game Loading Process
1. **User clicks "Start Picture Game"**
2. **API checks for pre-generated items** (3+ available)
3. **Selects 3 items with rotation logic** (least used first)
4. **Updates usage tracking** (used_count, last_used)
5. **Returns game data instantly** (no API calls)

### Rotation Logic
- **Priority**: Items with lowest `used_count`
- **Secondary**: Items used longest ago (`last_used`)
- **Fallback**: Random selection if all items equally used

## API Endpoint Changes

### Before (Real-time Generation)
```javascript
// 30+ second loading time
const response = await fetch('/routes1/api/picture-word-game');
// Gemini API calls for each word
// Base64 image generation
// Memory intensive
```

### After (Pre-generated)
```javascript
// <1 second loading time
const response = await fetch('/routes1/api/picture-word-game');
// Instant response with stored images
// No API calls during gameplay
// Memory efficient
```

## Monitoring

### Check Generation Status
```bash
# View recent logs
tail -f daily_pictures.log

# Check generated files
ls -la glconnect/static/pictures/

# Check database records
# (Use your database client to query picture_game_items table)
```

### Manual Generation
```bash
# Generate pictures immediately
python generate_daily_pictures.py

# Check available items count
# (Query database: SELECT COUNT(*) FROM picture_game_items WHERE is_active = true)
```

## Troubleshooting

### Not Enough Pictures Error
- **Cause**: Less than 3 pre-generated items available
- **Solution**: Run `python generate_daily_pictures.py` manually
- **Prevention**: Ensure cron job is running daily

### Image Loading Issues
- **Check**: Files exist in `static/pictures/`
- **Check**: Database records have correct `image_filename`
- **Check**: Web server can serve static files

### Database Issues
- **Check**: Migration applied correctly
- **Check**: Database connection working
- **Check**: Table exists: `picture_game_items`

## Future Enhancements

1. **Real Image Generation**: Replace placeholder with actual Gemini image generation
2. **Image Optimization**: Compress images for faster loading
3. **Content Management**: Admin interface to manage generated content
4. **Analytics**: Track which pictures are most/least used
5. **Quality Control**: Review system for generated content

## Cost Analysis

### Before (Per User)
- 3 Gemini API calls per game start
- 10 users = 30 API calls
- 100 users = 300 API calls

### After (Daily)
- 6 Gemini API calls per day total (3 + pause + 3)
- 10 users = 6 API calls
- 100 users = 6 API calls
- **98% cost reduction!**

## Performance Impact

- **Loading Time**: 30+ seconds → <1 second
- **Memory Usage**: High (base64 images) → Low (file references)
- **API Reliability**: Dependent on Gemini → Independent
- **User Experience**: Poor (waiting) → Excellent (instant)
