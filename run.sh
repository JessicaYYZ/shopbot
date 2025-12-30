#!/bin/bash

# ShopBot - Run Script
# Stops any existing processes and starts both backend and frontend servers

echo "🚀 Starting ShopBot..."
echo "====================="
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Stop any existing processes first
echo "🛑 Stopping any existing ShopBot processes..."
pkill -f "python.*backend/app.py" 2>/dev/null && echo "   ✅ Stopped existing backend" || echo "   ℹ️  No existing backend running"
pkill -f "npm.*start" 2>/dev/null && echo "   ✅ Stopped existing frontend" || echo "   ℹ️  No existing frontend running"
pkill -f "node.*react-scripts" 2>/dev/null  # Kill React dev server
sleep 2
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please run ./setup.sh first"
    exit 1
fi

# Check if OpenAI API key is set
if ! grep -q "OPENAI_API_KEY=sk-" .env 2>/dev/null; then
    echo "⚠️  Warning: OPENAI_API_KEY not set in .env file"
    echo "Some features may not work without it."
    echo ""
fi

# Check database - Flipkart is the default
if [ ! -f "data/flipkart_products.db" ]; then
    echo "❌ Database not found!"
    echo "Run: python scripts/import_flipkart_dataset.py"
    exit 1
fi

# Check if embeddings exist - Flipkart vector store is the default
if [ ! -d "vector_store_flipkart" ] || [ ! -f "vector_store_flipkart/chroma.sqlite3" ]; then
    echo "⚠️  Warning: No embeddings found"
    echo "Run: python scripts/generate_embeddings.py"
    echo ""
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down ShopBot..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        echo "   ✅ Backend stopped"
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        # Also kill the npm process
        pkill -P $FRONTEND_PID 2>/dev/null
        echo "   ✅ Frontend stopped"
    fi
    exit 0
}

trap cleanup SIGINT SIGTERM

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run ./setup.sh first"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Start backend
echo "🔧 Starting Backend API (http://localhost:5001)..."
python backend/app.py > backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
echo "   Waiting for backend to initialize..."
sleep 5

# Check backend logs for embedding count
if grep -q "✅ Found [1-9][0-9]* embeddings" backend.log; then
    EMBEDDING_COUNT=$(grep "✅ Found" backend.log | grep "embeddings" | grep -o "[0-9]*" | tail -1)
    echo "   ✅ Loaded $EMBEDDING_COUNT embeddings"
else
    echo "   ⚠️  Warning: No embeddings loaded!"
    echo "   Run: python scripts/generate_embeddings.py"
fi

# Check if backend is running
if ! curl -s http://localhost:5001/api/health > /dev/null 2>&1; then
    echo "❌ Backend failed to start!"
    echo "Check backend.log for errors"
    cat backend.log
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo "   ✅ Backend is running!"

# Start frontend
echo "⚛️  Starting Frontend (http://localhost:3000)..."
cd frontend
npm start > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ ShopBot is running!"
echo "====================="
echo ""
echo "📍 Frontend: http://localhost:3000"
echo "📍 Backend API: http://localhost:5001"
echo ""
echo "📋 Logs:"
echo "   Backend:  tail -f backend.log"
echo "   Frontend: tail -f frontend.log"
echo ""
echo "💡 Tip: If you don't see products, make sure embeddings are generated:"
echo "   python scripts/generate_embeddings.py"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Wait for processes
wait

