import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './hooks/useAuth';
import { Landing } from './pages/Landing';
import { AskAI } from './pages/AskAI';
import { AdminLogin } from './pages/Admin/Login';
import { AdminDashboard } from './pages/Admin/Dashboard';
import { Health } from './pages/Admin/Health';
import { Monitor } from './pages/Admin/Monitor';
import { DashboardOverview } from './pages/Admin/Dashboard/Overview';
import { DashboardOrigins } from './pages/Admin/Dashboard/Origins';
import { DashboardJobs } from './pages/Admin/Dashboard/Jobs';
import { DashboardDocuments } from './pages/Admin/Dashboard/Documents';
import { DashboardSettings } from './pages/Admin/Dashboard/Settings';
import { Sidebar } from './components/Navigation';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/admin/login" replace />;
  }
  
  return <>{children}</>;
};

const AdminLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAdmin } = useAuth();
  
  if (!isAdmin) {
    return <Navigate to="/" replace />;
  }
  
  const navItems = [
    { label: 'Overview', path: '/admin/dashboard/overview' },
    { label: 'Origins', path: '/admin/dashboard/origins' },
    { label: 'Jobs', path: '/admin/dashboard/jobs' },
    { label: 'Documents', path: '/admin/dashboard/documents' },
    { label: 'Settings', path: '/admin/dashboard/settings' },
    { label: 'Legacy Dashboard', path: '/admin/dashboard' },
    { label: 'Health', path: '/admin/health' },
    { label: 'Monitor', path: '/admin/monitor' },
  ];
  
  return (
    <div className="flex min-h-screen">
      <Sidebar items={navItems} />
      <main className="flex-1">{children}</main>
    </div>
  );
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter
          future={{
            v7_startTransition: true,
            v7_relativeSplatPath: true,
          }}
        >
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/ask" element={<AskAI />} />
            <Route path="/admin/login" element={<AdminLogin />} />
            {/* Redirect /monitor/login to /admin/login for convenience */}
            <Route path="/monitor/login" element={<Navigate to="/admin/login" replace />} />
            <Route
              path="/admin/dashboard"
              element={
                <ProtectedRoute>
                  <AdminLayout>
                    <AdminDashboard />
                  </AdminLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/dashboard/overview"
              element={
                <ProtectedRoute>
                  <AdminLayout>
                    <DashboardOverview />
                  </AdminLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/dashboard/origins"
              element={
                <ProtectedRoute>
                  <AdminLayout>
                    <DashboardOrigins />
                  </AdminLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/dashboard/jobs"
              element={
                <ProtectedRoute>
                  <AdminLayout>
                    <DashboardJobs />
                  </AdminLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/dashboard/documents"
              element={
                <ProtectedRoute>
                  <AdminLayout>
                    <DashboardDocuments />
                  </AdminLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/dashboard/settings"
              element={
                <ProtectedRoute>
                  <AdminLayout>
                    <DashboardSettings />
                  </AdminLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/health"
              element={
                <ProtectedRoute>
                  <AdminLayout>
                    <Health />
                  </AdminLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/monitor"
              element={
                <ProtectedRoute>
                  <AdminLayout>
                    <Monitor />
                  </AdminLayout>
                </ProtectedRoute>
              }
            />
            {/* Catch-all route for unknown paths */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;

