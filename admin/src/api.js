const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

const getAuthHeaders = () => {
  const token = localStorage.getItem('token')
  return {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` })
  }
}

const handleResponse = async (response) => {
  const data = await response.json()
  if (!response.ok) {
    throw new Error(data.error || data.message || `HTTP ${response.status}`)
  }
  return data
}

// Auth API
export const login = async (email, password) => {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  })
  return handleResponse(response)
}

export const logout = () => {
  // Just remove token from localStorage
  localStorage.removeItem('token')
}

export const getCurrentUser = async () => {
  const response = await fetch(`${API_BASE_URL}/api/auth/profile`, {
    headers: getAuthHeaders()
  })
  return handleResponse(response)
}

// Dashboard API
export const getDashboardStats = async () => {
  const response = await fetch(`${API_BASE_URL}/api/stats`, {
    headers: getAuthHeaders()
  })
  return handleResponse(response)
}

// Domains API
export const getDomains = async (page = 1, status = '') => {
  const params = new URLSearchParams({ page: page.toString() })
  if (status) params.append('status', status)
  
  const response = await fetch(`${API_BASE_URL}/api/domains?${params}`, {
    headers: getAuthHeaders()
  })
  return handleResponse(response)
}

export const createDomain = async (domainData) => {
  const response = await fetch(`${API_BASE_URL}/api/domains`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(domainData)
  })
  return handleResponse(response)
}

export const updateDomain = async (domainId, domainData) => {
  const response = await fetch(`${API_BASE_URL}/api/domains/${domainId}`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify(domainData)
  })
  return handleResponse(response)
}

export const deleteDomain = async (domainId) => {
  const response = await fetch(`${API_BASE_URL}/api/domains/${domainId}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  })
  return handleResponse(response)
}

export const toggleDomainCDN = async (domainId) => {
  const response = await fetch(`${API_BASE_URL}/api/domains/${domainId}/toggle`, {
    method: 'POST',
    headers: getAuthHeaders()
  })
  return handleResponse(response)
}

// Cache API
export const purgeDomainCache = async (domainId) => {
  const response = await fetch(`${API_BASE_URL}/api/cache/purge/domain`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ domain_id: domainId })
  })
  return handleResponse(response)
}

export const purgeUrlCache = async (domainId, urlPath) => {
  const response = await fetch(`${API_BASE_URL}/api/cache/purge/url`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ domain_id: domainId, url_path: urlPath })
  })
  return handleResponse(response)
}

export const getCacheStats = async (domainId, days = 7) => {
  const response = await fetch(`${API_BASE_URL}/api/cache/stats/domain/${domainId}?days=${days}`, {
    headers: getAuthHeaders()
  })
  return handleResponse(response)
}

// Edge Nodes API
export const getEdgeNodes = async (page = 1, region = '', status = '') => {
  const params = new URLSearchParams({ page: page.toString() })
  if (region) params.append('region', region)
  if (status) params.append('status', status)
  
  const response = await fetch(`${API_BASE_URL}/api/auto-scale/edge-nodes?${params}`, {
    headers: getAuthHeaders()
  })
  return handleResponse(response)
}

export const createEdgeNode = async (nodeData) => {
  const response = await fetch(`${API_BASE_URL}/api/auto-scale/edge-nodes`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(nodeData)
  })
  return handleResponse(response)
}

export const updateEdgeNode = async (nodeId, nodeData) => {
  const response = await fetch(`${API_BASE_URL}/api/auto-scale/edge-nodes/${nodeId}`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify(nodeData)
  })
  return handleResponse(response)
}

export const deleteEdgeNode = async (nodeId) => {
  const response = await fetch(`${API_BASE_URL}/api/auto-scale/edge-nodes/${nodeId}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  })
  return handleResponse(response)
}

export const getScalingStats = async () => {
  const response = await fetch(`${API_BASE_URL}/api/auto-scale/stats`, {
    headers: getAuthHeaders()
  })
  return handleResponse(response)
}

export const triggerScaleUp = async (region, provider) => {
  const response = await fetch(`${API_BASE_URL}/api/auto-scale/scale-up`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ region, provider })
  })
  return handleResponse(response)
}

export const triggerScaleDown = async (region) => {
  const response = await fetch(`${API_BASE_URL}/api/auto-scale/scale-down`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ region })
  })
  return handleResponse(response)
}

// SSL API
export const getSSLCertificates = async (page = 1, status = '') => {
  const params = new URLSearchParams({ page: page.toString() })
  if (status) params.append('status', status)
  
  const response = await fetch(`${API_BASE_URL}/api/ssl/certificates?${params}`, {
    headers: getAuthHeaders()
  })
  return handleResponse(response)
}

export const issueSSLCertificate = async (domainId) => {
  const response = await fetch(`${API_BASE_URL}/api/ssl/issue`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ domain_id: domainId })
  })
  return handleResponse(response)
}

export const renewSSLCertificate = async (certId) => {
  const response = await fetch(`${API_BASE_URL}/api/ssl/certificates/${certId}/renew`, {
    method: 'POST',
    headers: getAuthHeaders()
  })
  return handleResponse(response)
}

export const deleteSSLCertificate = async (certId) => {
  const response = await fetch(`${API_BASE_URL}/api/ssl/certificates/${certId}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  })
  return handleResponse(response)
}

export const getExpiringCertificates = async (days = 30) => {
  const response = await fetch(`${API_BASE_URL}/api/ssl/expiring?days=${days}`, {
    headers: getAuthHeaders()
  })
  return handleResponse(response)
}

// Users API (Admin only)
export const getUsers = async (page = 1) => {
  const response = await fetch(`${API_BASE_URL}/api/auth/users?page=${page}`, {
    headers: getAuthHeaders()
  })
  return handleResponse(response)
}

export const toggleUserStatus = async (userId) => {
  const response = await fetch(`${API_BASE_URL}/api/auth/users/${userId}/toggle`, {
    method: 'POST',
    headers: getAuthHeaders()
  })
  return handleResponse(response)
}

// Statistics API
export const getBandwidthReport = async (days = 30) => {
  const response = await fetch(`${API_BASE_URL}/api/stats/bandwidth-report?days=${days}`, {
    headers: getAuthHeaders()
  })
  return handleResponse(response)
}

export const getDomainAnalytics = async (domainId, days = 30) => {
  const response = await fetch(`${API_BASE_URL}/api/stats/domains/${domainId}/analytics?days=${days}`, {
    headers: getAuthHeaders()
  })
  return handleResponse(response)
}

export const getEdgeNodeMetrics = async (edgeId, days = 7) => {
  const response = await fetch(`${API_BASE_URL}/api/stats/edge-nodes/${edgeId}/metrics?days=${days}`, {
    headers: getAuthHeaders()
  })
  return handleResponse(response)
}

export const getRealTimeStats = async () => {
  const response = await fetch(`${API_BASE_URL}/api/stats/real-time`, {
    headers: getAuthHeaders()
  })
  return handleResponse(response)
}