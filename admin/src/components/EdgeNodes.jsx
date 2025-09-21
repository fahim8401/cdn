import React, { useState, useEffect } from 'react'
import { getEdgeNodes, createEdgeNode, updateEdgeNode, deleteEdgeNode, triggerScaleUp, triggerScaleDown } from '../api.js'

const EdgeNodes = () => {
  const [edgeNodes, setEdgeNodes] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAddForm, setShowAddForm] = useState(false)
  const [editingNode, setEditingNode] = useState(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [regionFilter, setRegionFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  const [formData, setFormData] = useState({
    name: '',
    hostname: '',
    ip_address: '',
    region: '',
    country: '',
    city: '',
    provider: 'digitalocean',
    max_clients: 25
  })

  const [scaleData, setScaleData] = useState({
    region: 'nyc1',
    provider: 'digitalocean'
  })

  useEffect(() => {
    loadEdgeNodes()
  }, [currentPage, regionFilter, statusFilter])

  const loadEdgeNodes = async () => {
    try {
      setLoading(true)
      const response = await getEdgeNodes(currentPage, regionFilter, statusFilter)
      setEdgeNodes(response.edge_nodes)
      setTotalPages(response.pages)
    } catch (error) {
      console.error('Error loading edge nodes:', error)
      alert('Failed to load edge nodes: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      if (editingNode) {
        await updateEdgeNode(editingNode.id, formData)
        alert('Edge node updated successfully')
      } else {
        await createEdgeNode(formData)
        alert('Edge node created successfully')
      }
      
      resetForm()
      loadEdgeNodes()
    } catch (error) {
      alert('Error: ' + error.message)
    }
  }

  const resetForm = () => {
    setFormData({
      name: '',
      hostname: '',
      ip_address: '',
      region: '',
      country: '',
      city: '',
      provider: 'digitalocean',
      max_clients: 25
    })
    setShowAddForm(false)
    setEditingNode(null)
  }

  const handleEdit = (node) => {
    setEditingNode(node)
    setFormData({
      name: node.name,
      hostname: node.hostname,
      ip_address: node.ip_address,
      region: node.region,
      country: node.country || '',
      city: node.city || '',
      provider: node.provider || 'digitalocean',
      max_clients: node.max_clients
    })
    setShowAddForm(true)
  }

  const handleDelete = async (node) => {
    if (confirm(`Are you sure you want to delete edge node "${node.name}"?`)) {
      try {
        await deleteEdgeNode(node.id)
        alert('Edge node deleted successfully')
        loadEdgeNodes()
      } catch (error) {
        alert('Error deleting edge node: ' + error.message)
      }
    }
  }

  const handleScaleUp = async () => {
    try {
      await triggerScaleUp(scaleData.region, scaleData.provider)
      alert(`Scale-up initiated in region ${scaleData.region}`)
      loadEdgeNodes()
    } catch (error) {
      alert('Error scaling up: ' + error.message)
    }
  }

  const handleScaleDown = async () => {
    if (confirm(`Are you sure you want to scale down in region ${scaleData.region}?`)) {
      try {
        await triggerScaleDown(scaleData.region)
        alert(`Scale-down initiated in region ${scaleData.region}`)
        loadEdgeNodes()
      } catch (error) {
        alert('Error scaling down: ' + error.message)
      }
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return '#27ae60'
      case 'pending': return '#f39c12'
      case 'deploying': return '#3498db'
      case 'maintenance': return '#9b59b6'
      case 'error': return '#e74c3c'
      default: return '#666'
    }
  }

  const getLoadColor = (loadScore) => {
    if (loadScore < 0.5) return '#27ae60'
    if (loadScore < 0.8) return '#f39c12'
    return '#e74c3c'
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
        <h1 style={{ margin: 0, color: '#2c3e50' }}>🚀 Edge Node Management</h1>
        <button
          onClick={() => {
            setShowAddForm(true)
            setEditingNode(null)
            resetForm()
          }}
          style={{
            ...buttonStyle,
            backgroundColor: '#27ae60',
            color: 'white'
          }}
        >
          ➕ Add Edge Node
        </button>
      </div>

      {/* Auto-scaling Controls */}
      <div style={cardStyle}>
        <h3 style={{ marginTop: 0, color: '#2c3e50' }}>⚙️ Auto-scaling Controls</h3>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'end' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
              Region:
            </label>
            <select
              value={scaleData.region}
              onChange={(e) => setScaleData({ ...scaleData, region: e.target.value })}
              style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #ddd' }}
            >
              <option value="nyc1">New York 1</option>
              <option value="nyc3">New York 3</option>
              <option value="ams3">Amsterdam 3</option>
              <option value="sgp1">Singapore 1</option>
              <option value="lon1">London 1</option>
              <option value="fra1">Frankfurt 1</option>
              <option value="tor1">Toronto 1</option>
              <option value="sfo3">San Francisco 3</option>
            </select>
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
              Provider:
            </label>
            <select
              value={scaleData.provider}
              onChange={(e) => setScaleData({ ...scaleData, provider: e.target.value })}
              style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #ddd' }}
            >
              <option value="digitalocean">DigitalOcean</option>
              <option value="linode">Linode</option>
              <option value="vultr">Vultr</option>
              <option value="hetzner">Hetzner</option>
            </select>
          </div>
          
          <button
            onClick={handleScaleUp}
            style={{
              ...buttonStyle,
              backgroundColor: '#27ae60',
              color: 'white'
            }}
          >
            📈 Scale Up
          </button>
          
          <button
            onClick={handleScaleDown}
            style={{
              ...buttonStyle,
              backgroundColor: '#e74c3c',
              color: 'white'
            }}
          >
            📉 Scale Down
          </button>
        </div>
      </div>

      {/* Filters */}
      <div style={{ ...cardStyle, marginBottom: '1rem' }}>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <label>
            <strong>Region:</strong>
            <select
              value={regionFilter}
              onChange={(e) => setRegionFilter(e.target.value)}
              style={{ marginLeft: '0.5rem', padding: '0.25rem' }}
            >
              <option value="">All Regions</option>
              <option value="nyc1">New York 1</option>
              <option value="nyc3">New York 3</option>
              <option value="ams3">Amsterdam 3</option>
              <option value="sgp1">Singapore 1</option>
              <option value="lon1">London 1</option>
              <option value="fra1">Frankfurt 1</option>
            </select>
          </label>
          
          <label>
            <strong>Status:</strong>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{ marginLeft: '0.5rem', padding: '0.25rem' }}
            >
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="pending">Pending</option>
              <option value="deploying">Deploying</option>
              <option value="maintenance">Maintenance</option>
              <option value="error">Error</option>
            </select>
          </label>
          
          <button
            onClick={loadEdgeNodes}
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
            {editingNode ? '✏️ Edit Edge Node' : '➕ Add New Edge Node'}
          </h3>
          <form onSubmit={handleSubmit}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                  Name:
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid #ddd',
                    borderRadius: '4px'
                  }}
                />
              </div>
              
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                  Hostname:
                </label>
                <input
                  type="text"
                  value={formData.hostname}
                  onChange={(e) => setFormData({ ...formData, hostname: e.target.value })}
                  required
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid #ddd',
                    borderRadius: '4px'
                  }}
                />
              </div>
              
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                  IP Address:
                </label>
                <input
                  type="text"
                  value={formData.ip_address}
                  onChange={(e) => setFormData({ ...formData, ip_address: e.target.value })}
                  required
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid #ddd',
                    borderRadius: '4px'
                  }}
                />
              </div>
              
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                  Region:
                </label>
                <input
                  type="text"
                  value={formData.region}
                  onChange={(e) => setFormData({ ...formData, region: e.target.value })}
                  required
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid #ddd',
                    borderRadius: '4px'
                  }}
                />
              </div>
              
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                  Provider:
                </label>
                <select
                  value={formData.provider}
                  onChange={(e) => setFormData({ ...formData, provider: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid #ddd',
                    borderRadius: '4px'
                  }}
                >
                  <option value="digitalocean">DigitalOcean</option>
                  <option value="linode">Linode</option>
                  <option value="vultr">Vultr</option>
                  <option value="hetzner">Hetzner</option>
                </select>
              </div>
              
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                  Max Clients:
                </label>
                <input
                  type="number"
                  value={formData.max_clients}
                  onChange={(e) => setFormData({ ...formData, max_clients: parseInt(e.target.value) })}
                  min="1"
                  max="100"
                  required
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid #ddd',
                    borderRadius: '4px'
                  }}
                />
              </div>
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
                {editingNode ? 'Update Node' : 'Add Node'}
              </button>
              <button
                type="button"
                onClick={resetForm}
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

      {/* Edge Nodes List */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
          Loading edge nodes...
        </div>
      ) : edgeNodes.length === 0 ? (
        <div style={cardStyle}>
          <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
            No edge nodes found. Add your first edge node to get started!
          </div>
        </div>
      ) : (
        <div>
          {edgeNodes.map((node) => (
            <div key={node.id} style={cardStyle}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <div style={{ flex: 1 }}>
                  <h3 style={{ margin: '0 0 0.5rem 0', color: '#2c3e50' }}>
                    {node.name}
                  </h3>
                  
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '0.5rem' }}>
                    <div>
                      <strong>Hostname:</strong> {node.hostname}
                    </div>
                    <div>
                      <strong>IP Address:</strong> {node.ip_address}
                    </div>
                    <div>
                      <strong>Region:</strong> {node.region}
                    </div>
                    <div>
                      <strong>Provider:</strong> 
                      <span style={{ marginLeft: '0.5rem', textTransform: 'capitalize' }}>
                        {node.provider}
                      </span>
                    </div>
                  </div>
                  
                  <div style={{ display: 'flex', gap: '2rem', marginBottom: '0.5rem' }}>
                    <div>
                      <strong>Status:</strong> 
                      <span style={{ 
                        marginLeft: '0.5rem',
                        color: getStatusColor(node.status),
                        fontWeight: 'bold',
                        textTransform: 'capitalize'
                      }}>
                        {node.status}
                      </span>
                    </div>
                    
                    <div>
                      <strong>Load:</strong> 
                      <span style={{ 
                        marginLeft: '0.5rem',
                        color: getLoadColor(node.load_score || 0),
                        fontWeight: 'bold'
                      }}>
                        {((node.load_score || 0) * 100).toFixed(1)}%
                      </span>
                    </div>
                    
                    <div>
                      <strong>Clients:</strong> {node.client_count || 0}/{node.max_clients}
                    </div>
                  </div>
                  
                  <div style={{ fontSize: '14px', color: '#666' }}>
                    Last Seen: {node.last_seen ? new Date(node.last_seen).toLocaleString() : 'Never'}
                  </div>
                </div>
                
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    onClick={() => handleEdit(node)}
                    style={{
                      ...buttonStyle,
                      backgroundColor: '#3498db',
                      color: 'white',
                      fontSize: '12px'
                    }}
                  >
                    Edit
                  </button>
                  
                  <button
                    onClick={() => handleDelete(node)}
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

export default EdgeNodes