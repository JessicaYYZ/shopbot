# ShopBot - AI Shopping Assistant

> **🎥 DEMO VIDEO**
>
> **Watch ShopBot in action:** [**View Demo on Google Drive**](https://drive.google.com/file/d/1Tf0EREGZ66N13l8X7WrL1teqCvQyF7Nm/view?usp=sharing)
>
> See how ShopBot handles natural language search, image-based shopping, scenario planning, and personalized recommendations!

---

An intelligent e-commerce assistant powered by **OpenAI GPT-4o** with **20,000+ Flipkart products** across fashion, electronics, beauty, home & lifestyle, and more.

## ✨ Features

### 🔍 Natural Language Search

Search products using plain English with smart entity extraction and filtering:

- `"Women's dresses under ₹2,000"`
- `"Blue leather wallet for men"`
- `"Running shoes for sports"`
- Automatically extracts: category, gender, price range, color, brand, and more

### 📸 Image-Based Search

Upload any product image to find similar items using OpenAI Vision API:

- AI analyzes product type, color, style, material, and pattern
- Hybrid search combines image understanding with text intent
- Combine with text: `"Find this in black"` or `"Cheaper options"`
- Follow-up queries maintain product type consistency

### 🎯 Scenario Shopping

Describe an occasion and get curated recommendations:

- `"I'm going camping next week"` → Tent, sleeping bag, flashlight, etc.
- `"Preparing for a beach vacation"` → Swimwear, sunglasses, sunscreen
- `"Wedding guest outfit ideas"` → Formal wear, accessories, shoes
- Refine individual items: `"Replace the first one with something cheaper"`

### 💬 Conversational Follow-ups

Refine results naturally through multi-turn conversations:

- `"Show me cheaper options"` → Price refinement
- `"Something more formal"` → Style refinement
- `"Tell me about the first one"` → Product discussion
- `"Show me in different colors"` → Attribute refinement

### 👤 Personalized Recommendations

User profiles customize results based on:

- **Gender enforcement** for fashion/apparel categories
- Age, interests, and style preferences
- Budget level and shopping habits

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 16+
- OpenAI API key

### Installation & Setup

```bash
# 1. Clone repository
git clone <your-repo-url>
cd AI_Agent

# 2. Setup environment and install dependencies
./setup.sh

# 3. Configure API key
echo "OPENAI_API_KEY=sk-your-key-here" > .env
echo "DATABASE_PATH=data/flipkart_products.db" >> .env
echo "VECTOR_STORE_PATH=vector_store_flipkart/" >> .env

# 4. Import Flipkart dataset
source venv/bin/activate
python scripts/import_flipkart_dataset.py

# 5. Generate embeddings (takes ~10-15 minutes for 20K products)
python scripts/generate_embeddings.py

# 6. Start application (backend + frontend)
./run.sh
```

Open **http://localhost:3000** (Frontend)  
API: **http://localhost:5001** (Backend)

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  React Frontend (localhost:3000)                             │
│  ├── ChatInterface      → Main chat UI with message history  │
│  ├── MessageInput       → Text + image upload + user profile │
│  ├── MessageList        → Conversation display               │
│  ├── ProductCard        → Product display with details       │
│  └── Sidebar            → Help panel & statistics            │
└──────────────────────────────────────────────────────────────┘
                              │ REST API (CORS enabled)
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Flask Backend (localhost:5001)                              │
│  ├── /api/chat          → Process messages & images          │
│  ├── /api/reset         → Reset conversation                 │
│  ├── /api/stats         → Product counts & metrics           │
│  └── /api/products      → List/filter products               │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Core Agent System                                           │
│  ├── ShoppingAgent           → Main orchestrator             │
│  │   ├── ConversationManager → History & context tracking    │
│  │   └── process()           → Route to appropriate handler  │
│  ├── IntentClassifier        → Classify user intent          │
│  ├── QueryProcessor          → Extract entities & filters    │
│  ├── FollowUpAnalyzer        → Detect follow-up queries      │
│  ├── ScenarioProcessor       → Handle scenario shopping      │
│  ├── SearchEngine            → Hybrid & vector search        │
│  └── ResponseGenerator       → Generate AI responses         │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Data Layer                                                  │
│  ├── SQLite (flipkart_products.db)                           │
│  │   └── Products, specs, reviews, metadata                  │
│  ├── ChromaDB (vector_store_flipkart/)                       │
│  │   └── Text embeddings for semantic search                 │
│  └── OpenAI API                                              │
│      ├── GPT-4o → Intent, entities, responses                │
│      ├── GPT-4o-mini → Vision analysis                       │
│      └── text-embedding-3-small → Vector embeddings          │
└──────────────────────────────────────────────────────────────┘
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

### Chat API

**POST** `/api/chat`

Send a message with optional image and user profile.

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
    "budget": "mid-range",
    "style": "sporty"
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
      "review_count": 234,
      "category": "Sports Shoes",
      "brand": "Nike",
      "image_path": "https://...",
      "description": "...",
      "product_url": "https://flipkart.com/...",
      "reviews": [...]
    }
  ]
}
```

### Other Endpoints

| Endpoint        | Method | Description                                 |
| --------------- | ------ | ------------------------------------------- |
| `/api/reset`    | POST   | Reset conversation history                  |
| `/api/stats`    | GET    | Get product counts and embedding statistics |
| `/api/products` | GET    | List products with optional filters         |
| `/api/health`   | GET    | Health check endpoint                       |

---

## ⚙️ Configuration

Create a `.env` file in the project root:

```env
# Required
OPENAI_API_KEY=sk-your-key-here

