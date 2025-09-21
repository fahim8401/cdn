import React, { useState, useEffect } from 'react'
import { getDomains, createDomain, updateDomain, deleteDomain, toggleDomainCDN } from '../api.js'
import PurgeButton from './PurgeButton.jsx'

const Domains = () => {
  const [domains, setDomains] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAddForm, setShowAddForm] = useState(false)
  const [editingDomain, setEditingDomain] = useState(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')

  const [formData, setFormData] = useState({
    domain_name: '',
    origin_server: '',
    cache_ttl: 3600
  })

  useEffect(() => {
    loadDomains()
  }, [currentPage, statusFilter])

  const loadDomains = async () => {
    try {
      setLoading(true)
      const response = await getDomains(currentPage, statusFilter)
      setDomains(response.domains)
      setTotalPages(response.pages)
    } catch (error) {
      console.error('Error loading domains:', error)
      alert('Failed to load domains: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      if (editingDomain) {
        await updateDomain(editingDomain.id, formData)
        alert('Domain updated successfully')
      } else {
        await createDomain(formData)
        alert('Domain added successfully')
      }
      
      setFormData({ domain_name: '', origin_server: '', cache_ttl: 3600 })
      setShowAddForm(false)
      setEditingDomain(null)
      loadDomains()
    } catch (error) {
      alert('Error: ' + error.message)
    }
  }

  const handleEdit = (domain) => {
    setEditingDomain(domain)
    setFormData({
      domain_name: domain.domain_name,
      origin_server: domain.origin_server,
      cache_ttl: domain.cache_ttl
    })
    setShowAddForm(true)
  }

  const handleDelete = async (domain) => {
    if (confirm(`Are you sure you want to delete domain "${domain.domain_name}"?`)) {
      try {
        await deleteDomain(domain.id)
        alert('Domain deleted successfully')
        loadDomains()
      } catch (error) {
        alert('Error deleting domain: ' + error.message)
      }
    }
  }

  const handleToggleCDN = async (domain) => {
    try {
      await toggleDomainCDN(domain.id)
      alert(`CDN ${domain.cdn_enabled ? 'disabled' : 'enabled'} for ${domain.domain_name}`)
      loadDomains()
    } catch (error) {
      alert('Error toggling CDN: ' + error.message)
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return '#27ae60'
      case 'pending': return '#f39c12'
      case 'error': return '#e74c3c'
      case 'suspended': return '#95a5a6'
      default: return '#666'
    }
  }

  const cardStyle = {
    backgroundColor: 'white',
    padding: '1.5rem',
    borderRadius: '8px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    marginBottom: '1rem'
  }

  const buttonStyle = {
    padding: '0.5rem 1rem',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '14px',
    marginRight: '0.5rem'
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1 style={{ margin: 0, color: '#2c3e50' }}>🌐 Domain Management</h1>
        <button
          onClick={() => {
            setShowAddForm(true)
            setEditingDomain(null)
            setFormData({ domain_name: '', origin_server: '', cache_ttl: 3600 })
          }}
          style={{
            ...buttonStyle,
            backgroundColor: '#27ae60',
            color: 'white'
          }}
        >
          ➕ Add Domain
        </button>
      </div>

      {/* Filters */}
      <div style={{ ...cardStyle, marginBottom: '1rem' }}>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <label>
            <strong>Filter by Status:</strong>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{ marginLeft: '0.5rem', padding: '0.25rem' }}
            >
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="pending">Pending</option>
              <option value="error">Error</option>
              <option value="suspended">Suspended</option>
            </select>
          </label>
          <button
            onClick={loadDomains}
            style={{
              ...buttonStyle,
              backgroundColor: '#3498db',
              color: 'white'
            }}
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Add/Edit Form */}
      {showAddForm && (
        <div style={cardStyle}>
          <h3 style={{ marginTop: 0, color: '#2c3e50' }}>
            {editingDomain ? '✏️ Edit Domain' : '➕ Add New Domain'}
          </h3>
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                Domain Name:
              </label>
              <input
                type="text"
                value={formData.domain_name}
                onChange={(e) => setFormData({ ...formData, domain_name: e.target.value })}
                placeholder="example.com"
                required
                disabled={editingDomain !== null}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  fontSize: '16px',
                  backgroundColor: editingDomain ? '#f5f5f5' : 'white'
                }}
              />
            </div>
            
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                Origin Server:
              </label>
              <input
                type="url"
                value={formData.origin_server}
                onChange={(e) => setFormData({ ...formData, origin_server: e.target.value })}
                placeholder="https://your-server.com"
                required
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  fontSize: '16px'
                }}
              />
            </div>
            
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                Cache TTL (seconds):
              </label>
              <input
                type="number"
                value={formData.cache_ttl}
                onChange={(e) => setFormData({ ...formData, cache_ttl: parseInt(e.target.value) })}
                min="60"
                max="31536000"
                required
                style={{
                  width: '200px',
                  padding: '0.75rem',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  fontSize: '16px'
                }}
              />
            </div>
            
            <div>
              <button
                type="submit"
                style={{
                  ...buttonStyle,
                  backgroundColor: '#27ae60',
                  color: 'white'
                }}
              >
                {editingDomain ? 'Update Domain' : 'Add Domain'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowAddForm(false)
                  setEditingDomain(null)
                }}
                style={{
                  ...buttonStyle,
                  backgroundColor: '#95a5a6',
                  color: 'white'
                }}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Domains List */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
          Loading domains...
        </div>
      ) : domains.length === 0 ? (
        <div style={cardStyle}>
          <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
            No domains found. Add your first domain to get started!
          </div>
        </div>
      ) : (
        <div>
          {domains.map((domain) => (
            <div key={domain.id} style={cardStyle}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <div style={{ flex: 1 }}>
                  <h3 style={{ margin: '0 0 0.5rem 0', color: '#2c3e50' }}>
                    {domain.domain_name}
                  </h3>
                  
                  <div style={{ marginBottom: '0.5rem' }}>
                    <strong>Origin Server:</strong> {domain.origin_server}
                  </div>
                  
                  <div style={{ display: 'flex', gap: '1rem', marginBottom: '0.5rem' }}>
                    <div>
                      <strong>Status:</strong> 
                      <span style={{ 
                        marginLeft: '0.5rem',
                        color: getStatusColor(domain.status),
                        fontWeight: 'bold',
                        textTransform: 'capitalize'
                      }}>
                        {domain.status}
                      </span>
                    </div>
                    
                    <div>
                      <strong>CDN:</strong> 
                      <span style={{ 
                        marginLeft: '0.5rem',
                        color: domain.cdn_enabled ? '#27ae60' : '#e74c3c',
                        fontWeight: 'bold'
                      }}>
                        {domain.cdn_enabled ? 'Enabled' : 'Disabled'}
                      </span>
                    </div>
                    
                    <div>
                      <strong>SSL:</strong> 
                      <span style={{ 
                        marginLeft: '0.5rem',
                        color: domain.ssl_enabled ? '#27ae60' : '#e74c3c',
                        fontWeight: 'bold'
                      }}>
                        {domain.ssl_enabled ? 'Enabled' : 'Disabled'}
                      </span>
                    </div>
                    
                    <div>
                      <strong>Cache TTL:</strong> {domain.cache_ttl}s
                    </div>
                  </div>
                  
                  <div style={{ fontSize: '14px', color: '#666' }}>
                    Created: {new Date(domain.created_at).toLocaleDateString()}
                  </div>
                </div>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', minWidth: '200px' }}>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button
                      onClick={() => handleToggleCDN(domain)}
                      style={{
                        ...buttonStyle,
                        backgroundColor: domain.cdn_enabled ? '#e74c3c' : '#27ae60',
                        color: 'white',
                        fontSize: '12px'
                      }}
                    >
                      {domain.cdn_enabled ? 'Disable CDN' : 'Enable CDN'}
                    </button>
                    
                    <button
                      onClick={() => handleEdit(domain)}
                      style={{
                        ...buttonStyle,
                        backgroundColor: '#3498db',
                        color: 'white',
                        fontSize: '12px'
                      }}
                    >
                      Edit
                    </button>
                  </div>
                  
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <PurgeButton domainId={domain.id} domainName={domain.domain_name} />
                    
                    <button
                      onClick={() => handleDelete(domain)}
                      style={{
                        ...buttonStyle,
                        backgroundColor: '#e74c3c',
                        color: 'white',
                        fontSize: '12px'
                      }}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          gap: '0.5rem',
          marginTop: '2rem'
        }}>
          <button
            onClick={() => setCurrentPage(currentPage - 1)}
            disabled={currentPage === 1}
            style={{
              ...buttonStyle,
              backgroundColor: currentPage === 1 ? '#95a5a6' : '#3498db',
              color: 'white'
            }}
          >
            Previous
          </button>
          
          <span style={{ 
            padding: '0.5rem 1rem',
            display: 'flex',
            alignItems: 'center',
            color: '#666'
          }}>
            Page {currentPage} of {totalPages}
          </span>
          
          <button
            onClick={() => setCurrentPage(currentPage + 1)}
            disabled={currentPage === totalPages}
            style={{
              ...buttonStyle,
              backgroundColor: currentPage === totalPages ? '#95a5a6' : '#3498db',
              color: 'white'
            }}
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}

export default Domains