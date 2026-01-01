# ShopBot Agent API Documentation

Technical reference for the agent API, internal processing pipeline, search mechanisms, and system architecture.

---

### Chat & Conversation

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/chat` | Main conversational endpoint for text, image, and profile-based queries |
| `POST` | `/api/reset` | Clear conversation history and start fresh session |

#### POST /api/chat

**Request:**
```json
{
  "message": "Show me blue running shoes under 2000",
  "image": "data:image/jpeg;base64,/9j/4AAQ...",
  "user_profile": {
    "name": "Jessica",
    "gender": "female",
    "age": 25,
    "interests": ["fitness", "fashion"],
    "budget": "mid-range"
  }
}
```
- `message`: Text query (optional if image provided)
- `image`: Base64-encoded image (optional)
- `user_profile`: User context for personalization (optional)

**Response:**
```json
{
  "success": true,
  "response": "Here are some running shoes for you...",
  "products": [
    {
      "id": 123,
      "title": "Nike Air Zoom",
      "price": 1999.0,
      "category": "Sports Shoes",
      "brand": "Nike",
      "image_path": "https://...",
      "product_url": "https://flipkart.com/..."
    }
  ]
}
```

#### POST /api/reset

**Request:** Empty body

**Response:**
```json
{
  "success": true,
  "message": "Conversation reset successfully"
}
```

---

### Product Data

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/products` | List products with optional filters |
| `GET` | `/api/products/{id}` | Get single product by ID |
| `GET` | `/api/categories` | Get all available categories |

#### GET /api/products

**Query Parameters:**
- `category` (string): Filter by category
- `min_price` (float): Minimum price
- `max_price` (float): Maximum price
- `limit` (int): Result count (default: 50)

**Example:**
```
GET /api/products?category=Footwear&max_price=2000&limit=10
```

---

### System

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/stats` | Product count, embedding count, category count |
| `GET` | `/api/health` | Service health check |

---

## Agent Processing Pipeline

The `ShoppingAgent.process()` method routes requests based on input type and conversation state.

```
                        User Input
                            │
                            ▼
                   ┌────────────────┐
                   │ Image Present? │
                   └────────────────┘
                     │ Yes      │ No
                     ▼          ▼
              ┌──────────┐  ┌──────────────────┐
              │  Image   │  │ Scenario Active? │
              │  Search  │  └──────────────────┘
              └──────────┘    │ Yes        │ No
                              ▼            ▼
                    ┌──────────────┐  ┌────────────────┐
                    │  Scenario    │  │ Has History?   │
                    │  Refinement? │  └────────────────┘
                    └──────────────┘    │ Yes      │ No
                      │ Yes    │ No     ▼          │
                      ▼        │   ┌───────────┐   │
              ┌────────────┐   │   │ Follow-up │   │
              │  Scenario  │   │   │ Analysis  │   │
              │ Refinement │   │   └───────────┘   │
              └────────────┘   │        │          │
                               └────────┼──────────┘
                                        ▼
                            ┌───────────────────────┐
                            │   Intent Router       │
                            ├───────────────────────┤
                            │ • general_conversation│
                            │ • product_search      │
                            │ • scenario_shopping   │
                            │ • product_discussion  │
                            │ • refine_search       │
                            │ • image_followup      │
                            └───────────────────────┘
                                        │
                                        ▼
                               Search & Response
                                        │
                                        ▼
                              Update History & Return
```

### Routing Logic

1. **Image Present**: Routes directly to `handle_image_search` (hybrid search)
2. **Active Scenario**: Checks for item replacement requests (e.g., "replace the first one")
3. **Has History**: Analyzes if query is a follow-up:
   - **Image context preserved**: Routes to `handle_image_search_followup`
   - **Text context**: Routes to `handle_search_refinement` or `handle_product_discussion`
4. **New Query**: Intent classification determines handler:
   - `general_conversation`: Greetings, help, non-shopping
   - `product_search`: Specific product requests
   - `scenario_shopping`: Event-based multi-product recommendations

---

## Search Mechanisms

### Text Search
```
Query → Entity Extraction → Embedding → ChromaDB → SQLite → Filter → Products
```
Extracts: `category`, `price_min/max`, `brand`, `color`, `gender`, `material`

### Image Search (Hybrid)
```
Image + Text
      │
      ▼
