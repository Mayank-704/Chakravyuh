import React, { useEffect, useState } from 'react';
import { Shield, ShieldAlert, Network, Server, Terminal, Activity, Wifi } from 'lucide-react';
import axios from 'axios';
import type { Stats, Alert, FederatedStatus, Honeypot, ThreatMap } from '../types';
import { ThreatTimeline, AttackDistribution, TopTargeted } from './charts';
import Ticker from './Ticker';

const API_BASE_URL = 'http://localhost:8000/api';
const WS_URL = 'ws://localhost:8000/ws/alerts';

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [nodes, setNodes] = useState<FederatedStatus[]>([]);
  const [honeypots, setHoneypots] = useState<Honeypot[]>([]);
  const [threatMap, setThreatMap] = useState<ThreatMap | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, alertsRes, nodesRes, honeypotsRes, threatMapRes] = await Promise.all([
          axios.get<Stats>(`${API_BASE_URL}/stats`),
          axios.get<Alert[]>(`${API_BASE_URL}/alerts`),
          axios.get<FederatedStatus[]>(`${API_BASE_URL}/federated/status`),
          axios.get<Honeypot[]>(`${API_BASE_URL}/honeypots`),
          axios.get<ThreatMap>(`${API_BASE_URL}/threat-map`),
        ]);
        
        setStats(statsRes.data);
        setAlerts(alertsRes.data);
        setNodes(nodesRes.data);
        setHoneypots(honeypotsRes.data);
        setThreatMap(threatMapRes.data);

      } catch (error) {
        console.error("Error fetching initial data: ", error);
      }
    };
    fetchData();

    const ws = new WebSocket(WS_URL);
    ws.onmessage = (event) => {
      const newAlert = JSON.parse(event.data);
      setAlerts(prevAlerts => [newAlert, ...prevAlerts]);
    };

    return () => {
      ws.close();
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#0B0F19] text-slate-300 font-sans p-6 selection:bg-emerald-500/30">
      
      {/* HEADER: Clean, Professional, Minimal Logo styling */}
      <header className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <Shield className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">CHAKRAVYUH.</h1>
            <p className="text-sm font-medium text-slate-400">Autonomous Cyber Defense Grid Center</p>
          </div>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-slate-900 border border-slate-800 rounded-full">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className="text-xs font-semibold text-slate-300">Live Telemetry Linked</span>
        </div>
      </header>

      {/* OVERVIEW STATS: Clean modular cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <StatCard title="Total Alerts" value={stats?.alerts_total?.toLocaleString() || "0"} icon={<Activity className="w-5 h-5 text-blue-400" />} trend="+12% today" />
        <StatCard title="Critical Incidents" value={stats?.alerts_critical?.toLocaleString() || "0"} icon={<ShieldAlert className="w-5 h-5 text-rose-400" />} alert />
        <StatCard title="Honeypots Active" value={stats?.honeypots_active?.toLocaleString() || "0"} icon={<Server className="w-5 h-5 text-amber-400" />} />
        <StatCard title="Federated Nodes" value={stats?.nodes_online?.toString() || "0"} icon={<Network className="w-5 h-5 text-emerald-400" />} />
      </div>

      {/* CORE DASHBOARD: 3-Column Layout */}
      <div className="grid grid-cols-12 gap-6 h-[580px] mb-8">
        
        {/* LEFT COLUMN: Threat Alerts Feed */}
        <div className="col-span-12 xl:col-span-3 flex flex-col bg-[#131A2A] border border-[#1E293B] rounded-2xl overflow-hidden shadow-xl">
          <div className="px-5 py-4 border-b border-[#1E293B] bg-[#171f33]/50 flex justify-between items-center">
             <h2 className="text-sm font-semibold text-white">Auto-SOC Intelligence</h2>
             <Wifi className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="p-4 flex-1 overflow-y-auto space-y-3 custom-scrollbar">
            {alerts.map((alert, i) => (
              <div key={i} className={`p-4 rounded-xl border leading-snug group transition-all duration-200 hover:bg-[#1e293b]/50 ${
                alert.severity === 'critical' ? 'border-rose-500/20 bg-rose-500/5' :
                alert.severity === 'high' ? 'border-amber-500/20 bg-amber-500/5' : 'border-blue-500/20 bg-blue-500/5'
              }`}>
                <div className="flex items-center gap-2 mb-2">
                  <span className={`w-2 h-2 rounded-full ${alert.severity === 'critical' ? 'bg-rose-500' : alert.severity === 'high' ? 'bg-amber-500' : 'bg-blue-500'}`}></span>
                  <span className="text-[10px] font-bold tracking-wider uppercase text-slate-400">ID: {alert.id}</span>
                </div>
                <p className="text-sm text-slate-200 font-medium">{alert.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* CENTER COLUMN: The Geo-Spatial Map */}
        <div className="col-span-12 xl:col-span-6 bg-[#131A2A] border border-[#1E293B] rounded-2xl relative overflow-hidden shadow-xl flex flex-col">
          <div className="absolute top-5 left-5 z-10">
             <h2 className="text-sm font-semibold text-white bg-[#131A2A]/80 backdrop-blur-md px-3 py-1.5 rounded-lg border border-[#1E293B]">Sovereign Defense Grid Map</h2>
          </div>
          <div className="absolute bottom-5 left-5 z-10 flex gap-4 bg-[#131A2A]/80 backdrop-blur-md px-4 py-2 rounded-xl border border-[#1E293B]">
             <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span><span className="text-xs font-semibold">Secure</span></div>
             <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span><span className="text-xs font-semibold">Flagged</span></div>
             <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span><span className="text-xs font-semibold">Under Attack</span></div>
          </div>
          
          <div className="flex-1 w-full relative" style={{ height: "500px", background: "linear-gradient(135deg, #0B0F19 0%, #0F1425 100%)" }}>
            <svg width="100%" height="100%" style={{ background: "radial-gradient(circle at 30% 40%, rgba(16, 185, 129, 0.05) 0%, transparent 50%)" }}>
              {/* Grid Background */}
              <defs>
                <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1e293b" strokeWidth="0.5" opacity="0.3" />
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#grid)" />
              
              {/* India Border (Simplified SVG Path) */}
              <g transform="translate(100, 50) scale(1.8, 1.8)">
                <path d="M 68.2 8.3 L 97.3 7.9 L 97.2 25 L 101.9 32.5 L 97.6 35 L 101 40.2 L 95.1 44.5 L 94.3 50 L 88.9 52 L 88.1 59.5 L 82.7 60 L 73 68 L 67.8 65.5 L 68 58.5 L 61 56.5 L 60 52 L 55 51.5 L 52 48 L 48 47.5 L 47.5 42 L 43 40.5 L 42 35.5 L 38 34 L 37 28 L 33.5 27 L 32 20.5 L 28.5 18.5 L 29 14 L 33.5 12 L 36.5 8.5 L 40.5 7 L 45 5.5 L 50 6 L 55 4 L 60 3.5 L 65 4 Z" 
                      fill="#1e293b" stroke="#0f7938" strokeWidth="1.2" opacity="0.6" />
              </g>
              
              {/* Map Markers with Connections */}
              {threatMap?.nodes.map((node) => {
                const color = node.status === 'under_attack' ? '#f43f5e' : node.status === 'online' ? '#10b981' : '#f59e0b';
                const x = (node.location[1] - 68) * 4.5 + 100;
                const y = (32 - node.location[0]) * 4.5 + 50;
                
                return (
                  <g key={node.id}>
                    {/* Pulsing outer ring */}
                    {node.status === 'under_attack' && (
                      <circle cx={x} cy={y} r="15" fill={color} opacity="0.1" style={{ animation: "pulse 2s infinite" }} />
                    )}
                    {/* Connection line to center */}
                    <line x1={x} y1={y} x2="200" y2="150" stroke={color} strokeWidth="0.8" opacity="0.2" strokeDasharray="2,2" />
                    {/* Marker circle */}
                    <circle cx={x} cy={y} r="5" fill={color} stroke="#1e293b" strokeWidth="1.5" />
                    {/* Label */}
                    <text x={x + 8} y={y - 5} fontSize="10" fontWeight="bold" fill="white" fontFamily="Inter, sans-serif">{node.name}</text>
                    <text x={x + 8} y={y + 5} fontSize="9" fill="#94a3b8" fontFamily="Inter, sans-serif">{node.type}</text>
                  </g>
                );
              })}
              
              {/* Central Hub */}
              <circle cx="200" cy="150" r="8" fill="#10b981" stroke="#1e293b" strokeWidth="2" opacity="0.8" />
              <circle cx="200" cy="150" r="3" fill="#ffffff" />
            </svg>
            
            <style>{`
              @keyframes pulse {
                0%, 100% { opacity: 0.1; }
                50% { opacity: 0.3; }
              }
            `}</style>
          </div>
        </div>

        {/* RIGHT COLUMN: Honeypot Interactive Terminal */}
        <div className="col-span-12 xl:col-span-3 flex flex-col bg-[#131A2A] border border-[#1E293B] rounded-2xl overflow-hidden shadow-xl">
           <div className="h-12 bg-[#171f33] border-b border-[#1E293B] px-4 flex items-center justify-between">
              <div className="flex gap-2">
                 <div className="w-3 h-3 rounded-full bg-rose-500/20 border border-rose-500/50"></div>
                 <div className="w-3 h-3 rounded-full bg-amber-500/20 border border-amber-500/50"></div>
                 <div className="w-3 h-3 rounded-full bg-emerald-500/20 border border-emerald-500/50"></div>
              </div>
              <span className="text-xs font-semibold text-slate-400 flex items-center gap-1">
                 <Terminal className="w-3 h-3" /> GenAI Deception Node
              </span>
           </div>
           
           <div className="p-4 flex-1 bg-[#090b14] overflow-y-auto font-mono text-[12px] leading-relaxed custom-scrollbar">
              <div className="text-slate-500 mb-4 pb-2 border-b border-white/5">
                 Welcome to Ubuntu 22.04.2 LTS (GNU/Linux 5.15.0-76-generic x86_64)<br/>
                 Last login: {new Date().toUTCString().slice(0, -4)}
              </div>
              
              <div className="space-y-1">
                {honeypots[0]?.commands_run > 0 && <div>...Honeypot log for {honeypots[0].name}...</div>}
                <div className="flex gap-3 pt-1">
                  <span className="text-slate-600 shrink-0 select-none">[{new Date().toLocaleTimeString('en-US', { hour12: false })}]</span>
                  <span className="text-emerald-500 animate-pulse block w-2 h-4 bg-emerald-500/80"></span>
                </div>
              </div>
           </div>
        </div>

      </div>

        <div className="grid grid-cols-12 gap-6 h-[300px] mb-20">
            <ThreatTimeline alerts={alerts} />
            <AttackDistribution alerts={alerts} />
            <TopTargeted alerts={alerts} />
        </div>
        <Ticker alerts={alerts} />
    </div>
  );
}

// Subcomponents

function StatCard({ title, value, icon, trend, alert }: { title: string, value: string, icon: React.ReactNode, trend?: string, alert?: boolean }) {
  return (
    <div className={`bg-[#131A2A] border rounded-2xl p-5 flex flex-col justify-between shadow-lg relative overflow-hidden ${alert ? 'border-rose-500/30' : 'border-[#1E293B]'}`}>
      {alert && <div className="absolute top-0 right-0 w-32 h-32 bg-rose-500/10 blur-3xl rounded-full translate-x-1/2 -translate-y-1/2"></div>}
      <div className="flex items-start justify-between relative z-10">
        <div className="bg-[#1e293b] p-2.5 rounded-xl border border-white/5">
          {icon}
        </div>
        {trend && <span className="text-xs font-semibold text-slate-400 bg-slate-800 px-2 py-1 rounded-md">{trend}</span>}
      </div>
      <div className="mt-4 relative z-10">
        <h3 className={`text-3xl font-bold tracking-tight ${alert ? 'text-rose-100' : 'text-white'}`}>{value}</h3>
        <p className="text-slate-400 text-sm font-medium mt-1">{title}</p>
      </div>
    </div>
  );
}