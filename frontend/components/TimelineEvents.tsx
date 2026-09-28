import React from 'react';
import { EventLog } from '@/lib/api';
import {
  FilePlus,
  Bot,
  ListTodo,
  Link,
  Unlink,
  RefreshCw,
  Unlock,
  XCircle,
  UserCheck,
  Building2,
  MessageSquare,
  TrendingUp,
  CheckCircle,
  Eye,
  RotateCcw,
} from 'lucide-react';

interface TimelineEventsProps {
  events: EventLog[];
}

const EVENT_ICON_MAP: Record<string, { icon: any; color: string; bg: string }> = {
  issue_created: { icon: FilePlus, color: 'text-indigo-600', bg: 'bg-indigo-100' },
  classified: { icon: Bot, color: 'text-purple-600', bg: 'bg-purple-100' },
  task_created: { icon: ListTodo, color: 'text-blue-600', bg: 'bg-blue-100' },
  dependency_added: { icon: Link, color: 'text-amber-600', bg: 'bg-amber-100' },
  dependency_removed: { icon: Unlink, color: 'text-slate-600', bg: 'bg-slate-100' },
  task_status_changed: { icon: RefreshCw, color: 'text-blue-600', bg: 'bg-blue-100' },
  task_unblocked: { icon: Unlock, color: 'text-emerald-600', bg: 'bg-emerald-100' },
  task_rejected: { icon: XCircle, color: 'text-rose-600', bg: 'bg-rose-100' },
  task_reassigned: { icon: UserCheck, color: 'text-cyan-600', bg: 'bg-cyan-100' },
  department_added: { icon: Building2, color: 'text-violet-600', bg: 'bg-violet-100' },
  message_posted: { icon: MessageSquare, color: 'text-sky-600', bg: 'bg-sky-100' },
  priority_changed: { icon: TrendingUp, color: 'text-orange-600', bg: 'bg-orange-100' },
  issue_resolved: { icon: CheckCircle, color: 'text-emerald-600', bg: 'bg-emerald-100' },
  issue_reopened: { icon: RotateCcw, color: 'text-amber-600', bg: 'bg-amber-100' },
  raw_description_viewed: { icon: Eye, color: 'text-rose-600', bg: 'bg-rose-100' },
};

export default function TimelineEvents({ events }: TimelineEventsProps) {
  if (!events || events.length === 0) {
    return (
      <div className="p-4 text-center text-xs text-slate-500 bg-slate-50 rounded-lg border border-slate-200">
        No audit history recorded yet.
      </div>
    );
  }

  const formatEventText = (e: EventLog) => {
    let details = '';
    if (e.payload) {
      try {
        const p = JSON.parse(e.payload);
        if (e.type === 'task_status_changed') {
          details = `Status changed from ${p.from_status} → ${p.to_status}`;
          if (p.note) details += ` ("${p.note}")`;
        } else if (e.type === 'task_rejected') {
          details = `Rejected: "${p.note || 'Not ours'}"`;
        } else if (e.type === 'task_unblocked') {
          details = `Unblocked as all dependencies completed`;
        } else if (e.type === 'raw_description_viewed') {
          details = `Raw student description accessed for audit (Viewer: ${p.viewer_email || 'Staff'})`;
        } else if (e.type === 'classified') {
          details = `Classified via ${p.source.toUpperCase()} (${p.urgency_reason || ''})`;
        } else if (e.type === 'department_added') {
          details = `Added department ${p.department_code}: ${p.note}`;
        } else if (e.type === 'dependency_added') {
          details = `Dependency configured: ${p.reason || ''}`;
        } else if (e.type === 'issue_reopened') {
          details = `Issue reopened`;
        }
      } catch {
        // ignore parse error
      }
    }

    const typeLabel = e.type.replace(/_/g, ' ');
    return { typeLabel, details };
  };

  return (
    <div className="flow-root">
      <ul className="-mb-8">
        {events.map((event, eventIdx) => {
          const style = EVENT_ICON_MAP[event.type] || {
            icon: RefreshCw,
            color: 'text-slate-600',
            bg: 'bg-slate-100',
          };
          const Icon = style.icon;
          const { typeLabel, details } = formatEventText(event);
          const isLast = eventIdx === events.length - 1;

          return (
            <li key={event.id}>
              <div className="relative pb-6">
                {!isLast && (
                  <span
                    className="absolute left-4 top-4 -ml-px h-full w-0.5 bg-slate-200"
                    aria-hidden="true"
                  />
                )}
                <div className="relative flex items-start space-x-3">
                  <div className={`relative px-1`}>
                    <div
                      className={`h-7 w-7 rounded-full flex items-center justify-center ring-4 ring-white ${style.bg} ${style.color}`}
                    >
                      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                    </div>
                  </div>
                  <div className="min-w-0 flex-1 pt-0.5">
                    <div className="text-xs font-semibold text-slate-800 capitalize">
                      {typeLabel}{' '}
                      <span className="font-normal text-slate-500">
                        by {event.actor_name || 'System / AI'}
                      </span>
                    </div>
                    {details && <p className="mt-0.5 text-xs text-slate-600">{details}</p>}
                    <span className="text-[10px] text-slate-400">
                      {new Date(event.created_at).toLocaleString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
