import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { dashboardAPI, adminAPI } from '../../../services/api';
import { Card, CardHeader, CardTitle, CardContent } from '../../../components/Card';
import { Button } from '../../../components/Button';
import { Input } from '../../../components/Input';
import { Select } from '../../../components/Select';

export const DashboardOrigins: React.FC = () => {
  const [selectedOrigin, setSelectedOrigin] = useState<number | null>(null);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const queryClient = useQueryClient();

  const { data: origins, isLoading } = useQuery({
    queryKey: ['dashboard-origins'],
    queryFn: dashboardAPI.getOrigins,
  });

  const { data: originDetail } = useQuery({
    queryKey: ['dashboard-origin', selectedOrigin],
    queryFn: () => dashboardAPI.getOrigin(selectedOrigin!),
    enabled: selectedOrigin !== null,
  });

  const updateConfigMutation = useMutation({
    mutationFn: ({ id, config }: { id: number; config: any }) =>
      dashboardAPI.updateOriginConfig(id, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard-origins'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-origin', selectedOrigin] });
      setShowConfigModal(false);
      alert('Configuration updated successfully');
    },
    onError: (error: any) => {
      alert(`Error updating configuration: ${error.response?.data?.detail || error.message}`);
    },
  });

  const createOriginMutation = useMutation({
    mutationFn: (data: any) => adminAPI.createOrigin(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard-origins'] });
      setShowCreateModal(false);
      setCreateForm({
        name: '',
        url: '',
        country_code: '',
        topic_tags: '',
        crawl_priority: 5,
        frequency_hours: 24,
        enabled: true,
        allowed_path_patterns: '',
        excluded_path_patterns: '',
        sitemap_url: '',
      });
      alert('Origin created successfully. Crawling will start according to its schedule.');
    },
    onError: (error: any) => {
      alert(`Error creating origin: ${error.response?.data?.detail || error.message}`);
    },
  });

  const [configForm, setConfigForm] = useState({
    enabled: true,
    frequency_hours: 24,
    max_pages_per_run: 30,
    max_depth: 1,
  });

  const [createForm, setCreateForm] = useState({
    name: '',
    url: '',
    country_code: '',
    topic_tags: '',
    crawl_priority: 5,
    frequency_hours: 24,
    enabled: true,
    allowed_path_patterns: '',
    excluded_path_patterns: '',
    sitemap_url: '',
  });

  const handleOpenConfig = (origin: any) => {
    setConfigForm({
      enabled: origin.enabled,
      frequency_hours: origin.frequency_hours,
      max_pages_per_run: 30, // Default, not stored per-origin yet
      max_depth: 1, // Default, not stored per-origin yet
    });
    setSelectedOrigin(origin.id);
    setShowConfigModal(true);
  };

  const handleSaveConfig = () => {
    if (selectedOrigin) {
      updateConfigMutation.mutate({
        id: selectedOrigin,
        config: configForm,
      });
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-secondary-50 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center py-12">
            <p className="text-secondary-600">Loading origins...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-secondary-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-secondary-900">Origins & Schedules</h1>
            <p className="text-secondary-600 mt-2">Configure and monitor crawling origins</p>
          </div>
          <Button onClick={() => setShowCreateModal(true)}>
            Create Origin
          </Button>
        </div>

        {/* Origins Table */}
        <Card>
          <CardHeader>
            <CardTitle>Origins</CardTitle>
          </CardHeader>
          <CardContent>
            {origins && origins.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-secondary-200">
                  <thead className="bg-secondary-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                        Name
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                        URL
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                        Country
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                        Enabled
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                        Frequency
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                        Last Run
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                        Next Run
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-secondary-200">
                    {origins.map((origin: any) => (
                      <tr
                        key={origin.id}
                        className="hover:bg-secondary-50 cursor-pointer"
                        onClick={() => setSelectedOrigin(origin.id)}
                      >
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-secondary-900">
                          {origin.name}
                        </td>
                        <td className="px-6 py-4 text-sm text-secondary-600 max-w-xs truncate">
                          {origin.url}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-600">
                          {origin.country_code || 'N/A'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 text-xs rounded ${
                            origin.enabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                          }`}>
                            {origin.enabled ? 'Enabled' : 'Disabled'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-600">
                          Every {origin.frequency_hours}h
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-600">
                          {origin.last_run ? new Date(origin.last_run).toLocaleString() : 'Never'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 text-xs rounded ${
                            origin.last_status?.toLowerCase().includes('success') ? 'bg-green-100 text-green-700' :
                            origin.last_status?.toLowerCase().includes('failed') ? 'bg-red-100 text-red-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {origin.last_status || 'Unknown'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-600">
                          {origin.next_run ? new Date(origin.next_run).toLocaleString() : 'N/A'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <Button
                            size="sm"
                            variant="primary"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenConfig(origin);
                            }}
                          >
                            Configure
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-secondary-600 text-center py-8">No origins configured</p>
            )}
          </CardContent>
        </Card>

        {/* Origin Detail Modal */}
        {selectedOrigin && originDetail && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <Card className="max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
              <CardHeader>
                <div className="flex justify-between items-center">
                  <CardTitle>{originDetail.name}</CardTitle>
                  <Button variant="subtle" onClick={() => setSelectedOrigin(null)}>Close</Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <h3 className="font-semibold text-secondary-900 mb-2">Metadata</h3>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-secondary-600">URL:</span>
                        <p className="text-secondary-900">{originDetail.url}</p>
                      </div>
                      <div>
                        <span className="text-secondary-600">Country:</span>
                        <p className="text-secondary-900">{originDetail.country_code || 'N/A'}</p>
                      </div>
                      <div>
                        <span className="text-secondary-600">Topics:</span>
                        <p className="text-secondary-900">
                          {originDetail.topic_tags?.join(', ') || 'N/A'}
                        </p>
                      </div>
                      <div>
                        <span className="text-secondary-600">Priority:</span>
                        <p className="text-secondary-900">{originDetail.crawl_priority || 'N/A'}</p>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h3 className="font-semibold text-secondary-900 mb-2">Performance</h3>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-secondary-600">Documents:</span>
                        <p className="text-secondary-900">{originDetail.documents_count || 0}</p>
                      </div>
                      <div>
                        <span className="text-secondary-600">Chunks:</span>
                        <p className="text-secondary-900">{originDetail.chunks_count || 0}</p>
                      </div>
                    </div>
                  </div>

                  {originDetail.latest_error && (
                    <div className="bg-red-50 border border-red-200 rounded p-4">
                      <h4 className="font-semibold text-red-900 mb-2">Latest Error</h4>
                      <p className="text-sm text-red-700">{originDetail.latest_error}</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Configuration Modal */}
        {showConfigModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <Card className="max-w-md w-full mx-4">
              <CardHeader>
                <div className="flex justify-between items-center">
                  <CardTitle>Configure Origin</CardTitle>
                  <Button variant="subtle" onClick={() => setShowConfigModal(false)}>Close</Button>
                </div>
              </CardHeader>
              <CardContent>
                <form onSubmit={(e) => { e.preventDefault(); handleSaveConfig(); }} className="space-y-4">
                  <Select
                    label="Enabled"
                    value={configForm.enabled ? 'enabled' : 'disabled'}
                    onChange={(e) => setConfigForm({ ...configForm, enabled: e.target.value === 'enabled' })}
                    options={[
                      { value: 'enabled', label: 'Enabled' },
                      { value: 'disabled', label: 'Disabled' },
                    ]}
                  />
                  <Input
                    label="Frequency (hours)"
                    type="number"
                    value={configForm.frequency_hours}
                    onChange={(e) => setConfigForm({ ...configForm, frequency_hours: parseInt(e.target.value) || 24 })}
                    min={1}
                    required
                  />
                  <div className="flex gap-4">
                    <Button type="submit" disabled={updateConfigMutation.isPending}>
                      {updateConfigMutation.isPending ? 'Saving...' : 'Save'}
                    </Button>
                    <Button type="button" variant="secondary" onClick={() => setShowConfigModal(false)}>
                      Cancel
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Create Origin Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <Card className="max-w-3xl w-full mx-4 max-h-[90vh] overflow-y-auto">
              <CardHeader>
                <div className="flex justify-between items-center">
                  <CardTitle>Create New Origin</CardTitle>
                  <Button variant="subtle" onClick={() => setShowCreateModal(false)}>Close</Button>
                </div>
              </CardHeader>
              <CardContent>
                <form onSubmit={(e) => {
                  e.preventDefault();
                  
                  // Validate required fields
                  if (!createForm.name.trim() || !createForm.url.trim()) {
                    alert('Name and URL are required');
                    return;
                  }

                  // Map form data to API payload
                  const payload: any = {
                    name: createForm.name.trim(),
                    url: createForm.url.trim(),
                    frequency_hours: createForm.frequency_hours,
                    enabled: createForm.enabled,
                    crawl_priority: createForm.crawl_priority,
                  };

                  // Convert topic_tags from comma-separated string to array
                  if (createForm.topic_tags.trim()) {
                    payload.topic_tags = createForm.topic_tags
                      .split(',')
                      .map(tag => tag.trim())
                      .filter(tag => tag.length > 0);
                  }

                  // Convert allowed_path_patterns from newline-separated string to array
                  if (createForm.allowed_path_patterns.trim()) {
                    payload.allowed_path_patterns = createForm.allowed_path_patterns
                      .split('\n')
                      .map(pattern => pattern.trim())
                      .filter(pattern => pattern.length > 0);
                  }

                  // Convert excluded_path_patterns from newline-separated string to array
                  if (createForm.excluded_path_patterns.trim()) {
                    payload.excluded_path_patterns = createForm.excluded_path_patterns
                      .split('\n')
                      .map(pattern => pattern.trim())
                      .filter(pattern => pattern.length > 0);
                  }

                  // Convert empty strings to null for optional fields
                  if (createForm.country_code.trim()) {
                    payload.country_code = createForm.country_code.trim();
                  } else {
                    payload.country_code = null;
                  }

                  if (createForm.sitemap_url.trim()) {
                    payload.sitemap_url = createForm.sitemap_url.trim();
                  } else {
                    payload.sitemap_url = null;
                  }

                  createOriginMutation.mutate(payload);
                }} className="space-y-6">
                  {/* Section A - Basic Information */}
                  <div>
                    <h3 className="text-lg font-semibold text-secondary-900 mb-4">Basic Information</h3>
                    <div className="space-y-4">
                      <Input
                        label="Name *"
                        value={createForm.name}
                        onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                        required
                        placeholder="e.g., EU AI Act Official Site"
                      />
                      <Input
                        label="URL *"
                        type="url"
                        value={createForm.url}
                        onChange={(e) => setCreateForm({ ...createForm, url: e.target.value })}
                        required
                        placeholder="https://example.com"
                      />
                      <Select
                        label="Enabled"
                        value={createForm.enabled ? 'enabled' : 'disabled'}
                        onChange={(e) => setCreateForm({ ...createForm, enabled: e.target.value === 'enabled' })}
                        options={[
                          { value: 'enabled', label: 'Enabled' },
                          { value: 'disabled', label: 'Disabled' },
                        ]}
                      />
                    </div>
                  </div>

                  {/* Section B - Classification */}
                  <div>
                    <h3 className="text-lg font-semibold text-secondary-900 mb-4">Classification</h3>
                    <div className="space-y-4">
                      <Select
                        label="Country Code"
                        value={createForm.country_code}
                        onChange={(e) => setCreateForm({ ...createForm, country_code: e.target.value })}
                        options={[
                          { value: '', label: 'None' },
                          { value: 'EU', label: 'EU' },
                          { value: 'US', label: 'US' },
                          { value: 'UK', label: 'UK' },
                          { value: 'FI', label: 'FI' },
                          { value: 'DE', label: 'DE' },
                          { value: 'FR', label: 'FR' },
                          { value: 'NL', label: 'NL' },
                          { value: 'CA', label: 'CA' },
                          { value: 'AU', label: 'AU' },
                        ]}
                      />
                      <div>
                        <Input
                          label="Topic Tags"
                          value={createForm.topic_tags}
                          onChange={(e) => setCreateForm({ ...createForm, topic_tags: e.target.value })}
                          placeholder="ai_governance, ai_risk, compliance"
                        />
                        <p className="mt-1 text-sm text-secondary-500">
                          Comma-separated, e.g. ai_governance, ai_risk, compliance
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Section C - Crawling Behavior */}
                  <div>
                    <h3 className="text-lg font-semibold text-secondary-900 mb-4">Crawling Behavior</h3>
                    <div className="grid grid-cols-2 gap-4">
                      <Input
                        label="Crawl Priority (1-10)"
                        type="number"
                        min={1}
                        max={10}
                        value={createForm.crawl_priority}
                        onChange={(e) => setCreateForm({ ...createForm, crawl_priority: parseInt(e.target.value) || 5 })}
                      />
                      <Input
                        label="Frequency (hours)"
                        type="number"
                        min={1}
                        value={createForm.frequency_hours}
                        onChange={(e) => setCreateForm({ ...createForm, frequency_hours: parseInt(e.target.value) || 24 })}
                      />
                      <Input
                        label="Max Depth"
                        type="number"
                        min={0}
                        value={2}
                        disabled
                      />
                      <div>
                        <Input
                          label="Max Pages Per Run"
                          type="number"
                          min={1}
                          value={50}
                          disabled
                        />
                        <p className="mt-1 text-sm text-secondary-500">
                          Higher = more pages per crawl, but more data and load
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Section D - Path Patterns & Sitemap */}
                  <div>
                    <h3 className="text-lg font-semibold text-secondary-900 mb-4">Path Patterns & Sitemap</h3>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-secondary-700 mb-1">
                          Allowed Path Patterns
                        </label>
                        <textarea
                          className="w-full px-4 py-2 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                          rows={4}
                          value={createForm.allowed_path_patterns}
                          onChange={(e) => setCreateForm({ ...createForm, allowed_path_patterns: e.target.value })}
                          placeholder="/ai-act&#10;/legislation&#10;/regulation"
                        />
                        <p className="mt-1 text-sm text-secondary-500">
                          One pattern per line, e.g. /ai-act, /legislation, /regulation. Use this to focus on legislation/regulation paths.
                        </p>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-secondary-700 mb-1">
                          Excluded Path Patterns
                        </label>
                        <textarea
                          className="w-full px-4 py-2 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                          rows={4}
                          value={createForm.excluded_path_patterns}
                          onChange={(e) => setCreateForm({ ...createForm, excluded_path_patterns: e.target.value })}
                          placeholder="/news&#10;/blog&#10;/media"
                        />
                        <p className="mt-1 text-sm text-secondary-500">
                          One pattern per line, e.g. /news, /blog, /media. Use this to exclude news/blog/media paths.
                        </p>
                      </div>
                      <Input
                        label="Sitemap URL (optional)"
                        type="url"
                        value={createForm.sitemap_url}
                        onChange={(e) => setCreateForm({ ...createForm, sitemap_url: e.target.value })}
                        placeholder="https://example.com/sitemap.xml"
                      />
                    </div>
                  </div>

                  <div className="flex gap-4 pt-4">
                    <Button type="submit" disabled={createOriginMutation.isPending || !createForm.name.trim() || !createForm.url.trim()}>
                      {createOriginMutation.isPending ? 'Creating...' : 'Create Origin'}
                    </Button>
                    <Button type="button" variant="secondary" onClick={() => setShowCreateModal(false)}>
                      Cancel
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
};

