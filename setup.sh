#!/bin/bash

# ShopBot - Complete Setup Script
# This script sets up both backend and frontend

echo "🚀 ShopBot Complete Setup Script"
echo "================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✅ Python found: $(python3 --version)"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16 or higher."
    exit 1
fi

echo "✅ Node.js found: $(node --version)"
echo ""

# ==== BACKEND SETUP ====
echo "📦 Setting up Backend..."
echo "------------------------"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Backend dependencies installed"
echo ""

# ==== FRONTEND SETUP ====
echo "⚛️  Setting up Frontend..."
echo "------------------------"

cd frontend

# Install Node.js dependencies
echo "Installing Node.js dependencies..."
npm install

echo "✅ Frontend dependencies installed"
cd ..
echo ""

# ==== DATABASE SETUP ====
echo "🗄️  Setting up Database..."
echo "------------------------"

# Setup database schema
python scripts/setup_db.py

# Create sample data
python scripts/create_sample_data.py

echo "✅ Database setup complete"
echo ""

# ==== ENVIRONMENT SETUP ====
echo "⚙️  Setting up Environment..."
echo "------------------------"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    if [ -f "env_template.txt" ]; then
        cp env_template.txt .env
        echo "⚠️  Please edit .env and add your OPENAI_API_KEY"
    else
        echo "⚠️  env_template.txt not found. Please create .env manually."
    fi
else
    echo "✅ .env file already exists"
fi

echo ""

# ==== SUMMARY ====
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Add your OpenAI API key to .env file:"
echo "   OPENAI_API_KEY=your-api-key-here"
echo ""
echo "2. Generate embeddings (one-time, ~\$0.01):"
echo "   python scripts/generate_embeddings.py"
echo ""
echo "3. Start the application:"
echo "   ./run.sh"
echo ""
echo "   OR start manually:"
echo "   - Backend:  python backend/app.py"
echo "   - Frontend: cd frontend && npm start"
echo ""
echo "4. Open your browser:"
echo "   http://localhost:3000"
echo ""

