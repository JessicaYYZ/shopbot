import React, { useState, useEffect } from "react";
import { getStats } from "../services/api";
import "../styles/Sidebar.css";

function Sidebar() {
  const [stats, setStats] = useState({
    products: 0,
    embeddings: 0,
    categories: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const response = await getStats();
      if (response.success) {
        setStats(response.stats);
      }
    } catch (error) {
      console.error("Failed to load stats:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-section">
        <h3>💡 How to Use</h3>

        <div className="info-block">
          <h4>🔍 Natural Language Search</h4>
          <ul>
            <li>"Women's dresses under ₹2,000"</li>
            <li>"Blue leather wallet for men"</li>
            <li>"Gold necklace ₹5,000-₹10,000"</li>
          </ul>
        </div>

        <div className="info-block">
          <h4>📸 Image Search</h4>
          <ul>
            <li>Upload any product image</li>
            <li>Add text: "Find this in black"</li>
            <li>"Show cheaper options like this"</li>
          </ul>
        </div>

        <div className="info-block">
          <h4>🎯 Scenario Shopping</h4>
          <ul>
            <li>"I'm going camping next week"</li>
            <li>"Preparing for a beach vacation"</li>
            <li>"Wedding guest outfit ideas"</li>
          </ul>
        </div>

        <div className="info-block">
          <h4>💬 Follow-up Queries</h4>
          <ul>
            <li>"Show me cheaper options"</li>
            <li>"Something more formal"</li>
            <li>"Tell me about the first one"</li>
          </ul>
        </div>

        <div className="info-block">
          <h4>🏷️ Categories</h4>
          <p className="category-tags">
            Clothing • Jewellery • Footwear • Watches • Electronics • Beauty •
            Home Decor
          </p>
        </div>
      </div>

      <div className="sidebar-section stats-section">
        <h3>📊 System Stats</h3>
        {loading ? (
          <div className="stats-loading">Loading...</div>
        ) : (
          <div className="stats-grid">
            <div className="stat-item">
              <div className="stat-value">{stats.products}</div>
              <div className="stat-label">Products</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{stats.embeddings}</div>
              <div className="stat-label">Embeddings</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{stats.categories}</div>
              <div className="stat-label">Categories</div>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}

export default Sidebar;
