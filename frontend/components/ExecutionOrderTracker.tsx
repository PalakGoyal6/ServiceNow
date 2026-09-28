import React from 'react';
import { ExecutionStage } from '@/lib/api';
import StatusBadge from './StatusBadge';
import { ArrowRight, CheckCircle2, Clock, Lock, Sparkles } from 'lucide-react';

interface ExecutionOrderTrackerProps {
  stages: ExecutionStage[];
  currentDeptCode?: string;
  isStaffView?: boolean;
}

export default function ExecutionOrderTracker({
  stages,
  currentDeptCode,
  isStaffView = false,
}: ExecutionOrderTrackerProps) {
  if (!stages || stages.length === 0) {
    return (
      <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 text-center text-slate-500 text-sm">
        No active department workflow stages configured.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between pb-2 border-b border-slate-200">
        <h3 className="text-sm font-bold tracking-wide uppercase text-slate-700 flex items-center gap-1.5">
          <Sparkles className="w-4 h-4 text-brand-600" />
          <span>Workflow Execution Sequence</span>
        </h3>
        <span className="text-xs text-slate-500">
          {stages.length} {stages.length === 1 ? 'Phase' : 'Sequential Phases'}
        </span>
      </div>

      <div className="space-y-3">
        {stages.map((stage, idx) => {
          const isAllResolved = stage.tasks.every((t) => t.status === 'resolved' || t.status === 'rejected');
          const isBlocked = stage.tasks.every((t) => t.status === 'blocked');

          return (
            <div
              key={stage.stage_number}
              className={`relative rounded-xl border p-4 transition-all ${
                isAllResolved
                  ? 'bg-emerald-50/40 border-emerald-200'
                  : isBlocked
                  ? 'bg-slate-50 border-slate-200 opacity-90'
                  : 'bg-white border-blue-200 shadow-sm ring-1 ring-blue-100'
              }`}
            >
              {/* Stage Header */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span
                    className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${
                      isAllResolved
                        ? 'bg-emerald-600 text-white'
                        : isBlocked
                        ? 'bg-slate-300 text-slate-700'
                        : 'bg-blue-600 text-white'
                    }`}
                  >
                    {stage.stage_number}
                  </span>
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-700">
                    Step {stage.stage_number}
                    {stage.tasks.length > 1 && ' (Parallel Tasks)'}
                  </span>
                </div>

                {isAllResolved ? (
                  <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Completed</span>
                  </span>
                ) : isBlocked ? (
                  <span className="inline-flex items-center gap-1 text-xs font-medium text-slate-500">
                    <Lock className="w-3.5 h-3.5" />
                    <span>Waiting on previous steps</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-xs font-medium text-blue-700">
                    <Clock className="w-3.5 h-3.5" />
                    <span>In Action</span>
                  </span>
                )}
              </div>

              {/* Tasks within this Stage */}
              <div className="grid grid-cols-1 gap-2.5">
                {stage.tasks.map((task) => {
                  const isCurrent = currentDeptCode && task.department_code === currentDeptCode;

                  return (
                    <div
                      key={task.task_id}
                      className={`p-3 rounded-lg border text-sm transition-all ${
                        isCurrent
                          ? 'bg-blue-50/60 border-blue-300 ring-2 ring-blue-400/30'
                          : 'bg-white border-slate-200'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-slate-900">
                              {task.department_name}
                            </span>
                            <span className="text-xs px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-mono">
                              {task.department_code}
                            </span>
                            {isCurrent && (
                              <span className="text-[10px] uppercase font-bold px-1.5 py-0.2 rounded bg-blue-600 text-white">
                                Your Dept
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-slate-600 mt-1">{task.action_needed}</p>
                        </div>
                        <StatusBadge status={task.status} size="sm" />
                      </div>

                      {/* Blocker Notes */}
                      {task.status === 'blocked' && task.blocked_by_dept_names.length > 0 && (
                        <div className="mt-2 text-xs flex items-center gap-1 text-amber-700 bg-amber-50 px-2 py-1 rounded border border-amber-200/60">
                          <Lock className="w-3 h-3 flex-shrink-0" />
                          <span>Waiting on: {task.blocked_by_dept_names.join(', ')}</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Arrow separator if not last stage */}
              {idx < stages.length - 1 && (
                <div className="absolute -bottom-3 left-1/2 -translate-x-1/2 z-10">
                  <div className="w-5 h-5 rounded-full bg-slate-100 border border-slate-300 flex items-center justify-center text-slate-500 shadow-sm">
                    <ArrowRight className="w-3 h-3 rotate-90" />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
