import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar, Legend } from 'recharts';
import { Shield, Target, PieChart as PieChartIcon } from 'lucide-react';
import type { Alert } from '../types';

const COLORS = ['#f43f5e', '#f59e0b', '#10b981', '#3b82f6'];

export function ThreatTimeline({ alerts }: { alerts: Alert[] }) {
    const timelineData = alerts.reduce((acc, alert) => {
        const hour = new Date(alert.timestamp).getHours();
        const hourStr = `${hour}:00`;
        const existing = acc.find(d => d.time === hourStr);
        if (existing) {
            existing.attacks++;
        } else {
            acc.push({ time: hourStr, attacks: 1 });
        }
        return acc;
    }, [] as { time: string; attacks: number }[]).sort((a, b) => a.time.localeCompare(b.time));

  return (
    <div className="w-full flex flex-col bg-[#131A2A] border border-[#1E293B] rounded-2xl overflow-hidden shadow-xl min-h-[320px]">
        <div className="px-5 py-4 border-b border-[#1E293B] bg-[#171f33]/50 flex justify-between items-center">
            <h2 className="text-sm font-semibold text-white flex items-center gap-2"><Shield className="w-4 h-4 text-blue-400" />24-Hour Threat Timeline</h2>
        </div>
        <div className="p-4 h-[260px]">
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={timelineData} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                    <defs>
                        <linearGradient id="colorUv" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#8884d8" stopOpacity={0.8}/>
                        <stop offset="95%" stopColor="#8884d8" stopOpacity={0}/>
                        </linearGradient>
                    </defs>
                    <XAxis dataKey="time" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                    <Tooltip
                        contentStyle={{
                            backgroundColor: 'var(--theme-surface-alt)',
                            border: '2px solid var(--theme-border)',
                            color: 'var(--theme-text-strong)',
                        }}
                        labelStyle={{ color: 'var(--theme-text-strong)', fontWeight: 700 }}
                        itemStyle={{ color: 'var(--theme-text)' }}
                    />
                    <Area type="monotone" dataKey="attacks" stroke="#8884d8" fillOpacity={1} fill="url(#colorUv)" />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    </div>
  );
}

export function AttackDistribution({ alerts }: { alerts: Alert[] }) {
    const distributionData = alerts.reduce((acc, alert) => {
        const existing = acc.find(d => d.name === alert.attack_type);
        if (existing) {
            existing.value++;
        } else {
            acc.push({ name: alert.attack_type, value: 1 });
        }
        return acc;
    }, [] as { name: string; value: number }[]);

    return (
        <div className="w-full flex flex-col bg-[#131A2A] border border-[#1E293B] rounded-2xl overflow-hidden shadow-xl min-h-[320px]">
            <div className="px-5 py-4 border-b border-[#1E293B] bg-[#171f33]/50 flex justify-between items-center">
                <h2 className="text-sm font-semibold text-white flex items-center gap-2"><PieChartIcon className="w-4 h-4 text-amber-400" />Attack Type Distribution</h2>
            </div>
            <div className="p-4 h-[260px]">
                <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                        <Pie data={distributionData} cx="50%" cy="50%" labelLine={false} outerRadius={80} fill="#8884d8" dataKey="value">
                            {distributionData.map((entry, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
                        </Pie>
                        <Tooltip
                            contentStyle={{
                                backgroundColor: 'var(--theme-surface-alt)',
                                border: '2px solid var(--theme-border)',
                                color: 'var(--theme-text-strong)',
                            }}
                            labelStyle={{ color: 'var(--theme-text-strong)', fontWeight: 700 }}
                            itemStyle={{ color: 'var(--theme-text)' }}
                        />
                        <Legend iconSize={10} layout="vertical" verticalAlign="middle" align="right" wrapperStyle={{ color: 'var(--theme-text)' }} />
                    </PieChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}

export function TopTargeted({ alerts }: { alerts: Alert[] }) {
    const targetedData = alerts.reduce((acc, alert) => {
        const existing = acc.find(d => d.name === alert.target);
        if (existing) {
            existing.attacks++;
        } else {
            acc.push({ name: alert.target, attacks: 1 });
        }
        return acc;
    }, [] as { name: string; attacks: number }[]).sort((a, b) => b.attacks - a.attacks).slice(0, 5);

    return (
        <div className="w-full flex flex-col bg-[#131A2A] border border-[#1E293B] rounded-2xl overflow-hidden shadow-xl min-h-[320px]">
            <div className="px-5 py-4 border-b border-[#1E293B] bg-[#171f33]/50 flex justify-between items-center">
                <h2 className="text-sm font-semibold text-white flex items-center gap-2"><Target className="w-4 h-4 text-rose-400" />Top Targeted Institutions</h2>
            </div>
            <div className="p-4 h-[260px]">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={targetedData} layout="vertical" margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                        <XAxis type="number" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                        <YAxis type="category" dataKey="name" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                        <Tooltip
                            contentStyle={{
                                backgroundColor: 'var(--theme-surface-alt)',
                                border: '2px solid var(--theme-border)',
                                color: 'var(--theme-text-strong)',
                            }}
                            labelStyle={{ color: 'var(--theme-text-strong)', fontWeight: 700 }}
                            itemStyle={{ color: 'var(--theme-text)' }}
                        />
                        <Bar dataKey="attacks" fill="#8884d8" />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
