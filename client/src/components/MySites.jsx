import React, { useState, useEffect } from 'react'
import { getDomains, toggleDomainCDN, getCacheOverview } from '../api.js'
import PurgeButton from './PurgeButton.jsx'

const MySites = () => {
  const [domains, setDomains] = useState([])
  const [cacheOverview, setCacheOverview] = useState(null)
  const [loading, setLoading] = useState(true)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)

  useEffect(() => {
    loadData()
  }, [currentPage])

  const loadData = async () => {
    try {
      setLoading(true)
      const [domainsResponse, cacheResponse] = await Promise.all([
        getDomains(currentPage, ''),
        getCacheOverview(30) // Last 30 days
      ])
      
      setDomains(domainsResponse.domains)
      setTotalPages(domainsResponse.pages)
      setCacheOverview(cacheResponse)
    } catch (error) {
      console.error('Error loading data:', error)
      alert('Failed to load data: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  const handleToggleCDN = async (domain) => {
    try {
      await toggleDomainCDN(domain.id)
      alert(`CDN ${domain.cdn_enabled ? 'disabled' : 'enabled'} for ${domain.domain_name}`)
      loadData()
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

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '300px',
        fontSize: '18px',
        color: '#666'
      }}>
        Loading your sites...
      </div>
    )
  }

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '2rem', color: '#2c3e50' }}>
        🌐 My CDN-Enabled Sites
      </h1>

      {/* Overview Stats */}
      {cacheOverview && (
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
          gap: '1rem',
          marginBottom: '2rem'
        }}>
          <div style={{
            ...cardStyle,
            textAlign: 'center',
            backgroundColor: '#3498db',
            color: 'white'
          }}>
            <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '24px' }}>
              {cacheOverview.total_domains || 0}
            </h3>
            <p style={{ margin: 0, opacity: 0.9 }}>Total Domains</p>
          </div>
          
          <div style={{
            ...cardStyle,
            textAlign: 'center',
            backgroundColor: '#27ae60',
            color: 'white'
          }}>
            <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '24px' }}>
              {cacheOverview.cache_hit_ratio || 0}%
            </h3>
            <p style={{ margin: 0, opacity: 0.9 }}>Cache Hit Ratio</p>
          </div>
          
          <div style={{
            ...cardStyle,
            textAlign: 'center',
            backgroundColor: '#f39c12',
            color: 'white'
          }}>
            <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '24px' }}>
              {cacheOverview.bandwidth_saved_gb || 0} GB
            </h3>
            <p style={{ margin: 0, opacity: 0.9 }}>Bandwidth Saved</p>
          </div>
          
          <div style={{
            ...cardStyle,
            textAlign: 'center',
            backgroundColor: '#e74c3c',
            color: 'white'
          }}>
            <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '24px' }}>
              {(cacheOverview.total_requests || 0).toLocaleString()}
            </h3>
            <p style={{ margin: 0, opacity: 0.9 }}>Total Requests</p>
          </div>
        </div>
      )}

      {/* Domains List */}
      {domains.length === 0 ? (
        <div style={cardStyle}>
          <div style={{ textAlign: 'center', padding: '3rem', color: '#666' }}>
            <h3 style={{ marginBottom: '1rem', color: '#2c3e50' }}>
              No domains found
            </h3>
            <p style={{ marginBottom: '2rem' }}>
              Contact your administrator to add domains to your CDN account.
            </p>
            <div style={{ 
              padding: '1rem',
              backgroundColor: '#f8f9fa',
              borderRadius: '4px',
              border: '1px solid #dee2e6'
            }}>
              <h4 style={{ margin: '0 0 0.5rem 0', color: '#495057' }}>
                Benefits of Cachenet CDN:
              </h4>
              <ul style={{ textAlign: 'left', color: '#6c757d', paddingLeft: '1.5rem' }}>
                <li>Faster page load times for your visitors</li>
                <li>Reduced server load and bandwidth usage</li>
                <li>Global edge network for worldwide performance</li>
                <li>Automatic SSL certificate management</li>
                <li>Real-time cache purging and management</li>
              </ul>
            </div>
          </div>
        </div>
      ) : (
        <div>
          {domains.map((domain) => (
            <div key={domain.id} style={cardStyle}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <div style={{ flex: 1 }}>
                  <h2 style={{ margin: '0 0 1rem 0', color: '#2c3e50' }}>
                    {domain.domain_name}
                  </h2>
                  
                  <div style={{ 
                    display: 'grid', 
                    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
                    gap: '1rem',
                    marginBottom: '1rem'
                  }}>
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
                    <strong>Origin Server:</strong> {domain.origin_server}
                  </div>
                </div>
                
                <div style={{ 
                  display: 'flex', 
                  flexDirection: 'column', 
                  gap: '0.5rem', 
                  minWidth: '150px',
                  alignItems: 'end'
                }}>
                  <button
                    onClick={() => handleToggleCDN(domain)}
                    style={{
                      ...buttonStyle,
                      backgroundColor: domain.cdn_enabled ? '#e74c3c' : '#27ae60',
                      color: 'white',
                      width: '140px'
                    }}
                  >
                    {domain.cdn_enabled ? '⏹️ Disable CDN' : '▶️ Enable CDN'}
                  </button>
                  
                  {domain.cdn_enabled && (
                    <PurgeButton domainId={domain.id} domainName={domain.domain_name} />
                  )}
                </div>
              </div>
              
              {/* Performance Metrics */}
              {domain.cdn_enabled && (
                <div style={{
                  marginTop: '1rem',
                  padding: '1rem',
                  backgroundColor: '#f8f9fa',
                  borderRadius: '4px',
                  border: '1px solid #dee2e6'
                }}>
                  <h4 style={{ margin: '0 0 0.5rem 0', color: '#495057' }}>
                    📊 Quick Stats (Last 7 Days)
                  </h4>
                  <div style={{ 
                    display: 'grid', 
                    gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', 
                    gap: '0.5rem',
                    fontSize: '14px',
                    color: '#6c757d'
                  }}>
                    <div>Requests: Loading...</div>
                    <div>Cache Hits: Loading...</div>
                    <div>Bandwidth Saved: Loading...</div>
                    <div>Response Time: Loading...</div>
                  </div>
                </div>
              )}
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

      {/* Refresh Button */}
      <div style={{ textAlign: 'center', marginTop: '2rem' }}>
        <button
          onClick={loadData}
          style={{
            ...buttonStyle,
            backgroundColor: '#3498db',
            color: 'white',
            fontSize: '16px',
            padding: '0.75rem 1.5rem'
          }}
        >
          🔄 Refresh Data
        </button>
      </div>
    </div>
  )
}

export default MySites