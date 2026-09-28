'use client';

import React, { useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { DemoUser } from '@/lib/api';
import {
  Layers,
  Sparkles,
  GraduationCap,
  Building,
  Shield,
  ArrowRight,
  Lock,
  Mail,
  CheckCircle2,
} from 'lucide-react';

export default function LoginPage() {
  const { login, demoUsers, switchPersona } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('demo1234');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuickLogin = async (demoUser: DemoUser) => {
    setError(null);
    setIsSubmitting(true);
    try {
      await switchPersona(demoUser);
    } catch (err: any) {
      setError(err.message || 'Persona switch failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const students = demoUsers.filter((u) => u.role === 'student');
  const staffMembers = demoUsers.filter((u) => u.role === 'staff');
  const admin = demoUsers.find((u) => u.role === 'admin');

  // Key departments for demo switcher per §12.1: FIN, EXAM, SCHOL, COUNS, ACAD, IT, HOSTEL, DSW
  const keyDeptCodes = ['FIN', 'EXAM', 'SCHOL', 'COUNS', 'ACAD', 'IT', 'HOSTEL', 'DSW'];
  const keyStaff = keyDeptCodes
    .map((code) => staffMembers.find((s) => s.department_code === code))
    .filter(Boolean) as DemoUser[];

  return (
    <div className="max-w-5xl mx-auto py-6 sm:py-10 space-y-10">
      {/* Hero Header */}
      <div className="text-center space-y-3">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold shadow-sm">
          <Sparkles className="w-4 h-4 text-emerald-600" />
          <span>Hackathon Demo Edition • One-Click Persona Switching</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
          Student Support Triage & Joined-Up Case Management
        </h1>
        <p className="text-sm sm:text-base text-slate-600 max-w-2xl mx-auto">
          Single-point intake, AI cross-department routing, priority inheritance, and synchronized multi-department task execution.
        </p>
      </div>

      {/* Demo Persona Switcher Grid */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 sm:p-8 space-y-6">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-emerald-600" />
            <h2 className="text-base font-bold text-slate-900">
              One-Click Demo Personas
            </h2>
          </div>
          <span className="text-xs font-medium text-slate-500">
            Click any card to sign in instantly
          </span>
        </div>

        {/* 1. Students */}
        <div className="space-y-2.5">
          <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-500">
            <GraduationCap className="w-3.5 h-3.5 text-emerald-600" />
            <span>Students</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {students.slice(0, 3).map((st) => (
              <button
                key={st.id}
                type="button"
                onClick={() => handleQuickLogin(st)}
                disabled={isSubmitting}
                className="group text-left p-3.5 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-emerald-50 hover:border-emerald-300 transition-all hover:shadow-md flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold text-emerald-700 bg-emerald-100/70 px-2 py-0.5 rounded-md">
                      Student
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-emerald-600 group-hover:translate-x-0.5 transition-all" />
                  </div>
                  <div className="font-bold text-sm text-slate-900">{st.full_name}</div>
                  <p className="text-xs text-slate-500 mt-1 line-clamp-1">{st.description}</p>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* 2. Key Staff Departments */}
        <div className="space-y-2.5 pt-2">
          <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-500">
            <Building className="w-3.5 h-3.5 text-blue-600" />
            <span>Department Staff (FIN, EXAM, SCHOL, COUNS, ACAD, IT, HOSTEL, DSW)</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {keyStaff.map((staff) => (
              <button
                key={staff.id}
                type="button"
                onClick={() => handleQuickLogin(staff)}
                disabled={isSubmitting}
                className="group text-left p-3.5 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-blue-50 hover:border-blue-300 transition-all hover:shadow-md"
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-mono font-bold text-blue-800 bg-blue-100 px-2 py-0.5 rounded-md">
                    {staff.department_code}
                  </span>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-600 group-hover:translate-x-0.5 transition-all" />
                </div>
                <div className="font-bold text-xs text-slate-900 truncate">
                  {staff.full_name}
                </div>
                <div className="text-[11px] text-slate-500 truncate mt-0.5">
                  {staff.department_name}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* 3. System Admin */}
        {admin && (
          <div className="pt-2">
            <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
              <Shield className="w-3.5 h-3.5 text-purple-600" />
              <span>Administration</span>
            </div>
            <button
              type="button"
              onClick={() => handleQuickLogin(admin)}
              disabled={isSubmitting}
              className="group w-full text-left p-3.5 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-purple-50 hover:border-purple-300 transition-all hover:shadow-md flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-purple-100 text-purple-700 font-bold text-xs">
                  ADMIN
                </div>
                <div>
                  <div className="font-bold text-sm text-slate-900">{admin.full_name}</div>
                  <p className="text-xs text-slate-500">
                    System Administrator • Bottleneck Analytics & SLA Monitoring
                  </p>
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-purple-600 group-hover:translate-x-0.5 transition-all" />
            </button>
          </div>
        )}
      </div>

      {/* Standard Email/Password Form */}
      <div className="max-w-md mx-auto bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-4">
        <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wide">
          Or Sign In with Email Credentials
        </h3>

        {error && (
          <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3.5">
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Email Address
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="priya.sharma@student.edu"
                className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
              />
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Default demo password: demo1234</p>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-sm font-semibold shadow-sm transition-colors flex items-center justify-center gap-2"
          >
            {isSubmitting ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}
