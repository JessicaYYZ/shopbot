# ShopBot - AI Shopping Assistant

An intelligent e-commerce assistant powered by **OpenAI GPT-4o** with **20,000+ Flipkart products**.

---

## Quick Access
### DEMO VIDEO: [Watch on Google Drive](https://drive.google.com/file/d/1Tf0EREGZ66N13l8X7WrL1teqCvQyF7Nm/view?usp=sharing)

### AGENT API: [AGENT_API.md](docs/AGENT_API.md)

---

## Features

**Natural Language Search**

- Smart entity extraction (category, gender, price, color, brand)
- Example: `"Women's dresses under ₹2,000"`

**Image-Based Search**

- OpenAI Vision API analyzes product images
- Hybrid search combining image understanding with text intent
- Follow-up support: `"Find this in black"` or `"Cheaper options"`

**Scenario Shopping**

- Curated recommendations for occasions
- Example: `"I'm going camping next week"`
- Item refinement: `"Replace the first one with something cheaper"`

**Conversational Follow-ups**

- Multi-turn conversation with context preservation
- Price/style refinement, product discussion, attribute filtering

**Personalized Recommendations**

- Gender enforcement for fashion categories
- Customization based on age, interests, budget, and preferences

---

## Quick Start

**Prerequisites:** Python 3.10+, Node.js 16+, OpenAI API key

```bash
# 1. Clone and setup
git clone <your-repo-url>
cd AI_Agent
./setup.sh

# 2. Configure environment
echo "OPENAI_API_KEY=sk-your-key-here" > .env
echo "DATABASE_PATH=data/flipkart_products.db" >> .env
echo "VECTOR_STORE_PATH=vector_store_flipkart/" >> .env

# 3. Import dataset and generate embeddings
source venv/bin/activate
python scripts/import_flipkart_dataset.py
python scripts/generate_embeddings.py  # ~10-15 minutes

# 4. Start application
./run.sh
```

**URLs:** Frontend - http://localhost:3000 | Backend API - http://localhost:5001

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  React Frontend (localhost:3000)                             │
│  ├── ChatInterface, MessageInput, MessageList                │
│  ├── ProductCard, Sidebar                                    │
└──────────────────────────────────────────────────────────────┘
                        │ REST API (CORS)
                        ▼
┌──────────────────────────────────────────────────────────────┐
│  Flask Backend (localhost:5001)                              │
│  ├── /api/chat, /api/reset, /api/stats, /api/products       │
└──────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│  Core Agent System                                           │
│  ├── ShoppingAgent (orchestrator + ConversationManager)      │
│  ├── IntentClassifier, QueryProcessor, FollowUpAnalyzer      │
│  ├── ScenarioProcessor, SearchEngine, ResponseGenerator      │
└──────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│  Data Layer                                                  │
│  ├── SQLite (flipkart_products.db)                           │
│  ├── ChromaDB (vector_store_flipkart/)                       │
│  ├── OpenAI GPT-4o (intent, entities, responses)            │
│  ├── OpenAI GPT-4o-mini (vision)                            │
│  └── text-embedding-3-small (embeddings)                    │
└──────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
AI_Agent/
├── backend/           # Flask REST API
│   ├── app.py        # Main application
│   └── api/          # Endpoints
├── docs/             # Technical documentation
├── frontend/         # React application
│   └── src/
│       ├── components/
│       ├── services/
│       └── styles/
├── src/              # Core Python modules
│   ├── core/         # Agent, search, response logic
│   ├── data/         # Database & schemas
│   └── models/       # OpenAI & vector store
├── scripts/          # Setup & import utilities
├── data/             # SQLite database
└── vector_store_flipkart/  # ChromaDB embeddings
```

---

## API Reference

For a detailed breakdown of the internal agent logic, search mechanisms, and multi-modal processing, see the **[Agent API Documentation](docs/AGENT_API.md)**.

### POST /api/chat

**Request:**

```json
{
  "message": "Show me running shoes",
  "image": "base64_encoded_image (optional)",
  "user_profile": {
    "name": "Jessica",
    "gender": "female",
    "age": 25,
    "interests": ["fitness", "fashion"],
    "preferences": "modern style",
    "budget": "mid-range"
  }
}
```

**Response:**

```json
{
  "success": true,
  "response": "Here are some great running shoes...",
  "products": [
    {
      "id": "FLP001",
      "title": "Nike Air Zoom Pegasus",
      "price": 5499.0,
      "rating": 4.5,
      "category": "Sports Shoes",
      "brand": "Nike",
      "product_url": "https://flipkart.com/..."
    }
  ]
}
```

### Other Endpoints

| Endpoint        | Method | Description                             |
| --------------- | ------ | --------------------------------------- |
| `/api/reset`    | POST   | Reset conversation history              |
| `/api/stats`    | GET    | Product counts and embedding statistics |
| `/api/products` | GET    | List products with filters              |
| `/api/health`   | GET    | Health check                            |

---

## Configuration

Create `.env` file:

```env
OPENAI_API_KEY=sk-your-key-here
DATABASE_PATH=data/flipkart_products.db
VECTOR_STORE_PATH=vector_store_flipkart/
FLASK_DEBUG=False
```

---

## Available Scripts

| Script                       | Purpose                    |
| ---------------------------- | -------------------------- |
| `setup.sh`                   | Install dependencies       |
| `run.sh`                     | Start backend + frontend   |
| `import_flipkart_dataset.py` | Import ~20K products       |
| `generate_embeddings.py`     | Generate vector embeddings |
| `cleanup_duplicates.py`      | Remove duplicates          |

---

## Tech Stack

**Frontend:** React 18, Fetch API
**Backend:** Flask 3.0, Flask-CORS, Pydantic
**AI/ML:** OpenAI GPT-4o, GPT-4o-mini Vision, text-embedding-3-small
**Database:** SQLite, ChromaDB
**Libraries:** Pillow, pandas, numpy, python-dotenv

---

## Dataset

**Source:** Flipkart E-commerce Dataset
**Products:** ~20,000 items from Flipkart Products (https://www.kaggle.com/datasets/PromptCloudHQ/flipkart-products)
**Categories:** Fashion, Footwear, Accessories, Beauty, Electronics, Home & Lifestyle, Sports

**Data:** Product names, descriptions, specifications, category hierarchy, pricing, brand info, images, URLs

---
