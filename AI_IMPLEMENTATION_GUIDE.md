# 🤖 AI Implementation Guide - Chakravyuh Frontend

**For use by other AI tools/developers to understand and extend this codebase.**

---

## 📌 Quick Facts

| Property | Value |
|----------|-------|
| **Project** | Chakravyuh - Autonomous Cyber Defense |
| **Branch** | Front-end |
| **Runtime** | Node.js 22.22.1 + React 19 |
| **Status** | ✅ Fully Functional |
| **Port** | http://localhost:5173 |
| **API Port** | http://localhost:8000 |

---

## 🏗️ Architecture at a Glance

```
┌─────────────────────────────────────────┐
│         React Dashboard                 │
│    ┌──────────────────────────────┐    │
│    │ Dashboard (Main Component)    │    │
│    ├──────────────────────────────┤    │
│    │ ├─ EmergencyControl.tsx      │    │
│    │ ├─ ThreatTimeline.tsx        │    │
│    │ ├─ NetworkControl.tsx        │    │
│    │ └─ StatCard (sub-component)  │    │
│    └──────────────────────────────┘    │
└─────────────────────────────────────────┘
              ↓ (Axios HTTP)
┌─────────────────────────────────────────┐
│      FastAPI Backend (main.py)          │
│  ├─ GET  /api/stats                    │
│  ├─ GET  /api/alerts                   │
│  ├─ POST /api/emergency/isolate-node   │
│  ├─ POST /api/emergency/block-ip       │
│  ├─ POST /api/emergency/lockdown       │
│  ├─ POST /api/emergency/quarantine     │
│  ├─ POST /api/emergency/rotate-creds   │
│  ├─ POST /api/emergency/escalate       │
│  ├─ GET  /api/emergency/actions-history│
│  └─ GET  /api/emergency/blocked-ips    │
└─────────────────────────────────────────┘
              ↓ (Mock Data)
         Local State Objects
```

---

## 📂 Key Files Reference

### **Frontend Components**

#### 1. `Dashboard.tsx` (270 lines)
**Purpose:** Main container component  
**What it does:**
- Fetches data via Axios
- Renders 4-column stat cards
- Renders ThreatTimeline, NetworkControl
- Has Geo-spatial map with SVG
- Honeypot terminal mockup
- Passes props to EmergencyControl

**Key Functions:**
```typescript
export default function Dashboard()
fetchData() → setStats, setAlerts
Renders → StatCard components
```

#### 2. `EmergencyControl.tsx` (200 lines)
**Purpose:** Floating 🚨 emergency command panel  
**What it does:**
- Floating button (bottom-right)
- Opens modal with 6 action buttons
- Action history display
- Blocked IPs tracker
- Sends POST requests to backend

**Key Functions:**
```typescript
executeAction(actionType) → POST to API
fetchActionHistory() → Gets last 20 actions
fetchBlockedIPs() → Gets blocked attackers
```

#### 3. `ThreatTimeline.tsx` (130 lines)
**Purpose:** Animated real-time alert feed  
**What it does:**
- Maps alert array with animations
- Color-codes by severity
- Shows timestamps
- Polls API every 3 seconds
- Smooth slide-in animations

**Key Display:** Alert list with severity badges

#### 4. `NetworkControl.tsx` (160 lines)
**Purpose:** Network bandwidth visualization  
**What it does:**
- Shows total bandwidth gauge
- Per-node traffic breakdown
- Anomaly score indicators
- Packet loss metrics
- Mock network stats

**Key Display:** 3 nodes with bandwidth/anomaly metrics

### **Backend Endpoint File**

#### `backend/api/main.py` (280 new lines)
**Purpose:** FastAPI emergency response endpoints  
**Endpoints Added:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/emergency/isolate-node` | POST | Network isolation |
| `/api/emergency/block-ip` | POST | IP blocking |
| `/api/emergency/lockdown` | POST | Full lockdown |
| `/api/emergency/quarantine` | POST | Node quarantine |
| `/api/emergency/rotate-credentials` | POST | Credential rotation |
| `/api/emergency/escalate` | POST | Auto-escalation |
| `/api/emergency/actions-history` | GET | View history |
| `/api/emergency/blocked-ips` | GET | View blocked IPs |

**Data Models Added:**
```python
IsolateNodeRequest(BaseModel)
BlockIPRequest(BaseModel)
LockdownRequest(BaseModel)
QuarantineRequest(BaseModel)
RotateCredsRequest(BaseModel)
EscalateRequest(BaseModel)
```

---

## 🔄 Data Flow Examples

### Example 1: Block an IP
```
User clicks "Block Attacker IP"
         ↓
User enters IP: 203.168.1.1
         ↓
Clicks "Execute" button
         ↓
executeAction("block-ip") called
         ↓
axios.post("/api/emergency/block-ip", { attacker_ip: "203.168.1.1" })
         ↓
Backend receives request
         ↓
Adds IP to blocked_ips list
         ↓
Returns success response
         ↓
Action appears in "Recent Actions" log
         ↓
Blocked IP appears in dashboard
```

### Example 2: Fetch Alerts
```
Dashboard component mounts (useEffect)
         ↓
axios.get("/api/alerts")
         ↓
Backend returns mock alerts array
         ↓
setAlerts(mockAlerts)
         ↓
Components re-render
         ↓
ThreatTimeline shows new alerts
```

---

## 🎨 Styling System

**CSS Framework:** Tailwind CSS 3.4

**Color Scheme:**
- **Background:** `#0B0F19` (very dark blue)
- **Cards:** `#131A2A` (dark blue)
- **Borders:** `#1E293B` (slate)
- **Success:** Emerald 500
- **Warning:** Amber 500
- **Critical:** Rose 500
- **Text:** Slate 300/400

