'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/lib/auth-context';
import {
  Layers,
  LogOut,
  UserCheck,
  GraduationCap,
  Building,
  Shield,
  BarChart3,
  ListTodo,
  PlusCircle,
  Sparkles,
} from 'lucide-react';
import PersonaSwitcherModal from './PersonaSwitcherModal';

export default function Navbar() {
  const { user, logout } = useAuth();
  const [isSwitcherOpen, setIsSwitcherOpen] = useState(false);

  if (!user) {
    return (
      <header className="border-b border-slate-200 bg-white sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link href="/login" className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-slate-900 text-brand-400 flex items-center justify-center font-bold shadow-md shadow-slate-900/10">
              <Layers className="w-5 h-5 text-brand-500" />
            </div>
            <div>
              <span className="font-bold text-slate-900 tracking-tight text-base sm:text-lg">
                UniSupport
              </span>
              <span className="hidden sm:inline-block ml-2 text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                Joined-Up Case Management
              </span>
            </div>
          </Link>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsSwitcherOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-sm transition-colors"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Demo Persona Switcher</span>
            </button>
          </div>
        </div>
        <PersonaSwitcherModal isOpen={isSwitcherOpen} onClose={() => setIsSwitcherOpen(false)} />
      </header>
    );
  }

  const roleStyles = {
    student: {
      label: 'Student',
      icon: GraduationCap,
      badgeBg: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    },
    staff: {
      label: 'Staff',
      icon: Building,
      badgeBg: 'bg-blue-50 text-blue-800 border-blue-200',
    },
    admin: {
      label: 'Admin',
      icon: Shield,
      badgeBg: 'bg-purple-50 text-purple-800 border-purple-200',
    },
  }[user.role] || {
    label: user.role,
    icon: UserCheck,
    badgeBg: 'bg-slate-100 text-slate-800 border-slate-200',
  };

  const RoleIcon = roleStyles.icon;

  return (
    <>
      <header className="border-b border-slate-200 bg-white/95 backdrop-blur-md sticky top-0 z-40 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          {/* Left Brand & Navigation */}
          <div className="flex items-center gap-6">
            <Link
              href={
                user.role === 'student'
                  ? '/student'
                  : user.role === 'admin'
                  ? '/admin'
                  : '/staff'
              }
              className="flex items-center gap-2.5 group"
            >
              <div className="w-9 h-9 rounded-xl bg-slate-900 text-brand-400 flex items-center justify-center font-bold shadow-md group-hover:scale-105 transition-transform">
                <Layers className="w-5 h-5 text-emerald-400" />
              </div>
              <div className="flex flex-col">
                <span className="font-bold text-slate-900 tracking-tight text-base">
                  UniSupport
                </span>
                <span className="text-[10px] text-slate-500 font-medium -mt-0.5">
                  Cross-Department Triage
                </span>
              </div>
            </Link>

            {/* Quick Navigation Links */}
            <nav className="hidden md:flex items-center gap-1">
              {user.role === 'student' && (
                <>
                  <Link
                    href="/student"
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100 flex items-center gap-1.5 transition-colors"
                  >
                    <ListTodo className="w-3.5 h-3.5 text-slate-500" />
                    <span>My Issues</span>
                  </Link>
                  <Link
                    href="/student/new"
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 flex items-center gap-1.5 transition-colors"
                  >
                    <PlusCircle className="w-3.5 h-3.5" />
                    <span>Submit Issue</span>
                  </Link>
                </>
              )}

              {user.role === 'staff' && (
                <Link
                  href="/staff"
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 flex items-center gap-1.5 transition-colors"
                >
                  <ListTodo className="w-3.5 h-3.5" />
                  <span>Task Queue ({user.department_code || 'Dept'})</span>
                </Link>
              )}

              {user.role === 'admin' && (
                <Link
                  href="/admin"
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold text-purple-700 bg-purple-50 hover:bg-purple-100 border border-purple-200 flex items-center gap-1.5 transition-colors"
                >
                  <BarChart3 className="w-3.5 h-3.5" />
                  <span>Analytics & Bottlenecks</span>
                </Link>
              )}
            </nav>
          </div>

          {/* Right User & Persona Actions */}
          <div className="flex items-center gap-3">
            {/* Quick Persona Switcher Button */}
            <button
              onClick={() => setIsSwitcherOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold shadow-sm transition-all"
              title="Click to switch persona (Students, Staff, Admin)"
            >
              <Sparkles className="w-3.5 h-3.5 text-brand-400" />
              <span className="hidden sm:inline">Switch Persona</span>
              <span className="sm:hidden">Switch</span>
            </button>

            {/* User Profile info */}
            <div className="flex items-center gap-2 pl-2 border-l border-slate-200">
              <div className="hidden sm:flex flex-col text-right">
                <span className="text-xs font-bold text-slate-800 truncate max-w-[140px]">
                  {user.full_name}
                </span>
                <span className="text-[10px] text-slate-500 truncate max-w-[140px]">
                  {user.role === 'staff'
                    ? `${user.department_name || 'Staff'}`
                    : user.role === 'student'
                    ? user.student_profile?.roll_no || 'Student'
                    : 'System Administrator'}
                </span>
              </div>

              <span
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border ${roleStyles.badgeBg}`}
              >
                <RoleIcon className="w-3 h-3" />
                <span>{user.department_code || roleStyles.label}</span>
              </span>

              <button
                onClick={logout}
                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                title="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <PersonaSwitcherModal isOpen={isSwitcherOpen} onClose={() => setIsSwitcherOpen(false)} />
    </>
  );
}
