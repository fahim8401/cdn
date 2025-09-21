import React, { useState } from 'react'
import { purgeDomainCache, purgeUrlCache } from '../api.js'

const PurgeButton = ({ domainId, domainName }) => {
  const [showPurgeOptions, setShowPurgeOptions] = useState(false)
  const [urlPath, setUrlPath] = useState('')
  const [purging, setPurging] = useState(false)

  const handlePurgeDomain = async () => {
    if (confirm(`Are you sure you want to purge all cache for "${domainName}"?`)) {
      try {
        setPurging(true)
        await purgeDomainCache(domainId)
        alert(`Cache purge initiated for ${domainName}`)
        setShowPurgeOptions(false)
      } catch (error) {
        alert('Error purging cache: ' + error.message)
      } finally {
        setPurging(false)
      }
    }
  }

  const handlePurgeUrl = async (e) => {
    e.preventDefault()
    if (!urlPath.trim()) {
      alert('Please enter a URL path')
      return
    }

    try {
      setPurging(true)
      await purgeUrlCache(domainId, urlPath)
      alert(`URL cache purge initiated for ${domainName}${urlPath}`)
      setUrlPath('')
      setShowPurgeOptions(false)
    } catch (error) {
      alert('Error purging URL cache: ' + error.message)
    } finally {
      setPurging(false)
    }
  }

  const buttonStyle = {
    padding: '0.5rem 1rem',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '12px',
    marginRight: '0.5rem'
  }

  if (showPurgeOptions) {
    return (
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0,0,0,0.5)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 1000
      }}>
        <div style={{
          backgroundColor: 'white',
          padding: '2rem',
          borderRadius: '8px',
          maxWidth: '500px',
          width: '90%',
          maxHeight: '90vh',
          overflow: 'auto'
        }}>
          <h3 style={{ marginTop: 0, color: '#2c3e50' }}>
            🧹 Purge Cache for {domainName}
          </h3>
          
          <div style={{ marginBottom: '2rem' }}>
            <h4 style={{ color: '#34495e' }}>Option 1: Purge Entire Domain</h4>
            <p style={{ color: '#666', marginBottom: '1rem' }}>
              This will purge all cached content for the entire domain.
            </p>
            <button
              onClick={handlePurgeDomain}
              disabled={purging}
              style={{
                ...buttonStyle,
                backgroundColor: '#e74c3c',
                color: 'white'
              }}
            >
              {purging ? 'Purging...' : '🧹 Purge All Cache'}
            </button>
          </div>
          
          <div style={{ marginBottom: '2rem' }}>
            <h4 style={{ color: '#34495e' }}>Option 2: Purge Specific URL</h4>
            <p style={{ color: '#666', marginBottom: '1rem' }}>
              Purge cache for a specific URL path on this domain.
            </p>
            <form onSubmit={handlePurgeUrl}>
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
                <span style={{ 
                  padding: '0.75rem',
                  backgroundColor: '#ecf0f1',
                  border: '1px solid #bdc3c7',
                  borderRadius: '4px 0 0 4px',
                  color: '#666'
                }}>
                  {domainName}
                </span>
                <input
                  type="text"
                  value={urlPath}
                  onChange={(e) => setUrlPath(e.target.value)}
                  placeholder="/path/to/file.js"
                  style={{
                    flex: 1,
                    padding: '0.75rem',
                    border: '1px solid #bdc3c7',
                    borderLeft: 'none',
                    borderRadius: '0 4px 4px 0',
                    fontSize: '14px'
                  }}
                />
              </div>
              <button
                type="submit"
                disabled={purging || !urlPath.trim()}
                style={{
                  ...buttonStyle,
                  backgroundColor: '#f39c12',
                  color: 'white'
                }}
              >
                {purging ? 'Purging...' : '🎯 Purge URL'}
              </button>
            </form>
          </div>
          
          <div style={{ textAlign: 'right' }}>
            <button
              onClick={() => setShowPurgeOptions(false)}
              disabled={purging}
              style={{
                ...buttonStyle,
                backgroundColor: '#95a5a6',
                color: 'white'
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <button
      onClick={() => setShowPurgeOptions(true)}
      style={{
        ...buttonStyle,
        backgroundColor: '#f39c12',
        color: 'white'
      }}
    >
      🧹 Purge
    </button>
  )
}

export default PurgeButton