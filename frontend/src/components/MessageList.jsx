import React, { useState } from "react";
import ProductCard from "./ProductCard";
import "../styles/MessageList.css";

function MessageList({ messages, isLoading }) {
  // Track sort order for each message with products
  const [sortOrders, setSortOrders] = useState({});

  const formatMessage = (content) => {
    // Convert markdown-style formatting to HTML
    return content
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\n/g, "<br />");
  };

  const handleSortChange = (messageIndex, sortOrder) => {
    setSortOrders((prev) => ({
      ...prev,
      [messageIndex]: sortOrder,
    }));
  };

  const getSortedProducts = (products, sortOrder) => {
    if (!products || products.length === 0) return [];

    switch (sortOrder) {
      case "price-asc":
        return [...products].sort((a, b) => a.price - b.price);
      case "price-desc":
        return [...products].sort((a, b) => b.price - a.price);
      case "rating":
        return [...products].sort((a, b) => b.rating - a.rating);
      case "relevance":
      default:
        return products; // Keep original order (relevance from AI search)
    }
  };

  return (
    <div className="message-list">
      {messages.map((message, index) => {
        const sortOrder = sortOrders[index] || "relevance";
        const sortedProducts = message.products
          ? getSortedProducts(message.products, sortOrder)
          : [];

        return (
          <div
            key={index}
            className={`message ${message.role}-message ${
              message.isError ? "error" : ""
            }`}
          >
            <div className="message-content">
              <div
                className="message-text"
                dangerouslySetInnerHTML={{
                  __html: formatMessage(message.content),
                }}
              />

              {message.hasImage && (
                <div className="image-indicator">📷 Image attached</div>
              )}

              {message.products && message.products.length > 0 && (
                <div className="products-container">
                  <div className="products-header">
                    <div className="products-header-left">
                      📦{" "}
                      <strong>
                        Products Found ({message.products.length})
                      </strong>
                    </div>
                    <div className="products-sort">
                      <label htmlFor={`sort-${index}`}>Sort by:</label>
                      <select
                        id={`sort-${index}`}
                        value={sortOrder}
                        onChange={(e) =>
                          handleSortChange(index, e.target.value)
                        }
                        className="sort-select"
                      >
                        <option value="relevance">🎯 Relevance</option>
                        <option value="price-asc">💰 Price: Low to High</option>
                        <option value="price-desc">
                          💰 Price: High to Low
                        </option>
                        <option value="rating">⭐ Highest Rated</option>
                      </select>
                    </div>
                  </div>
                  <div className="products-grid">
                    {sortedProducts.map((product, prodIndex) => (
                      <ProductCard
                        key={`${index}-${product.id}-${sortOrder}`}
                        product={product}
                        loadDelay={prodIndex * 150}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })}

      {isLoading && (
        <div className="message assistant-message">
          <div className="message-content">
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default MessageList;
