import React, { useState, useEffect, useRef } from "react";
import "../styles/ProductCard.css";

function ProductCard({ product, loadDelay = 0 }) {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [imageSrc, setImageSrc] = useState(null);
  const timeoutRef = useRef(null);
  const imgRef = useRef(null);

  const MAX_RETRIES = 3;
  const IMAGE_TIMEOUT = 10000; // 10 seconds

  // Reset and load image when product or image_path changes
  useEffect(() => {
    setImageLoaded(false);
    setImageError(false);
    setRetryCount(0);
    setImageSrc(null);

    // Clear any existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // Staggered loading - add delay to prevent network congestion
    const loadTimer = setTimeout(() => {
      if (product.image_path && product.image_path.startsWith("http")) {
        loadImageWithRetry(product.image_path, 0);
      }
    }, loadDelay);

    return () => {
      clearTimeout(loadTimer);
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [product.id, product.image_path, loadDelay]);

  // Load image with retry and timeout logic
  const loadImageWithRetry = (url, attempt) => {
    if (attempt >= MAX_RETRIES) {
      setImageError(true);
      setImageLoaded(true);
      return;
    }

    // Set timeout for this attempt
    timeoutRef.current = setTimeout(() => {
      if (!imageLoaded && !imageError) {
        // Timeout occurred, retry
        const nextAttempt = attempt + 1;
        setRetryCount(nextAttempt);

        if (nextAttempt < MAX_RETRIES) {
          // Exponential backoff: 100ms, 300ms, 900ms
          const backoffDelay = Math.min(
            100 * Math.pow(3, nextAttempt - 1),
            1000
          );
          setTimeout(() => {
            loadImageWithRetry(url, nextAttempt);
          }, backoffDelay);
        } else {
          setImageError(true);
          setImageLoaded(true);
        }
      }
    }, IMAGE_TIMEOUT);

    // Add cache-busting for retries
    const cacheBustedUrl =
      attempt > 0
        ? `${url}${url.includes("?") ? "&" : "?"}retry=${attempt}`
        : url;
    setImageSrc(cacheBustedUrl);
  };

  // Format price in Indian Rupees
  const formatPrice = (price) => {
    return `₹${price.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ",")}`;
  };

  // Handle successful image load
  const handleImageLoad = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setImageLoaded(true);
    setImageError(false);
  };

  // Handle image error
  const handleImageError = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    const nextAttempt = retryCount + 1;
    setRetryCount(nextAttempt);

    if (nextAttempt < MAX_RETRIES) {
      // Retry with exponential backoff
      const backoffDelay = Math.min(100 * Math.pow(3, nextAttempt - 1), 1000);
      setTimeout(() => {
        loadImageWithRetry(product.image_path, nextAttempt);
      }, backoffDelay);
    } else {
      setImageError(true);
      setImageLoaded(true);
    }
  };

  // Get category icon based on product category
  const getCategoryIcon = (category) => {
    const cat = (category || "").toLowerCase();
    if (
      cat.includes("clothing") ||
      cat.includes("dress") ||
      cat.includes("shirt")
    )
      return "👗";
    if (
      cat.includes("jewel") ||
      cat.includes("necklace") ||
      cat.includes("ring")
    )
      return "💍";
    if (cat.includes("watch")) return "⌚";
    if (
      cat.includes("footwear") ||
      cat.includes("shoe") ||
      cat.includes("sandal")
    )
      return "👟";
    if (cat.includes("bag") || cat.includes("wallet")) return "👜";
    if (
      cat.includes("electronic") ||
      cat.includes("laptop") ||
      cat.includes("mobile")
    )
      return "📱";
    if (cat.includes("beauty") || cat.includes("fragrance")) return "💄";
    if (cat.includes("home") || cat.includes("kitchen")) return "🏠";
    if (cat.includes("sport") || cat.includes("fitness")) return "🏃";
    return "📦";
  };

  // Check if image URL is valid
  const hasValidImage =
    product.image_path && product.image_path.startsWith("http") && !imageError;

  return (
    <div className="product-card">
      <div className="product-image-container">
        {hasValidImage && imageSrc ? (
          <>
            {!imageLoaded && (
              <div className="product-image-loading">
                <div className="spinner"></div>
                {retryCount > 0 && (
                  <div className="retry-indicator">
                    Retry {retryCount}/{MAX_RETRIES}
                  </div>
                )}
              </div>
            )}
            <img
              ref={imgRef}
              src={imageSrc}
              alt={product.title}
              className={`product-image ${imageLoaded ? "loaded" : "loading"}`}
              onLoad={handleImageLoad}
              onError={handleImageError}
              referrerPolicy="no-referrer"
            />
          </>
        ) : (
          <div className="product-image-placeholder">
            {getCategoryIcon(product.category)}
          </div>
        )}
      </div>

      <div className="product-info">
        <h4 className="product-title">
          {product.title.length > 60
            ? product.title.substring(0, 60) + "..."
            : product.title}
        </h4>

        <div className="product-price-section">
          <span className="product-price">{formatPrice(product.price)}</span>
        </div>

        <div className="product-meta">
          <span className="product-brand">🏷️ {product.brand}</span>
          <span className="product-category">
            {getCategoryIcon(product.category)} {product.category}
          </span>
        </div>

        {product.description && (
          <p className="product-description">
            {product.description.length > 120
              ? product.description.substring(0, 120) + "..."
              : product.description}
          </p>
        )}

        {product.tags && product.tags.length > 0 && (
          <div className="product-tags">
            {product.tags.slice(0, 4).map((tag, index) => (
              <span key={index} className="product-tag">
                #{tag}
              </span>
            ))}
          </div>
        )}

        {product.product_url && product.product_url.startsWith("http") && (
          <a
            href={product.product_url}
            target="_blank"
            rel="noopener noreferrer"
            className="product-url-link"
          >
            🔗 View on Flipkart
          </a>
        )}
      </div>
    </div>
  );
}

export default ProductCard;
