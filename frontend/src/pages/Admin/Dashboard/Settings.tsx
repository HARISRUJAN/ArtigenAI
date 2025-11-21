import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { dashboardAPI } from '../../../services/api';
import { Card, CardHeader, CardTitle, CardContent } from '../../../components/Card';
import { Button } from '../../../components/Button';
import { Input } from '../../../components/Input';
import { Select } from '../../../components/Select';

export const DashboardSettings: React.FC = () => {
  const queryClient = useQueryClient();
  const { data: settings, isLoading } = useQuery({
    queryKey: ['dashboard-settings'],
    queryFn: dashboardAPI.getSettings,
  });

  const [formData, setFormData] = useState({
    crawling: {
      priority_score_threshold: -10.0,
      max_low_priority_pages: 10,
      sitemap_max_urls_per_origin: 1000,
      enable_priority_queue: false,
      enable_topic_filtering: false,
      policy_keyword_threshold: 3,
    },
    realtime_web: {
      enable_realtime_web: false,
      realtime_web_max_seconds: 5.0,
      realtime_web_max_pages: 10,
      realtime_web_max_bytes_per_page: 500000,
      min_similarity_threshold: 0.6,
      min_results: 3,
    },
    rag: {
      rag_mode: 'semantic_only',
      enable_hybrid_search: false,
      enable_reranking: false,
    },
    data_retention: {
      scheduled_docs_retention: 'keep_all',
      realtime_web_ttl_hours: 24,
      enable_deduplication: false,
    },
  });

  useEffect(() => {
    if (settings) {
      setFormData({
        crawling: settings.crawling || formData.crawling,
        realtime_web: settings.realtime_web || formData.realtime_web,
        rag: settings.rag || formData.rag,
        data_retention: settings.data_retention || formData.data_retention,
      });
    }
  }, [settings]);

  const updateSettingsMutation = useMutation({
    mutationFn: (updates: any) => dashboardAPI.updateSettings(updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard-settings'] });
      alert('Settings updated successfully');
    },
    onError: (error: any) => {
      alert(`Error updating settings: ${error.response?.data?.detail || error.message}`);
    },
  });

  const handleSave = (section: string) => {
    updateSettingsMutation.mutate({
      [section]: formData[section as keyof typeof formData],
    });
  };

  const handleChange = (section: string, key: string, value: any) => {
    setFormData({
      ...formData,
      [section]: {
        ...formData[section as keyof typeof formData],
        [key]: value,
      },
    });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-secondary-50 p-8">
        <div className="max-w-4xl mx-auto">
          <div className="text-center py-12">
            <p className="text-secondary-600">Loading settings...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-secondary-50 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-secondary-900">Settings</h1>
          <p className="text-secondary-600 mt-2">Configure system-wide settings</p>
        </div>

        {/* Crawling Settings */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Crawling Settings</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <Input
                label="Priority Score Threshold"
                type="number"
                step="0.1"
                value={formData.crawling.priority_score_threshold}
                onChange={(e) => handleChange('crawling', 'priority_score_threshold', parseFloat(e.target.value))}
              />
              <Input
                label="Max Low Priority Pages"
                type="number"
                value={formData.crawling.max_low_priority_pages}
                onChange={(e) => handleChange('crawling', 'max_low_priority_pages', parseInt(e.target.value))}
                min={0}
              />
              <Input
                label="Sitemap Max URLs per Origin"
                type="number"
                value={formData.crawling.sitemap_max_urls_per_origin}
                onChange={(e) => handleChange('crawling', 'sitemap_max_urls_per_origin', parseInt(e.target.value))}
                min={1}
              />
              <Select
                label="Enable Priority Queue"
                value={formData.crawling.enable_priority_queue ? 'true' : 'false'}
                onChange={(e) => handleChange('crawling', 'enable_priority_queue', e.target.value === 'true')}
                options={[
                  { value: 'false', label: 'Disabled' },
                  { value: 'true', label: 'Enabled' },
                ]}
              />
              <Select
                label="Enable Topic Filtering"
                value={formData.crawling.enable_topic_filtering ? 'true' : 'false'}
                onChange={(e) => handleChange('crawling', 'enable_topic_filtering', e.target.value === 'true')}
                options={[
                  { value: 'false', label: 'Disabled' },
                  { value: 'true', label: 'Enabled' },
                ]}
              />
              <Input
                label="Policy Keyword Threshold"
                type="number"
                value={formData.crawling.policy_keyword_threshold}
                onChange={(e) => handleChange('crawling', 'policy_keyword_threshold', parseInt(e.target.value))}
                min={1}
              />
              <Button onClick={() => handleSave('crawling')} disabled={updateSettingsMutation.isPending}>
                Save Crawling Settings
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Real-Time Web Settings */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Real-Time Web Settings</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <Select
                label="Enable Realtime Web"
                value={formData.realtime_web.enable_realtime_web ? 'true' : 'false'}
                onChange={(e) => handleChange('realtime_web', 'enable_realtime_web', e.target.value === 'true')}
                options={[
                  { value: 'false', label: 'Disabled' },
                  { value: 'true', label: 'Enabled' },
                ]}
              />
              <Input
                label="Max Seconds"
                type="number"
                step="0.1"
                value={formData.realtime_web.realtime_web_max_seconds}
                onChange={(e) => handleChange('realtime_web', 'realtime_web_max_seconds', parseFloat(e.target.value))}
                min={1}
              />
              <Input
                label="Max Pages"
                type="number"
                value={formData.realtime_web.realtime_web_max_pages}
                onChange={(e) => handleChange('realtime_web', 'realtime_web_max_pages', parseInt(e.target.value))}
                min={1}
              />
              <Input
                label="Max Bytes per Page"
                type="number"
                value={formData.realtime_web.realtime_web_max_bytes_per_page}
                onChange={(e) => handleChange('realtime_web', 'realtime_web_max_bytes_per_page', parseInt(e.target.value))}
                min={1000}
              />
              <Input
                label="Min Similarity Threshold"
                type="number"
                step="0.1"
                value={formData.realtime_web.min_similarity_threshold}
                onChange={(e) => handleChange('realtime_web', 'min_similarity_threshold', parseFloat(e.target.value))}
                min={0}
                max={1}
              />
              <Input
                label="Min Results"
                type="number"
                value={formData.realtime_web.min_results}
                onChange={(e) => handleChange('realtime_web', 'min_results', parseInt(e.target.value))}
                min={1}
              />
              <Button onClick={() => handleSave('realtime_web')} disabled={updateSettingsMutation.isPending}>
                Save Real-Time Web Settings
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* RAG Settings */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>RAG & Retrieval Settings</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <Select
                label="RAG Mode"
                value={formData.rag.rag_mode}
                onChange={(e) => handleChange('rag', 'rag_mode', e.target.value)}
                options={[
                  { value: 'semantic_only', label: 'Semantic Only' },
                  { value: 'hybrid', label: 'Hybrid' },
                  { value: 'hybrid_rerank', label: 'Hybrid + Rerank' },
                ]}
              />
              <Select
                label="Enable Hybrid Search"
                value={formData.rag.enable_hybrid_search ? 'true' : 'false'}
                onChange={(e) => handleChange('rag', 'enable_hybrid_search', e.target.value === 'true')}
                options={[
                  { value: 'false', label: 'Disabled' },
                  { value: 'true', label: 'Enabled' },
                ]}
              />
              <Select
                label="Enable Reranking"
                value={formData.rag.enable_reranking ? 'true' : 'false'}
                onChange={(e) => handleChange('rag', 'enable_reranking', e.target.value === 'true')}
                options={[
                  { value: 'false', label: 'Disabled' },
                  { value: 'true', label: 'Enabled' },
                ]}
              />
              <Button onClick={() => handleSave('rag')} disabled={updateSettingsMutation.isPending}>
                Save RAG Settings
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Data Retention Settings */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Data Retention Settings</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <Select
                label="Scheduled Docs Retention"
                value={formData.data_retention.scheduled_docs_retention}
                onChange={(e) => handleChange('data_retention', 'scheduled_docs_retention', e.target.value)}
                options={[
                  { value: 'keep_all', label: 'Keep All' },
                  { value: 'keep_latest', label: 'Keep Latest Only' },
                ]}
              />
              <Input
                label="Realtime Web TTL (hours)"
                type="number"
                value={formData.data_retention.realtime_web_ttl_hours}
                onChange={(e) => handleChange('data_retention', 'realtime_web_ttl_hours', parseInt(e.target.value))}
                min={1}
              />
              <Select
                label="Enable Deduplication"
                value={formData.data_retention.enable_deduplication ? 'true' : 'false'}
                onChange={(e) => handleChange('data_retention', 'enable_deduplication', e.target.value === 'true')}
                options={[
                  { value: 'false', label: 'Disabled' },
                  { value: 'true', label: 'Enabled' },
                ]}
              />
              <Button onClick={() => handleSave('data_retention')} disabled={updateSettingsMutation.isPending}>
                Save Data Retention Settings
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

