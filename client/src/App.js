import React, { useState, useEffect } from 'react'
import MySites from './components/MySites.jsx'
import { login, logout, getCurrentUser } from './api.js'

const App = () => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loginData, setLoginData] = useState({ email: '', password: '' })

  useEffect(() => {
    // Check if user is already logged in
    const token = localStorage.getItem('token')
    if (token) {
      getCurrentUser()
        .then(userData => {
          setUser(userData.user)
          setLoading(false)
        })
        .catch(() => {
          localStorage.removeItem('token')
          setLoading(false)
        })
    } else {
      setLoading(false)
    }
  }, [])

  const handleLogin = async (e) => {
    e.preventDefault()
    try {
      const response = await login(loginData.email, loginData.password)
      localStorage.setItem('token', response.access_token)
      setUser(response.user)
    } catch (error) {
      alert('Login failed: ' + (error.message || 'Unknown error'))
    }
  }

  const handleLogout = () => {
    logout()
    localStorage.removeItem('token')
    setUser(null)
  }

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        fontSize: '18px',
        color: '#666'
      }}>
        Loading...
      </div>
    )
  }

  if (!user) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        backgroundColor: '#f5f5f5'
      }}>
        <div style={{
          backgroundColor: 'white',
          padding: '2rem',
          borderRadius: '8px',
          boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
          width: '100%',
          maxWidth: '400px'
        }}>
          <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
            <h1 style={{ color: '#2c3e50', marginBottom: '0.5rem' }}>
              Cachenet CDN
            </h1>
            <p style={{ color: '#666', margin: 0 }}>
              Client Dashboard
            </p>
          </div>
          
          <form onSubmit={handleLogin}>
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', color: '#555' }}>
                Email:
              </label>
              <input
                type="email"
                value={loginData.email}
                onChange={(e) => setLoginData({ ...loginData, email: e.target.value })}
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
              <label style={{ display: 'block', marginBottom: '0.5rem', color: '#555' }}>
                Password:
              </label>
              <input
                type="password"
                value={loginData.password}
                onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
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
            <button
              type="submit"
              style={{
                width: '100%',
                padding: '0.75rem',
                backgroundColor: '#3498db',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                fontSize: '16px',
                cursor: 'pointer'
              }}
            >
              Login to Dashboard
            </button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div style={{ 
      minHeight: '100vh',
      backgroundColor: '#f5f5f5'
    }}>
      {/* Header */}
      <div style={{
        backgroundColor: '#2c3e50',
        color: 'white',
        padding: '1rem 2rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
      }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '24px' }}>
            🚀 Cachenet CDN
          </h1>
          <p style={{ margin: 0, fontSize: '14px', opacity: 0.8 }}>
            Client Dashboard
          </p>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '14px', opacity: 0.8 }}>
              Welcome back
            </div>
            <div style={{ fontWeight: 'bold' }}>
              {user.first_name || user.email}
            </div>
          </div>
          
          <button
            onClick={handleLogout}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#e74c3c',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            Logout
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div style={{ padding: '2rem' }}>
        <MySites />
      </div>
    </div>
  )
}

export default App