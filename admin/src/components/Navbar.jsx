import React, { useState } from 'react'
import { 
  BarChart3, 
  Globe, 
  Server, 
  Shield, 
  TrendingUp, 
  User, 
  LogOut,
  Menu,
  X
} from 'lucide-react'

const Navbar = ({ user, currentPage, setCurrentPage, onLogout }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
    { id: 'domains', label: 'Domains', icon: Globe },
    { id: 'edge-nodes', label: 'Edge Nodes', icon: Server },
    { id: 'ssl', label: 'SSL Certificates', icon: Shield },
    { id: 'stats', label: 'Analytics', icon: TrendingUp },
  ]

  const handleMenuClick = (pageId) => {
    setCurrentPage(pageId)
    setMobileMenuOpen(false)
  }

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <div className="navbar-brand">
          <h1>🚀 Cachenet</h1>
          <span className="navbar-subtitle">Enterprise CDN</span>
        </div>

        {/* Desktop Menu */}
        <div className="navbar-menu desktop-only">
          {menuItems.map((item) => {
            const Icon = item.icon
            return (
              <button
                key={item.id}
                className={`navbar-item ${currentPage === item.id ? 'active' : ''}`}
                onClick={() => handleMenuClick(item.id)}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </button>
            )
          })}
        </div>

        {/* User Menu */}
        <div className="navbar-user">
          <div className="user-info">
            <User size={18} />
            <span className="username">{user?.username || user?.email}</span>
          </div>
          
          <button className="logout-button" onClick={onLogout}>
            <LogOut size={18} />
            <span className="desktop-only">Logout</span>
          </button>

          {/* Mobile Menu Toggle */}
          <button 
            className="mobile-menu-toggle mobile-only"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="mobile-menu">
          {menuItems.map((item) => {
            const Icon = item.icon
            return (
              <button
                key={item.id}
                className={`mobile-menu-item ${currentPage === item.id ? 'active' : ''}`}
                onClick={() => handleMenuClick(item.id)}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </button>
            )
          })}
        </div>
      )}
    </nav>
  )
}

export default Navbar