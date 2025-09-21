import React, { useState, useEffect } from 'react'
import { getDashboardStats, getScalingStats, getExpiringCertificates } from '../api.js'

const Dashboard = () => {
  const [stats, setStats] = useState(null)
  const [scalingStats, setScalingStats] = useState(null)
  const [expiringCerts, setExpiringCerts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    try {
      setLoading(true)
      const [dashboardData, scalingData, expiringData] = await Promise.all([
        getDashboardStats(),
        getScalingStats(),
        getExpiringCertificates()
      ])
      
      setStats(dashboardData)
      setScalingStats(scalingData)
      setExpiringCerts(expiringData.expiring_certificates || [])
    } catch (error) {
      console.error('Error loading dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '400px',
        fontSize: '18px',
        color: '#666'
      }}>
        Loading dashboard...
      </div>
    )
  }

  const cardStyle = {
    backgroundColor: 'white',
    padding: '1.5rem',
    borderRadius: '8px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    marginBottom: '1rem'
  }

  const statCardStyle = {
    ...cardStyle,
    textAlign: 'center',
    minHeight: '120px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center'
  }

  return (
    <div>
      <h1 style={{ marginBottom: '2rem', color: '#2c3e50' }}>
        📊 Dashboard Overview
      </h1>

      {/* Key Metrics */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
        gap: '1rem',
        marginBottom: '2rem'
      }}>
        <div style={statCardStyle}>
          <h3 style={{ margin: '0 0 0.5rem 0', color: '#3498db' }}>
            {stats?.domains_count || 0}
          </h3>
          <p style={{ margin: 0, color: '#666' }}>Total Domains</p>
        </div>
        
        <div style={statCardStyle}>
          <h3 style={{ margin: '0 0 0.5rem 0', color: '#27ae60' }}>
            {scalingStats?.active_nodes || 0}
          </h3>
          <p style={{ margin: 0, color: '#666' }}>Active Edge Nodes</p>
        </div>
        
        <div style={statCardStyle}>
          <h3 style={{ margin: '0 0 0.5rem 0', color: '#f39c12' }}>
            {stats?.cache_hit_ratio || 0}%
          </h3>
          <p style={{ margin: 0, color: '#666' }}>Cache Hit Ratio</p>
        </div>
        
        <div style={statCardStyle}>
          <h3 style={{ margin: '0 0 0.5rem 0', color: '#e74c3c' }}>
            {stats?.total_bandwidth_saved_gb || 0} GB
          </h3>
          <p style={{ margin: 0, color: '#666' }}>Bandwidth Saved</p>
        </div>
        
        <div style={statCardStyle}>
          <h3 style={{ margin: '0 0 0.5rem 0', color: '#9b59b6' }}>
            {stats?.ssl_certificates || 0}
          </h3>
          <p style={{ margin: 0, color: '#666' }}>SSL Certificates</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        {/* Regional Distribution */}
        <div style={cardStyle}>
          <h3 style={{ marginTop: 0, color: '#2c3e50' }}>🌍 Regional Distribution</h3>
          {scalingStats?.regional_stats?.length > 0 ? (
            <div>
              {scalingStats.regional_stats.map((region, index) => (
                <div key={index} style={{ 
                  padding: '0.75rem',
                  marginBottom: '0.5rem',
                  backgroundColor: '#f8f9fa',
                  borderRadius: '4px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <div>
                    <strong>{region.region}</strong>
                    <div style={{ fontSize: '14px', color: '#666' }}>
                      Avg Load: {region.avg_load?.toFixed(2) || 0}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#3498db' }}>
                      {region.node_count}
                    </div>
                    <div style={{ fontSize: '12px', color: '#666' }}>nodes</div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: '#666', fontStyle: 'italic' }}>
              No regional data available
            </p>
          )}
        </div>

        {/* Expiring SSL Certificates */}
        <div style={cardStyle}>
          <h3 style={{ marginTop: 0, color: '#2c3e50' }}>🔒 Expiring SSL Certificates</h3>
          {expiringCerts.length > 0 ? (
            <div>
              {expiringCerts.slice(0, 5).map((cert, index) => (
                <div key={index} style={{ 
                  padding: '0.75rem',
                  marginBottom: '0.5rem',
                  backgroundColor: cert.days_until_expiry <= 7 ? '#ffebee' : '#fff3e0',
                  borderRadius: '4px',
                  border: cert.days_until_expiry <= 7 ? '1px solid #ffcdd2' : '1px solid #ffcc02'
                }}>
                  <div style={{ fontWeight: 'bold' }}>{cert.domain_name}</div>
                  <div style={{ 
                    fontSize: '14px', 
                    color: cert.days_until_expiry <= 7 ? '#d32f2f' : '#f57c00'
                  }}>
                    Expires in {cert.days_until_expiry} days
                  </div>
                </div>
              ))}
              {expiringCerts.length > 5 && (
                <p style={{ margin: '1rem 0 0 0', color: '#666', fontSize: '14px' }}>
                  And {expiringCerts.length - 5} more...
                </p>
              )}
            </div>
          ) : (
            <p style={{ color: '#666', fontStyle: 'italic' }}>
              No certificates expiring soon
            </p>
          )}
        </div>
      </div>

      {/* Auto-scaling Configuration */}
      <div style={cardStyle}>
        <h3 style={{ marginTop: 0, color: '#2c3e50' }}>⚙️ Auto-scaling Configuration</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <div>
            <strong>Status:</strong> 
            <span style={{ 
              marginLeft: '0.5rem',
              color: scalingStats?.auto_scale_config?.enabled ? '#27ae60' : '#e74c3c',
              fontWeight: 'bold'
            }}>
              {scalingStats?.auto_scale_config?.enabled ? 'Enabled' : 'Disabled'}
            </span>
          </div>
          <div>
            <strong>Max Clients per Node:</strong> {scalingStats?.auto_scale_config?.max_clients_per_node || 'N/A'}
          </div>
          <div>
            <strong>Min Nodes:</strong> {scalingStats?.auto_scale_config?.min_nodes || 'N/A'}
          </div>
          <div>
            <strong>Max Nodes:</strong> {scalingStats?.auto_scale_config?.max_nodes || 'N/A'}
          </div>
        </div>
      </div>

      {/* Provider Distribution */}
      {scalingStats?.provider_stats?.length > 0 && (
        <div style={cardStyle}>
          <h3 style={{ marginTop: 0, color: '#2c3e50' }}>☁️ Provider Distribution</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem' }}>
            {scalingStats.provider_stats.map((provider, index) => (
              <div key={index} style={{ 
                textAlign: 'center',
                padding: '1rem',
                backgroundColor: '#f8f9fa',
                borderRadius: '4px'
              }}>
                <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#3498db' }}>
                  {provider.node_count}
                </div>
                <div style={{ fontSize: '14px', color: '#666', textTransform: 'capitalize' }}>
                  {provider.provider}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Refresh Button */}
      <div style={{ textAlign: 'center', marginTop: '2rem' }}>
        <button
          onClick={loadDashboardData}
          style={{
            padding: '0.75rem 1.5rem',
            backgroundColor: '#3498db',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '16px'
          }}
        >
          🔄 Refresh Dashboard
        </button>
      </div>
    </div>
  )
}

export default Dashboard