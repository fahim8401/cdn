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