'use client';

import React from 'react';
import { useAuth } from '@/lib/auth-context';
import { DemoUser } from '@/lib/api';
import { UserCheck, GraduationCap, Building, Shield, X, Sparkles } from 'lucide-react';

interface PersonaSwitcherModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function PersonaSwitcherModal({ isOpen, onClose }: PersonaSwitcherModalProps) {
  const { demoUsers, switchPersona, user } = useAuth();

  if (!isOpen) return null;

  const students = demoUsers.filter((u) => u.role === 'student');
  const staffMembers = demoUsers.filter((u) => u.role === 'staff');
  const admins = demoUsers.filter((u) => u.role === 'admin');

  const handleSelect = async (demoUser: DemoUser) => {
    await switchPersona(demoUser);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto animate-fade-in">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-3xl overflow-hidden my-8">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-brand-500/20 text-brand-400 border border-brand-400/30">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold">Demo Persona Switcher</h2>
              <p className="text-xs text-slate-300">
                Instantly switch accounts to demo cross-department coordination
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 max-h-[75vh] overflow-y-auto space-y-6">
          {/* Students Section */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <GraduationCap className="w-4 h-4 text-emerald-600" />
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-700">
                Student Personas
              </h3>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {students.map((st) => {
                const isActive = user?.email === st.email;
                return (
                  <button
                    key={st.id}
                    onClick={() => handleSelect(st)}
                    className={`text-left p-3 rounded-xl border transition-all flex items-start justify-between ${
                      isActive
                        ? 'bg-emerald-50 border-emerald-400 ring-2 ring-emerald-300/40 shadow-sm'
                        : 'bg-slate-50/70 border-slate-200 hover:bg-emerald-50/40 hover:border-emerald-300'
                    }`}
                  >
                    <div>
                      <div className="font-semibold text-sm text-slate-900 flex items-center gap-1.5">
                        {st.full_name}
                        {isActive && (
                          <span className="text-[10px] bg-emerald-600 text-white px-1.5 py-0.2 rounded font-bold">
                            Active
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">{st.description || st.email}</p>
                    </div>
                    <span className="text-xs font-medium text-emerald-700 bg-white px-2 py-0.5 rounded border border-emerald-200">
                      Student
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Key Staff Personas (FIN, EXAM, SCHOL, COUNS, ACAD, IT, HOSTEL, DSW) */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Building className="w-4 h-4 text-blue-600" />
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-700">
                Department Staff Personas
              </h3>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
              {staffMembers.map((staff) => {
                const isActive = user?.email === staff.email;
                return (
                  <button
                    key={staff.id}
                    onClick={() => handleSelect(staff)}
                    className={`text-left p-3 rounded-xl border transition-all ${
                      isActive
                        ? 'bg-blue-50 border-blue-400 ring-2 ring-blue-300/40 shadow-sm'
                        : 'bg-slate-50/70 border-slate-200 hover:bg-blue-50/40 hover:border-blue-300'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-bold font-mono px-1.5 py-0.5 rounded bg-blue-100 text-blue-800">
                        {staff.department_code}
                      </span>
                      {isActive && (
                        <span className="text-[10px] bg-blue-600 text-white px-1.5 py-0.2 rounded font-bold">
                          Active
                        </span>
                      )}
                    </div>
                    <div className="font-semibold text-xs text-slate-900 truncate">
                      {staff.full_name}
                    </div>
                    <p className="text-[11px] text-slate-500 truncate mt-0.5">
                      {staff.department_name}
                    </p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Admin Section */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Shield className="w-4 h-4 text-purple-600" />
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-700">
                System Administrator
              </h3>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {admins.map((adm) => {
                const isActive = user?.email === adm.email;
                return (
                  <button
                    key={adm.id}
                    onClick={() => handleSelect(adm)}
                    className={`text-left p-3 rounded-xl border transition-all flex items-center justify-between ${
                      isActive
                        ? 'bg-purple-50 border-purple-400 ring-2 ring-purple-300/40 shadow-sm'
                        : 'bg-slate-50/70 border-slate-200 hover:bg-purple-50/40 hover:border-purple-300'
                    }`}
                  >
                    <div>
                      <div className="font-semibold text-sm text-slate-900 flex items-center gap-1.5">
                        {adm.full_name}
                        {isActive && (
                          <span className="text-[10px] bg-purple-600 text-white px-1.5 py-0.2 rounded font-bold">
                            Active
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">Dean of Academic Administration</p>
                    </div>
                    <span className="text-xs font-medium text-purple-700 bg-white px-2 py-0.5 rounded border border-purple-200">
                      Admin
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 flex justify-between items-center text-xs text-slate-500">
          <span>All seeded personas authenticate with default password</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-200 hover:bg-slate-300 text-slate-800 font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
