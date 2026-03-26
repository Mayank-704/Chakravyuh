import React, { useEffect, useState, useMemo } from 'react';
import { Shield, ShieldAlert, Network, Server, Terminal, Activity, Wifi } from 'lucide-react';
import { MapContainer, GeoJSON, Marker, Popup, Polyline } from 'react-leaflet';
import * as L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import axios from 'axios';
import type { Stats, Alert, FederatedStatus, Honeypot, ThreatMap } from '../types';
import { ThreatTimeline, AttackDistribution, TopTargeted } from './charts';
import Ticker from './Ticker';

const API_BASE_URL = 'http://localhost:8000/api';
const WS_URL = 'ws://localhost:8000/ws/alerts';

function StatCard({ title, value, icon, alert, trend }: { title: string, value: string | number, icon: React.ReactNode, alert?: boolean, trend?: string }) {
  return (
    <div className="bg-[#131A2A] border border-[#1E293B] p-5 rounded-2xl relative overflow-hidden group hover:border-[#334155] transition-colors">
      {alert && <div className="absolute top-0 right-0 w-24 h-24 bg-rose-500/10 blur-2xl rounded-full -mr-12 -mt-12"></div>}
      <div className="flex justify-between items-start mb-4">
        <div className="p-2 bg-[#1E293B]/50 rounded-xl">{icon}</div>
        {trend && <span className="text-xs font-semibold text-emerald-400 bg-emerald-400/10 px-2 py-1 rounded-full">{trend}</span>}
      </div>
      <p className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-1">{title}</p>
      <h3 className="text-3xl font-bold text-white tracking-tight">{value}</h3>
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [nodes, setNodes] = useState<FederatedStatus[]>([]);
  const [honeypots, setHoneypots] = useState<Honeypot[]>([]);
  const [threatMap, setThreatMap] = useState<ThreatMap | null>(null);
  const [selectedNode, setSelectedNode] = useState<any | null>(null);
  const [indiaGeoJson, setIndiaGeoJson] = useState<any>(null);

  const activeNodes = useMemo(() => {
    if (!threatMap?.nodes) return [];
    return threatMap.nodes.map(node => {
      const affectingAlerts = alerts.filter(a => a.target === node.name || a.target === node.id || a.target.includes(node.name));
      const latestAlert = affectingAlerts[0];
      let currentStatus = node.status;
      if (latestAlert && (latestAlert.severity === 'critical' || latestAlert.severity === 'high')) {
        currentStatus = 'under_attack';
      } else if (latestAlert && latestAlert.severity === 'medium') {
        currentStatus = 'flagged';
      }
      return { ...node, status: currentStatus, latestAlert };
    });
  }, [threatMap, alerts]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, alertsRes, nodesRes, honeypotsRes, threatMapRes] = await Promise.all([
          axios.get<Stats>(`${API_BASE_URL}/stats`),
          axios.get<Alert[]>(`${API_BASE_URL}/alerts`),
          axios.get<FederatedStatus[]>(`${API_BASE_URL}/federated/status`),
          axios.get<Honeypot[]>(`${API_BASE_URL}/honeypots`),
          axios.get<ThreatMap>(`${API_BASE_URL}/threat-map`)
        ]);
        setStats(statsRes.data);
        setAlerts(alertsRes.data);
        setNodes(nodesRes.data);
        setHoneypots(honeypotsRes.data);
        setThreatMap(threatMapRes.data);
        
        try {
           const geoRes = await axios.get('/india.geojson');
           setIndiaGeoJson(geoRes.data);
        } catch(e) { console.error('Geojson failed:', e); }

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

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <StatCard title="Total Alerts" value={stats?.alerts_total?.toLocaleString() || "0"} icon={<Activity className="w-5 h-5 text-blue-400" />} trend="+12% today" />
        <StatCard title="Critical Incidents" value={stats?.alerts_critical?.toLocaleString() || "0"} icon={<ShieldAlert className="w-5 h-5 text-rose-400" />} alert />
        <StatCard title="Honeypots Active" value={stats?.honeypots_active?.toLocaleString() || "0"} icon={<Server className="w-5 h-5 text-amber-400" />} />
        <StatCard title="Federated Nodes" value={stats?.nodes_online?.toString() || "0"} icon={<Network className="w-5 h-5 text-emerald-400" />} />
      </div>

      <div className="grid grid-cols-12 gap-6 h-[580px] mb-8">
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

        <div className="col-span-12 xl:col-span-6 bg-[#131A2A] border border-[#1E293B] rounded-2xl relative overflow-hidden shadow-xl flex flex-col">
          <div className="absolute top-5 left-5 z-[1000]">
             <h2 className="text-sm font-semibold text-white bg-[#131A2A]/80 backdrop-blur-md px-3 py-1.5 rounded-lg border border-[#1E293B]">Sovereign Defense Grid Map</h2>
          </div>
          <div className="absolute bottom-5 left-5 z-[1000] flex gap-4 bg-[#131A2A]/80 backdrop-blur-md px-4 py-2 rounded-xl border border-[#1E293B]">
             <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span><span className="text-xs font-semibold">Secure</span></div>
             <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span><span className="text-xs font-semibold">Flagged</span></div>
             <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span><span className="text-xs font-semibold">Under Attack</span></div>
          </div>
          
          <div className="flex-1 w-full relative leaflet-transparent-bg" style={{ height: "500px", minHeight: "500px", background: "#0B0F19" }}>
            <MapContainer
              center={[22, 80]}
              zoom={4.5}
              zoomControl={false}
              style={{ width: '100%', height: '100%', background: 'transparent' }}
              attributionControl={false}
            >
              {indiaGeoJson && (
                <GeoJSON
                  data={indiaGeoJson}
                  style={{
                    color: '#1E293B',
                    weight: 1.5,
                    fillColor: '#131A2A',
                    fillOpacity: 1,
                  }}
                />
              )}

              {activeNodes?.map((node, i) => (
                <Polyline 
                  key={`line-${i}`} 
                  positions={[[node.location[0], node.location[1]], [28.6139, 77.2090]]} 
                  pathOptions={{ 
                    color: node.status === 'under_attack' ? '#f43f5e' : node.status === 'online' ? '#10b981' : '#f59e0b',
                    weight: 1.5,
                    opacity: 0.5,
                    dashArray: '4, 4'
                  }} 
                />
              ))}

              {activeNodes?.map((node) => {
                const color = node.status === 'under_attack' ? '#f43f5e' : node.status === 'online' ? '#10b981' : '#f59e0b';
                
                const isPulsing = node.status === 'under_attack';
                const htmlContent = `
                  <div style="position: relative; display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer;">
                    ${isPulsing ? `<div style="position: absolute; width: 48px; height: 48px; border-radius: 50%; background: rgba(244, 63, 94, 0.2); animation: ping 1s infinite;"></div>` : ''}
                    <div style="width: 12px; height: 12px; border-radius: 50%; border: 2px solid #131A2A; background-color: ${color}; z-index: 10;"></div>
                    <div style="margin-top: 4px; display: flex; flex-direction: column; align-items: center; z-index: 10;">
                      <span style="font-size: 10px; font-weight: bold; color: white; text-shadow: 0 1px 2px rgba(0,0,0,0.5); white-space: nowrap;">${node.name}</span>
                      <span style="font-size: 8px; color: #cbd5e1; text-shadow: 0 1px 1px rgba(0,0,0,0.3); white-space: nowrap;">${node.type}</span>
                    </div>
                  </div>
                `;

                const customMarkerIcon = L.divIcon({
                  html: htmlContent,
                  className: '',
                  iconSize: [40, 40],
                  iconAnchor: [20, 20]
                });

                return (
                  <Marker 
                    key={node.id} 
                    position={[node.location[0], node.location[1]]} 
                    icon={customMarkerIcon}
                    eventHandlers={{
                      click: () => setSelectedNode({...node}),
                    }}
                  />
                );
              })}

              <Marker 
                position={[28.6139, 77.2090]}
                icon={L.divIcon({
                  html: `
                    <div style="position: relative; display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer;">
                      <div style="position: absolute; width: 32px; height: 32px; border-radius: 50%; background: rgba(16, 185, 129, 0.2); animation: pulse 2s infinite;"></div>
                      <div style="width: 20px; height: 20px; border-radius: 50%; background: #10b981; border: 2px solid #131A2A; z-index: 10; display: flex; align-items: center; justify-content: center;">
                        <div style="width: 8px; height: 8px; border-radius: 50%; background: white;"></div>
                      </div>
                      <div style="margin-top: 4px; z-index: 10;">
                        <span style="font-size: 10px; font-weight: bold; color: #10b981; text-shadow: 0 1px 2px rgba(0,0,0,0.5); white-space: nowrap;">CERT-In Hub</span>
                      </div>
                    </div>
                  `,
                  className: '',
                  iconSize: [40, 40],
                  iconAnchor: [20, 20]
                })}
              />

              {selectedNode && (
                <Popup
                  position={[selectedNode.location[0], selectedNode.location[1]]}
                  offset={[0, -10]}
                  eventHandlers={{
                     remove: () => setSelectedNode(null),
                  }}
                  className="leaflet-custom-popup"
                >
                  <div className="bg-[#131A2A] border border-[#1E293B] shadow-2xl overflow-hidden rounded-xl w-[250px] !m-0 !p-0">
                    <div className="p-3 border-b border-[#1E293B] bg-[#171f33]/80">
                      <h3 className="text-white font-bold text-sm tracking-tight m-0 leading-none">{selectedNode.name}</h3>
                      <p className="text-slate-400 text-[10px] uppercase font-bold tracking-wider mt-1 m-0 leading-none">{selectedNode.type}</p>
                    </div>
                    
                    <div className="p-3">
                      {selectedNode.latestAlert ? (
                        <div className="bg-rose-500/10 border border-rose-500/20 p-2.5 rounded-lg">
                          <div className="flex items-center gap-2 mb-2">
                             <span className="text-rose-500 text-xs font-bold uppercase tracking-wider">Active Threat</span>
                          </div>
                          <p className="text-slate-300 text-xs leading-snug m-0">{selectedNode.latestAlert.description}</p>
                        </div>
                      ) : (
                        <div className="bg-emerald-500/10 border border-emerald-500/20 p-3 rounded-lg flex flex-col items-center justify-center py-4">
                          <span className="text-emerald-500 text-xs font-bold uppercase tracking-wider">System Secure</span>
                        </div>
                      )}
                    </div>
                  </div>
                </Popup>
              )}
            </MapContainer>
          </div>
        </div>

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
              <div className="space-y-2">
                 <div className="flex gap-2"><span className="text-emerald-500">root@honeypot-dmz:~#</span><span className="text-slate-300"> tail -f /var/log/auth.log</span></div>
                 {alerts.slice(0,5).map((a, idx) => (
                    <div key={idx} className={`${a.severity === 'critical' ? 'text-rose-400' : 'text-slate-400'}`}>
                       [{new Date().toISOString()}] Failed password for root from {a.source_ip} port 22 ssh2
                    </div>
                 ))}
                 <div className="flex gap-2"><span className="text-emerald-500 animate-pulse">_</span></div>
              </div>
           </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
         <ThreatTimeline alerts={alerts} />
         <AttackDistribution alerts={alerts} />
         <TopTargeted alerts={alerts} />
      </div>
      
      <Ticker alerts={alerts} />
    </div>
  );
}