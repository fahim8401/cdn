import React, { useState, useEffect } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import Dashboard from './components/Dashboard.jsx'
import Domains from './components/Domains.jsx'
import EdgeNodes from './components/EdgeNodes.jsx'
import SSLManager from './components/SSLManager.jsx'
import UsageStats from './components/UsageStats.jsx'
import Navbar from './components/Navbar.jsx'
import { login, logout, getCurrentUser } from './api.js'
import './styles/main.css'

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
    },
  },
})

const App = () => {
  const [user, setUser] = useState(null)
  const [currentPage, setCurrentPage] = useState('dashboard')
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
    setCurrentPage('dashboard')
  }

  const renderPage = () => {
    switch(currentPage) {
      case 'dashboard':
        return <Dashboard />
      case 'domains':
        return <Domains />
      case 'edge-nodes':
        return <EdgeNodes />
      case 'ssl':
        return <SSLManager />
      case 'stats':
        return <UsageStats />
      default:
        return <Dashboard />
    }
  }

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading Cachenet Admin...</p>
      </div>
    )
  }

  if (!user) {
    return (
      <QueryClientProvider client={queryClient}>
        <div className="login-container">
          <div className="login-card">
            <div className="login-header">
              <h1>🚀 Cachenet Enterprise</h1>
              <p>CDN Administration Portal</p>
            </div>
            
            <form onSubmit={handleLogin} className="login-form">
              <div className="form-group">
                <label htmlFor="email">Email</label>
                <input
                  id="email"
                  type="email"
                  value={loginData.email}
                  onChange={(e) => setLoginData({...loginData, email: e.target.value})}
                  required
                  placeholder="admin@yourcompany.com"
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="password">Password</label>
                <input
                  id="password"
                  type="password"
                  value={loginData.password}
                  onChange={(e) => setLoginData({...loginData, password: e.target.value})}
                  required
                  placeholder="••••••••"
                />
              </div>
              
              <button type="submit" className="login-button">
                Sign In
              </button>
            </form>
            
            <div className="login-footer">
              <p>Default credentials: admin@cachenet.local / admin123</p>
            </div>
          </div>
        </div>
        <Toaster position="top-right" />
      </QueryClientProvider>
    )
  }

  return (
    <QueryClientProvider client={queryClient}>
      <div className="app">
        <Navbar 
          user={user} 
          currentPage={currentPage} 
          setCurrentPage={setCurrentPage}
          onLogout={handleLogout}
        />
        
        <main className="main-content">
          <div className="container">
            {renderPage()}
          </div>
        </main>
        
        <Toaster position="top-right" />
      </div>
    </QueryClientProvider>
  )
}

export default App
    switch (currentPage) {
      case 'dashboard':
        return <Dashboard />
      case 'domains':
        return <Domains />
      case 'edge-nodes':
        return <EdgeNodes />
      case 'ssl':
        return <SSLManager />
      default:
        return <Dashboard />
    }
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
          <h1 style={{ textAlign: 'center', marginBottom: '2rem', color: '#333' }}>
            Cachenet CDN Admin
          </h1>
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
                backgroundColor: '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                fontSize: '16px',
                cursor: 'pointer'
              }}
            >
              Login
            </button>
          </form>
          <div style={{ 
            marginTop: '1rem', 
            padding: '1rem', 
            backgroundColor: '#f8f9fa', 
            borderRadius: '4px',
            fontSize: '14px',
            color: '#666'
          }}>
            <strong>Default Admin Credentials:</strong><br />
            Email: admin@cachenet.local<br />
            Password: admin123
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <div style={{
        width: '250px',
        backgroundColor: '#2c3e50',
        color: 'white',
        padding: '1rem'
      }}>
        <h2 style={{ marginBottom: '2rem', color: '#ecf0f1' }}>
          Cachenet CDN
        </h2>
        
        <nav>
          <button
            onClick={() => setCurrentPage('dashboard')}
            style={{
              width: '100%',
              padding: '0.75rem',
              marginBottom: '0.5rem',
              backgroundColor: currentPage === 'dashboard' ? '#34495e' : 'transparent',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              textAlign: 'left',
              cursor: 'pointer'
            }}
          >
            📊 Dashboard
          </button>
          
          <button
            onClick={() => setCurrentPage('domains')}
            style={{
              width: '100%',
              padding: '0.75rem',
              marginBottom: '0.5rem',
              backgroundColor: currentPage === 'domains' ? '#34495e' : 'transparent',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              textAlign: 'left',
              cursor: 'pointer'
            }}
          >
            🌐 Domains
          </button>
          
          <button
            onClick={() => setCurrentPage('edge-nodes')}
            style={{
              width: '100%',
              padding: '0.75rem',
              marginBottom: '0.5rem',
              backgroundColor: currentPage === 'edge-nodes' ? '#34495e' : 'transparent',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              textAlign: 'left',
              cursor: 'pointer'
            }}
          >
            🚀 Edge Nodes
          </button>
          
          <button
            onClick={() => setCurrentPage('ssl')}
            style={{
              width: '100%',
              padding: '0.75rem',
              marginBottom: '0.5rem',
              backgroundColor: currentPage === 'ssl' ? '#34495e' : 'transparent',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              textAlign: 'left',
              cursor: 'pointer'
            }}
          >
            🔒 SSL Certificates
          </button>
        </nav>
        
        <div style={{ 
          position: 'absolute', 
          bottom: '1rem', 
          left: '1rem', 
          right: '1rem' 
        }}>
          <div style={{ 
            padding: '1rem', 
            backgroundColor: '#34495e', 
            borderRadius: '4px',
            marginBottom: '1rem'
          }}>
            <div style={{ fontSize: '14px', marginBottom: '0.5rem' }}>
              Logged in as:
            </div>
            <div style={{ fontWeight: 'bold' }}>
              {user.email}
            </div>
            {user.is_admin && (
              <div style={{ 
                fontSize: '12px', 
                color: '#f39c12',
                marginTop: '0.25rem'
              }}>
                Administrator
              </div>
            )}
          </div>
          
          <button
            onClick={handleLogout}
            style={{
              width: '100%',
              padding: '0.75rem',
              backgroundColor: '#e74c3c',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Logout
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div style={{ 
        flex: 1, 
        padding: '2rem',
        backgroundColor: '#ecf0f1',
        overflow: 'auto'
      }}>
        {renderPage()}
      </div>
    </div>
  )
}

export default App