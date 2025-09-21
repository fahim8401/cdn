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
  localStorage.removeItem('token')
}

export const getCurrentUser = async () => {
  const response = await fetch(`${API_BASE_URL}/api/auth/profile`, {
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

export const toggleDomainCDN = async (domainId) => {
  const response = await fetch(`${API_BASE_URL}/api/domains/${domainId}/toggle`, {
    method: 'POST',
    headers: getAuthHeaders()
  })
  return handleResponse(response)
}

export const regeneratePurgeKey = async (domainId) => {
  const response = await fetch(`${API_BASE_URL}/api/domains/${domainId}/regenerate-purge-key`, {
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

export const getCacheOverview = async (days = 7) => {
  const response = await fetch(`${API_BASE_URL}/api/cache/stats/overview?days=${days}`, {
    headers: getAuthHeaders()
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

export const downloadSSLCertificate = (certId, type = 'cert') => {
  const token = localStorage.getItem('token')
  const url = `${API_BASE_URL}/api/ssl/certificates/${certId}/download?type=${type}`
  
  // Create a temporary link and click it to download
  const link = document.createElement('a')
  link.href = url
  link.download = ''
  link.style.display = 'none'
  
  // Add authorization header by opening in new window if needed
  if (token) {
    fetch(url, {
      headers: getAuthHeaders()
    }).then(response => response.blob())
      .then(blob => {
        const url = window.URL.createObjectURL(blob)
        link.href = url
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
      })
      .catch(error => {
        alert('Download failed: ' + error.message)
      })
  }
}