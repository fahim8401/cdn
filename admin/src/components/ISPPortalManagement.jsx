import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import { Button } from './ui/Button';
import { Input } from './ui/Input';
import { Modal } from './ui/Modal';
import { Badge } from './ui/Badge';
import { Alert, AlertDescription } from './ui/Alert';
import { 
  Building2, 
  Search, 
  Check, 
  X, 
  Eye, 
  Download, 
  TrendingUp,
  Globe,
  CheckCircle,
  AlertTriangle,
  Clock
} from 'lucide-react';
import api from '../api';

const ISPPortalManagement = () => {
  const [isps, setIsps] = useState([]);
  const [selectedIsp, setSelectedIsp] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  
  // Modal states
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [showApprovalModal, setShowApprovalModal] = useState(false);
  
  // Approval form state
  const [approvalData, setApprovalData] = useState({
    anycast_ip: '',
    traffic_limit_gbps: 100
  });

  useEffect(() => {
    fetchIsps();
  }, [searchTerm, statusFilter, currentPage]);

  const fetchIsps = async () => {
    try {
      setLoading(true);
      const response = await api.get('/admin/isps', {
        params: {
          search: searchTerm,
          status: statusFilter,
          page: currentPage,
          per_page: 25
        }
      });
      setIsps(response.data.isps);
      setTotalPages(response.data.pagination.pages);
    } catch (err) {
      setError('Failed to fetch ISP registrations');
      console.error('Error fetching ISPs:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApproveIsp = async (ispId) => {
    try {
      setLoading(true);
      await api.post(`/admin/isps/${ispId}/approve`, approvalData);
      setSuccess('ISP approved successfully');
      setShowApprovalModal(false);
      setApprovalData({ anycast_ip: '', traffic_limit_gbps: 100 });
      fetchIsps();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to approve ISP');
    } finally {
      setLoading(false);
    }
  };

  const handleRejectIsp = async (ispId, reason = '') => {
    if (!window.confirm('Are you sure you want to reject this ISP registration?')) {
      return;
    }

    try {
      setLoading(true);
      await api.post(`/admin/isps/${ispId}/reject`, { reason });
      setSuccess('ISP rejected');
      fetchIsps();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to reject ISP');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      case 'approved': return 'bg-green-100 text-green-800';
      case 'active': return 'bg-blue-100 text-blue-800';
      case 'rejected': return 'bg-red-100 text-red-800';
      case 'disconnected': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'pending': return <Clock className="w-4 h-4" />;
      case 'approved': return <CheckCircle className="w-4 h-4" />;
      case 'active': return <CheckCircle className="w-4 h-4" />;
      case 'rejected': return <X className="w-4 h-4" />;
      case 'disconnected': return <AlertTriangle className="w-4 h-4" />;
      default: return <Clock className="w-4 h-4" />;
    }
  };

  const getPeeringMethodColor = (method) => {
    const colors = {
      'IXP': 'bg-blue-100 text-blue-800',
      'Direct': 'bg-green-100 text-green-800',
      'GRE': 'bg-purple-100 text-purple-800',
      'Hosted': 'bg-orange-100 text-orange-800'
    };
    return colors[method] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">ISP Portal Management</h1>
          <p className="text-gray-600">Manage ISP registrations and peering requests</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchIsps}>
            Refresh
          </Button>
        </div>
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

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <Input
                  type="text"
                  placeholder="Search ISPs..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Status</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="active">Active</option>
              <option value="rejected">Rejected</option>
              <option value="disconnected">Disconnected</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* ISP Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-yellow-100 rounded-lg">
                <Clock className="w-6 h-6 text-yellow-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Pending</p>
                <p className="text-2xl font-bold text-gray-900">
                  {isps.filter(isp => isp.status === 'pending').length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-green-100 rounded-lg">
                <CheckCircle className="w-6 h-6 text-green-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Active</p>
                <p className="text-2xl font-bold text-gray-900">
                  {isps.filter(isp => isp.status === 'active').length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Building2 className="w-6 h-6 text-blue-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total ISPs</p>
                <p className="text-2xl font-bold text-gray-900">{isps.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Globe className="w-6 h-6 text-purple-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">BGP Sessions</p>
                <p className="text-2xl font-bold text-gray-900">
                  {isps.filter(isp => isp.status === 'active' && isp.asn).length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ISP Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="w-5 h-5" />
            ISP Registrations ({isps.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-2 text-gray-600">Loading ISPs...</p>
            </div>
          ) : isps.length === 0 ? (
            <div className="text-center py-8">
              <Building2 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">No ISP registrations found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-900">Company</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900">Contact</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900">ASN</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900">Peering</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900">Status</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900">Registered</th>
                    <th className="text-center py-3 px-4 font-medium text-gray-900">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {isps.map((isp) => (
                    <tr key={isp.id} className="hover:bg-gray-50">
                      <td className="py-3 px-4">
                        <div className="font-medium text-gray-900">{isp.company_name}</div>
                        <div className="text-sm text-gray-500">{isp.email}</div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="text-sm">
                          <div className="font-medium text-gray-900">{isp.contact_name}</div>
                          {isp.phone && (
                            <div className="text-gray-500">{isp.phone}</div>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        {isp.asn ? (
                          <div className="text-sm">
                            <div className="font-medium">AS{isp.asn}</div>
                            {isp.public_ip && (
                              <div className="text-gray-500">{isp.public_ip}</div>
                            )}
                          </div>
                        ) : (
                          <span className="text-gray-400">Not provided</span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <div className="space-y-1">
                          <Badge className={getPeeringMethodColor(isp.peering_method)}>
                            {isp.peering_method}
                          </Badge>
                          {isp.peering_point && (
                            <div className="text-xs text-gray-500">{isp.peering_point}</div>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(isp.status)}
                          <Badge className={getStatusColor(isp.status)}>
                            {isp.status}
                          </Badge>
                        </div>
                        {isp.anycast_ip && (
                          <div className="text-xs text-gray-500 mt-1">
                            IP: {isp.anycast_ip}
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-sm text-gray-600">
                          {new Date(isp.created_at).toLocaleDateString()}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex justify-center gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setSelectedIsp(isp);
                              setShowDetailsModal(true);
                            }}
                          >
                            <Eye className="w-4 h-4" />
                          </Button>
                          
                          {isp.status === 'pending' && (
                            <>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => {
                                  setSelectedIsp(isp);
                                  setApprovalData({
                                    anycast_ip: `203.0.113.${10 + isp.id}`,
                                    traffic_limit_gbps: 100
                                  });
                                  setShowApprovalModal(true);
                                }}
                                className="text-green-600 hover:text-green-700"
                              >
                                <Check className="w-4 h-4" />
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleRejectIsp(isp.id)}
                                className="text-red-600 hover:text-red-700"
                              >
                                <X className="w-4 h-4" />
                              </Button>
                            </>
                          )}
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

      {/* ISP Details Modal */}
      <Modal 
        isOpen={showDetailsModal} 
        onClose={() => setShowDetailsModal(false)}
        title={`ISP Details - ${selectedIsp?.company_name}`}
        size="large"
      >
        {selectedIsp && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-6">
              <div>
                <h3 className="text-lg font-medium mb-4">Company Information</h3>
                <div className="space-y-3">
                  <div>
                    <label className="text-sm font-medium text-gray-500">Company Name</label>
                    <p className="text-gray-900">{selectedIsp.company_name}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Contact Name</label>
                    <p className="text-gray-900">{selectedIsp.contact_name}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Email</label>
                    <p className="text-gray-900">{selectedIsp.email}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Phone</label>
                    <p className="text-gray-900">{selectedIsp.phone || 'Not provided'}</p>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-medium mb-4">Network Information</h3>
                <div className="space-y-3">
                  <div>
                    <label className="text-sm font-medium text-gray-500">ASN</label>
                    <p className="text-gray-900">AS{selectedIsp.asn}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Public IP</label>
                    <p className="text-gray-900">{selectedIsp.public_ip}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Peering Method</label>
                    <p className="text-gray-900">{selectedIsp.peering_method}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Peering Point</label>
                    <p className="text-gray-900">{selectedIsp.peering_point || 'Not specified'}</p>
                  </div>
                  {selectedIsp.tunnel_endpoint && (
                    <div>
                      <label className="text-sm font-medium text-gray-500">Tunnel Endpoint</label>
                      <p className="text-gray-900">{selectedIsp.tunnel_endpoint}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {selectedIsp.status === 'approved' || selectedIsp.status === 'active' ? (
              <div>
                <h3 className="text-lg font-medium mb-4">XenCDN Assignment</h3>
                <div className="space-y-3">
                  <div>
                    <label className="text-sm font-medium text-gray-500">Assigned Anycast IP</label>
                    <p className="text-gray-900 font-mono">{selectedIsp.anycast_ip}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Traffic Limit</label>
                    <p className="text-gray-900">{selectedIsp.traffic_limit_gbps} Gbps</p>
                  </div>
                </div>
              </div>
            ) : null}

            {selectedIsp.bgp_config && (
              <div>
                <h3 className="text-lg font-medium mb-4">BGP Configuration</h3>
                <pre className="bg-gray-100 p-4 rounded-md text-sm overflow-x-auto">
                  {selectedIsp.bgp_config}
                </pre>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Approval Modal */}
      <Modal 
        isOpen={showApprovalModal} 
        onClose={() => setShowApprovalModal(false)}
        title={`Approve ISP - ${selectedIsp?.company_name}`}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Anycast IP Assignment
            </label>
            <Input
              type="text"
              placeholder="203.0.113.10"
              value={approvalData.anycast_ip}
              onChange={(e) => setApprovalData({...approvalData, anycast_ip: e.target.value})}
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              IP address from your BGP anycast block
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Traffic Limit (Gbps)
            </label>
            <Input
              type="number"
              value={approvalData.traffic_limit_gbps}
              onChange={(e) => setApprovalData({...approvalData, traffic_limit_gbps: parseInt(e.target.value)})}
              min="1"
              max="1000"
            />
          </div>

          <div className="flex justify-end gap-3">
            <Button 
              variant="outline" 
              onClick={() => setShowApprovalModal(false)}
            >
              Cancel
            </Button>
            <Button 
              onClick={() => handleApproveIsp(selectedIsp.id)}
              disabled={loading}
            >
              {loading ? 'Approving...' : 'Approve ISP'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default ISPPortalManagement;