'use client';

import React, { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import useSWR from 'swr';
import { useAuth } from '@/lib/auth-context';
import { apiRequest, Message, EventLog, ExecutionStage } from '@/lib/api';
import StatusBadge from '@/components/StatusBadge';
import PriorityBadge from '@/components/PriorityBadge';
import ExecutionOrderTracker from '@/components/ExecutionOrderTracker';
import TimelineEvents from '@/components/TimelineEvents';
import {
  ArrowLeft,
  Calendar,
  Send,
  Eye,
  Building,
  User,
  PlusCircle,
  Link as LinkIcon,
  XCircle,
  CheckCircle2,
  PlayCircle,
  UserCheck,
  RotateCcw,
  Sparkles,
  Lock,
  Clock,
  Flame,
  AlertTriangle,

  History,
  ShieldCheck,
  MessageSquare,
} from 'lucide-react';

interface StaffTaskDetail {
  task: {
    id: string;
    issue_id: string;
    department_id: number;
    department_code: string;
    department_name: string;
    status: string;
    dept_summary: string;
    action_needed: string;
    base_priority: number;
    effective_priority: number;
    priority_label: string;
    priority_inherited: boolean;
    priority_inheritance_reason?: string | null;
    assigned_to?: string | null;
    assignee_name?: string | null;
    created_at: string;
    updated_at: string;
    resolved_at?: string | null;
    unblocked_at?: string | null;
    is_newly_unblocked: boolean;
  };
  issue_id: string;
  issue_title: string;
  issue_status: string;
  issue_urgency: number;
  issue_deadline?: string | null;
  issue_created_at: string;
  classification_source: string;
  student_info: {
    name: string;
    roll_no: string;
    programme: string;
    year_of_study: number;
  };
  other_tasks: {
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
  events: EventLog[];
  allowed_transitions: string[];
}

interface DepartmentOption {
  id: number;
  code: string;
  name: string;
  description: string;
}

export default function StaffTaskDetailPage() {
  const params = useParams();
  const router = useRouter();
  const taskId = params?.id as string;
  const { user } = useAuth();

  const { data: detail, error, mutate } = useSWR<StaffTaskDetail>(
    taskId ? `/staff/tasks/${taskId}` : null,
    (url: string) => apiRequest(url),
    { refreshInterval: 5000 }
  );

  const { data: allDepts } = useSWR<DepartmentOption[]>('/staff/departments', (url: string) =>
    apiRequest(url)
  );

  // Messaging state
  const [msgBody, setMsgBody] = useState('');
  const [msgVisibility, setMsgVisibility] = useState<'student_and_staff' | 'department_only'>(
    'student_and_staff'
  );
  const [isSendingMsg, setIsSendingMsg] = useState(false);

  // Original Message modal state
  const [showOriginalModal, setShowOriginalModal] = useState(false);
  const [originalDescription, setOriginalDescription] = useState<string | null>(null);
  const [isLoadingOriginal, setIsLoadingOriginal] = useState(false);

  // Modals
  const [showAddDeptModal, setShowAddDeptModal] = useState(false);
  const [newDeptCode, setNewDeptCode] = useState('');
  const [newDeptNote, setNewDeptNote] = useState('');
  const [newDeptBlockedBy, setNewDeptBlockedBy] = useState('');
  const [isAddingDept, setIsAddingDept] = useState(false);

  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [isRejecting, setIsRejecting] = useState(false);

  const [showDepModal, setShowDepModal] = useState(false);
  const [depBlockedTask, setDepBlockedTask] = useState('');
  const [depBlockerTask, setDepBlockerTask] = useState('');
  const [depReason, setDepReason] = useState('');
  const [isUpdatingDep, setIsUpdatingDep] = useState(false);

  // Status transitions
  const handleTransition = async (newStatus: string) => {
    if (newStatus === 'rejected') {
      setShowRejectModal(true);
      return;
    }

    try {
      await apiRequest(`/staff/tasks/${taskId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      });
      mutate();
    } catch (err: any) {
      alert(`Status transition failed: ${err.message}`);
    }
  };

  const handleConfirmReject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rejectReason.trim()) return;

    setIsRejecting(true);
    try {
      await apiRequest(`/staff/tasks/${taskId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: 'rejected', note: rejectReason.trim() }),
      });
      setShowRejectModal(false);
      setRejectReason('');
      mutate();
    } catch (err: any) {
      alert(`Rejection failed: ${err.message}`);
    } finally {
      setIsRejecting(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!msgBody.trim()) return;

    setIsSendingMsg(true);
    try {
      await apiRequest(`/staff/tasks/${taskId}/messages`, {
        method: 'POST',
        body: JSON.stringify({ body: msgBody.trim(), visibility: msgVisibility }),
      });
      setMsgBody('');
      mutate();
    } catch (err: any) {
      alert(`Failed to send message: ${err.message}`);
    } finally {
      setIsSendingMsg(false);
    }
  };

  const handleFetchOriginal = async () => {
    setIsLoadingOriginal(true);
    setShowOriginalModal(true);
    try {
      const res = await apiRequest<{ description: string }>(
        `/staff/tasks/${taskId}/original-message`
      );
      setOriginalDescription(res.description);
      mutate(); // will update events list with raw_description_viewed
    } catch (err: any) {
      alert(`Access denied: ${err.message}`);
      setShowOriginalModal(false);
    } finally {
      setIsLoadingOriginal(false);
    }
  };

  const handleAddDepartment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDeptCode || !newDeptNote.trim()) return;

    setIsAddingDept(true);
    try {
      await apiRequest(`/staff/issues/${detail?.issue_id}/departments`, {
        method: 'POST',
        body: JSON.stringify({
          department_code: newDeptCode,
          note: newDeptNote.trim(),
          blocked_by_task_id: newDeptBlockedBy || null,
        }),
      });
      setShowAddDeptModal(false);
      setNewDeptCode('');
      setNewDeptNote('');
      setNewDeptBlockedBy('');
      mutate();
    } catch (err: any) {
      alert(`Failed to add department: ${err.message}`);
    } finally {
      setIsAddingDept(false);
    }
  };

  const handleAddDependency = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!depBlockedTask || !depBlockerTask) return;

    setIsUpdatingDep(true);
    try {
      await apiRequest(`/staff/issues/${detail?.issue_id}/dependencies`, {
        method: 'POST',
        body: JSON.stringify({
          task_id: depBlockedTask,
          blocked_by_task_id: depBlockerTask,
          reason: depReason.trim() || 'Staff configured workflow dependency',
        }),
      });
      setShowDepModal(false);
      setDepBlockedTask('');
      setDepBlockerTask('');
      setDepReason('');
      mutate();
    } catch (err: any) {
      alert(`Failed to add dependency: ${err.message}`);
    } finally {
      setIsUpdatingDep(false);
    }
  };

  if (error) {
    return (
      <div className="py-12 text-center max-w-lg mx-auto space-y-4">
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm">
          {error.message || 'Task not found or access forbidden for your department'}
        </div>
        <Link
          href="/staff"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 hover:text-slate-900"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Staff Queue</span>
        </Link>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="py-20 text-center text-slate-500">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-3"></div>
        <p className="text-sm">Loading task details...</p>
      </div>
    );
  }

  const { task, student_info } = detail;
  const isMyDeptTask = user?.role === 'admin' || user?.department_id === task.department_id;

  // All tasks on this issue for dependency picker
  const allIssueTasks = [
    { id: task.id, code: task.department_code, name: task.department_name },
    ...detail.other_tasks.map((o) => ({ id: o.id, code: o.department_code, name: o.department_name })),
  ];

  return (
    <div className="space-y-6 py-4">
      {/* Top Header & Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <Link
          href="/staff"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to {task.department_code} Queue</span>
        </Link>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAddDeptModal(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-100 text-slate-700 text-xs font-semibold shadow-sm transition-colors"
          >
            <PlusCircle className="w-3.5 h-3.5 text-slate-500" />
            <span>Add Department</span>
          </button>
          <button
            onClick={() => setShowDepModal(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-100 text-slate-700 text-xs font-semibold shadow-sm transition-colors"
          >
            <LinkIcon className="w-3.5 h-3.5 text-slate-500" />
            <span>Configure Dependencies</span>
          </button>
        </div>
      </div>

      {/* Main 2-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols): Our Department Task, Actions, Messaging */}
        <div className="lg:col-span-2 space-y-6">
          {/* Main Task Card */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-5">
            {/* Title & Badges */}
            <div className="space-y-2">
              <div className="flex items-center gap-2 flex-wrap">
                <PriorityBadge
                  priority={task.effective_priority}
                  label={task.priority_label}
                  inherited={task.priority_inherited}
                  reason={task.priority_inheritance_reason}
                />
                <StatusBadge status={task.status} size="md" />

                {task.is_newly_unblocked && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-500 text-white text-[10px] font-extrabold uppercase animate-pulse">
                    Newly Unblocked
                  </span>
                )}

                {detail.issue_deadline && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 text-xs font-semibold">
                    <Calendar className="w-3.5 h-3.5 text-amber-600" />
                    <span>Target: {detail.issue_deadline}</span>
                  </span>
                )}
              </div>

              <h1 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">
                {detail.issue_title}
              </h1>

              {/* Priority Inheritance Notice Banner */}
              {task.priority_inherited && task.priority_inheritance_reason && (
                <div className="p-3 rounded-xl bg-gradient-to-r from-orange-50 to-amber-50 border border-orange-200 text-xs text-orange-900 flex items-start gap-2">
                  <Flame className="w-4 h-4 text-orange-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold">Priority Inheritance Active: </span>
                    <span>{task.priority_inheritance_reason}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Department Summary (AI-tailored) */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                  <span>{task.department_name} Summary (AI Tailored)</span>
                </span>
                <span className="text-[11px] text-slate-400">
                  Private to {task.department_code} staff
                </span>
              </div>
              <p className="text-sm text-slate-800 leading-relaxed font-medium">
                {task.dept_summary}
              </p>
            </div>

            {/* Action Needed */}
            <div className="p-4 rounded-xl bg-blue-50/60 border border-blue-200 space-y-1">
              <div className="text-xs font-bold uppercase tracking-wider text-blue-900">
                Action Required from your department
              </div>
              <p className="text-sm font-semibold text-blue-950">{task.action_needed}</p>
            </div>

            {/* Status Controls & "Not Ours" Reject Button */}
            {isMyDeptTask && (
              <div className="space-y-3 pt-2 border-t border-slate-100">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
                    Update Task Status
                  </span>
                  {task.status !== 'rejected' && (
                    <button
                      onClick={() => setShowRejectModal(true)}
                      className="text-xs font-semibold text-rose-600 hover:text-rose-800 transition-colors flex items-center gap-1"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Not Ours (Reject)</span>
                    </button>
                  )}
                </div>

                {/* Transition Action Buttons */}
                <div className="flex items-center gap-2 flex-wrap">
                  {task.status === 'blocked' && (
                    <div className="p-3 rounded-lg bg-slate-100 text-slate-600 text-xs flex items-center gap-2 w-full">
                      <Lock className="w-4 h-4 text-slate-500 flex-shrink-0" />
                      <span>
                        This task is waiting on upstream prerequisite departments to finish. It will automatically unblock to Pending once completed.
                      </span>
                    </div>
                  )}

                  {detail.allowed_transitions.map((nextStatus) => {
                    if (nextStatus === 'rejected') return null; // handled via button above

                    const config = {
                      in_progress: {
                        label: 'Start Work (In Progress)',
                        bg: 'bg-blue-600 hover:bg-blue-700 text-white',
                        icon: PlayCircle,
                      },
                      waiting_on_student: {
                        label: 'Wait on Student Reply',
                        bg: 'bg-purple-600 hover:bg-purple-700 text-white',
                        icon: UserCheck,
                      },
                      resolved: {
                        label: 'Mark Resolved (Done)',
                        bg: 'bg-emerald-600 hover:bg-emerald-700 text-white',
                        icon: CheckCircle2,
                      },
                      pending: {
                        label: 'Move to Pending',
                        bg: 'bg-amber-600 hover:bg-amber-700 text-white',
                        icon: Clock,
                      },
                    }[nextStatus] || {
                      label: `Move to ${nextStatus}`,
                      bg: 'bg-slate-800 hover:bg-slate-900 text-white',
                      icon: PlayCircle,
                    };

                    const IconComponent = config.icon;

                    return (
                      <button
                        key={nextStatus}
                        onClick={() => handleTransition(nextStatus)}
                        className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold shadow-sm transition-all hover:scale-102 ${config.bg}`}
                      >
                        <IconComponent className="w-4 h-4" />
                        <span>{config.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Audited View Original Student Message Button (§7) */}
            <div className="pt-2 flex items-center justify-between border-t border-slate-100">
              <span className="text-xs text-slate-400">
                Data minimization privacy active: student raw description is shielded
              </span>
              <button
                type="button"
                onClick={handleFetchOriginal}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold transition-colors"
              >
                <Eye className="w-3.5 h-3.5 text-slate-600" />
                <span>View Original Student Message</span>
              </button>
            </div>
          </div>

          {/* Messages & Internal Department Notes */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-800 flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-blue-600" />
                <span>Communication & Internal Notes</span>
              </h3>
              <span className="text-xs text-slate-400">
                {detail.messages.length} {detail.messages.length === 1 ? 'entry' : 'entries'}
              </span>
            </div>

            {/* Message Thread */}
            <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
              {detail.messages.length === 0 ? (
                <div className="text-center py-6 text-xs text-slate-400">
                  No messages or internal notes recorded yet.
                </div>
              ) : (
                detail.messages.map((m) => {
                  const isInternal = m.visibility === 'department_only';
                  const isStudent = m.author_role === 'student';

                  return (
                    <div
                      key={m.id}
                      className={`p-3.5 rounded-xl border text-xs sm:text-sm space-y-1 ${
                        isInternal
                          ? 'bg-amber-50/70 border-amber-300 ring-1 ring-amber-200/50'
                          : isStudent
                          ? 'bg-emerald-50/40 border-emerald-200'
                          : 'bg-slate-50 border-slate-200'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-900">{m.author_name}</span>
                          {m.department_code && (
                            <span className="font-mono text-[10px] font-bold px-1.5 py-0.2 rounded bg-slate-200 text-slate-800">
                              {m.department_code}
                            </span>
                          )}
                          {isInternal ? (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded bg-amber-200 text-amber-900">
                              <Lock className="w-2.5 h-2.5" />
                              <span>Internal Note ({task.department_code} only)</span>
                            </span>
                          ) : (
                            <span className="text-[10px] text-slate-400 capitalize">
                              ({m.author_role})
                            </span>
                          )}
                        </div>
                        <span className="text-[10px] text-slate-400">
                          {new Date(m.created_at).toLocaleString([], {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                      </div>
                      <p className="text-slate-800 leading-relaxed whitespace-pre-wrap">{m.body}</p>
                    </div>
                  );
                })
              )}
            </div>

            {/* Post Message / Internal Note Form */}
            <form onSubmit={handleSendMessage} className="space-y-3 pt-2 border-t border-slate-100">
              <div className="flex items-center gap-4 text-xs font-semibold">
                <label className="flex items-center gap-1.5 cursor-pointer text-slate-700">
                  <input
                    type="radio"
                    name="visibility"
                    value="student_and_staff"
                    checked={msgVisibility === 'student_and_staff'}
                    onChange={() => setMsgVisibility('student_and_staff')}
                    className="text-blue-600 focus:ring-blue-500"
                  />
                  <span>Reply to Student & All Departments</span>
                </label>
                <label className="flex items-center gap-1.5 cursor-pointer text-amber-900 font-bold">
                  <input
                    type="radio"
                    name="visibility"
                    value="department_only"
                    checked={msgVisibility === 'department_only'}
                    onChange={() => setMsgVisibility('department_only')}
                    className="text-amber-600 focus:ring-amber-500"
                  />
                  <span className="flex items-center gap-1">
                    <Lock className="w-3 h-3 text-amber-700" />
                    <span>Internal Note ({task.department_code} Only)</span>
                  </span>
                </label>
              </div>

              <textarea
                rows={3}
                value={msgBody}
                onChange={(e) => setMsgBody(e.target.value)}
                placeholder={
                  msgVisibility === 'department_only'
                    ? 'Type private department internal note (hidden from student and other departments)...'
                    : 'Type response to student...'
                }
                className="w-full p-3 text-xs sm:text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder:text-slate-400 leading-relaxed"
              />

              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={isSendingMsg || !msgBody.trim()}
                  className={`inline-flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-bold text-white shadow-sm transition-all ${
                    msgVisibility === 'department_only'
                      ? 'bg-amber-700 hover:bg-amber-800'
                      : 'bg-blue-600 hover:bg-blue-700'
                  }`}
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>{isSendingMsg ? 'Posting...' : 'Post Message'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Right Column (1 Col): Execution Order, Student Profile, Audit Timeline */}
        <div className="space-y-6">
          {/* Student Profile Card */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
            <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
              <User className="w-4 h-4 text-blue-600" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Student Profile
              </h3>
            </div>
            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between py-0.5">
                <span className="text-slate-500">Name:</span>
                <span className="font-bold text-slate-800">{student_info.name}</span>
              </div>
              <div className="flex justify-between py-0.5">
                <span className="text-slate-500">Roll No:</span>
                <span className="font-mono font-bold text-slate-800">{student_info.roll_no}</span>
              </div>
              <div className="flex justify-between py-0.5">
                <span className="text-slate-500">Programme:</span>
                <span className="font-medium text-slate-800 text-right">{student_info.programme}</span>
              </div>
              <div className="flex justify-between py-0.5">
                <span className="text-slate-500">Year of Study:</span>
                <span className="font-bold text-slate-800">Year {student_info.year_of_study}</span>
              </div>
            </div>
          </div>

          {/* Workflow Sequence Tracker */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
            <ExecutionOrderTracker
              stages={detail.execution_order}
              currentDeptCode={task.department_code}
              isStaffView={true}
            />
          </div>

          {/* Audit Timeline */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                <History className="w-4 h-4 text-slate-600" />
                <span>Audit Timeline Log</span>
              </h3>
              <span className="text-[11px] text-slate-400">Append-only</span>
            </div>
            <TimelineEvents events={detail.events} />
          </div>
        </div>
      </div>

      {/* Audited View Original Description Modal */}
      {showOriginalModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-fade-in">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-xl w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2 text-slate-900">
                <ShieldCheck className="w-5 h-5 text-rose-600" />
                <h3 className="font-bold text-base">Unredacted Student Submission</h3>
              </div>
              <span className="text-[10px] uppercase font-bold bg-rose-100 text-rose-800 px-2 py-0.5 rounded">
                Audited Access Logged
              </span>
            </div>

            <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-900">
              Notice: Access to the student's raw un-synthesized submission has been recorded in the append-only audit trail per data minimization rules.
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-sm text-slate-900 whitespace-pre-wrap leading-relaxed max-h-[300px] overflow-y-auto font-serif">
              {isLoadingOriginal ? 'Decrypting audit log...' : originalDescription}
            </div>

            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setShowOriginalModal(false)}
                className="px-4 py-2 rounded-lg bg-slate-900 text-white text-xs font-bold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Department Modal */}
      {showAddDeptModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-fade-in">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-lg w-full p-6 space-y-4">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <PlusCircle className="w-5 h-5 text-blue-600" />
              <span>Add Department to Issue</span>
            </h3>
            <p className="text-xs text-slate-500">
              Assign an additional university department to collaborate on this case.
            </p>

            <form onSubmit={handleAddDepartment} className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase text-slate-700 mb-1">
                  Department
                </label>
                <select
                  required
                  value={newDeptCode}
                  onChange={(e) => setNewDeptCode(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-slate-300 text-xs font-semibold bg-white"
                >
                  <option value="">Select department...</option>
                  {allDepts?.map((d) => (
                    <option key={d.code} value={d.code}>
                      {d.code} - {d.name} ({d.description})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-slate-700 mb-1">
                  Action Note / Reason for adding
                </label>
                <textarea
                  required
                  rows={3}
                  value={newDeptNote}
                  onChange={(e) => setNewDeptNote(e.target.value)}
                  placeholder="Need health centre to verify medical prescription for condonation..."
                  className="w-full p-3 rounded-xl border border-slate-300 text-xs"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-slate-700 mb-1">
                  Prerequisite Blocker (Optional)
                </label>
                <select
                  value={newDeptBlockedBy}
                  onChange={(e) => setNewDeptBlockedBy(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-slate-300 text-xs bg-white"
                >
                  <option value="">Can run in parallel (No blocker)</option>
                  {allIssueTasks.map((t) => (
                    <option key={t.id} value={t.id}>
                      Must wait for {t.name} ({t.code})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddDeptModal(false)}
                  className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isAddingDept || !newDeptCode}
                  className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-sm"
                >
                  {isAddingDept ? 'Adding...' : 'Add Department'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reject ("Not Ours") Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-fade-in">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-md w-full p-6 space-y-4">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <XCircle className="w-5 h-5 text-rose-600" />
              <span>Mark Task as Not Ours (Reject)</span>
            </h3>
            <p className="text-xs text-slate-600">
              Explain why this issue is not handled by {task.department_name}. If all assigned departments reject, the issue will be automatically re-routed to DSW.
            </p>

            <form onSubmit={handleConfirmReject} className="space-y-4">
              <textarea
                required
                rows={3}
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Reason: This matter falls under Academic Affairs, not Finance..."
                className="w-full p-3 rounded-xl border border-slate-300 text-xs focus:ring-2 focus:ring-rose-500"
              />

              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowRejectModal(false)}
                  className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isRejecting || !rejectReason.trim()}
                  className="px-5 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold shadow-sm"
                >
                  {isRejecting ? 'Rejecting...' : 'Confirm Rejection'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Configure Dependencies Modal */}
      {showDepModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-fade-in">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-lg w-full p-6 space-y-4">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <LinkIcon className="w-5 h-5 text-blue-600" />
              <span>Configure Workflow Dependency</span>
            </h3>
            <p className="text-xs text-slate-600">
              Specify that one department task cannot proceed until another department resolves its task. Cycle checks will prevent invalid loops.
            </p>

            <form onSubmit={handleAddDependency} className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase text-slate-700 mb-1">
                  Blocked Task (Cannot start)
                </label>
                <select
                  required
                  value={depBlockedTask}
                  onChange={(e) => setDepBlockedTask(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-slate-300 text-xs bg-white"
                >
                  <option value="">Select blocked task...</option>
                  {allIssueTasks.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name} ({t.code})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-slate-700 mb-1">
                  Must wait for (Prerequisite Blocker)
                </label>
                <select
                  required
                  value={depBlockerTask}
                  onChange={(e) => setDepBlockerTask(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-slate-300 text-xs bg-white"
                >
                  <option value="">Select blocker task...</option>
                  {allIssueTasks
                    .filter((t) => t.id !== depBlockedTask)
                    .map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name} ({t.code})
                      </option>
                    ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-slate-700 mb-1">
                  Dependency Reason
                </label>
                <input
                  type="text"
                  value={depReason}
                  onChange={(e) => setDepReason(e.target.value)}
                  placeholder="e.g. Exam admit card generation requires fee payment clearance"
                  className="w-full p-2.5 rounded-xl border border-slate-300 text-xs"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowDepModal(false)}
                  className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isUpdatingDep || !depBlockedTask || !depBlockerTask}
                  className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-sm"
                >
                  {isUpdatingDep ? 'Saving...' : 'Add Dependency'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