┌─────────────────────────────────────────────────┐
│ 1. GPT-4o Vision → Product Description          │
│    (type, demographic, colors, style, keywords) │
│                                                 │
│ 2. Description → Embedding → Vector Search      │
│                                                 │
│ 3. LLM extracts text modifications              │
│    (color, price_preference, style, material)   │
│                                                 │
│ 4. Apply modifications as filters               │
│                                                 │
│ 5. Apply profile-based gender filtering         │
└─────────────────────────────────────────────────┘
      │
      ▼
  Products (product type from image preserved)
```

### Image Follow-up
Stores `image_description` in conversation context. Follow-ups like "show me in black" reuse the stored description to maintain product type consistency without re-uploading the image.

### Scenario Shopping
```
"I'm going camping" → GPT-4o identifies 5 categories
                           │
                           ▼
                   [hiking shoes, backpack, tent, sleeping bag, flashlight]
                           │
                           ▼
                   Search best product per category
                           │
                           ▼
                   Store state for refinements
```
Supports item replacement: "Replace the first one with something cheaper"

---

## Query Processing

| Component | Function |
|-----------|----------|
| `IntentClassifier` | GPT-4o classifies: `general_conversation`, `product_search`, `scenario_shopping` |
| `FollowUpAnalyzer` | Determines: `new_search`, `refine_search`, `product_discussion`, `general_chat` |
| `QueryProcessor` | Extracts entities (price, color, brand, gender) from text |
| `ScenarioProcessor` | Identifies event categories and parses refinement requests |

---

## Personalization

### Gender Enforcement
For fashion-related queries, profile gender automatically filters results:
- Female profile → women's products
- Male profile → men's products

### Profile Filter Context
```python
{
  "gender_include": ["women", "women's", "ladies"],
  "gender_exclude": ["men", "men's", "male"],
  "age_group": "young_adult"
}
```

---

## Response Generation

The `ResponseGenerator` synthesizes natural language responses using GPT-4o.

### Response Types

| Method | Use Case |
|--------|----------|
| `generate_general_response` | Greetings, help, non-shopping queries |
| `generate_product_response` | Text-based product search results |
| `generate_image_search_response` | Image-based search results |
| `generate_refinement_response` | Refined/filtered search results |
| `generate_product_discussion_response` | Q&A about previously shown products |
| `generate_scenario_response` | Multi-product scenario recommendations |
| `generate_scenario_refinement_response` | Updated scenario after item replacement |

### Product Context Formatting

Products are formatted for LLM with strict labeling to prevent hallucination:
```
EXACT TITLE: Nike Air Zoom Pegasus
EXACT PRICE: ₹5,499 (MRP: ₹7,999, 31% off)
Category: Sports Shoes
Brand: Nike
Specifications: Ideal For: Men | Type: Running | Material: Mesh
```
- Max 5 products included per response
- Titles truncated to 80 chars, descriptions to 120 chars

### Hallucination Prevention

1. **Temperature**: Set to 0.3 for deterministic output
2. **Explicit Instructions**: LLM prompted to use EXACT titles and prices only
3. **Validation**: `_validate_response()` checks if first 20 chars of any product title appears in response; appends warning with actual products if not found
4. **Boundary Markers**: Products wrapped with clear delimiters (`===`) and "DO NOT recommend products not listed above"

### Personalization Injection

When `user_profile` is provided, personalization rules are injected into the system prompt:
- Address user by name
- Gender-based product prioritization (e.g., dresses for female, suits for male)
- Interest-based feature highlighting
- Budget-aware price commentary

---

## Data Flow Summary

```
POST /api/chat
      │
┌─────┴──────────────────────────────────────────┐
│ Flask: Validate request, decode base64 image   │
├────────────────────────────────────────────────┤
│ ShoppingAgent.process(): Route by intent       │
├────────────────────────────────────────────────┤
│ SearchEngine: Vector search + filter           │
├────────────────────────────────────────────────┤
│ ResponseGenerator: Personalized synthesis      │
├────────────────────────────────────────────────┤
│ ConversationManager: Store turn, update state  │
└─────┬──────────────────────────────────────────┘
      │
   JSON Response
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| LLM | GPT-4o (intent, entities, responses) |
| Vision | GPT-4o (image analysis) |
| Embeddings | text-embedding-3-small |
| Vector Store | ChromaDB |
| Database | SQLite |
