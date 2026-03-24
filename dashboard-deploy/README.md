# Chakravyuh Dashboard - Deployment Ready Package

**Autonomous Cyber Defense Grid - SOC Dashboard**

dashboard for the Chakravyuh cyber defense system. This package contains everything needed to deploy the dashboard frontend in production or development environments.

---

## 📋 Quick Start

### Prerequisites
- **Node.js** v18.x or higher
- **npm** v9.x or higher

### Installation & Setup

1. **Navigate to the dashboard directory:**
   ```bash
   cd dashboard-deploy
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```
   Or use the included script:
   ```bash
   npm run install-deps
   ```

3. **Development Server:**
   ```bash
   npm run dev
   ```
   The dashboard will be available at `http://localhost:5173`

4. **Production Build:**
   ```bash
   npm run build
   ```
   Output files will be in the `dist/` directory

5. **Preview Production Build:**
   ```bash
   npm run preview
   ```

---

## 🏗️ Project Structure

```
dashboard-deploy/
├── src/
│   ├── components/
│   │   └── Dashboard.tsx         # Main dashboard component
│   ├── App.tsx                   # Root app component with error boundary
│   ├── main.tsx                  # React entry point
│   ├── types.ts                  # TypeScript type definitions
│   └── index.css                 # Tailwind CSS imports & base styles
├── public/                       # Static assets
├── index.html                    # HTML template
├── vite.config.ts                # Vite build configuration
├── tsconfig.json                 # TypeScript configuration
├── tailwind.config.js            # Tailwind CSS configuration
├── postcss.config.js             # PostCSS configuration
├── package.json                  # Dependencies & scripts
└── README.md                     # This file
```

---

## 🎯 Features

### 1. **Professional SOC Interface**

### 2. **Core Panels**

   **Left Column: Auto-SOC Intelligence Feed**
   - Real-time threat alert feed with severity color-coding
   - Minimal scrollable list with hover states
   - Live connection indicator

   **Center Column: Sovereign Federated Network Map**
   - Interactive map of India showing defense nodes
   - Geo-spatial visualization of critical infrastructure
   - Status indicators (Safe, Flagged, Under Attack)
   - Node names and operational types

   **Right Column: GenAI Deception Terminal**
   - Live honeypot activity capture display
   - Realistic terminal emulation with syntax highlighting
   - Shows attacker commands, system responses, and AI deception logic
   - Live cursor animation

### 3. **Dashboard Stats**
   - Total Threats Prevented (with daily trend)
   - Critical Incidents Counter
   - Threats in Honeypot
   - Active Federated Nodes

---

## 🔌 API Configuration

The dashboard connects to a FastAPI backend on `http://localhost:8000/api`. Configure the API endpoint in `src/components/Dashboard.tsx`:

```typescript
const API_BASE_URL = 'http://localhost:8000/api';
```

### Expected Endpoints:
- `GET /api/stats` - Get threat statistics
- `GET /api/alerts` - Get alert feed
- `GET /api/honeypots` - Get honeypot status
- `GET /api/federated/status` - Get federated node status

---

## 📦 Deployment Options

### Option 1: Docker Deployment (Recommended)

1. **Create a Dockerfile** in the root:
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY . .
RUN npm install --legacy-peer-deps
RUN npm run build
EXPOSE 5173
CMD ["npm", "run", "preview"]
```

2. **Build & Run:**
```bash
docker build -t chakravyuh-dashboard .
docker run -p 5173:5173 chakravyuh-dashboard
```

### Option 2: Traditional Server Deployment

1. Build the project:
```bash
npm run build
```

2. Deploy the `dist/` directory to your web server (Nginx, Apache, etc.)

**Nginx Configuration Example:**
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    root /var/www/chakravyuh-dashboard/dist;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### Option 3: Cloud Deployment

**Vercel / Netlify:**
```bash
npm run build
# Upload dist/ folder to Vercel/Netlify
```

**AWS S3 + CloudFront:**
```bash
npm run build
aws s3 sync dist/ s3://your-bucket-name/
```

---

## 🎨 Customization

### Color Scheme
Edit `tailwind.config.js` to modify the color palette:
```javascript
theme: {
  colors: {
    emerald: { 500: '#10b981', 400: '#34d399', ... },
    rose: { 500: '#f43f5e', 400: '#fb7185', ... },
    // ... add your colors
  }
}
```

### API Endpoints
Update `src/components/Dashboard.tsx` to connect to your backend:
```typescript
const API_BASE_URL = process.env.VITE_API_URL || 'http://localhost:8000/api';
```

### Map Configuration
To customize the geographic map, modify the `mapMarkers` array in `src/components/Dashboard.tsx`:
```typescript
const mapMarkers = [
  { name: "Your Node", type: "Location", coordinates: [lon, lat], status: "safe" }
];
```

---

## 🔒 Security Considerations

1. **CORS Configuration**: Ensure your backend FastAPI server allows the dashboard origin.
2. **Environment Variables**: Use `.env` files for sensitive data (never commit to git).
3. **Authentication**: Implement JWT/OAuth2 for production deployments.
4. **HTTPS**: Always use HTTPS in production.

Example `.env`:
```
VITE_API_URL=https://your-api-domain.com/api
VITE_API_KEY=your-secret-key
```

---

## 🚀 Performance Optimization

- **Bundle Size**: ~353KB (gzip: 117KB) - optimized for fast load
- **CSS Purging**: Tailwind automatically purges unused styles
- **Code Splitting**: Automatic with Vite
- **Asset Optimization**: Images and fonts automatically optimized during build

---

## 📊 Dashboard Data Flow

```
┌─────────────────────────────────────────────┐
│         FastAPI Backend (8000)              │
│    /api/stats, /alerts, /honeypots, etc.    │
└──────────────────┬──────────────────────────┘
                   │ axios.get()
                   ▼
┌─────────────────────────────────────────────┐
│      React Dashboard Component              │
│   (Fetches data on mount, displays static)  │
└──────────────────┬──────────────────────────┘
                   │ Renders
                   ▼
┌─────────────────────────────────────────────┐
│        Browser (http://5173)                │
│    Professional SOC Interface               │
└─────────────────────────────────────────────┘
```

---

## 🛠️ Troubleshooting

### Issue: Blank White Screen
- **Solution**: Clear browser cache (`Ctrl+Shift+R`) and check console for errors

### Issue: Failed to fetch API
- **Ensure**: FastAPI backend is running on `http://localhost:8000`
- **Check**: CORS is properly configured in backend
- **Verify**: API endpoints match the expected format

### Issue: Map not rendering
- **Check**: TopoJSON file can be accessed (https://raw.githubusercontent.com/...)
- **Verify**: Internet connection available
- **Try**: Refresh page or check browser console for network errors

### Issue: Tailwind styles not loading
```bash
npm run build
# or restart dev server
```

---

## 📞 Support

For issues, questions, or feature requests:
1. Check the console for error messages (`Dev Tools > Console`)
2. Verify API backend is responding correctly
3. Ensure all dependencies are installed: `npm install --legacy-peer-deps`

---

## 📜 License

Chakravyuh Project - Delhi Hackathon 2026

---

## 👥 Team

Built for **India's Sovereign Cyber Defense Grid**

**Last Updated**: March 24, 2026  
**Version**: 1.0.0 Production Ready
