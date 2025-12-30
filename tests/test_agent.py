"""
Tests for Shopping Agent
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.core.agent import ShoppingAgent
from src.data.schemas import Product, AgentResponse


def test_agent_initialization():
    """Test agent initialization"""
    openai_mock = Mock()
    vector_store_mock = Mock()
    database_mock = Mock()
    
    agent = ShoppingAgent(openai_mock, vector_store_mock, database_mock)
    
    assert agent is not None
    assert agent.openai == openai_mock
    assert agent.vector_store == vector_store_mock
    assert agent.database == database_mock


def test_general_conversation():
    """Test general conversation handling"""
    openai_mock = Mock()
    openai_mock.generate_text.return_value = "I'm ShopBot, your AI shopping assistant!"
    
    vector_store_mock = Mock()
    database_mock = Mock()
    
    agent = ShoppingAgent(openai_mock, vector_store_mock, database_mock)
    
    result = agent.handle_general_conversation("What's your name?")
    
    assert isinstance(result, AgentResponse)
    assert result.intent == "general_conversation"
    assert "ShopBot" in result.response
    assert len(result.products) == 0


def test_text_search():
    """Test text-based product search"""
    openai_mock = Mock()
    openai_mock.generate_embedding.return_value = [0.1] * 1536
    openai_mock.generate_text.return_value = "Here are some great t-shirts..."
    
    vector_store_mock = Mock()
    vector_store_mock.search_text.return_value = {
        "ids": [["1", "2"]],
        "distances": [[0.1, 0.2]],
        "metadatas": [[]]
    }
    
    database_mock = Mock()
    database_mock.get_products_by_ids.return_value = [
        Product(
            id=1,
            title="Test T-Shirt",
            description="A test t-shirt",
            category="Clothing",
            price=29.99,
            brand="TestBrand",
            image_path="test.jpg"
        )
    ]
    
    agent = ShoppingAgent(openai_mock, vector_store_mock, database_mock)
    
    result = agent.handle_text_search("recommend me a t-shirt")
    
    assert isinstance(result, AgentResponse)
    assert result.intent == "product_search"
    assert len(result.products) > 0
    assert result.products[0].title == "Test T-Shirt"


if __name__ == "__main__":
    pytest.main([__file__])

