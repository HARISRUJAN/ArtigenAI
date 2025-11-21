import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { dashboardAPI } from '../../../services/api';
import { Card, CardHeader, CardTitle, CardContent } from '../../../components/Card';
import { Button } from '../../../components/Button';
import { Select } from '../../../components/Select';

export const DashboardDocuments: React.FC = () => {
  const [filters, setFilters] = useState({
    source_type: '',
    relevance_flag: '',
    page: 1,
    limit: 20,
  });
  const [selectedDocument, setSelectedDocument] = useState<number | null>(null);

  const { data: documents, isLoading } = useQuery({
    queryKey: ['dashboard-documents', filters],
    queryFn: () => dashboardAPI.getDocuments(filters),
  });

  const { data: documentDetail } = useQuery({
    queryKey: ['dashboard-document', selectedDocument],
    queryFn: () => dashboardAPI.getDocument(selectedDocument!),
    enabled: selectedDocument !== null,
  });

  const handleFilterChange = (key: string, value: any) => {
    setFilters({ ...filters, [key]: value, page: 1 });
  };

  // Calculate aggregated metrics
  const totalDocs = documents?.total || 0;
  const totalChunks = documents?.items?.reduce((sum: number, doc: any) => sum + (doc.chunks_count || 0), 0) || 0;
  const avgChunksPerDoc = totalDocs > 0 ? (totalChunks / totalDocs).toFixed(1) : '0';

  if (isLoading) {
    return (
      <div className="min-h-screen bg-secondary-50 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center py-12">
            <p className="text-secondary-600">Loading documents...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-secondary-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-secondary-900">Documents & Ingestion</h1>
          <p className="text-secondary-600 mt-2">Monitor ingested documents and content quality</p>
        </div>

        {/* Aggregated Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-secondary-600">Total Documents</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-secondary-900">{totalDocs}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-secondary-600">Total Chunks</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-secondary-900">{totalChunks}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-secondary-600">Avg Chunks per Doc</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-secondary-900">{avgChunksPerDoc}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-secondary-600">Duplicated</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-secondary-900">
                {documents?.items?.filter((d: any) => d.dedup_status === 'duplicate').length || 0}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card className="mb-6">
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Select
                label="Source Type"
                value={filters.source_type}
                onChange={(e) => handleFilterChange('source_type', e.target.value)}
                options={[
                  { value: '', label: 'All' },
                  { value: 'scheduled', label: 'Scheduled' },
                  { value: 'query_seeded', label: 'Query Seeded' },
                  { value: 'web_live', label: 'Realtime Web' },
                ]}
              />
              <Select
                label="Relevance"
                value={filters.relevance_flag}
                onChange={(e) => handleFilterChange('relevance_flag', e.target.value)}
                options={[
                  { value: '', label: 'All' },
                  { value: 'high', label: 'High' },
                  { value: 'medium', label: 'Medium' },
                  { value: 'low', label: 'Low' },
                ]}
              />
            </div>
          </CardContent>
        </Card>

        {/* Documents Table */}
        <Card>
          <CardHeader>
            <CardTitle>Documents</CardTitle>
          </CardHeader>
          <CardContent>
            {documents?.items && documents.items.length > 0 ? (
              <>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-secondary-200">
                    <thead className="bg-secondary-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                          Title
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                          Origin
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                          Source Type
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                          Ingestion Date
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                          Chunks
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                          Relevance
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                          Dedup Status
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-secondary-200">
                      {documents.items.map((doc: any) => (
                        <tr key={doc.id} className="hover:bg-secondary-50">
                          <td className="px-6 py-4 text-sm font-medium text-secondary-900 max-w-xs truncate">
                            {doc.title}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-600">
                            {doc.origin_name || 'N/A'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-600">
                            {doc.source_type || 'scheduled'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-600">
                            {doc.ingestion_date ? new Date(doc.ingestion_date).toLocaleDateString() : 'N/A'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-600">
                            {doc.chunks_count || 0}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            {doc.relevance_flag && (
                              <span className={`px-2 py-1 text-xs rounded ${
                                doc.relevance_flag === 'high' ? 'bg-green-100 text-green-700' :
                                doc.relevance_flag === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                                'bg-gray-100 text-gray-700'
                              }`}>
                                {doc.relevance_flag}
                              </span>
                            )}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-600">
                            {doc.dedup_status === 'duplicate' ? (
                              <span className="text-yellow-600">Duplicate</span>
                            ) : (
                              <span className="text-green-600">Unique</span>
                            )}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm">
                            <Button
                              size="sm"
                              variant="primary"
                              onClick={() => setSelectedDocument(doc.id)}
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
                {documents.pages > 1 && (
                  <div className="mt-4 flex justify-between items-center">
                    <div className="text-sm text-secondary-600">
                      Page {documents.page} of {documents.pages} ({documents.total} total)
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
                        disabled={filters.page >= documents.pages}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <p className="text-secondary-600 text-center py-8">No documents found</p>
            )}
          </CardContent>
        </Card>

        {/* Document Detail Modal */}
        {selectedDocument && documentDetail && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <Card className="max-w-3xl w-full mx-4 max-h-[90vh] overflow-y-auto">
              <CardHeader>
                <div className="flex justify-between items-center">
                  <CardTitle>{documentDetail.title}</CardTitle>
                  <Button variant="subtle" onClick={() => setSelectedDocument(null)}>Close</Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <h3 className="font-semibold text-secondary-900 mb-2">Metadata</h3>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-secondary-600">Source:</span>
                        <p className="text-secondary-900">{documentDetail.source}</p>
                      </div>
                      <div>
                        <span className="text-secondary-600">Origin:</span>
                        <p className="text-secondary-900">{documentDetail.origin_name || 'N/A'}</p>
                      </div>
                      <div>
                        <span className="text-secondary-600">URL:</span>
                        <p className="text-secondary-900 break-all">{documentDetail.url || 'N/A'}</p>
                      </div>
                      <div>
                        <span className="text-secondary-600">Ingestion Date:</span>
                        <p className="text-secondary-900">
                          {new Date(documentDetail.ingestion_date).toLocaleString()}
                        </p>
                      </div>
                      <div>
                        <span className="text-secondary-600">Chunks:</span>
                        <p className="text-secondary-900">{documentDetail.chunks_count}</p>
                      </div>
                    </div>
                  </div>

                  {documentDetail.metadata && (
                    <div>
                      <h3 className="font-semibold text-secondary-900 mb-2">Additional Metadata</h3>
                      <pre className="bg-secondary-50 p-4 rounded text-xs overflow-x-auto">
                        {JSON.stringify(documentDetail.metadata, null, 2)}
                      </pre>
                    </div>
                  )}

                  {documentDetail.chunks_summary && documentDetail.chunks_summary.length > 0 && (
                    <div>
                      <h3 className="font-semibold text-secondary-900 mb-2">Chunks Summary</h3>
                      <div className="space-y-2">
                        {documentDetail.chunks_summary.slice(0, 5).map((chunk: any) => (
                          <div key={chunk.id} className="bg-secondary-50 p-3 rounded text-sm">
                            <div className="font-medium text-secondary-700">Chunk {chunk.chunk_index}</div>
                            <div className="text-secondary-600 mt-1">{chunk.content_preview}</div>
                          </div>
                        ))}
                        {documentDetail.chunks_summary.length > 5 && (
                          <p className="text-sm text-secondary-500">
                            ... and {documentDetail.chunks_summary.length - 5} more chunks
                          </p>
                        )}
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

