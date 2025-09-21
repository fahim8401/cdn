import React, { useState, useEffect } from 'react'
import { getSSLCertificates, issueSSLCertificate, renewSSLCertificate, deleteSSLCertificate, getDomains } from '../api.js'

const SSLManager = () => {
  const [certificates, setCertificates] = useState([])
  const [domains, setDomains] = useState([])
  const [loading, setLoading] = useState(true)
  const [showIssueForm, setShowIssueForm] = useState(false)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const [selectedDomain, setSelectedDomain] = useState('')

  useEffect(() => {
    loadData()
  }, [currentPage, statusFilter])

  const loadData = async () => {
    try {
      setLoading(true)
      const [certsResponse, domainsResponse] = await Promise.all([
        getSSLCertificates(currentPage, statusFilter),
        getDomains(1, '')
      ])
      
      setCertificates(certsResponse.certificates)
      setTotalPages(certsResponse.pages)
      setDomains(domainsResponse.domains)
    } catch (error) {
      console.error('Error loading SSL data:', error)
      alert('Failed to load SSL data: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  const handleIssueCertificate = async (e) => {
    e.preventDefault()
    if (!selectedDomain) {
      alert('Please select a domain')
      return
    }

    try {
      await issueSSLCertificate(selectedDomain)
      alert('SSL certificate issuance initiated')
      setShowIssueForm(false)
      setSelectedDomain('')
      loadData()
    } catch (error) {
      alert('Error issuing certificate: ' + error.message)
    }
  }

  const handleRenewCertificate = async (certId) => {
    try {
      await renewSSLCertificate(certId)
      alert('SSL certificate renewal initiated')
      loadData()
    } catch (error) {
      alert('Error renewing certificate: ' + error.message)
    }
  }

  const handleDeleteCertificate = async (cert) => {
    if (confirm(`Are you sure you want to delete SSL certificate for "${cert.domain_name}"?`)) {
      try {
        await deleteSSLCertificate(cert.id)
        alert('SSL certificate deleted successfully')
        loadData()
      } catch (error) {
        alert('Error deleting certificate: ' + error.message)
      }
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return '#27ae60'
      case 'pending': return '#f39c12'
      case 'issuing': return '#3498db'
      case 'renewing': return '#9b59b6'
      case 'expired': return '#e74c3c'
      case 'error': return '#e74c3c'
      default: return '#666'
    }
  }

  const getExpiryColor = (daysUntilExpiry) => {
    if (daysUntilExpiry === null) return '#666'
    if (daysUntilExpiry <= 7) return '#e74c3c'
    if (daysUntilExpiry <= 30) return '#f39c12'
    return '#27ae60'
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
        <h1 style={{ margin: 0, color: '#2c3e50' }}>🔒 SSL Certificate Management</h1>
        <button
          onClick={() => setShowIssueForm(true)}
          style={{
            ...buttonStyle,
            backgroundColor: '#27ae60',
            color: 'white'
          }}
        >
          ➕ Issue Certificate
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
              <option value="issuing">Issuing</option>
              <option value="renewing">Renewing</option>
              <option value="expired">Expired</option>
              <option value="error">Error</option>
            </select>
          </label>
          <button
            onClick={loadData}
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

      {/* Issue Certificate Form */}
      {showIssueForm && (
        <div style={cardStyle}>
          <h3 style={{ marginTop: 0, color: '#2c3e50' }}>🔒 Issue SSL Certificate</h3>
          <form onSubmit={handleIssueCertificate}>
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                Select Domain:
              </label>
              <select
                value={selectedDomain}
                onChange={(e) => setSelectedDomain(e.target.value)}
                required
                style={{
                  width: '300px',
                  padding: '0.75rem',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  fontSize: '16px'
                }}
              >
                <option value="">Choose a domain...</option>
                {domains.map((domain) => (
                  <option key={domain.id} value={domain.id}>
                    {domain.domain_name}
                  </option>
                ))}
              </select>
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
                Issue Certificate
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowIssueForm(false)
                  setSelectedDomain('')
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

      {/* Certificates List */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
          Loading SSL certificates...
        </div>
      ) : certificates.length === 0 ? (
        <div style={cardStyle}>
          <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
            No SSL certificates found. Issue your first certificate to get started!
          </div>
        </div>
      ) : (
        <div>
          {certificates.map((cert) => (
            <div key={cert.id} style={cardStyle}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <div style={{ flex: 1 }}>
                  <h3 style={{ margin: '0 0 0.5rem 0', color: '#2c3e50' }}>
                    {cert.domain_name}
                  </h3>
                  
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '0.5rem' }}>
                    <div>
                      <strong>Status:</strong> 
                      <span style={{ 
                        marginLeft: '0.5rem',
                        color: getStatusColor(cert.status),
                        fontWeight: 'bold',
                        textTransform: 'capitalize'
                      }}>
                        {cert.status}
                      </span>
                    </div>
                    
                    <div>
                      <strong>Issuer:</strong> {cert.issuer}
                    </div>
                    
                    <div>
                      <strong>Auto Renew:</strong> 
                      <span style={{ 
                        marginLeft: '0.5rem',
                        color: cert.auto_renew ? '#27ae60' : '#e74c3c',
                        fontWeight: 'bold'
                      }}>
                        {cert.auto_renew ? 'Enabled' : 'Disabled'}
                      </span>
                    </div>
                    
                    {cert.days_until_expiry !== null && (
                      <div>
                        <strong>Expires in:</strong> 
                        <span style={{ 
                          marginLeft: '0.5rem',
                          color: getExpiryColor(cert.days_until_expiry),
                          fontWeight: 'bold'
                        }}>
                          {cert.days_until_expiry} days
                        </span>
                      </div>
                    )}
                  </div>
                  
                  <div style={{ display: 'flex', gap: '2rem', marginBottom: '0.5rem' }}>
                    {cert.issued_at && (
                      <div style={{ fontSize: '14px', color: '#666' }}>
                        <strong>Issued:</strong> {new Date(cert.issued_at).toLocaleDateString()}
                      </div>
                    )}
                    
                    {cert.expires_at && (
                      <div style={{ fontSize: '14px', color: '#666' }}>
                        <strong>Expires:</strong> {new Date(cert.expires_at).toLocaleDateString()}
                      </div>
                    )}
                  </div>
                </div>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', minWidth: '200px' }}>
                  {cert.status === 'active' && (
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button
                        onClick={() => handleRenewCertificate(cert.id)}
                        style={{
                          ...buttonStyle,
                          backgroundColor: '#3498db',
                          color: 'white',
                          fontSize: '12px'
                        }}
                      >
                        🔄 Renew
                      </button>
                      
                      <a
                        href={`/api/ssl/certificates/${cert.id}/download?type=cert`}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          ...buttonStyle,
                          backgroundColor: '#9b59b6',
                          color: 'white',
                          fontSize: '12px',
                          textDecoration: 'none',
                          display: 'inline-block',
                          textAlign: 'center'
                        }}
                      >
                        📥 Download
                      </a>
                    </div>
                  )}
                  
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    {cert.status === 'active' && (
                      <>
                        <a
                          href={`/api/ssl/certificates/${cert.id}/download?type=key`}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            ...buttonStyle,
                            backgroundColor: '#f39c12',
                            color: 'white',
                            fontSize: '12px',
                            textDecoration: 'none',
                            display: 'inline-block',
                            textAlign: 'center'
                          }}
                        >
                          🔑 Key
                        </a>
                        
                        <a
                          href={`/api/ssl/certificates/${cert.id}/download?type=chain`}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            ...buttonStyle,
                            backgroundColor: '#16a085',
                            color: 'white',
                            fontSize: '12px',
                            textDecoration: 'none',
                            display: 'inline-block',
                            textAlign: 'center'
                          }}
                        >
                          🔗 Chain
                        </a>
                      </>
                    )}
                    
                    <button
                      onClick={() => handleDeleteCertificate(cert)}
                      style={{
                        ...buttonStyle,
                        backgroundColor: '#e74c3c',
                        color: 'white',
                        fontSize: '12px'
                      }}
                    >
                      🗑️ Delete
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

export default SSLManager