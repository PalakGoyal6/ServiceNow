import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { AuthProvider } from '@/lib/auth-context';
import Navbar from '@/components/Navbar';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'UniSupport | Student Support Triage & Joined-Up Case Management',
  description:
    'Single-point intake, AI multi-department triage, priority inheritance, and joined-up student support case management.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <AuthProvider>
          <div className="min-h-screen flex flex-col bg-slate-50">
            <Navbar />
            <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
              {children}
            </main>
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
