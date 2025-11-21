import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { dashboardAPI } from '../../../services/api';
import { Card, CardHeader, CardTitle, CardContent } from '../../../components/Card';

export const DashboardOverview: React.FC = () => {
  const { data: overview, isLoading, error } = useQuery({
    queryKey: ['dashboard-overview'],
    queryFn: dashboardAPI.getOverview,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const { data: recentJobs } = useQuery({
    queryKey: ['dashboard-jobs-recent'],
    queryFn: () => dashboardAPI.getJobs({ page: 1, limit: 20 }),
  });

  const { data: timeseriesData } = useQuery({
    queryKey: ['dashboard-timeseries'],
    queryFn: () => dashboardAPI.getOverviewTimeseries(7),
    refetchInterval: 60000, // Refresh every minute
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-secondary-50 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center py-12">
            <p className="text-secondary-600">Loading dashboard...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-secondary-50 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center py-12">
            <p className="text-red-600">Error loading dashboard: {error instanceof Error ? error.message : 'Unknown error'}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-secondary-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-secondary-900">Dashboard Overview</h1>
          <p className="text-secondary-600 mt-2">Monitor crawling and ingestion operations</p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-secondary-600">Total Origins</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-secondary-900">{overview?.total_origins || 0}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-secondary-600">Active Origins</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-primary-600">{overview?.active_origins || 0}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-secondary-600">Crawls Last 24h</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-secondary-900">{overview?.crawls_last_24h || 0}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-secondary-600">Documents Ingested Last 24h</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-secondary-900">{overview?.docs_ingested_last_24h || 0}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-secondary-600">Policy Relevance Ratio</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-secondary-900">
                {overview?.policy_relevance_ratio_last_24h?.toFixed(1) || '0.0'}%
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-secondary-600">Crawl Error Rate</CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`text-3xl font-bold ${
                (overview?.crawl_error_rate_last_24h || 0) > 10 ? 'text-red-600' : 
                (overview?.crawl_error_rate_last_24h || 0) > 5 ? 'text-yellow-600' : 
                'text-green-600'
              }`}>
                {overview?.crawl_error_rate_last_24h?.toFixed(1) || '0.0'}%
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <Card>
            <CardHeader>
              <CardTitle>Crawls Over Time (Last 7 Days)</CardTitle>
            </CardHeader>
            <CardContent>
              {timeseriesData?.crawls ? (
                <ResponsiveContainer width="100%" height={256}>
                  <LineChart data={timeseriesData.crawls}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="date" 
                      tick={{ fontSize: 12 }}
                      angle={-45}
                      textAnchor="end"
                      height={60}
                    />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Legend />
                    <Line 
                      type="monotone" 
                      dataKey="count" 
                      stroke="#3b82f6" 
                      strokeWidth={2}
                      name="Crawls"
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-64 flex items-center justify-center text-secondary-500">
                  Loading chart data...
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Documents Ingested Over Time (Last 7 Days)</CardTitle>
            </CardHeader>
            <CardContent>
              {timeseriesData?.documents ? (
                <ResponsiveContainer width="100%" height={256}>
                  <LineChart data={timeseriesData.documents}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="date" 
                      tick={{ fontSize: 12 }}
                      angle={-45}
                      textAnchor="end"
                      height={60}
                    />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Legend />
                    <Line 
                      type="monotone" 
                      dataKey="count" 
                      stroke="#10b981" 
                      strokeWidth={2}
                      name="Documents"
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-64 flex items-center justify-center text-secondary-500">
                  Loading chart data...
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Recent Jobs Table */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Crawl Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            {recentJobs?.items && recentJobs.items.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-secondary-200">
                  <thead className="bg-secondary-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                        Origin
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                        Mode
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                        Start Time
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                        Duration
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                        Pages
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                        Policy-Relevant
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-secondary-200">
                    {recentJobs.items.map((job: any) => (
                      <tr key={job.job_id} className="hover:bg-secondary-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-900">
                          {job.origin_name || 'N/A'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-600">
                          {job.mode || 'unknown'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-600">
                          {job.start_time ? new Date(job.start_time).toLocaleString() : 'N/A'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-600">
                          {job.duration_seconds ? `${job.duration_seconds.toFixed(1)}s` : 'N/A'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 text-xs rounded ${
                            job.status === 'completed' ? 'bg-green-100 text-green-700' :
                            job.status === 'failed' ? 'bg-red-100 text-red-700' :
                            job.status === 'running' ? 'bg-blue-100 text-blue-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {job.status || 'unknown'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-600">
                          {job.pages_succeeded || 0}/{job.pages_attempted || 0}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-600">
                          {job.policy_relevant_pages || 0}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-secondary-600 text-center py-8">No recent jobs</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

