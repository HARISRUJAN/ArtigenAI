import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminAPI } from '../../services/api';
import { Button } from '../../components/Button';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/Card';
import { Input } from '../../components/Input';
import { Select } from '../../components/Select';

export const AdminDashboard: React.FC = () => {
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    url: '',
    frequency_hours: 24,
    enabled: true,
  });
  const queryClient = useQueryClient();

  const { data: origins, isLoading } = useQuery({
    queryKey: ['origins'],
    queryFn: adminAPI.getOrigins,
  });

  const createMutation = useMutation({
    mutationFn: adminAPI.createOrigin,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['origins'] });
      setShowForm(false);
      resetForm();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => adminAPI.updateOrigin(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['origins'] });
      setEditingId(null);
      resetForm();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: adminAPI.deleteOrigin,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['origins'] });
    },
  });

  const resetForm = () => {
    setFormData({
      name: '',
      url: '',
      frequency_hours: 24,
      enabled: true,
    });
  };

  const handleEdit = (origin: any) => {
    setEditingId(origin.id);
    setFormData({
      name: origin.name,
      url: origin.url,
      frequency_hours: origin.frequency_hours,
      enabled: origin.enabled,
    });
    setShowForm(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingId) {
      updateMutation.mutate({ id: editingId, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingId(null);
    resetForm();
  };

  const handleDelete = (id: number) => {
    if (confirm('Are you sure you want to delete this origin?')) {
      deleteMutation.mutate(id);
    }
  };

  const handleToggle = (origin: any) => {
    updateMutation.mutate({
      id: origin.id,
      data: { enabled: !origin.enabled },
    });
  };

  return (
    <div className="min-h-screen bg-secondary-50 p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-secondary-900">Admin Dashboard</h1>
            <p className="text-secondary-600 mt-2">Manage scraping origins and system configuration</p>
          </div>
          <Button onClick={() => setShowForm(true)} disabled={showForm}>
            Add Origin
          </Button>
        </div>

        {showForm && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>{editingId ? 'Edit Origin' : 'Add New Origin'}</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <Input
                  label="Name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
                <Input
                  label="URL"
                  type="url"
                  value={formData.url}
                  onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                  required
                />
                <Input
                  label="Frequency (hours)"
                  type="number"
                  value={formData.frequency_hours}
                  onChange={(e) => setFormData({ ...formData, frequency_hours: parseInt(e.target.value) })}
                  min={1}
                  required
                />
                <Select
                  label="Status"
                  value={formData.enabled ? 'enabled' : 'disabled'}
                  onChange={(e) => setFormData({ ...formData, enabled: e.target.value === 'enabled' })}
                  options={[
                    { value: 'enabled', label: 'Enabled' },
                    { value: 'disabled', label: 'Disabled' },
                  ]}
                />
                <div className="flex gap-4">
                  <Button type="submit">
                    {editingId ? 'Update' : 'Create'}
                  </Button>
                  <Button type="button" variant="secondary" onClick={handleCancel}>
                    Cancel
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        {isLoading ? (
          <div className="text-center py-12">
            <p className="text-secondary-600">Loading...</p>
          </div>
        ) : origins && origins.length > 0 ? (
          <div className="grid gap-4">
            {origins.map((origin: any) => (
              <Card key={origin.id} hover>
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-secondary-900 mb-2">
                      {origin.name}
                    </h3>
                    <p className="text-secondary-600 mb-2">
                      <a href={origin.url} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">
                        {origin.url}
                      </a>
                    </p>
                    <div className="flex gap-4 text-sm text-secondary-500">
                      <span>Frequency: {origin.frequency_hours}h</span>
                      <span>Last run: {origin.last_run ? new Date(origin.last_run).toLocaleString() : 'Never'}</span>
                      <span>Status: {origin.last_status || 'N/A'}</span>
                    </div>
                  </div>
                  <div className="flex gap-2 ml-4">
                    <Button
                      variant={origin.enabled ? 'secondary' : 'primary'}
                      size="sm"
                      onClick={() => handleToggle(origin)}
                    >
                      {origin.enabled ? 'Disable' : 'Enable'}
                    </Button>
                    <Button
                      variant="subtle"
                      size="sm"
                      onClick={() => handleEdit(origin)}
                    >
                      Edit
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDelete(origin.id)}
                    >
                      Delete
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <Card>
            <CardContent>
              <p className="text-secondary-600 text-center py-8">
                No origins configured. Add your first origin to get started.
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

