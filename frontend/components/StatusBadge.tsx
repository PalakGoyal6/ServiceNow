import React from 'react';
import { Clock, PlayCircle, UserCheck, CheckCircle2, XCircle, Lock } from 'lucide-react';

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const STATUS_CONFIG: Record<string, { label: string; bg: string; text: string; border: string; icon: any }> = {
  blocked: {
    label: 'Blocked',
    bg: 'bg-slate-100',
    text: 'text-slate-700',
    border: 'border-slate-300',
    icon: Lock,
  },
  pending: {
    label: 'Pending',
    bg: 'bg-amber-50',
    text: 'text-amber-800',
    border: 'border-amber-300',
    icon: Clock,
  },
  in_progress: {
    label: 'In Progress',
    bg: 'bg-blue-50',
    text: 'text-blue-800',
    border: 'border-blue-300',
    icon: PlayCircle,
  },
  waiting_on_student: {
    label: 'Waiting on Student',
    bg: 'bg-purple-50',
    text: 'text-purple-800',
    border: 'border-purple-300',
    icon: UserCheck,
  },
  resolved: {
    label: 'Resolved',
    bg: 'bg-emerald-50',
    text: 'text-emerald-800',
    border: 'border-emerald-300',
    icon: CheckCircle2,
  },
  rejected: {
    label: 'Rejected (Not Ours)',
    bg: 'bg-rose-50',
    text: 'text-rose-800',
    border: 'border-rose-300',
    icon: XCircle,
  },
  open: {
    label: 'Open',
    bg: 'bg-indigo-50',
    text: 'text-indigo-800',
    border: 'border-indigo-300',
    icon: Clock,
  },
};

export default function StatusBadge({ status, size = 'md', className = '' }: StatusBadgeProps) {
  const normalizedStatus = status.toLowerCase();
  const config = STATUS_CONFIG[normalizedStatus] || {
    label: status,
    bg: 'bg-gray-100',
    text: 'text-gray-700',
    border: 'border-gray-200',
    icon: Clock,
  };

  const IconComponent = config.icon;

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 gap-1',
    md: 'text-xs font-medium px-2.5 py-1 gap-1.5',
    lg: 'text-sm font-medium px-3 py-1.5 gap-2',
  }[size];

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-3.5 h-3.5',
    lg: 'w-4 h-4',
  }[size];

  return (
    <span
      className={`inline-flex items-center rounded-full border ${config.bg} ${config.text} ${config.border} ${sizeClasses} ${className}`}
    >
      <IconComponent className={`${iconSizes} flex-shrink-0`} />
      <span>{config.label}</span>
    </span>
  );
}
