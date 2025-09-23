import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Modal } from '../components/ui/Modal';
import { Badge } from '../components/ui/Badge';
import { Alert, AlertDescription } from '../components/ui/Alert';
import { Trash2, Plus, Search, Globe, Settings, CheckCircle, Clock, AlertTriangle } from 'lucide-react';
import api from '../api';

const DNSZoneManager = () => {
  const [zones, setZones] = useState([]);
  const [records, setRecords] = useState([]);
  const [selectedZone, setSelectedZone] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  
  // Modal states
  const [showAddZoneModal, setShowAddZoneModal] = useState(false);
  const [showAddRecordModal, setShowAddRecordModal] = useState(false);
  const [showRecordsModal, setShowRecordsModal] = useState(false);
  
  // Form states
  const [newZoneName, setNewZoneName] = useState('');
  const [newRecord, setNewRecord] = useState({
    name: '',
    type: 'A',
    content: '',
    ttl: 3600,
    priority: 0
  });

  const recordTypes = ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'NS', 'SRV', 'CAA'];

  useEffect(() => {
    fetchZones();
  }, [searchTerm, currentPage]);

  const fetchZones = async () => {
    try {
      setLoading(true);
      const response = await api.get('/dns/zones', {
        params: {
          search: searchTerm,
          page: currentPage,
          per_page: 25
        }
      });
      setZones(response.data.zones);
      setTotalPages(response.data.pagination.pages);
    } catch (err) {
      setError('Failed to fetch DNS zones');
      console.error('Error fetching zones:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchZoneRecords = async (zoneId) => {
    try {
      setLoading(true);
      const response = await api.get(`/dns/zones/${zoneId}/records`);
      setRecords(response.data.records);
      setSelectedZone(response.data.zone);
    } catch (err) {
      setError('Failed to fetch zone records');
      console.error('Error fetching records:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddZone = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      await api.post('/dns/zones', {
        name: newZoneName.toLowerCase().trim()
      });
      setSuccess('DNS zone created successfully');
      setNewZoneName('');
      setShowAddZoneModal(false);
      fetchZones();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to create DNS zone');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteZone = async (zoneId, zoneName) => {
    if (!window.confirm(`Are you sure you want to delete zone "${zoneName}"? This will remove all DNS records.`)) {
      return;
    }

    try {
      setLoading(true);
      await api.delete(`/dns/zones/${zoneId}`);
      setSuccess('DNS zone deleted successfully');
      fetchZones();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to delete DNS zone');
    } finally {
      setLoading(false);
    }
  };

  const handleAddRecord = async (e) => {
    e.preventDefault();
    if (!selectedZone) return;

    try {
      setLoading(true);
      await api.post(`/dns/zones/${selectedZone.id}/records`, newRecord);
      setSuccess('DNS record created successfully');
      setNewRecord({
        name: '',
        type: 'A',
        content: '',
        ttl: 3600,
        priority: 0
      });
      setShowAddRecordModal(false);
      fetchZoneRecords(selectedZone.id);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to create DNS record');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteRecord = async (recordId) => {
    if (!selectedZone) return;
    
    if (!window.confirm('Are you sure you want to delete this DNS record?')) {
      return;
    }

    try {
      setLoading(true);
      await api.delete(`/dns/zones/${selectedZone.id}/records/${recordId}`);
      setSuccess('DNS record deleted successfully');
      fetchZoneRecords(selectedZone.id);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to delete DNS record');
    } finally {
      setLoading(false);
    }
  };

  const handleAutoProvisionCDN = async (zoneId, zoneName) => {
    if (!window.confirm(`Auto-provision CDN for "${zoneName}"? This will create an A record pointing to the anycast IP.`)) {
      return;
    }

    try {
      setLoading(true);
      const response = await api.post(`/dns/zones/${zoneId}/provision`);
      setSuccess(response.data.message);
      fetchZones();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to auto-provision CDN');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800';
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      case 'inactive': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getRecordTypeColor = (type) => {
    const colors = {
      'A': 'bg-blue-100 text-blue-800',
      'AAAA': 'bg-purple-100 text-purple-800',
      'CNAME': 'bg-green-100 text-green-800',
      'MX': 'bg-orange-100 text-orange-800',
      'TXT': 'bg-gray-100 text-gray-800',
      'NS': 'bg-indigo-100 text-indigo-800',
      'SOA': 'bg-red-100 text-red-800'
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">DNS Zone Manager</h1>
          <p className="text-gray-600">Manage DNS zones and records for XenCDN</p>
        </div>
        <Button 
          onClick={() => setShowAddZoneModal(true)}
          className="bg-blue-600 hover:bg-blue-700"
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Zone
        </Button>
      </div>

      {/* Alerts */}
      {error && (
        <Alert className="border-red-200 bg-red-50">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription className="text-red-800">{error}</AlertDescription>
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => setError('')}
            className="ml-auto"
          >
            ×
          </Button>
        </Alert>
      )}

      {success && (
        <Alert className="border-green-200 bg-green-50">
          <CheckCircle className="h-4 w-4" />
          <AlertDescription className="text-green-800">{success}</AlertDescription>
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => setSuccess('')}
            className="ml-auto"
          >
            ×
          </Button>
        </Alert>
      )}

      {/* Search and Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <Input
                  type="text"
                  placeholder="Search zones..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <Button variant="outline" onClick={fetchZones}>
              Refresh
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* DNS Zones Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="w-5 h-5" />
            DNS Zones ({zones.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-2 text-gray-600">Loading zones...</p>
            </div>
          ) : zones.length === 0 ? (
            <div className="text-center py-8">
              <Globe className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">No DNS zones found</p>
              <Button 
                onClick={() => setShowAddZoneModal(true)}
                className="mt-4"
              >
                Create your first zone
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-900">Zone Name</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900">Type</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900">Records</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900">Status</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900">Created</th>
                    <th className="text-center py-3 px-4 font-medium text-gray-900">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {zones.map((zone) => (
                    <tr key={zone.id} className="hover:bg-gray-50">
                      <td className="py-3 px-4">
                        <div className="font-medium text-gray-900">{zone.name}</div>
                        <div className="text-sm text-gray-500">
                          NS: {JSON.parse(zone.ns_records || '[]').join(', ')}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <Badge className="bg-blue-100 text-blue-800">
                          {zone.kind}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-sm text-gray-600">
                          {zone.record_count} records
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <Badge className={getStatusColor(zone.status)}>
                          {zone.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-sm text-gray-600">
                          {new Date(zone.created_at).toLocaleDateString()}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex justify-center gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              fetchZoneRecords(zone.id);
                              setShowRecordsModal(true);
                            }}
                          >
                            Records
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleAutoProvisionCDN(zone.id, zone.name)}
                            className="text-green-600 hover:text-green-700"
                          >
                            <Settings className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDeleteZone(zone.id, zone.name)}
                            className="text-red-600 hover:text-red-700"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-center mt-6 gap-2">
              <Button
                variant="outline"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage(currentPage - 1)}
              >
                Previous
              </Button>
              <span className="flex items-center px-4 text-sm text-gray-600">
                Page {currentPage} of {totalPages}
              </span>
              <Button
                variant="outline"
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage(currentPage + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Add Zone Modal */}
      <Modal 
        isOpen={showAddZoneModal} 
        onClose={() => setShowAddZoneModal(false)}
        title="Add DNS Zone"
      >
        <form onSubmit={handleAddZone} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Domain Name
            </label>
            <Input
              type="text"
              placeholder="example.com"
              value={newZoneName}
              onChange={(e) => setNewZoneName(e.target.value)}
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Enter the domain name without http:// or www.
            </p>
          </div>
          <div className="flex justify-end gap-3">
            <Button 
              type="button" 
              variant="outline" 
              onClick={() => setShowAddZoneModal(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'Creating...' : 'Create Zone'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Zone Records Modal */}
      <Modal 
        isOpen={showRecordsModal} 
        onClose={() => setShowRecordsModal(false)}
        title={`DNS Records - ${selectedZone?.name}`}
        size="large"
      >
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-medium">
              Records for {selectedZone?.name}
            </h3>
            <Button
              onClick={() => setShowAddRecordModal(true)}
              size="sm"
            >
              <Plus className="w-4 h-4 mr-2" />
              Add Record
            </Button>
          </div>

          {records.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-600">No records found for this zone</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-2 font-medium">Name</th>
                    <th className="text-left py-2 font-medium">Type</th>
                    <th className="text-left py-2 font-medium">Content</th>
                    <th className="text-left py-2 font-medium">TTL</th>
                    <th className="text-center py-2 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {records.map((record) => (
                    <tr key={record.id} className="hover:bg-gray-50">
                      <td className="py-2 pr-4">
                        <div className="font-medium">{record.name}</div>
                      </td>
                      <td className="py-2 pr-4">
                        <Badge className={getRecordTypeColor(record.type)}>
                          {record.type}
                        </Badge>
                      </td>
                      <td className="py-2 pr-4">
                        <div className="max-w-xs truncate" title={record.content}>
                          {record.content}
                        </div>
                        {record.priority > 0 && (
                          <div className="text-xs text-gray-500">
                            Priority: {record.priority}
                          </div>
                        )}
                      </td>
                      <td className="py-2 pr-4">
                        {record.ttl}s
                      </td>
                      <td className="py-2 text-center">
                        {!['SOA', 'NS'].includes(record.type) || record.name !== selectedZone?.name ? (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDeleteRecord(record.id)}
                            className="text-red-600 hover:text-red-700"
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        ) : (
                          <span className="text-xs text-gray-400">Protected</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Modal>

      {/* Add Record Modal */}
      <Modal 
        isOpen={showAddRecordModal} 
        onClose={() => setShowAddRecordModal(false)}
        title="Add DNS Record"
      >
        <form onSubmit={handleAddRecord} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Name
            </label>
            <Input
              type="text"
              placeholder="www or @ for root"
              value={newRecord.name}
              onChange={(e) => setNewRecord({...newRecord, name: e.target.value})}
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Type
            </label>
            <select
              value={newRecord.type}
              onChange={(e) => setNewRecord({...newRecord, type: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {recordTypes.map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Content
            </label>
            <Input
              type="text"
              placeholder={newRecord.type === 'A' ? '192.168.1.1' : 'example.com'}
              value={newRecord.content}
              onChange={(e) => setNewRecord({...newRecord, content: e.target.value})}
              required
            />
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                TTL (seconds)
              </label>
              <Input
                type="number"
                value={newRecord.ttl}
                onChange={(e) => setNewRecord({...newRecord, ttl: parseInt(e.target.value)})}
                min="60"
                max="86400"
              />
            </div>
            
            {newRecord.type === 'MX' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Priority
                </label>
                <Input
                  type="number"
                  value={newRecord.priority}
                  onChange={(e) => setNewRecord({...newRecord, priority: parseInt(e.target.value)})}
                  min="0"
                  max="65535"
                />
              </div>
            )}
          </div>
          
          <div className="flex justify-end gap-3">
            <Button 
              type="button" 
              variant="outline" 
              onClick={() => setShowAddRecordModal(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'Creating...' : 'Create Record'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default DNSZoneManager;