'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import useSWR from 'swr';
import { useAuth } from '@/lib/auth-context';
import { apiRequest } from '@/lib/api';
import StatusBadge from '@/components/StatusBadge';
import PriorityBadge from '@/components/PriorityBadge';
import {
  ListTodo,
  Clock,
  Lock,
  CheckCircle2,
  AlertCircle,
  Calendar,
  Sparkles,
  ArrowRight,
  Filter,
  User,
  Zap,
} from 'lucide-react';

interface StaffTaskItem {
  task_id: string;
  issue_id: string;
  title: string;
  student_name: string;
  student_roll_no?: string | null;
  status: string;
  dept_summary: string;
  action_needed: string;
  effective_priority: number;
  priority_label: string;
  priority_inherited: boolean;
  deadline?: string | null;
  created_at: string;
  unblocked_at?: string | null;
  is_newly_unblocked: boolean;
  is_auto_classified: boolean;
  other_departments_count: number;
  other_departments_preview: { code: string; status: string }[];
}

interface StaffStats {
  active_count: number;
  blocked_count: number;
  resolved_this_week_count: number;
  department_name: string;
  department_code: string;
}

export default function StaffDashboardPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'active' | 'blocked' | 'resolved' | 'all'>('active');
  const [sortBy, setSortBy] = useState<'priority' | 'created'>('priority');

  const { data: stats } = useSWR<StaffStats>(
    '/staff/stats',
    (url: string) => apiRequest(url),
    { refreshInterval: 5000 }
  );

  const { data: tasks, error, isLoading } = useSWR<StaffTaskItem[]>(
    `/staff/tasks?status=${activeTab}&sort=${sortBy}`,
    (url: string) => apiRequest(url),
    { refreshInterval: 5000 }
  );

  return (
    <div className="space-y-8 py-4">
      {/* Department Header & Stats */}
      <div className="bg-slate-900 text-white rounded-2xl p-6 sm:p-8 shadow-xl border border-slate-800 relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-extrabold px-2.5 py-1 rounded-md bg-blue-500/20 text-blue-400 border border-blue-400/30">
                {stats?.department_code || user?.department_code || 'DEPT'}
              </span>
              <span className="text-xs text-slate-400">Department Dashboard</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              {stats?.department_name || user?.department_name || 'Staff Task Queue'}
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 max-w-xl">
              Real-time actionable queue sorted by effective priority. Tasks waiting on prerequisite departments are automatically held as blocked and unblock upon resolution.
            </p>
          </div>

          {/* Metric Cards */}
          <div className="grid grid-cols-3 gap-3 sm:gap-4 min-w-[280px]">
            <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-700 text-center">
              <div className="text-2xl font-black text-blue-400">{stats?.active_count ?? 0}</div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mt-0.5">
                Active
              </div>
            </div>
            <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-700 text-center">
              <div className="text-2xl font-black text-amber-400">{stats?.blocked_count ?? 0}</div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mt-0.5">
                Blocked
              </div>
            </div>
            <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-700 text-center">
              <div className="text-2xl font-black text-emerald-400">
                {stats?.resolved_this_week_count ?? 0}
              </div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mt-0.5">
                Resolved/Wk
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Task Queue Table/List */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-5">
        {/* Filter Tabs & Sort Controls */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
          <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-100 border border-slate-200/80">
            <button
              onClick={() => setActiveTab('active')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeTab === 'active'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Active Tasks
            </button>
            <button
              onClick={() => setActiveTab('blocked')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeTab === 'blocked'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Blocked
            </button>
            <button
              onClick={() => setActiveTab('resolved')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeTab === 'resolved'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Resolved
            </button>
            <button
              onClick={() => setActiveTab('all')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeTab === 'all'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              All
            </button>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-500 font-medium">Sort by:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="p-1.5 rounded-lg border border-slate-300 text-xs font-semibold bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="priority">Priority (Inherited first)</option>
              <option value="created">Newest Date</option>
            </select>
            <span className="text-slate-400 text-[11px] ml-2">Live polling (5s)</span>
          </div>
        </div>

        {/* Task List */}
        {isLoading ? (
          <div className="py-16 text-center text-slate-500">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-3"></div>
            <p className="text-sm">Fetching department task queue...</p>
          </div>
        ) : error ? (
          <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs">
            Failed to load tasks: {error.message}
          </div>
        ) : tasks?.length === 0 ? (
          <div className="py-16 text-center text-slate-500 space-y-2">
            <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto" />
            <h3 className="text-sm font-bold text-slate-800">No tasks in this view</h3>
            <p className="text-xs text-slate-400">All department queues are currently clear.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {tasks?.map((task) => (
              <Link
                key={task.task_id}
                href={`/staff/tasks/${task.task_id}`}
                className="group block py-4 px-2 sm:px-4 rounded-xl hover:bg-slate-50 transition-all border border-transparent hover:border-slate-200"
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div className="space-y-1.5 flex-1">
                    {/* Badges Bar */}
                    <div className="flex items-center gap-2 flex-wrap">
                      <PriorityBadge
                        priority={task.effective_priority}
                        label={task.priority_label}
                        inherited={task.priority_inherited}
                      />
                      <StatusBadge status={task.status} size="sm" />

                      {task.is_newly_unblocked && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-500 text-white text-[10px] font-extrabold uppercase tracking-wider animate-pulse">
                          <Zap className="w-3 h-3" />
                          <span>Newly Unblocked</span>
                        </span>
                      )}

                      {task.is_auto_classified && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-100 text-slate-600 text-[10px] font-medium border border-slate-200">
                          Auto-Classified
                        </span>
                      )}

                      {task.deadline && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 text-[11px] font-medium">
                          <Calendar className="w-3 h-3 text-amber-600" />
                          <span>Deadline: {task.deadline}</span>
                        </span>
                      )}
                    </div>

                    {/* Issue Title */}
                    <h3 className="text-base font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
                      {task.title}
                    </h3>

                    {/* Department Summary & Action */}
                    <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed">
                      <span className="font-semibold text-slate-700">Action:</span> {task.action_needed}
                    </p>

                    {/* Meta info: student and other depts */}
                    <div className="flex items-center gap-4 text-xs text-slate-500 pt-1 flex-wrap">
                      <span className="flex items-center gap-1">
                        <User className="w-3.5 h-3.5 text-slate-400" />
                        <span className="font-medium text-slate-700">{task.student_name}</span>
                        {task.student_roll_no && (
                          <span className="text-slate-400">({task.student_roll_no})</span>
                        )}
                      </span>

                      {task.other_departments_count > 0 && (
                        <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full font-medium">
                          +{task.other_departments_count} other{' '}
                          {task.other_departments_count === 1 ? 'department' : 'departments'}
                        </span>
                      )}

                      <span className="text-[11px] text-slate-400">
                        Created {new Date(task.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end md:self-center text-xs font-bold text-blue-600 group-hover:translate-x-1 transition-transform">
                    <span>Manage Task</span>
                    <ArrowRight className="w-4 h-4" />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
