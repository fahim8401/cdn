import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import { Button } from './ui/Button';
import { Input } from './ui/Input';
import { Modal } from './ui/Modal';
import { Badge } from './ui/Badge';
import { Alert, AlertDescription } from './ui/Alert';
import { 
  Users, 
  Search, 
  Eye, 
  Ban, 
  CheckCircle, 
  TrendingUp,
  Globe,
  Shield,
  CreditCard,
  AlertTriangle,
  Activity
} from 'lucide-react';
import api from '../api';

const ClientManagement = () => {
  const [clients, setClients] = useState([]);
  const [selectedClient, setSelectedClient] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [planFilter, setPlanFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  
  // Modal states
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [showUsageModal, setShowUsageModal] = useState(false);
  
  // Client usage data
  const [clientUsage, setClientUsage] = useState(null);
  const [clientDomains, setClientDomains] = useState([]);

  useEffect(() => {
    fetchClients();
  }, [searchTerm, planFilter, statusFilter, currentPage]);

  const fetchClients = async () => {
    try {
      setLoading(true);
      // This would be an admin endpoint to list all clients
      const response = await api.get('/admin/clients', {
        params: {
          search: searchTerm,
          plan: planFilter,
          status: statusFilter,
          page: currentPage,
          per_page: 25
        }
      });
      setClients(response.data.clients || []);
      setTotalPages(response.data.pagination?.pages || 1);
    } catch (err) {
      setError('Failed to fetch client data');
      console.error('Error fetching clients:', err);
      // Mock data for demonstration
      setClients([
        {
          id: 1,
          email: 'client1@example.com',
          first_name: 'John',
          last_name: 'Smith',
          company: 'Tech Startup Inc',
          is_active: true,
          created_at: '2024-01-15T10:30:00Z',
          client_info: {
            plan_type: 'pro',
            monthly_bandwidth_limit_gb: 1000,
            current_bandwidth_usage_gb: 450.5,
            domain_limit: 25,
            current_domain_count: 8,
            subscription_status: 'active'
          }
        },
        {
          id: 2,
          email: 'client2@example.com',
          first_name: 'Sarah',
          last_name: 'Johnson',
          company: 'E-commerce Solutions',
          is_active: true,
          created_at: '2024-02-20T14:15:00Z',
          client_info: {
            plan_type: 'enterprise',
            monthly_bandwidth_limit_gb: 10000,
            current_bandwidth_usage_gb: 2350.8,
            domain_limit: 100,
            current_domain_count: 34,
            subscription_status: 'active'
          }
        },
        {
          id: 3,
          email: 'client3@example.com',
          first_name: 'Mike',
          last_name: 'Chen',
          company: 'Digital Agency',
          is_active: false,
          created_at: '2024-03-05T09:45:00Z',
          client_info: {
            plan_type: 'free',
            monthly_bandwidth_limit_gb: 100,
            current_bandwidth_usage_gb: 85.2,
            domain_limit: 3,
            current_domain_count: 3,
            subscription_status: 'suspended'
          }
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const fetchClientUsage = async (clientId) => {
    try {
      setLoading(true);
      const response = await api.get(`/admin/clients/${clientId}/usage`);
      setClientUsage(response.data.usage);
      setClientDomains(response.data.domains || []);
    } catch (err) {
      // Mock usage data
      setClientUsage({
        current_month: {
          bandwidth_gb: 450.5,
          requests: 2500000,
          cache_hit_ratio: 89.2,
          cost_saved_usd: 22.5
        },
        last_30_days: [
          { date: '2024-03-01', bandwidth_gb: 15.2, requests: 80000 },
          { date: '2024-03-02', bandwidth_gb: 18.7, requests: 95000 },
          { date: '2024-03-03', bandwidth_gb: 12.3, requests: 75000 }
        ]
      });
      setClientDomains([
        { id: 1, domain_name: 'example.com', status: 'active', cdn_enabled: true },
        { id: 2, domain_name: 'shop.example.com', status: 'active', cdn_enabled: true },
        { id: 3, domain_name: 'blog.example.com', status: 'active', cdn_enabled: false }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleClientStatus = async (clientId, currentStatus) => {
    const action = currentStatus ? 'disable' : 'enable';
    if (!window.confirm(`Are you sure you want to ${action} this client account?`)) {
      return;
    }

    try {
      setLoading(true);
      await api.post(`/admin/clients/${clientId}/toggle-status`);
      setSuccess(`Client account ${action}d successfully`);
      fetchClients();
    } catch (err) {
      setError(err.response?.data?.error || `Failed to ${action} client account`);
    } finally {
      setLoading(false);
    }
  };

  const getPlanColor = (plan) => {
    switch (plan) {
      case 'free': return 'bg-gray-100 text-gray-800';
      case 'pro': return 'bg-blue-100 text-blue-800';
      case 'enterprise': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800';
      case 'suspended': return 'bg-red-100 text-red-800';
      case 'trial': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const calculateUsagePercentage = (used, limit) => {
    return limit > 0 ? Math.round((used / limit) * 100) : 0;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Client Management</h1>
          <p className="text-gray-600">Manage client accounts and monitor usage</p>
        </div>
        <Button variant="outline" onClick={fetchClients}>
          Refresh
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

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <Input
                  type="text"
                  placeholder="Search clients..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <select
              value={planFilter}
              onChange={(e) => setPlanFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Plans</option>
              <option value="free">Free</option>
              <option value="pro">Pro</option>
              <option value="enterprise">Enterprise</option>
            </select>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Status</option>
              <option value="active">Active</option>
              <option value="suspended">Suspended</option>
              <option value="trial">Trial</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Client Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Users className="w-6 h-6 text-blue-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Clients</p>
                <p className="text-2xl font-bold text-gray-900">{clients.length}</p>
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
                  {clients.filter(c => c.is_active && c.client_info?.subscription_status === 'active').length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-purple-100 rounded-lg">
                <CreditCard className="w-6 h-6 text-purple-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Enterprise</p>
                <p className="text-2xl font-bold text-gray-900">
                  {clients.filter(c => c.client_info?.plan_type === 'enterprise').length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-orange-100 rounded-lg">
                <TrendingUp className="w-6 h-6 text-orange-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Domains</p>
                <p className="text-2xl font-bold text-gray-900">
                  {clients.reduce((total, c) => total + (c.client_info?.current_domain_count || 0), 0)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Clients Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="w-5 h-5" />
            Client Accounts ({clients.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-2 text-gray-600">Loading clients...</p>
            </div>
          ) : clients.length === 0 ? (
            <div className="text-center py-8">
              <Users className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">No clients found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-900">Client</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900">Plan</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900">Domains</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900">Bandwidth Usage</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900">Status</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-900">Joined</th>
                    <th className="text-center py-3 px-4 font-medium text-gray-900">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {clients.map((client) => (
                    <tr key={client.id} className="hover:bg-gray-50">
                      <td className="py-3 px-4">
                        <div>
                          <div className="font-medium text-gray-900">
                            {client.first_name} {client.last_name}
                          </div>
                          <div className="text-sm text-gray-500">{client.email}</div>
                          {client.company && (
                            <div className="text-sm text-gray-500">{client.company}</div>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <Badge className={getPlanColor(client.client_info?.plan_type)}>
                          {client.client_info?.plan_type?.toUpperCase() || 'FREE'}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <div className="text-sm">
                          <div className="font-medium">
                            {client.client_info?.current_domain_count || 0} / {client.client_info?.domain_limit || 3}
                          </div>
                          <div className="text-gray-500">domains</div>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="text-sm">
                          <div className="font-medium">
                            {client.client_info?.current_bandwidth_usage_gb?.toFixed(1) || '0.0'} GB
                          </div>
                          <div className="text-gray-500">
                            of {client.client_info?.monthly_bandwidth_limit_gb || 100} GB
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-1.5 mt-1">
                            <div 
                              className="bg-blue-600 h-1.5 rounded-full" 
                              style={{
                                width: `${Math.min(100, calculateUsagePercentage(
                                  client.client_info?.current_bandwidth_usage_gb || 0,
                                  client.client_info?.monthly_bandwidth_limit_gb || 100
                                ))}%`
                              }}
                            ></div>
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            {client.is_active ? (
                              <CheckCircle className="w-4 h-4 text-green-500" />
                            ) : (
                              <Ban className="w-4 h-4 text-red-500" />
                            )}
                            <span className="text-sm">
                              {client.is_active ? 'Active' : 'Disabled'}
                            </span>
                          </div>
                          <Badge className={getStatusColor(client.client_info?.subscription_status)}>
                            {client.client_info?.subscription_status || 'unknown'}
                          </Badge>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-sm text-gray-600">
                          {new Date(client.created_at).toLocaleDateString()}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex justify-center gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setSelectedClient(client);
                              setShowDetailsModal(true);
                            }}
                          >
                            <Eye className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setSelectedClient(client);
                              fetchClientUsage(client.id);
                              setShowUsageModal(true);
                            }}
                          >
                            <Activity className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleToggleClientStatus(client.id, client.is_active)}
                            className={client.is_active ? "text-red-600 hover:text-red-700" : "text-green-600 hover:text-green-700"}
                          >
                            {client.is_active ? <Ban className="w-4 h-4" /> : <CheckCircle className="w-4 h-4" />}
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

      {/* Client Details Modal */}
      <Modal 
        isOpen={showDetailsModal} 
        onClose={() => setShowDetailsModal(false)}
        title={`Client Details - ${selectedClient?.first_name} ${selectedClient?.last_name}`}
        size="large"
      >
        {selectedClient && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-6">
              <div>
                <h3 className="text-lg font-medium mb-4">Account Information</h3>
                <div className="space-y-3">
                  <div>
                    <label className="text-sm font-medium text-gray-500">Full Name</label>
                    <p className="text-gray-900">{selectedClient.first_name} {selectedClient.last_name}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Email</label>
                    <p className="text-gray-900">{selectedClient.email}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Company</label>
                    <p className="text-gray-900">{selectedClient.company || 'Not provided'}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Account Status</label>
                    <div className="flex items-center gap-2">
                      {selectedClient.is_active ? (
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      ) : (
                        <Ban className="w-4 h-4 text-red-500" />
                      )}
                      <span>{selectedClient.is_active ? 'Active' : 'Disabled'}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-medium mb-4">Subscription Details</h3>
                <div className="space-y-3">
                  <div>
                    <label className="text-sm font-medium text-gray-500">Plan Type</label>
                    <div>
                      <Badge className={getPlanColor(selectedClient.client_info?.plan_type)}>
                        {selectedClient.client_info?.plan_type?.toUpperCase() || 'FREE'}
                      </Badge>
                    </div>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Subscription Status</label>
                    <div>
                      <Badge className={getStatusColor(selectedClient.client_info?.subscription_status)}>
                        {selectedClient.client_info?.subscription_status || 'unknown'}
                      </Badge>
                    </div>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Domain Limit</label>
                    <p className="text-gray-900">{selectedClient.client_info?.domain_limit || 3} domains</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Bandwidth Limit</label>
                    <p className="text-gray-900">{selectedClient.client_info?.monthly_bandwidth_limit_gb || 100} GB/month</p>
                  </div>
                </div>
              </div>
            </div>

            <div>
              <h3 className="text-lg font-medium mb-4">Current Usage</h3>
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <label className="text-sm font-medium text-gray-500">Domains Used</label>
                  <p className="text-gray-900">
                    {selectedClient.client_info?.current_domain_count || 0} / {selectedClient.client_info?.domain_limit || 3}
                  </p>
                  <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                    <div 
                      className="bg-blue-600 h-2 rounded-full" 
                      style={{
                        width: `${Math.min(100, calculateUsagePercentage(
                          selectedClient.client_info?.current_domain_count || 0,
                          selectedClient.client_info?.domain_limit || 3
                        ))}%`
                      }}
                    ></div>
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">Bandwidth Used</label>
                  <p className="text-gray-900">
                    {selectedClient.client_info?.current_bandwidth_usage_gb?.toFixed(1) || '0.0'} / {selectedClient.client_info?.monthly_bandwidth_limit_gb || 100} GB
                  </p>
                  <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                    <div 
                      className="bg-green-600 h-2 rounded-full" 
                      style={{
                        width: `${Math.min(100, calculateUsagePercentage(
                          selectedClient.client_info?.current_bandwidth_usage_gb || 0,
                          selectedClient.client_info?.monthly_bandwidth_limit_gb || 100
                        ))}%`
                      }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </Modal>

      {/* Usage Details Modal */}
      <Modal 
        isOpen={showUsageModal} 
        onClose={() => setShowUsageModal(false)}
        title={`Usage Details - ${selectedClient?.first_name} ${selectedClient?.last_name}`}
        size="large"
      >
        {clientUsage && (
          <div className="space-y-6">
            <div className="grid grid-cols-4 gap-4">
              <Card>
                <CardContent className="p-4">
                  <div className="text-center">
                    <p className="text-sm text-gray-600">Bandwidth</p>
                    <p className="text-2xl font-bold text-blue-600">
                      {clientUsage.current_month.bandwidth_gb}GB
                    </p>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="text-center">
                    <p className="text-sm text-gray-600">Requests</p>
                    <p className="text-2xl font-bold text-green-600">
                      {(clientUsage.current_month.requests / 1000000).toFixed(1)}M
                    </p>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="text-center">
                    <p className="text-sm text-gray-600">Cache Hit</p>
                    <p className="text-2xl font-bold text-purple-600">
                      {clientUsage.current_month.cache_hit_ratio}%
                    </p>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="text-center">
                    <p className="text-sm text-gray-600">Saved</p>
                    <p className="text-2xl font-bold text-orange-600">
                      ${clientUsage.current_month.cost_saved_usd}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div>
              <h3 className="text-lg font-medium mb-4">Client Domains</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="text-left py-2 font-medium">Domain</th>
                      <th className="text-left py-2 font-medium">Status</th>
                      <th className="text-left py-2 font-medium">CDN</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {clientDomains.map((domain) => (
                      <tr key={domain.id}>
                        <td className="py-2 pr-4">
                          <div className="font-medium">{domain.domain_name}</div>
                        </td>
                        <td className="py-2 pr-4">
                          <Badge className={domain.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                            {domain.status}
                          </Badge>
                        </td>
                        <td className="py-2">
                          <Badge className={domain.cdn_enabled ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'}>
                            {domain.cdn_enabled ? 'Enabled' : 'Disabled'}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default ClientManagement;