import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { dashboardAPI } from '../../../services/api';
import { Card, CardHeader, CardTitle, CardContent } from '../../../components/Card';
import { Button } from '../../../components/Button';
import { Input } from '../../../components/Input';
import { Select } from '../../../components/Select';

export const DashboardJobs: React.FC = () => {
  const [filters, setFilters] = useState({
    status: '',
    mode: '',
    page: 1,
    limit: 20,
  });
  const [selectedJob, setSelectedJob] = useState<string | null>(null);

  const { data: jobs, isLoading } = useQuery({
    queryKey: ['dashboard-jobs', filters],
    queryFn: () => dashboardAPI.getJobs(filters),
  });

  const { data: jobDetail } = useQuery({
    queryKey: ['dashboard-job', selectedJob],
    queryFn: () => dashboardAPI.getJob(selectedJob!),
    enabled: selectedJob !== null,
  });

  const handleFilterChange = (key: string, value: any) => {
    setFilters({ ...filters, [key]: value, page: 1 });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-secondary-50 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center py-12">
            <p className="text-secondary-600">Loading jobs...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-secondary-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-secondary-900">Crawl Jobs & Logs</h1>
          <p className="text-secondary-600 mt-2">Monitor and analyze crawl job execution</p>
        </div>

        {/* Filters */}
        <Card className="mb-6">
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Select
                label="Status"
                value={filters.status}
                onChange={(e) => handleFilterChange('status', e.target.value)}
                options={[
                  { value: '', label: 'All' },
                  { value: 'completed', label: 'Completed' },
                  { value: 'failed', label: 'Failed' },
                  { value: 'running', label: 'Running' },
                  { value: 'queued', label: 'Queued' },
                ]}
              />
              <Select
                label="Mode"
                value={filters.mode}
                onChange={(e) => handleFilterChange('mode', e.target.value)}
                options={[
                  { value: '', label: 'All' },
                  { value: 'query', label: 'Query' },
                  { value: 'domain', label: 'Domain' },
                  { value: 'scheduled', label: 'Scheduled' },
                  { value: 'realtime_web', label: 'Realtime Web' },
                ]}
              />
            </div>
          </CardContent>
        </Card>

        {/* Jobs Table */}
        <Card>
          <CardHeader>
            <CardTitle>Crawl Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            {jobs?.items && jobs.items.length > 0 ? (
              <>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-secondary-200">
                    <thead className="bg-secondary-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                          Job ID
                        </th>
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
                        <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-secondary-200">
                      {jobs.items.map((job: any) => (
                        <tr key={job.job_id} className="hover:bg-secondary-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-secondary-600">
                            {job.job_id.substring(0, 12)}...
                          </td>
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
                          <td className="px-6 py-4 whitespace-nowrap text-sm">
                            <Button
                              size="sm"
                              variant="primary"
                              onClick={() => setSelectedJob(job.job_id)}
                            >
                              View Details
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                {jobs.pages > 1 && (
                  <div className="mt-4 flex justify-between items-center">
                    <div className="text-sm text-secondary-600">
                      Page {jobs.page} of {jobs.pages} ({jobs.total} total)
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setFilters({ ...filters, page: filters.page - 1 })}
                        disabled={filters.page <= 1}
                      >
                        Previous
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setFilters({ ...filters, page: filters.page + 1 })}
                        disabled={filters.page >= jobs.pages}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <p className="text-secondary-600 text-center py-8">No jobs found</p>
            )}
          </CardContent>
        </Card>

        {/* Job Detail Modal */}
        {selectedJob && jobDetail && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <Card className="max-w-3xl w-full mx-4 max-h-[90vh] overflow-y-auto">
              <CardHeader>
                <div className="flex justify-between items-center">
                  <CardTitle>Job Details: {jobDetail.job_id.substring(0, 20)}...</CardTitle>
                  <Button variant="subtle" onClick={() => setSelectedJob(null)}>Close</Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <h3 className="font-semibold text-secondary-900 mb-2">Summary</h3>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-secondary-600">Origin:</span>
                        <p className="text-secondary-900">{jobDetail.origin_name || 'N/A'}</p>
                      </div>
                      <div>
                        <span className="text-secondary-600">Mode:</span>
                        <p className="text-secondary-900">{jobDetail.mode}</p>
                      </div>
                      <div>
                        <span className="text-secondary-600">Status:</span>
                        <p className="text-secondary-900">{jobDetail.status}</p>
                      </div>
                      <div>
                        <span className="text-secondary-600">Trigger:</span>
                        <p className="text-secondary-900">{jobDetail.trigger_type}</p>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h3 className="font-semibold text-secondary-900 mb-2">Metrics</h3>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-secondary-600">Pages Attempted:</span>
                        <p className="text-secondary-900">{jobDetail.pages_attempted}</p>
                      </div>
                      <div>
                        <span className="text-secondary-600">Pages Succeeded:</span>
                        <p className="text-secondary-900">{jobDetail.pages_succeeded}</p>
                      </div>
                      <div>
                        <span className="text-secondary-600">Policy-Relevant Pages:</span>
                        <p className="text-secondary-900">{jobDetail.policy_relevant_pages}</p>
                      </div>
                      <div>
                        <span className="text-secondary-600">New Documents:</span>
                        <p className="text-secondary-900">{jobDetail.new_docs_ingested}</p>
                      </div>
                    </div>
                  </div>

                  {jobDetail.error_summary && (
                    <div className="bg-red-50 border border-red-200 rounded p-4">
                      <h4 className="font-semibold text-red-900 mb-2">Error Summary</h4>
                      <p className="text-sm text-red-700">{jobDetail.error_summary}</p>
                    </div>
                  )}

                  {Object.keys(jobDetail.error_breakdown || {}).length > 0 && (
                    <div>
                      <h4 className="font-semibold text-secondary-900 mb-2">Error Breakdown</h4>
                      <div className="space-y-2">
                        {Object.entries(jobDetail.error_breakdown).map(([type, count]) => (
                          <div key={type} className="flex justify-between text-sm">
                            <span className="text-secondary-600">{type}:</span>
                            <span className="text-secondary-900">{count as number}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
};

