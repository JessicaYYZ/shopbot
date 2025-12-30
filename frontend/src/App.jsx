import React, { useState } from "react";
import ChatInterface from "./components/ChatInterface";
import Sidebar from "./components/Sidebar";
import "./styles/App.css";

const USER_PROFILES = {
  anna: {
    id: "anna",
    name: "Anna",
    avatar: "👩",
    gender: "female",
    age: 28,
    interests: ["clothing", "jewellery", "footwear", "beauty", "handbags"],
    preferences: "Trendy fashion, elegant jewellery, comfortable footwear",
    budget: "mid-range",
    style: "Modern and elegant",
  },
  mike: {
    id: "mike",
    name: "Mike",
    avatar: "👨",
    gender: "male",
    age: 32,
    interests: ["watches", "electronics", "footwear", "automotive", "sports"],
    preferences: "Quality watches, latest electronics, comfortable shoes",
    budget: "value-focused",
    style: "Practical and stylish",
  },
};

function App() {
  const [currentUser, setCurrentUser] = useState(USER_PROFILES.anna);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  const handleUserChange = (userId) => {
    setCurrentUser(USER_PROFILES[userId]);
    setIsDropdownOpen(false);
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <div className="header-left">
            <h1>ShopBot</h1>
            <p className="subtitle">AI Shopping Assistant · 12K+ Products</p>
          </div>

          <div className="user-selector">
            <button
              className="user-dropdown-trigger"
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            >
              <span className="user-avatar">{currentUser.avatar}</span>
              <span className="user-name">{currentUser.name}</span>
              <span className="dropdown-arrow">
                {isDropdownOpen ? "▲" : "▼"}
              </span>
            </button>

            {isDropdownOpen && (
              <div className="user-dropdown-menu">
                {Object.values(USER_PROFILES).map((user) => (
                  <button
                    key={user.id}
                    className={`user-option ${
                      currentUser.id === user.id ? "active" : ""
                    }`}
                    onClick={() => handleUserChange(user.id)}
                  >
                    <span className="user-avatar">{user.avatar}</span>
                    <div className="user-info">
                      <span className="user-option-name">{user.name}</span>
                      <span className="user-option-style">{user.style}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="user-profile-bar">
          <span className="profile-label">Shopping as:</span>
          <span className="profile-interests">
            {currentUser.interests.slice(0, 4).map((interest, i) => (
              <span key={i} className="interest-tag">
                {interest}
              </span>
            ))}
          </span>
        </div>
      </header>

      <div className="app-content">
        <Sidebar />
        <ChatInterface currentUser={currentUser} />
      </div>
    </div>
  );
}

export default App;
