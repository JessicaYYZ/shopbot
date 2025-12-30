import axios from "axios";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:5001";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000,
});

export const sendMessage = async (
  message,
  image = null,
  userProfile = null
) => {
  try {
    const payload = {
      message,
      image,
    };

    if (userProfile) {
      payload.user_profile = {
        id: userProfile.id,
        name: userProfile.name,
        gender: userProfile.gender,
        age: userProfile.age,
        interests: userProfile.interests,
        preferences: userProfile.preferences,
        budget: userProfile.budget,
        style: userProfile.style,
      };
    }

    const response = await apiClient.post("/api/chat", payload);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || "Failed to send message");
  }
};

export const resetConversation = async () => {
  try {
    const response = await apiClient.post("/api/reset");
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.error || "Failed to reset conversation"
    );
  }
};

export const getStats = async () => {
  try {
    const response = await apiClient.get("/api/stats");
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || "Failed to get stats");
  }
};

export const getProducts = async (filters = {}) => {
  try {
    const params = new URLSearchParams();
    if (filters.category) params.append("category", filters.category);
    if (filters.min_price) params.append("min_price", filters.min_price);
    if (filters.max_price) params.append("max_price", filters.max_price);
    if (filters.limit) params.append("limit", filters.limit);

    const response = await apiClient.get(`/api/products?${params.toString()}`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || "Failed to get products");
  }
};

export const getProduct = async (productId) => {
  try {
    const response = await apiClient.get(`/api/products/${productId}`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || "Failed to get product");
  }
};

export const getCategories = async () => {
  try {
    const response = await apiClient.get("/api/categories");
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || "Failed to get categories");
  }
};

export const healthCheck = async () => {
  try {
    const response = await apiClient.get("/api/health");
    return response.data;
  } catch (error) {
    throw new Error("Backend server is not responding");
  }
};

export default apiClient;
