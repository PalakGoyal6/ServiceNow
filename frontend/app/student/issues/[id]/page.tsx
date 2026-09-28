'use client';

import React, { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import useSWR from 'swr';
import { apiRequest, Message, ExecutionStage } from '@/lib/api';
import StatusBadge from '@/components/StatusBadge';
import ExecutionOrderTracker from '@/components/ExecutionOrderTracker';
import {
  ArrowLeft,
  Calendar,
  Send,
  AlertTriangle,
  RotateCcw,
  MessageSquare,
  Sparkles,
  CheckCircle2,
  Clock,
  Building,
} from 'lucide-react';

interface StudentIssueDetail {
  id: string;
  title: string;
  status: string;
  urgency: number;
  deadline?: string | null;
  created_at: string;
  resolved_at?: string | null;
  tasks: {
    id: string;
    department_id: number;
    department_code: string;
    department_name: string;
    status: string;
    action_needed: string;
    resolved_at?: string | null;
  }[];
  execution_order: ExecutionStage[];
  messages: Message[];
  waiting_banner?: {
    department_name: string;
    latest_message: string;
  } | null;
}

export default function StudentIssueDetailPage() {
  const params = useParams();
  const router = useRouter();
  const issueId = params?.id as string;

  const { data: issue, error, mutate } = useSWR<StudentIssueDetail>(
    issueId ? `/student/issues/${issueId}` : null,
    (url: string) => apiRequest(url),
    { refreshInterval: 5000 }
  );

  const [replyText, setReplyText] = useState('');
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const [reopenNote, setReopenNote] = useState('');
  const [showReopenModal, setShowReopenModal] = useState(false);
  const [isReopening, setIsReopening] = useState(false);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyText.trim()) return;

    setIsSendingMessage(true);
    try {
      await apiRequest(`/student/issues/${issueId}/messages`, {
        method: 'POST',
        body: JSON.stringify({ body: replyText.trim() }),
      });
      setReplyText('');
      mutate();
    } catch (err: any) {
      alert(`Failed to send message: ${err.message}`);
    } finally {
      setIsSendingMessage(false);
    }
  };

  const handleReopen = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reopenNote.trim()) return;

    setIsReopening(true);
    try {
      await apiRequest(`/student/issues/${issueId}/reopen`, {
        method: 'POST',
        body: JSON.stringify({ body: reopenNote.trim() }),
      });
      setShowReopenModal(false);
      setReopenNote('');
      mutate();
    } catch (err: any) {
      alert(`Failed to reopen issue: ${err.message}`);
    } finally {
      setIsReopening(false);
    }
  };

  if (error) {
    return (
      <div className="py-12 text-center max-w-lg mx-auto space-y-4">
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm">
          {error.message || 'Issue not found'}
        </div>
        <Link
          href="/student"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 hover:text-slate-900"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to My Issues</span>
        </Link>
      </div>
    );
  }

  if (!issue) {
    return (
      <div className="py-20 text-center text-slate-500">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600 mx-auto mb-3"></div>
        <p className="text-sm">Loading issue details...</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-6 space-y-6">
      {/* Top back navigation */}
      <div className="flex items-center justify-between">
        <Link
          href="/student"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to My Issues</span>
        </Link>

        {issue.status === 'resolved' && (
          <button
            onClick={() => setShowReopenModal(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-100 text-slate-700 text-xs font-semibold transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reopen Issue</span>
          </button>
        )}
      </div>

      {/* Prominent Waiting on Student Action Banner */}
      {issue.waiting_banner && (
        <div className="p-4 rounded-xl bg-gradient-to-r from-purple-50 to-indigo-50 border-2 border-purple-300 shadow-sm space-y-2 animate-fade-in">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-purple-700 flex-shrink-0" />
            <h3 className="font-bold text-sm text-purple-900">
              {issue.waiting_banner.department_name} needs something from you
            </h3>
          </div>
          <p className="text-xs text-purple-800 pl-7 leading-relaxed font-medium">
            "{issue.waiting_banner.latest_message}"
          </p>
          <p className="text-[11px] text-purple-600 pl-7">
            Reply in the message thread below to provide information and advance your case.
          </p>
        </div>
      )}

      {/* Issue Overview Header Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="space-y-1 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <StatusBadge status={issue.status} size="md" />
              <span className="text-xs text-slate-400">
                Submitted on {new Date(issue.created_at).toLocaleDateString()}
              </span>
              {issue.deadline && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 text-xs font-medium">
                  <Calendar className="w-3 h-3 text-amber-600" />
                  <span>Target Date: {issue.deadline}</span>
                </span>
              )}
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight pt-1">
              {issue.title}
            </h1>
          </div>
        </div>

        {/* Multi-Department Sequence Tracker */}
        <div className="pt-2">
          <ExecutionOrderTracker stages={issue.execution_order} />
        </div>
      </div>

      {/* Conversation Thread */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-6">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
            <MessageSquare className="w-4 h-4 text-emerald-600" />
            <span>Updates & Communication</span>
          </h2>
          <span className="text-xs text-slate-400">
            {issue.messages.length} {issue.messages.length === 1 ? 'message' : 'messages'}
          </span>
        </div>

        {/* Message list */}
        <div className="space-y-4">
          {issue.messages.length === 0 ? (
            <div className="text-center py-6 text-xs text-slate-400">
              No messages posted yet. Reply below if you have any questions or additional details.
            </div>
          ) : (
            issue.messages.map((msg) => {
              const isStaff = msg.author_role === 'staff' || msg.author_role === 'admin';
              return (
                <div
                  key={msg.id}
                  className={`p-4 rounded-xl border text-xs sm:text-sm space-y-1.5 transition-all ${
                    isStaff
                      ? 'bg-blue-50/50 border-blue-200 ml-0 sm:ml-4'
                      : 'bg-slate-50 border-slate-200 mr-0 sm:mr-4'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-900">{msg.author_name}</span>
                      {msg.department_code && (
                        <span className="font-mono text-[10px] font-bold px-1.5 py-0.2 rounded bg-blue-200 text-blue-900">
                          {msg.department_code}
                        </span>
                      )}
                      <span className="text-[11px] text-slate-400 capitalize">
                        ({msg.author_role})
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-400">
                      {new Date(msg.created_at).toLocaleString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                  <p className="text-slate-800 leading-relaxed whitespace-pre-wrap">{msg.body}</p>
                </div>
              );
            })
          )}
        </div>

        {/* Reply Box */}
        {issue.status === 'open' ? (
          <form onSubmit={handleSendMessage} className="space-y-3 pt-2">
            <textarea
              rows={3}
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              placeholder="Type your reply or additional details here..."
              className="w-full p-3 text-xs sm:text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 placeholder:text-slate-400 leading-relaxed"
            />
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={isSendingMessage || !replyText.trim()}
                className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-xs font-bold shadow-sm transition-all"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{isSendingMessage ? 'Sending...' : 'Send Reply'}</span>
              </button>
            </div>
          </form>
        ) : (
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-center text-xs text-slate-500">
            This issue is marked resolved. If you still need help with this, you can reopen it within 7 days.
          </div>
        )}
      </div>

      {/* Reopen Modal */}
      {showReopenModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-fade-in">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-lg w-full p-6 space-y-4">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <RotateCcw className="w-5 h-5 text-amber-600" />
              <span>Reopen Support Request</span>
            </h3>
            <p className="text-xs text-slate-600">
              Please let the departments know why this issue is not yet resolved.
            </p>
            <form onSubmit={handleReopen} className="space-y-4">
              <textarea
                required
                rows={4}
                value={reopenNote}
                onChange={(e) => setReopenNote(e.target.value)}
                placeholder="The admit card was not received..."
                className="w-full p-3 text-xs sm:text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-amber-500"
              />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowReopenModal(false)}
                  className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isReopening || !reopenNote.trim()}
                  className="px-5 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold"
                >
                  {isReopening ? 'Reopening...' : 'Confirm Reopen'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
