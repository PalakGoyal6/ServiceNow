'use client';

import React, { useState } from 'react';
import useSWR from 'swr';
import { apiRequest } from '@/lib/api';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import {
  BarChart3,
  Flame,
  Clock,
  RotateCw,
  Sparkles,
  Shield,
  Layers,
  AlertTriangle,
  CheckCircle2,
} from 'lucide-react';

interface AdminAnalytics {
  total_issues: number;
  open_issues_count: number;
  resolved_issues_count: number;
  open_issues_by_dept: {
    department_code: string;
    department_name: string;
    count: number;
  }[];
  median_resolution_time_hours_by_dept: {
    department_code: string;
    department_name: string;
    median_hours: number;
    sample_size: number;
  }[];
  currently_blocked_tasks_count: number;
  bottleneck_departments: {
    department_code: string;
    blocking_count: number;
  }[];
  urgency_distribution: {
    urgency: number;
    label: string;
    count: number;
  }[];
  classification_source_ratio: {
    llm: number;
    fallback: number;
  };
}

const COLORS = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899'];
const URGENCY_COLORS: Record<string, string> = {
  'Low (1)': '#94a3b8',
  'Medium (2)': '#f59e0b',
  'High (3)': '#f97316',
  'Critical (4)': '#ef4444',
};

