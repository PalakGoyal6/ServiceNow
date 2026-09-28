'use client';

import React from 'react';
import Link from 'next/link';
import useSWR from 'swr';
import { useAuth } from '@/lib/auth-context';
import { apiRequest } from '@/lib/api';
import StatusBadge from '@/components/StatusBadge';
import { PlusCircle, FileText, ArrowRight, Clock, CheckCircle2, AlertCircle } from 'lucide-react';

interface StudentIssueCard {
  id: string;
  title: string;
  urgency: number;
  status: string;
  created_at: string;
  resolved_at?: string | null;
  department_statuses: {
    department_code: string;
    department_name: string;
    status: string;
    action_needed: string;
  }[];
}

export default function StudentDashboardPage() {
  const { user } = useAuth();
  const { data: issues, error, isLoading } = useSWR<StudentIssueCard[]>(
    '/student/issues',
    (url: string) => apiRequest(url),
    { refreshInterval: 5000 }
  );

  const activeIssues = issues?.filter((i) => i.status === 'open') || [];
  const resolvedIssues = issues?.filter((i) => i.status === 'resolved') || [];

  return (
    <div className="space-y-8 py-4">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-emerald-950 rounded-2xl p-6 sm:p-8 text-white shadow-lg relative overflow-hidden">
        <div className="relative z-10 max-w-2xl space-y-3">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 text-xs font-semibold border border-emerald-400/30">
            Student Support Center
          </span>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
            Welcome, {user?.full_name || 'Student'}
          </h1>
          <p className="text-slate-300 text-sm">
            Describe your problem once in your own words. Our AI triage system coordinates all required university departments in sequence without duplicate paperwork.
          </p>
          <div className="pt-2">
            <Link
              href="/student/new"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold text-sm shadow-md transition-all hover:scale-102"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Submit a New Issue</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Issues Content */}
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <FileText className="w-5 h-5 text-emerald-600" />
            <span>My Support Requests</span>
          </h2>
          <span className="text-xs text-slate-500">Live updates every 5s</span>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-slate-500 bg-white rounded-2xl border border-slate-200">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600 mx-auto mb-3"></div>
            <p className="text-sm">Loading your issues...</p>
          </div>
        ) : error ? (
          <div className="p-6 bg-rose-50 text-rose-800 rounded-xl border border-rose-200 text-sm">
            Failed to load issues: {error.message}
          </div>
        ) : issues?.length === 0 ? (
          <div className="p-12 text-center bg-white rounded-2xl border border-slate-200 space-y-3">
            <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 mx-auto flex items-center justify-center">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-slate-800">No active support issues</h3>
            <p className="text-slate-500 text-xs max-w-sm mx-auto">
              You do not have any open support requests at this time. Click below if you need assistance with anything.
            </p>
            <div className="pt-2">
              <Link
                href="/student/new"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-900 text-white text-xs font-semibold hover:bg-slate-800 transition-colors"
              >
                <PlusCircle className="w-4 h-4" />
                <span>Submit Support Request</span>
              </Link>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Active Issues */}
            {activeIssues.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Active Issues ({activeIssues.length})
                </h3>
                <div className="grid grid-cols-1 gap-3.5">
                  {activeIssues.map((issue) => (
                    <Link
                      key={issue.id}
                      href={`/student/issues/${issue.id}`}
                      className="group bg-white rounded-xl border border-slate-200 hover:border-emerald-300 p-5 shadow-sm hover:shadow-md transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                    >
                      <div className="space-y-2 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <StatusBadge status={issue.status} size="sm" />
                          <span className="text-xs text-slate-400">
                            Submitted on {new Date(issue.created_at).toLocaleDateString()}
                          </span>
                        </div>
                        <h4 className="text-base font-bold text-slate-900 group-hover:text-emerald-700 transition-colors">
                          {issue.title}
                        </h4>

                        {/* Department Chips Row */}
                        <div className="flex items-center gap-2 flex-wrap pt-1">
                          <span className="text-xs text-slate-500 font-medium">Departments:</span>
                          {issue.department_statuses.map((dept, idx) => (
                            <span
                              key={idx}
                              className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 text-xs font-medium text-slate-700"
                            >
                              <span className="font-mono text-[11px] text-slate-500 font-bold">
                                {dept.department_code}
                              </span>
                              <span className="text-slate-400">•</span>
                              <span className="capitalize text-slate-800">{dept.status.replace(/_/g, ' ')}</span>
                            </span>
                          ))}
                        </div>
                      </div>

                      <div className="flex items-center gap-2 text-xs font-semibold text-emerald-700 group-hover:translate-x-1 transition-transform">
                        <span>View Progress</span>
                        <ArrowRight className="w-4 h-4" />
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {/* Resolved Issues */}
            {resolvedIssues.length > 0 && (
              <div className="space-y-3 pt-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Resolved History ({resolvedIssues.length})
                </h3>
                <div className="grid grid-cols-1 gap-3">
                  {resolvedIssues.map((issue) => (
                    <Link
                      key={issue.id}
                      href={`/student/issues/${issue.id}`}
                      className="bg-white/80 rounded-xl border border-slate-200 p-4 hover:border-slate-300 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 opacity-90 hover:opacity-100"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <StatusBadge status={issue.status} size="sm" />
                          <span className="text-xs text-slate-400">
                            Resolved on {issue.resolved_at ? new Date(issue.resolved_at).toLocaleDateString() : 'recently'}
                          </span>
                        </div>
                        <h4 className="text-sm font-semibold text-slate-800">{issue.title}</h4>
                      </div>
                      <span className="text-xs font-medium text-slate-500 flex items-center gap-1">
                        <span>Details</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </span>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
