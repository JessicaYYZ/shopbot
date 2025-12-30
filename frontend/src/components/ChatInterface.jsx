import React, { useState, useEffect, useRef } from 'react';
import { sendMessage, resetConversation } from '../services/api';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import '../styles/ChatInterface.css';

function ChatInterface({ currentUser }) {
  const getWelcomeMessage = (user) => {
    const interests = user.interests.slice(0, 3).join(', ');
    return {
      role: 'assistant',
      content: `**Welcome, ${user.name}! 👋**\n\nI'm your personal shopping assistant with **12,000+ products** across Clothing, Jewellery, Footwear, Watches, Electronics, Beauty & more!\n\nBased on your interests in **${interests}**, I'll help you find perfect matches.\n\n**Try asking:**\n• "Show me women's dresses under ₹2,000"\n• "Find me stylish watches"\n• "What's trending in ${user.interests[1]}?"\n\nHow can I help you today?`,
      products: [],
    };
  };

  const [messages, setMessages] = useState([getWelcomeMessage(currentUser)]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    // Reset backend conversation when user profile changes
    resetConversation().catch(err => console.error('Error resetting on profile change:', err));
    setMessages([getWelcomeMessage(currentUser)]);
  }, [currentUser]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (message, image) => {
    if (!message && !image) return;

    const userMessage = {
      role: 'user',
      content: message || '[Image uploaded]',
      hasImage: !!image,
    };
    setMessages((prev) => [...prev, userMessage]);
    setError(null);
    setIsLoading(true);

    try {
      const response = await sendMessage(message, image, currentUser);

      if (response.success) {
        const assistantMessage = {
          role: 'assistant',
          content: response.response,
          products: response.products || [],
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } else {
        throw new Error(response.error || 'Failed to get response');
      }
    } catch (err) {
      console.error('Error sending message:', err);
      setError(err.message || 'Failed to send message. Please try again.');
      
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        isError: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = async () => {
    if (!window.confirm('Start a new conversation?')) {
      return;
    }

    try {
      await resetConversation();
      setMessages([getWelcomeMessage(currentUser)]);
      setError(null);
    } catch (err) {
      console.error('Error resetting conversation:', err);
      setError('Failed to reset conversation');
    }
  };

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <div className="header-content">
          <h2>Chat</h2>
          <button className="reset-button" onClick={handleReset} title="Reset conversation">
            New Chat
          </button>
        </div>
        {error && (
          <div className="error-banner">
            {error}
          </div>
        )}
      </div>

      <MessageList messages={messages} isLoading={isLoading} />
      
      <div ref={messagesEndRef} />

      <MessageInput onSendMessage={handleSendMessage} isLoading={isLoading} />
    </div>
  );
}

export default ChatInterface;