export default function AdminAnalyticsPage() {
  const { data: analytics, error, isLoading, mutate } = useSWR<AdminAnalytics>(
    '/admin/analytics',
    (url: string) => apiRequest(url),
    { refreshInterval: 5000 }
  );

  const [isRecomputing, setIsRecomputing] = useState(false);
  const [recomputeMsg, setRecomputeMsg] = useState<string | null>(null);

  const handleRecompute = async () => {
    setIsRecomputing(true);
    setRecomputeMsg(null);
    try {
      const res = await apiRequest<{ message: string }>('/admin/recompute-priorities', {
        method: 'POST',
      });
      setRecomputeMsg(res.message);
      mutate();
    } catch (err: any) {
      alert(`Recompute failed: ${err.message}`);
    } finally {
      setIsRecomputing(false);
    }
  };

  if (isLoading) {
    return (
      <div className="py-20 text-center text-slate-500">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600 mx-auto mb-3"></div>
        <p className="text-sm font-medium">Gathering university operational metrics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-sm">
        Failed to load analytics: {error.message}
      </div>
    );
  }

  const sourceData = [
    { name: 'LLM AI Classified', value: analytics?.classification_source_ratio.llm || 0 },
    { name: 'Fallback Rule-Engine', value: analytics?.classification_source_ratio.fallback || 0 },
  ];

  return (
    <div className="space-y-8 py-4">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-purple-50 text-purple-800 text-xs font-semibold border border-purple-200">
            <Shield className="w-3.5 h-3.5 text-purple-600" />
            <span>Admin Executive Dashboard</span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">
            Cross-Department Analytics & Bottleneck Intelligence
          </h1>
          <p className="text-xs text-slate-500">
            Operational visibility into student caseload, SLA resolution times, and multi-department dependency friction.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRecompute}
            disabled={isRecomputing}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white text-xs font-bold shadow-md transition-all hover:scale-102"
          >
            <RotateCw className={`w-3.5 h-3.5 ${isRecomputing ? 'animate-spin' : ''}`} />
            <span>{isRecomputing ? 'Recalculating...' : 'Recompute Priorities'}</span>
          </button>
        </div>
      </div>

      {recomputeMsg && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-xl flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          <span>{recomputeMsg}</span>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-1">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Total Cases</span>
          <div className="text-3xl font-black text-slate-900">{analytics?.total_issues ?? 0}</div>
          <span className="text-[11px] text-slate-500">End-to-end issues logged</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-1">
          <span className="text-xs font-bold uppercase tracking-wider text-blue-500">Open Cases</span>
          <div className="text-3xl font-black text-blue-600">{analytics?.open_issues_count ?? 0}</div>
          <span className="text-[11px] text-slate-500">Currently in progress</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-1">
          <span className="text-xs font-bold uppercase tracking-wider text-amber-500">Blocked Tasks</span>
          <div className="text-3xl font-black text-amber-600">
            {analytics?.currently_blocked_tasks_count ?? 0}
          </div>
          <span className="text-[11px] text-slate-500">Waiting on prerequisite depts</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-1">
          <span className="text-xs font-bold uppercase tracking-wider text-emerald-500">Resolved Cases</span>
          <div className="text-3xl font-black text-emerald-600">
            {analytics?.resolved_issues_count ?? 0}
          </div>
          <span className="text-[11px] text-slate-500">Successfully completed</span>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 1. Bottleneck Departments Chart (Crucial Feature!) */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-600" />
              <h3 className="font-bold text-sm text-slate-900">
                Department Bottlenecks (Most Often Blocking Others)
              </h3>
            </div>
            <span className="text-xs text-slate-400">Dependency root causes</span>
          </div>

          <p className="text-xs text-slate-500 leading-relaxed">
            Surfaces departments whose unresolved tasks are directly stalling other departments' workflows (e.g. Finance holding up Examinations).
          </p>

          <div className="h-64 w-full">
            {analytics?.bottleneck_departments && analytics.bottleneck_departments.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={analytics.bottleneck_departments}
                  layout="vertical"
                  margin={{ top: 10, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" allowDecimals={false} />
                  <YAxis dataKey="department_code" type="category" tick={{ fontSize: 12 }} />
                  <Tooltip
                    formatter={(val: any) => [`${val} downstream tasks blocked`, 'Blocking Count']}
                  />
                  <Bar dataKey="blocking_count" fill="#f59e0b" radius={[0, 6, 6, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No blocking bottlenecks detected across departments.
              </div>
            )}
          </div>
        </div>

        {/* 2. Median Resolution Time (Hours) */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-blue-600" />
              <h3 className="font-bold text-sm text-slate-900">
                Median Task Resolution Time (Hours)
              </h3>
            </div>
            <span className="text-xs text-slate-400">SLA metric</span>
          </div>

          <p className="text-xs text-slate-500 leading-relaxed">
            Median hours elapsed from task creation/unblocking to final resolution across departments.
          </p>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={analytics?.median_resolution_time_hours_by_dept || []}
                margin={{ top: 10, right: 10, left: -20, bottom: 25 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="department_code"
                  tick={{ fontSize: 11 }}
                  interval={0}
                  angle={-30}
                  textAnchor="end"
                />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip
                  formatter={(val: any) => [`${val} hours`, 'Median Resolution']}
                />
                <Bar dataKey="median_hours" fill="#3b82f6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 3. Open Tasks by Department */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Layers className="w-5 h-5 text-purple-600" />
              <h3 className="font-bold text-sm text-slate-900">
                Open Task Caseload by Department
              </h3>
            </div>
            <span className="text-xs text-slate-400">Active queue size</span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={analytics?.open_issues_by_dept || []}
                margin={{ top: 10, right: 10, left: -20, bottom: 25 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="department_code"
                  tick={{ fontSize: 11 }}
                  interval={0}
                  angle={-30}
                  textAnchor="end"
                />
                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip formatter={(val: any) => [`${val} open tasks`, 'Active Count']} />
                <Bar dataKey="count" fill="#8b5cf6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 4. Urgency & AI Classification Sources */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-emerald-600" />
              <h3 className="font-bold text-sm text-slate-900">
                Urgency Distribution & AI Triage Ratio
              </h3>
            </div>
            <span className="text-xs text-slate-400">Classification mix</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 h-64">
            {/* Urgency Pie */}
            <div className="h-full flex flex-col items-center">
              <span className="text-xs font-bold text-slate-600 mb-1">Issue Urgency Levels</span>
              <ResponsiveContainer width="100%" height="85%">
                <PieChart>
                  <Pie
                    data={analytics?.urgency_distribution || []}
                    dataKey="count"
                    nameKey="label"
                    cx="50%"
                    cy="50%"
                    outerRadius={65}
                    label={({ name, percent }) => `${name.split(' ')[0]}: ${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {analytics?.urgency_distribution.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={URGENCY_COLORS[entry.label] || COLORS[index % COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Classification Source Ratio */}
            <div className="h-full flex flex-col items-center">
              <span className="text-xs font-bold text-slate-600 mb-1">Classifier Engine</span>
              <ResponsiveContainer width="100%" height="85%">
                <PieChart>
                  <Pie
                    data={sourceData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={65}
                    label={({ name, percent }) => `${name.split(' ')[0]}: ${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    <Cell fill="#10b981" />
                    <Cell fill="#64748b" />
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