**Responsive Breakpoints:**
- `col-span-12` = Mobile (full width)
- `lg:col-span-4` = Desktop (1/3 width)
- `lg:col-span-5` = Desktop (5/12 width)
- `lg:col-span-3` = Desktop (1/4 width)

---

## 🔌 API Response Examples

### GET /api/stats
```json
{
  "total_threats": 14032,
  "critical_count": 8,
  "honeypot_trapped_count": 312,
  "federated_node_count": 4
}
```

### GET /api/alerts
```json
[
  {
    "id": 8934,
    "severity": "critical",
    "description": "Zero-day lateral movement thwarted"
  }
]
```

### POST /api/emergency/block-ip (Request)
```json
{
  "attacker_ip": "203.168.1.1"
}
```

### POST /api/emergency/block-ip (Response)
```json
{
  "action_id": "block-1711266000",
  "action_type": "block-ip",
  "node_id": "203.168.1.1",
  "status_message": "✅ IP added to blocklist",
  "executed_at": "2026-03-24T13:40:00"
}
```

---

## 🛠️ How to Extend

### Add a New Emergency Action

**Step 1: Add TypeScript Type** (`src/types.ts`)
```typescript
interface YourAction {
  id: string;
  type: "your-action";
  // ... fields
}
```

**Step 2: Create Backend Endpoint** (`backend/api/main.py`)
```python
@app.post("/api/emergency/your-action")
async def your_action(request: YourActionRequest):
    # Your logic
    return {"status_message": "✅ Action completed"}
```

**Step 3: Add UI Button** (`EmergencyControl.tsx`)
```typescript
const actionButtons = [
  // ... existing buttons
  { 
    id: "your-action", 
    label: "🎯 Your Action", 
    color: "bg-blue-600",
    desc: "What it does"
  }
];
```

**Step 4: Handle Execution** (in `executeAction` function)
```typescript
case "your-action":
  endpoint = "/emergency/your-action";
  payload = { /* your fields */ };
  break;
```

---

## 📊 State Management

**React Hooks Used:**
- `useState` - Local component state
- `useEffect` - Data fetching on mount
- `setInterval` - Polling for updates

**State Variables:**
```typescript
const [stats, setStats] = useState<Stats | null>(null)
const [alerts, setAlerts] = useState<Alert[]>([])
const [actionHistory, setActionHistory] = useState<EmergencyAction[]>([])
const [blockedIPs, setBlockedIPs] = useState<BlockedAttacker[]>([])
```

**No Redux/Context API - Simple approach for demo**

---

## 🐛 Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| Module not found | Check imports match exact file paths |
| API 404 errors | Verify backend is running on :8000 |
| Styling not applied | Check Tailwind classes in tailwind.config.js |
| Hot reload not working | Kill dev server, restart: `npm run dev` |
| Type errors | Run `tsc --noEmit` for TypeScript check |

---

## 📋 File Addition Checklist

When adding files, ensure:

- [ ] Import statements are correct
- [ ] File exports default/named components
- [ ] TypeScript interfaces defined in types.ts
- [ ] Tailwind classes used for styling
- [ ] Props properly typed with interfaces
- [ ] useEffect cleanup functions if needed
- [ ] Error handling with try/catch
- [ ] Mock data updated if needed

---

## 🚀 Performance Tips

1. **Memoization:** Use `React.memo()` for expensive components
2. **Lazy Loading:** Use `React.lazy()` for code splitting
3. **Polling Frequency:** 5-10 seconds is good (avoid <2s)
4. **API Calls:** Batch requests when possible
5. **Bundle Size:** Keep components focused and small

---

## 🔐 Security Considerations

⚠️ **Current:** Mock data for demo  
✅ **Production:** Add:
- [ ] Environment variables for API URLs
- [ ] CORS configuration
- [ ] Input validation on all forms
- [ ] Authentication tokens in headers
- [ ] Rate limiting on API endpoints
- [ ] SQL injection prevention (if using DB)
- [ ] XSS protection (React does this by default)

---

## 📱 Responsive Design Notes

**Mobile (< 1024px):**
- Single column layout
- Stacked cards
- Hamburger menu (if needed)

**Tablet (1024px - 1280px):**
- 2 column layout
- Adjusted card sizes

**Desktop (> 1280px):**
- 3-4 column layout
- Full feature set visible

**Tested on:**
- ✅ Desktop (1920x1080)
- ✅ Tablet (768x1024)
- ✅ Mobile (375x667)

---

## 🎯 Next Steps for AI Systems

1. **Understand:** Read through Dashboard.tsx and types.ts
2. **Extend:** Add new components following the patterns
3. **Test:** Use mock data first, then real APIs
4. **Deploy:** Build with `npm run build` → dist/ folder
5. **Serve:** Use your server to host the dist/ folder

---

## 📞 Quick Commands

```bash
# Setup
npm install --legacy-peer-deps

# Development
npm run dev

# Production build
npm run build

# Type checking
tsc --noEmit

# Lint (if configured)
npm run lint

# Preview production build
npm preview
```

---

## 💡 Architecture Decisions Made

1. **Mock Data:** Uses mock data in JS objects (easy to replace with real API)
2. **Polling:** Uses setInterval instead of WebSockets (simpler, works everywhere)
3. **No Redux:** Simple useState (less boilerplate, easier to understand)
4. **Tailwind:** Chosen for rapid UI development
5. **Vite:** Chosen for fast builds and hot reload
6. **FastAPI:** Chosen for Python async/await simplicity

---

**Last Updated:** March 24, 2026  
**Status:** ✅ Complete and functional  
**Ready for:** Production demo & AI integration
