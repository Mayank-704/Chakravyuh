export interface Stats {
  total_threats: number;
  critical_count: number;
  honeypot_trapped_count: number;
  federated_node_count: number;
}

export interface Alert {
  id: number;
  severity: "critical" | "high" | "medium" | "low";
  description: string;
}

export interface Honeypot {
  id: string;
  name: string;
  status: string;
}

export interface NodeLocation {
  id: string;
  location: [number, number];
}

export interface ThreatMapData {
  nodes: NodeLocation[];
  attacks: { source: string; target: string }[];
}

export interface FederatedStatus {
  id: string;
  status: string;
  sample_count: number;
}