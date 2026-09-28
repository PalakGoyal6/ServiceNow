'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { apiRequest } from '@/lib/api';
import {
  Sparkles,
  ArrowLeft,
  Calendar,
  Send,
  HelpCircle,
  Lightbulb,
  CheckCircle2,
  Clock,
} from 'lucide-react';

export default function StudentNewIssuePage() {
  const router = useRouter();
  const [text, setText] = useState('');
  const [deadline, setDeadline] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (text.trim().length < 5) {
      setError('Please provide at least a few words describing your issue.');
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      const payload: any = { text: text.trim() };
      if (deadline) {
        payload.deadline = deadline;
      }

      const res = await apiRequest<{ id: string }>('/student/issues', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      router.push(`/student/issues/${res.id}`);
    } catch (err: any) {
      setError(err.message || 'Failed to submit issue. Please try again.');
      setIsSubmitting(false);
    }
  };

  const setDemoExample = (sampleText: string, sampleDaysAhead?: number) => {
    setText(sampleText);
    if (sampleDaysAhead !== undefined) {
      const d = new Date();
      d.setDate(d.getDate() + sampleDaysAhead);
      setDeadline(d.toISOString().split('T')[0]);
    } else {
      setDeadline('');
    }
  };

  return (
    <div className="max-w-3xl mx-auto py-6 space-y-6">
      <div className="flex items-center gap-2">
        <Link
          href="/student"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to My Issues</span>
        </Link>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-8 space-y-6">
        <div className="space-y-2 border-b border-slate-100 pb-5">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 text-emerald-800 text-xs font-semibold border border-emerald-200">
            <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
            <span>AI Multi-Department Triage</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Tell us what's going on
          </h1>
          <p className="text-sm text-slate-600">
            Explain your situation in your own words. You don't need to know which department handles it. Our system coordinates all required offices in the right sequence.
          </p>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs">
            {error}
          </div>
        )}

        {isSubmitting ? (
          <div className="py-16 text-center space-y-4">
            <div className="relative w-16 h-16 mx-auto">
              <div className="w-16 h-16 rounded-full border-4 border-emerald-200 border-t-emerald-600 animate-spin"></div>
              <Sparkles className="w-6 h-6 text-emerald-600 absolute inset-0 m-auto animate-pulse" />
            </div>
            <div className="space-y-1">
              <h3 className="text-base font-bold text-slate-900">Working out who can help…</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Analyzing your request, identifying involved departments, and establishing prerequisite dependencies.
              </p>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Description Textarea */}
            <div className="space-y-1.5">
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">
                Describe your issue
              </label>
              <textarea
                required
                rows={6}
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="I couldn't pay my semester fees because my scholarship money hasn't come yet, and now my name isn't on the exam list for the exam next week..."
                className="w-full p-4 text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 placeholder:text-slate-400 leading-relaxed"
              />
            </div>

            {/* Optional Deadline */}
            <div className="space-y-1.5">
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-slate-500" />
                <span>Is there a date this needs sorting by? (Optional)</span>
              </label>
              <input
                type="date"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                className="p-2.5 text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-slate-800"
              />
            </div>

            {/* Quick Demo Examples Picker */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2.5">
              <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700">
                <Lightbulb className="w-3.5 h-3.5 text-amber-500" />
                <span>Try a Demo Scenario:</span>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() =>
                    setDemoExample(
                      "My scholarship hasn't been credited so I couldn't pay my fees, and now my name isn't on the exam list. My exam is in two days.",
                      2
                    )
                  }
                  className="px-2.5 py-1.5 rounded-lg bg-white hover:bg-emerald-50 border border-slate-200 hover:border-emerald-300 text-xs font-medium text-slate-700 transition-colors text-left"
                >
                  ⚡ Scholarship → Fees → Exam chain (2-day deadline)
                </button>
                <button
                  type="button"
                  onClick={() =>
                    setDemoExample(
                      "My hostel Wi-Fi hasn't worked for a week and I can't submit assignments on the LMS."
                    )
                  }
                  className="px-2.5 py-1.5 rounded-lg bg-white hover:bg-blue-50 border border-slate-200 hover:border-blue-300 text-xs font-medium text-slate-700 transition-colors text-left"
                >
                  ⚡ Hostel Wi-Fi / IT issue
                </button>
                <button
                  type="button"
                  onClick={() =>
                    setDemoExample(
                      "I've been feeling really overwhelmed and I've missed a lot of classes, now I'm short on attendance."
                    )
                  }
                  className="px-2.5 py-1.5 rounded-lg bg-white hover:bg-purple-50 border border-slate-200 hover:border-purple-300 text-xs font-medium text-slate-700 transition-colors text-left"
                >
                  ⚡ Wellbeing + Academic attendance condonation
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <div className="pt-2 flex items-center justify-end gap-3">
              <Link
                href="/student"
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
              >
                Cancel
              </Link>
              <button
                type="submit"
                className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-sm font-bold shadow-md transition-all hover:scale-102"
              >
                <Send className="w-4 h-4" />
                <span>Submit Request</span>
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
