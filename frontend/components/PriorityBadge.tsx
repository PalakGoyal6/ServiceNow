import React from 'react';
import { AlertCircle, Flame, ArrowUpRight, ShieldAlert } from 'lucide-react';

interface PriorityBadgeProps {
  priority: number | string;
  label?: string;
  inherited?: boolean;
  reason?: string | null;
  className?: string;
}

export default function PriorityBadge({
  priority,
  label,
  inherited = false,
  reason,
  className = '',
}: PriorityBadgeProps) {
  let displayLabel = label;
  if (!displayLabel) {
    const num = typeof priority === 'number' ? priority : parseInt(String(priority), 10);
    if (num >= 85) displayLabel = 'Critical';
    else if (num >= 65) displayLabel = 'High';
    else if (num >= 45) displayLabel = 'Medium';
    else displayLabel = 'Low';
  }

  const styles: Record<string, { bg: string; text: string; border: string; icon: any }> = {
    Critical: {
      bg: 'bg-rose-50 text-rose-800 border-rose-300',
      text: 'text-rose-800',
      border: 'border-rose-300',
      icon: Flame,
    },
    High: {
      bg: 'bg-orange-50 text-orange-800 border-orange-300',
      text: 'text-orange-800',
      border: 'border-orange-300',
      icon: AlertCircle,
    },
    Medium: {
      bg: 'bg-amber-50 text-amber-800 border-amber-300',
      text: 'text-amber-800',
      border: 'border-amber-300',
      icon: AlertCircle,
    },
    Low: {
      bg: 'bg-slate-100 text-slate-700 border-slate-300',
      text: 'text-slate-700',
      border: 'border-slate-300',
      icon: AlertCircle,
    },
  };

  const style = styles[displayLabel] || styles.Medium;
  const Icon = style.icon;

  return (
    <div className={`inline-flex items-center gap-1.5 ${className}`}>
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-semibold border ${style.bg}`}
        title={typeof priority === 'number' ? `Priority score: ${priority}/100` : undefined}
      >
        <Icon className="w-3.5 h-3.5" />
        <span>{displayLabel}</span>
      </span>

      {inherited && (
        <span
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200 text-[11px] font-medium cursor-help"
          title={reason || 'Priority inherited from downstream blocking dependency'}
        >
          <ArrowUpRight className="w-3 h-3 text-indigo-600" />
          <span>Inherited</span>
        </span>
      )}
    </div>
  );
}
