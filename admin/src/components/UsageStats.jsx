import React, { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell
} from 'recharts'
import { getDashboardStats, getBandwidthReport, getDomainAnalytics } from '../api.js'
import { Download, TrendingUp, Globe, Zap } from 'lucide-react'

const UsageStats = () => {
  const [selectedDomain, setSelectedDomain] = useState('all')
  const [timeRange, setTimeRange] = useState('30')

  const { data: dashboardStats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: getDashboardStats,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  const { data: bandwidthData, isLoading: bandwidthLoading } = useQuery({
    queryKey: ['bandwidth-report', timeRange],
    queryFn: () => getBandwidthReport(timeRange),
  })

  const { data: domainAnalytics, isLoading: analyticsLoading } = useQuery({
    queryKey: ['domain-analytics', selectedDomain, timeRange],
    queryFn: () => selectedDomain !== 'all' ? getDomainAnalytics(selectedDomain, timeRange) : null,
    enabled: selectedDomain !== 'all',
  })

  // Mock data for charts (in production, this would come from the API)
  const generateMockData = () => {
    const days = parseInt(timeRange)
    const data = []
    
    for (let i = days; i >= 0; i--) {
      const date = new Date()
      date.setDate(date.getDate() - i)
      
      data.push({
        date: date.toISOString().split('T')[0],
        requests: Math.floor(Math.random() * 50000) + 10000,
        cacheHits: Math.floor(Math.random() * 40000) + 8000,
        bandwidth: Math.floor(Math.random() * 1000) + 200,
        responseTime: Math.floor(Math.random() * 50) + 20,
      })
    }
    
    return data
  }

  const chartData = generateMockData()

  const pieData = [
    { name: 'Cache Hits', value: dashboardStats?.cache_hit_ratio || 85, color: '#10B981' },
    { name: 'Cache Misses', value: 100 - (dashboardStats?.cache_hit_ratio || 85), color: '#EF4444' },
  ]

  const regionData = [
    { name: 'US East', nodes: 12, requests: 45000 },
    { name: 'US West', nodes: 8, requests: 32000 },
    { name: 'Europe', nodes: 15, requests: 38000 },
    { name: 'Asia', nodes: 10, requests: 25000 },
    { name: 'Australia', nodes: 5, requests: 15000 },
  ]

  const exportData = () => {
    const csvData = chartData.map(row => 
      `${row.date},${row.requests},${row.cacheHits},${row.bandwidth},${row.responseTime}`
    ).join('\n')
    
    const header = 'Date,Requests,Cache Hits,Bandwidth (GB),Response Time (ms)\n'
    const csv = header + csvData
    
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `cachenet-stats-${timeRange}days.csv`
    a.click()
    window.URL.revokeObjectURL(url)
  }

  if (statsLoading || bandwidthLoading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading analytics...</p>
      </div>
    )
  }

  return (
    <div className="usage-stats">
      <div className="stats-header">
        <h1>📊 Analytics & Usage Statistics</h1>
        <div className="stats-controls">
          <select 
            value={timeRange} 
            onChange={(e) => setTimeRange(e.target.value)}
            className="time-range-select"
          >
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
          </select>
          
          <button onClick={exportData} className="export-button">
            <Download size={16} />
            Export CSV
          </button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-header">
            <TrendingUp className="metric-icon" />
            <h3>Total Requests</h3>
          </div>
          <div className="metric-value">
            {(dashboardStats?.total_requests || 0).toLocaleString()}
          </div>
          <div className="metric-change positive">
            +12.5% from last period
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <Zap className="metric-icon" />
            <h3>Cache Hit Ratio</h3>
          </div>
          <div className="metric-value">
            {dashboardStats?.cache_hit_ratio || 0}%
          </div>
          <div className="metric-change positive">
            +2.3% from last period
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <Download className="metric-icon" />
            <h3>Bandwidth Saved</h3>
          </div>
          <div className="metric-value">
            {dashboardStats?.total_bandwidth_saved_gb || 0} GB
          </div>
          <div className="metric-change positive">
            +18.7% from last period
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <Globe className="metric-icon" />
            <h3>Active Domains</h3>
          </div>
          <div className="metric-value">
            {dashboardStats?.domains_count || 0}
          </div>
          <div className="metric-change neutral">
            No change
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="charts-grid">
        {/* Requests Over Time */}
        <div className="chart-card">
          <h3>Requests Over Time</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="requests" stroke="#3B82F6" strokeWidth={2} />
              <Line type="monotone" dataKey="cacheHits" stroke="#10B981" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Cache Hit Ratio */}
        <div className="chart-card">
          <h3>Cache Performance</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={5}
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Bandwidth Usage */}
        <div className="chart-card">
          <h3>Bandwidth Usage (GB)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="bandwidth" fill="#8B5CF6" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Regional Performance */}
        <div className="chart-card">
          <h3>Performance by Region</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={regionData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="requests" fill="#F59E0B" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Bandwidth Report */}
      {bandwidthData && (
        <div className="bandwidth-report">
          <h3>💰 Bandwidth Savings Report</h3>
          <div className="report-summary">
            <div className="report-item">
              <label>Total Bandwidth:</label>
              <span>{bandwidthData.summary?.total_bandwidth_gb || 0} GB</span>
            </div>
            <div className="report-item">
              <label>Saved Bandwidth:</label>
              <span>{bandwidthData.summary?.saved_bandwidth_gb || 0} GB</span>
            </div>
            <div className="report-item">
              <label>Savings Ratio:</label>
              <span>{bandwidthData.summary?.overall_savings_ratio || 0}%</span>
            </div>
            <div className="report-item">
              <label>Cost Savings:</label>
              <span>${((bandwidthData.summary?.saved_bandwidth_gb || 0) * 0.08).toFixed(2)}</span>
            </div>
          </div>
          
          {bandwidthData.domain_breakdown && (
            <div className="domain-breakdown">
              <h4>Breakdown by Domain</h4>
              <div className="breakdown-table">
                <div className="table-header">
                  <span>Domain</span>
                  <span>Total (GB)</span>
                  <span>Saved (GB)</span>
                  <span>Savings %</span>
                  <span>Requests</span>
                </div>
                {bandwidthData.domain_breakdown.map((domain, index) => (
                  <div key={index} className="table-row">
                    <span>{domain.domain_name}</span>
                    <span>{domain.total_bandwidth_gb}</span>
                    <span>{domain.saved_bandwidth_gb}</span>
                    <span>{domain.savings_ratio}%</span>
                    <span>{domain.total_requests?.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default UsageStats