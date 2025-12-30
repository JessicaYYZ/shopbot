import React, { useState, useRef } from 'react';
import '../styles/MessageInput.css';

function MessageInput({ onSendMessage, isLoading }) {
  const [message, setMessage] = useState('');
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const fileInputRef = useRef(null);

  const handleImageSelect = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      alert('Please select an image file');
      return;
    }

    // Create preview
    const reader = new FileReader();
    reader.onload = (event) => {
      setImagePreview(event.target.result);
      setImage(event.target.result);
    };
    reader.readAsDataURL(file);
  };

  const handleRemoveImage = () => {
    setImage(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (!message.trim() && !image) return;
    if (isLoading) return;

    onSendMessage(message.trim(), image);
    
    // Clear input
    setMessage('');
    handleRemoveImage();
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="message-input-container">
      {imagePreview && (
        <div className="image-preview">
          <img src={imagePreview} alt="Upload preview" />
          <button
            className="remove-image-button"
            onClick={handleRemoveImage}
            type="button"
          >
            ×
          </button>
        </div>
      )}

      <form className="message-input-form" onSubmit={handleSubmit}>
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleImageSelect}
          accept="image/*"
          style={{ display: 'none' }}
        />
        
        <button
          className="icon-button"
          type="button"
          onClick={() => fileInputRef.current?.click()}
          title="Upload image"
        >
          📷
        </button>

        <input
          type="text"
          className="message-input"
          placeholder="Type your message here..."
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={isLoading}
        />

        <button
          className="send-button"
          type="submit"
          disabled={isLoading || (!message.trim() && !image)}
        >
          {isLoading ? '⏳' : '📤'}
        </button>
      </form>
    </div>
  );
}

export default MessageInput;

