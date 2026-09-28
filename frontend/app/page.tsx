'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';

export default function HomePage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading) {
      if (!user) {
        router.replace('/login');
      } else if (user.role === 'student') {
        router.replace('/student');
      } else if (user.role === 'admin') {
        router.replace('/admin');
      } else {
        router.replace('/staff');
      }
    }
  }, [user, isLoading, router]);

  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-slate-900 mb-4"></div>
      <p className="text-slate-600 text-sm font-medium">Loading UniSupport workspace...</p>
    </div>
  );
}
