import React from 'react';
import { AlertTriangle } from 'lucide-react';
import type { Alert } from '../types';

export default function Ticker({ alerts }: { alerts: Alert[] }) {
    const criticalAlerts = alerts.filter(a => a.severity === 'critical' || a.severity === 'high');
    const tickerData = criticalAlerts.map(a => `${a.severity.toUpperCase()} alert: ${a.description}`);

    return (
        <div className="fixed bottom-0 left-0 right-0 bg-[#131A2A] border-t border-[#1E293B] h-12 flex items-center overflow-hidden">
            <div className="bg-rose-500/80 h-full flex items-center px-4 z-10 relative shadow-[4px_0_12px_rgba(0,0,0,0.5)]">
                <AlertTriangle className="w-5 h-5 text-white" />
                <span className="text-sm font-bold text-white ml-2 whitespace-nowrap">CRITICAL ALERTS</span>
            </div>
            <div className="flex-1 relative h-full overflow-hidden">
                <div className="absolute top-0 left-0 h-full w-full flex items-center animate-marquee">
                    {tickerData.map((text, i) => (
                        <p key={i} className="text-slate-300 text-sm font-medium mx-12 whitespace-nowrap">
                            {text}
                        </p>
                    ))}
                     {tickerData.map((text, i) => (
                        <p key={`dup-${i}`} className="text-slate-300 text-sm font-medium mx-12 whitespace-nowrap">
                            {text}
                        </p>
                    ))}
                </div>
            </div>
            <style>{`
                @keyframes marquee {
                    0% { transform: translateX(0%); }
                    100% { transform: translateX(-50%); }
                }
                .animate-marquee {
                    animation: marquee 40s linear infinite;
                }
            `}</style>
        </div>
    );
}