# Database paths (defaults to Flipkart)
DATABASE_PATH=data/flipkart_products.db
VECTOR_STORE_PATH=vector_store_flipkart/

# Optional
FLASK_DEBUG=False
FLASK_SECRET_KEY=your-secret-key
```

---

## 🛠️ Available Scripts

| Script                       | Purpose                                       | Usage                                       |
| ---------------------------- | --------------------------------------------- | ------------------------------------------- |
| `setup.sh`                   | Install dependencies & setup environment      | `./setup.sh`                                |
| `run.sh`                     | Start backend + frontend servers              | `./run.sh`                                  |
| `setup_db.py`                | Initialize database schema                    | `python scripts/setup_db.py`                |
| `import_flipkart_dataset.py` | Import Flipkart product data (~20K products)  | `python scripts/import_flipkart_dataset.py` |
| `generate_embeddings.py`     | Generate vector embeddings (batch processing) | `python scripts/generate_embeddings.py`     |
| `cleanup_duplicates.py`      | Remove duplicate products from database       | `python scripts/cleanup_duplicates.py`      |

---

## 🏷️ Product Categories

**Fashion & Apparel:** Men's Clothing, Women's Clothing, Kids' Wear, Ethnic Wear, Western Wear, Shirts, T-shirts, Jeans, Dresses

**Footwear:** Sports Shoes, Formal Shoes, Sandals, Casual Shoes, Sneakers

**Accessories:** Watches, Jewellery, Bags & Wallets, Sunglasses, Belts

**Beauty & Personal Care:** Makeup, Skincare, Fragrances, Hair Care, Health Products

**Electronics:** Mobile Phones, Laptops, Cameras, Audio Devices, Smart Watches

**Home & Lifestyle:** Furniture, Kitchen Appliances, Home Decor, Bedding

**Sports & Fitness:** Gym Equipment, Sports Apparel, Outdoor Gear

---

## 💻 Tech Stack

**Frontend:**

- React 18 with Hooks
- Modern CSS with responsive design
- Fetch API for REST communication

**Backend:**

- Flask 3.0 (Python REST API)
- Flask-CORS for cross-origin support
- Pydantic for data validation

**AI & ML:**

- OpenAI GPT-4o (intent classification, entity extraction, response generation)
- OpenAI GPT-4o-mini with Vision (image analysis)
- text-embedding-3-small (vector embeddings)

**Data Storage:**

- SQLite (product metadata, specifications, reviews)
- ChromaDB (vector embeddings for semantic search)

**Key Libraries:**

- Pillow (image processing)
- pandas, numpy (data processing)
- python-dotenv (configuration)

---

## 📊 Dataset Information

**Source:** Flipkart E-commerce Dataset  
**Products:** ~20,000 items  
**File:** `flipkart_com-ecommerce_sample.csv`

**Data Fields:**

- Product name, description, specifications
- Category hierarchy (main → sub → item)
- Pricing (retail + discounted)
- Brand information
- Product images & URLs
- Rich product specifications

---

## 🎯 Key Features Implementation

### 1. **Hybrid Search**

Combines semantic vector search with metadata filtering for optimal results.

### 2. **Conversation Memory**

Maintains context across turns to handle follow-up queries naturally.

### 3. **Intent Classification**

Automatically detects: product search, general chat, scenario shopping, or follow-ups.

### 4. **Entity Extraction**

Extracts structured filters from natural language:

- Category, gender, price range
- Colors, brands, materials
- Sizes, styles, occasions

### 5. **User Profile Integration**

Gender enforcement for fashion, personalized recommendations based on preferences.

### 6. **Image Understanding**

Vision API analyzes uploaded images to understand product attributes and find similar items.

---

**Version:** 2.0 | **Products:** 20,000+ from Flipkart | **Updated:** December 2025
