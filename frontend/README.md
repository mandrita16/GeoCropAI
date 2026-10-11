# GeoCropAI Frontend

React/Vite frontend for the FastAPI backend.

## Install
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

Copy the old project's `static/images` into:
`frontend/public/assets/images/`

The frontend connects to:
- `/auth/signup`
- `/auth/login`
- `/ml/crop-recommendation`
- `/ml/fertilizer-recommendation`
- `/ml/disease-prediction`
- `/marketplace/products`
- `/marketplace/my-listings`
- `/marketplace/orders`
- `/marketplace/my-orders`
- `/marketplace/seller-orders`

The crop page can call `/weather?city=...` once the weather FastAPI endpoint is added. Until then temperature and humidity can be entered manually.
