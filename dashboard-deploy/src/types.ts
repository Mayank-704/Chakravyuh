export interface Stats {
    total_threats: number;
    critical_count: number;
    honeypot_trapped_count: number;
    federated_node_count: number;
    alerts_total: number;
    alerts_critical: number;
    honeypots_active: number;
    nodes_online: number;
}

export interface Alert {
    id: number;
    severity: 'critical' | 'high' | 'medium' | 'low';
    source_ip: string;
    target: string;
    attack_type: string;
    description: string;
    status: string;
    timestamp: string;
    ttps: string[];
    session_id: string | null;
}

export interface Honeypot {
    id: string;
    name: string;
    institution_type: string;
    status: string;
    port: number;
    attacker_ip: string;
    session_id: string;
    commands_run: number;
    started_at: string;
}

export interface ThreatMapNode {
    id: string;
    name: string;
    location: [number, number];
    type: string;
    status: string;
}

export interface ThreatMapAttack {
    id: string;
    source_ip: string;
    source_country: string;
    target: string;
    severity: string;
    trapped: boolean;
}

export interface ThreatMap {
    nodes: ThreatMapNode[];
    attacks: ThreatMapAttack[];
}

export interface FederatedStatus {
    id: string;
    name: string;
    status: string;
    sample_count: number;
    last_sync: string;
    model_version: string;
}