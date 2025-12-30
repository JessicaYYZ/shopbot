# ShopBot - AI Shopping Assistant

An intelligent e-commerce assistant powered by **OpenAI GPT-4o** with **12,000+ products** across fashion, electronics, beauty, and more.

## ✨ Features

### 🔍 Natural Language Search
Search products using plain English with smart filtering:
- `"Women's dresses under ₹2,000"`
- `"Blue leather wallet for men"`
- `"Gold necklace ₹5,000-₹10,000"`

### 📸 Image-Based Search
Upload any product image to find similar items:
- AI analyzes product type, color, style, and material
- Combine with text: `"Find this in black"` or `"Cheaper options"`

### 🎯 Scenario Shopping
Describe an occasion and get curated recommendations:
- `"I'm going camping next week"`
- `"Preparing for a beach vacation"`
- `"Wedding guest outfit ideas"`

### 💬 Conversational Follow-ups
Refine results naturally in conversation:
- `"Show me cheaper options"`
- `"Something more formal"`
- `"Tell me about the first one"`

### 👤 Personalized Recommendations
User profiles customize results based on gender, age, interests, and style preferences.

---

## 🚀 Quick Start

```bash
# 1. Setup environment
./setup.sh

# 2. Configure API key
echo "OPENAI_API_KEY=sk-your-key" > .env

# 3. Generate embeddings
source venv/bin/activate
python scripts/generate_embeddings.py

# 4. Start application
./run.sh
```

Open **http://localhost:3000**

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────┐
│  React Frontend (localhost:3000)                 │
│  ├── ChatInterface  → Chat UI                    │
│  ├── MessageInput   → Text + image input         │
│  ├── ProductCard    → Product display            │
│  └── Sidebar        → Help & stats               │
└──────────────────────────────────────────────────┘
                    │ REST API
                    ▼
┌──────────────────────────────────────────────────┐
│  Flask Backend (localhost:5001)                  │
│  ├── ShoppingAgent      → Orchestrator           │
│  ├── QueryProcessor     → Intent classification  │
│  ├── SearchEngine       → Vector search          │
│  └── ResponseGenerator  → AI responses           │
└──────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────┐
│  Data Layer                                      │
│  ├── SQLite         → Product metadata           │
│  ├── ChromaDB       → Vector embeddings          │
│  └── OpenAI API     → GPT-4o + Embeddings        │
└──────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
AI_Agent/
├── backend/                 # Flask REST API
│   ├── app.py              # Main application
│   └── api/                # Endpoints (chat, stats, products)
├── frontend/                # React application
│   └── src/
│       ├── components/     # UI components
│       ├── services/       # API client
│       └── styles/         # CSS
├── src/                     # Core Python modules
│   ├── core/               # Agent, search, response logic
│   ├── data/               # Database & schemas
│   └── models/             # OpenAI & vector store
├── scripts/                 # Setup & import utilities
├── data/                    # SQLite database
├── vector_store/            # ChromaDB embeddings
└── .env                     # Configuration
```

---

## 🔌 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send message with optional image and user profile |
| `/api/reset` | POST | Reset conversation history |
| `/api/stats` | GET | Get product/embedding counts |
| `/api/products` | GET | List products with filters |
| `/api/health` | GET | Health check |

---

## ⚙️ Configuration

Create a `.env` file:

```env
OPENAI_API_KEY=sk-your-key-here
DATABASE_PATH=data/products.db
VECTOR_STORE_PATH=vector_store/
FLASK_DEBUG=False
```

---

## 🛠️ Scripts

| Script | Purpose |
|--------|---------|
| `setup_db.py` | Initialize database schema |
| `import_amazon_sales_data.py` | Import product data |
| `generate_embeddings.py` | Create vector embeddings |
| `cleanup_duplicates.py` | Remove duplicate products |

---

## 🏷️ Product Categories

Clothing • Jewellery • Footwear • Watches • Electronics • Beauty • Home Decor • Kitchen • Sports • Toys

---

## 💻 Tech Stack

- **Frontend:** React 18
- **Backend:** Flask + Python
- **AI:** OpenAI GPT-4o + text-embedding-3-small
- **Database:** SQLite + ChromaDB
- **Image Analysis:** OpenAI Vision API

---

**Version:** 2.0 | **Products:** 12,000+
