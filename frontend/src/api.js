
const BASE = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

// Common request handler
async function req(path, options = {}) {
  let response;

  try {
    response = await fetch(`${BASE}${path}`, options);
  } catch {
    throw new Error(
      "Cannot connect to the backend. Make sure the FastAPI server is running."
    );
  }

  const contentType = response.headers.get("content-type") || "";
  let data;

  if (contentType.includes("application/json")) {
    data = await response.json();
  } else {
    data = await response.text();
  }

  if (!response.ok) {
    const detail =
      typeof data === "object" && data !== null
        ? data.detail || data.message
        : data;

    throw new Error(
      typeof detail === "string"
        ? detail
        : `Request failed with status ${response.status}.`
    );
  }

  return data;
}

// Authentication headers
const headers = () => {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
};

// JSON POST options
const jsonOptions = (data, authenticated = false) => ({
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    ...(authenticated ? headers() : {}),
  },
  body: JSON.stringify(data),
});

// Validate and prepare crop recommendation data
function prepareCropPayload(data) {
  const payload = {
    city: String(data.city ?? "").trim(),
    nitrogen: Number(data.nitrogen),
    phosphorus: Number(data.phosphorus),
    potassium: Number(data.potassium),
    ph: Number(data.ph ?? data.ph_level),
    rainfall: Number(data.rainfall),
  };

  if (!payload.city || payload.city.length < 2) {
    throw new Error("Please enter a valid city name.");
  }

  const numericFields = [
    ["Nitrogen", payload.nitrogen],
    ["Phosphorus", payload.phosphorus],
    ["Potassium", payload.potassium],
    ["pH", payload.ph],
    ["Rainfall", payload.rainfall],
  ];

  for (const [name, value] of numericFields) {
    if (!Number.isFinite(value) || value < 0) {
      throw new Error(`${name} must be a valid non-negative number.`);
    }
  }

  if (payload.ph > 14) {
    throw new Error("pH must be between 0 and 14.");
  }

  return payload;
}

// Upload a product image and create a marketplace listing.
// The image is sent to FastAPI, which handles Cloudinary securely.
function uploadProduct(product, image) {
  if (!image) {
    return Promise.reject(
      new Error("Please choose a product image before publishing.")
    );
  }

  const formData = new FormData();

  formData.append("name", String(product.name ?? "").trim());
  formData.append("category", String(product.category ?? "").trim());
  formData.append(
    "description",
    String(product.description ?? "").trim()
  );
  formData.append("price", String(product.price ?? ""));
  formData.append("quantity", String(product.quantity ?? ""));
  formData.append("unit", String(product.unit || "kg"));
  formData.append("location", String(product.location ?? "").trim());
  formData.append("image", image);

  return req("/marketplace/products/upload", {
    method: "POST",
    headers: headers(),
    body: formData,
  });
}

// API methods
export const api = {
  // Authentication
  signup: (data) => req("/auth/signup", jsonOptions(data)),
  login: (data) => req("/auth/login", jsonOptions(data)),

  // Machine learning
  crop: (data) => {
    const payload = prepareCropPayload(data);
    return req(
      "/ml/crop-recommendation",
      jsonOptions(payload)
    );
  },

  fertilizer: (data) =>
    req("/ml/fertilizer-recommendation", jsonOptions(data)),

  disease: (file) => {
    if (!file) {
      return Promise.reject(
        new Error("Please select a plant image first.")
      );
    }

    const formData = new FormData();
    formData.append("file", file);

    return req("/ml/disease-prediction", {
      method: "POST",
      headers: headers(),
      body: formData,
    });
  },

  // Weather
  weather: (city) =>
    req(`/weather?city=${encodeURIComponent(city)}`),

  // Marketplace products
  products: () => req("/marketplace/products"),

  product: (id) =>
    req(`/marketplace/products/${encodeURIComponent(id)}`),

  createProduct: (data) =>
    req("/marketplace/products", jsonOptions(data, true)),

  // Upload image through the backend and publish a listing
  uploadProduct,

  // Farmer listings
  listings: () =>
    req("/marketplace/my-listings", {
      headers: headers(),
    }),

  // Orders
  order: (data) =>
    req("/marketplace/orders", jsonOptions(data, true)),

  orders: () =>
    req("/marketplace/my-orders", {
      headers: headers(),
    }),

  sellerOrders: () =>
    req("/marketplace/seller-orders", {
      headers: headers(),
    }),
};
