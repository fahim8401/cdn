import React, { useState } from 'react'
import { purgeDomainCache, purgeUrlCache } from '../api.js'

const PurgeButton = ({ domainId, domainName }) => {
  const [showPurgeOptions, setShowPurgeOptions] = useState(false)
  const [urlPath, setUrlPath] = useState('')
  const [purging, setPurging] = useState(false)

  const handlePurgeDomain = async () => {
    if (confirm(`Are you sure you want to purge all cache for "${domainName}"?\n\nThis will clear all cached content and may temporarily slow down your site until the cache rebuilds.`)) {
      try {
        setPurging(true)
        await purgeDomainCache(domainId)
        alert(`✅ Cache purge initiated for ${domainName}!\n\nIt may take a few minutes to complete across all edge servers.`)
        setShowPurgeOptions(false)
      } catch (error) {
        alert('❌ Error purging cache: ' + error.message)
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
      alert(`✅ URL cache purge initiated for ${domainName}${urlPath}!\n\nThe specific URL will be refreshed across all edge servers.`)
      setUrlPath('')
      setShowPurgeOptions(false)
    } catch (error) {
      alert('❌ Error purging URL cache: ' + error.message)
    } finally {
      setPurging(false)
    }
  }

  const buttonStyle = {
    padding: '0.5rem 1rem',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '14px',
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
          
          <div style={{ 
            marginBottom: '1.5rem',
            padding: '1rem',
            backgroundColor: '#e8f4fd',
            borderRadius: '4px',
            border: '1px solid #bee5eb'
          }}>
            <h4 style={{ margin: '0 0 0.5rem 0', color: '#0c5460' }}>
              💡 What is cache purging?
            </h4>
            <p style={{ margin: 0, color: '#0c5460', fontSize: '14px' }}>
              Cache purging removes stored content from our edge servers, forcing them to fetch fresh content from your origin server. Use this when you've updated your website and want changes to appear immediately.
            </p>
          </div>
          
          <div style={{ marginBottom: '2rem' }}>
            <h4 style={{ color: '#34495e', marginBottom: '0.5rem' }}>
              🌐 Option 1: Purge Entire Site
            </h4>
            <p style={{ color: '#666', marginBottom: '1rem', fontSize: '14px' }}>
              This will purge all cached content for your entire website. Use this after major updates or theme changes.
            </p>
            <button
              onClick={handlePurgeDomain}
              disabled={purging}
              style={{
                ...buttonStyle,
                backgroundColor: '#e74c3c',
                color: 'white',
                width: '100%',
                padding: '0.75rem'
              }}
            >
              {purging ? '🔄 Purging All Content...' : '🧹 Purge All Site Cache'}
            </button>
          </div>
          
          <div style={{ marginBottom: '2rem' }}>
            <h4 style={{ color: '#34495e', marginBottom: '0.5rem' }}>
              🎯 Option 2: Purge Specific Page/File
            </h4>
            <p style={{ color: '#666', marginBottom: '1rem', fontSize: '14px' }}>
              Purge cache for a specific page or file. Enter the path after your domain name.
            </p>
            <form onSubmit={handlePurgeUrl}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold', color: '#555' }}>
                  URL Path:
                </label>
                <div style={{ display: 'flex', borderRadius: '4px', overflow: 'hidden', border: '1px solid #ddd' }}>
                  <span style={{ 
                    padding: '0.75rem',
                    backgroundColor: '#f8f9fa',
                    color: '#666',
                    border: 'none',
                    fontSize: '14px'
                  }}>
                    {domainName}
                  </span>
                  <input
                    type="text"
                    value={urlPath}
                    onChange={(e) => setUrlPath(e.target.value)}
                    placeholder="/about-us.html"
                    style={{
                      flex: 1,
                      padding: '0.75rem',
                      border: 'none',
                      fontSize: '14px',
                      outline: 'none'
                    }}
                  />
                </div>
                <div style={{ fontSize: '12px', color: '#999', marginTop: '0.25rem' }}>
                  Examples: /contact.html, /images/logo.png, /css/style.css
                </div>
              </div>
              <button
                type="submit"
                disabled={purging || !urlPath.trim()}
                style={{
                  ...buttonStyle,
                  backgroundColor: urlPath.trim() ? '#f39c12' : '#95a5a6',
                  color: 'white',
                  width: '100%',
                  padding: '0.75rem'
                }}
              >
                {purging ? '🔄 Purging URL...' : '🎯 Purge This URL'}
              </button>
            </form>
          </div>
          
          <div style={{ textAlign: 'center' }}>
            <button
              onClick={() => setShowPurgeOptions(false)}
              disabled={purging}
              style={{
                ...buttonStyle,
                backgroundColor: '#95a5a6',
                color: 'white',
                padding: '0.75rem 1.5rem'
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
        color: 'white',
        width: '140px'
      }}
    >
      🧹 Purge Cache
    </button>
  )
}

export default PurgeButton