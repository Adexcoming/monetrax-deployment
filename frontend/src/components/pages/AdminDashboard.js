import React, { useState, useEffect, createContext, useContext } from 'react';
import { useNavigate, Link, Routes, Route, useLocation } from 'react-router-dom';
import { formatCurrency } from '../../contexts/SubscriptionContext';
import { toast } from 'sonner';
import {
  Shield, Users, Building2, Receipt, FileText, Settings, BarChart3,
  Crown, Search, ChevronRight, AlertTriangle, CheckCircle2, XCircle,
  TrendingUp, DollarSign, Activity, Clock, Eye, Ban, UserCheck,
  Flag, RefreshCw, Loader2, ChevronLeft, ChevronDown, Filter,
  Database, Server, Mail, CreditCard, Edit, Save, X, Menu, Trash2, UserPlus, Tag
} from 'lucide-react';

// API helper for admin dashboard (local implementation to avoid context issues)
const API_URL = process.env.REACT_APP_BACKEND_URL || '';
const apiCall = async (endpoint, options = {}) => {
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || 'Request failed');
  }
  
  return response.json();
};

// Local Admin Context to pass user info to child components
const AdminContext = createContext(null);
const useAuth = () => {
  const context = useContext(AdminContext);
  if (!context) return { user: null };
  return context;
};

// Admin Layout with Sidebar
export default function AdminDashboard({ auth, api }) {
  // Use passed props or fallback to local apiCall
  const apiFunc = api || apiCall;
  const [user, setUser] = useState(auth?.user || null);
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Fetch current user if not provided via props
  useEffect(() => {
    if (!user) {
      const fetchUser = async () => {
        try {
          const userData = await apiCall('/api/auth/me');
          setUser(userData);
        } catch (error) {
          console.error('Failed to fetch user:', error);
          navigate('/');
        }
      };
      fetchUser();
    }
  }, [user, navigate]);

  // Check admin access
  useEffect(() => {
    if (user && !['admin', 'superadmin'].includes(user.role)) {
      toast.error('Admin access required');
      navigate('/dashboard');
    }
  }, [user, navigate]);

  if (!user) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="w-12 h-12 border-4 border-red-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!['admin', 'superadmin'].includes(user.role)) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <Shield className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold mb-2">Access Denied</h1>
          <p className="text-muted-foreground">You do not have permission to access this area.</p>
          <Link to="/dashboard" className="btn-primary px-4 py-2 rounded-lg mt-4 inline-block">
            Go to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const navItems = [
    { path: '/admin', icon: BarChart3, label: 'Overview', exact: true },
    { path: '/admin/users', icon: Users, label: 'Users' },
    { path: '/admin/businesses', icon: Building2, label: 'Businesses' },
    { path: '/admin/transactions', icon: Receipt, label: 'Transactions' },
    { path: '/admin/tax-engine', icon: FileText, label: 'Tax Engine' },
    { path: '/admin/subscriptions', icon: Crown, label: 'Subscriptions' },
    { path: '/admin/logs', icon: Activity, label: 'Logs' },
    { path: '/admin/settings', icon: Settings, label: 'Settings', superadminOnly: true },
  ];

  const filteredNavItems = navItems.filter(item => 
    !item.superadminOnly || user.role === 'superadmin'
  );

  return (
    <AdminContext.Provider value={{ user }}>
    <div className="min-h-screen flex bg-background">
      {/* Sidebar */}
      <aside className={`fixed lg:static inset-y-0 left-0 z-50 w-64 bg-card border-r border-border transform transition-transform lg:translate-x-0 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-red-500/10 flex items-center justify-center">
              <Shield className="w-5 h-5 text-red-500" />
            </div>
            <div>
              <span className="font-bold text-lg">Admin Panel</span>
              <p className="text-xs text-muted-foreground capitalize">{user.role}</p>
            </div>
          </div>
        </div>

        <nav className="p-4 space-y-1">
          {filteredNavItems.map((item) => {
            const isActive = item.exact 
              ? location.pathname === item.path 
              : location.pathname.startsWith(item.path);
            
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${
                  isActive
                    ? 'bg-red-500/10 text-red-500 font-medium'
                    : 'text-muted-foreground hover:bg-secondary/50 hover:text-foreground'
                }`}
              >
                <item.icon className="w-5 h-5" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-border">
          <Link to="/dashboard" className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors">
            <ChevronLeft className="w-4 h-4" />
            Back to App
          </Link>
        </div>
      </aside>

      {/* Mobile Header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-40 bg-card border-b border-border p-4">
        <div className="flex items-center justify-between">
          <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-2">
            <Menu className="w-6 h-6" />
          </button>
          <span className="font-bold">Admin Panel</span>
          <div className="w-10" />
        </div>
      </div>

      {/* Mobile Overlay */}
      {sidebarOpen && (
        <div 
          className="lg:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main Content */}
      <main className="flex-1 lg:ml-0 pt-16 lg:pt-0 overflow-auto">
        <Routes>
          <Route index element={<AdminOverview />} />
          <Route path="users" element={<AdminUsers />} />
          <Route path="users/:userId" element={<AdminUserDetail />} />
          <Route path="businesses" element={<AdminBusinesses />} />
          <Route path="businesses/:businessId" element={<AdminBusinessDetail />} />
          <Route path="transactions" element={<AdminTransactions />} />
          <Route path="tax-engine" element={<AdminTaxEngine />} />
          <Route path="subscriptions" element={<AdminSubscriptions />} />
          <Route path="logs" element={<AdminLogs />} />
          <Route path="settings" element={<AdminSettings />} />
        </Routes>
      </main>
    </div>
    </AdminContext.Provider>
  );
}

// ============== OVERVIEW ==============
function AdminOverview() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchOverview();
  }, []);

  const fetchOverview = async () => {
    try {
      const result = await apiCall('/api/admin/overview');
      setData(result);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <LoadingSpinner />;
  }

  const healthStatus = (status) => {
    if (status === 'healthy') return <CheckCircle2 className="w-4 h-4 text-emerald-500" />;
    if (status === 'not_configured') return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
    return <XCircle className="w-4 h-4 text-red-500" />;
  };

  return (
    <div className="p-4 lg:p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Admin Overview</h1>
        <p className="text-muted-foreground">System metrics and health status</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard icon={Users} label="Total Users" value={data?.users?.total || 0} subtext={`${data?.users?.new_this_month || 0} new this month`} color="blue" />
        <MetricCard icon={Building2} label="Businesses" value={data?.businesses?.total || 0} color="purple" />
        <MetricCard icon={Receipt} label="Transactions" value={data?.transactions?.total || 0} subtext={`${data?.transactions?.this_month || 0} this month`} color="emerald" />
        <MetricCard icon={DollarSign} label="MRR" value={formatCurrency(data?.revenue?.mrr || 0)} color="orange" />
      </div>

      {/* Subscription Breakdown & System Health */}
      <div className="grid lg:grid-cols-2 gap-6">
        <div className="glass rounded-2xl p-6">
          <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
            <Crown className="w-5 h-5 text-yellow-500" />
            Subscription Breakdown
          </h3>
          <div className="space-y-3">
            {['free', 'starter', 'business', 'enterprise'].map((tier) => (
              <div key={tier} className="flex items-center justify-between">
                <span className="capitalize">{tier}</span>
                <span className="font-semibold">{data?.subscriptions?.[tier] || 0}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="glass rounded-2xl p-6">
          <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-emerald-500" />
            System Health
          </h3>
          <div className="space-y-3">
            {Object.entries(data?.system_health || {}).map(([key, status]) => (
              <div key={key} className="flex items-center justify-between">
                <span className="capitalize">{key.replace('_', ' ')}</span>
                <div className="flex items-center gap-2">
                  {healthStatus(status)}
                  <span className="text-sm capitalize">{status}</span>
                </div>
              </div>
            ))}
          </div>
          {data?.error_count_24h > 0 && (
            <div className="mt-4 p-3 bg-red-500/10 rounded-xl text-red-500 text-sm">
              <AlertTriangle className="w-4 h-4 inline mr-2" />
              {data.error_count_24h} errors in the last 24 hours
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="glass rounded-2xl p-6">
        <h3 className="font-semibold text-lg mb-4">Quick Actions</h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Link to="/admin/users" className="p-4 bg-secondary/30 rounded-xl hover:bg-secondary/50 transition-colors text-center">
            <Users className="w-6 h-6 mx-auto mb-2" />
            <span className="text-sm">Manage Users</span>
          </Link>
          <Link to="/admin/transactions?flagged=true" className="p-4 bg-secondary/30 rounded-xl hover:bg-secondary/50 transition-colors text-center">
            <Flag className="w-6 h-6 mx-auto mb-2 text-red-500" />
            <span className="text-sm">Flagged Transactions</span>
          </Link>
          <Link to="/admin/logs" className="p-4 bg-secondary/30 rounded-xl hover:bg-secondary/50 transition-colors text-center">
            <Activity className="w-6 h-6 mx-auto mb-2" />
            <span className="text-sm">View Logs</span>
          </Link>
          <Link to="/admin/tax-engine" className="p-4 bg-secondary/30 rounded-xl hover:bg-secondary/50 transition-colors text-center">
            <FileText className="w-6 h-6 mx-auto mb-2" />
            <span className="text-sm">Tax Rules</span>
          </Link>
        </div>
      </div>
    </div>
  );
}

// ============== USERS ==============
function AdminUsers() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [pagination, setPagination] = useState({ page: 1, pages: 1, total: 0 });
  const [showTierModal, setShowTierModal] = useState(null);
  const [selectedTier, setSelectedTier] = useState('free');
  const [actionLoading, setActionLoading] = useState(null);
  const navigate = useNavigate();

  // Check if current user is superadmin
  const isSuperadmin = currentUser?.role === 'superadmin';

  useEffect(() => {
    fetchUsers();
  }, [search, roleFilter, statusFilter, pagination.page]);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      let url = `/api/admin/users?page=${pagination.page}&limit=20`;
      if (search) url += `&search=${encodeURIComponent(search)}`;
      if (roleFilter) url += `&role=${roleFilter}`;
      if (statusFilter) url += `&status=${statusFilter}`;
      
      const result = await apiCall(url);
      setUsers(result.users);
      setPagination(result.pagination);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSuspend = async (userId) => {
    if (!window.confirm('Are you sure you want to suspend this user?')) return;
    try {
      await apiCall(`/api/admin/users/${userId}/suspend`, { method: 'POST' });
      toast.success('User suspended');
      fetchUsers();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleActivate = async (userId) => {
    try {
      await apiCall(`/api/admin/users/${userId}/activate`, { method: 'POST' });
      toast.success('User activated');
      fetchUsers();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleDelete = async (userId, userEmail) => {
    if (!window.confirm(`Are you sure you want to PERMANENTLY DELETE the account for ${userEmail}? This action cannot be undone!`)) return;
    if (!window.confirm(`FINAL WARNING: All data for ${userEmail} will be deleted including their business, transactions, and subscription. Continue?`)) return;
    
    try {
      await apiCall(`/api/admin/users/${userId}`, { method: 'DELETE' });
      toast.success(`User ${userEmail} deleted permanently`);
      fetchUsers();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleChangeTier = async () => {
    if (!showTierModal) return;
    try {
      await apiCall(`/api/admin/users/${showTierModal.user_id}/change-tier?tier=${selectedTier}`, { method: 'POST' });
      toast.success(`Tier changed to ${selectedTier}`);
      setShowTierModal(null);
      fetchUsers();
    } catch (error) {
      toast.error(error.message);
    }
  };

  return (
    <div className="p-4 lg:p-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Users</h1>
          <p className="text-muted-foreground">{pagination.total} total users</p>
        </div>
        {isSuperadmin && (
          <span className="px-3 py-1 bg-purple-500/10 text-purple-500 text-xs rounded-full font-medium">
            Superadmin Mode
          </span>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, email, or ID..."
            className="w-full bg-secondary/50 border border-border rounded-xl pl-10 pr-4 py-2"
          />
        </div>
        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          className="bg-secondary/50 border border-border rounded-xl px-4 py-2"
        >
          <option value="">All Roles</option>
          <option value="user">User</option>
          <option value="admin">Admin</option>
          <option value="superadmin">Superadmin</option>
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-secondary/50 border border-border rounded-xl px-4 py-2"
        >
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
        </select>
      </div>

      {/* Users Table */}
      <div className="glass rounded-2xl overflow-hidden">
        {loading ? (
          <LoadingSpinner />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-secondary/30">
                <tr>
                  <th className="text-left p-4 font-medium">User</th>
                  <th className="text-left p-4 font-medium">Role</th>
                  <th className="text-left p-4 font-medium">Status</th>
                  <th className="text-left p-4 font-medium">Subscription</th>
                  <th className="text-left p-4 font-medium">Business</th>
                  <th className="text-right p-4 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.user_id} className="border-t border-border hover:bg-secondary/20">
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        {user.picture && <img src={user.picture} alt="" className="w-8 h-8 rounded-full" />}
                        <div>
                          <p className="font-medium">{user.name}</p>
                          <p className="text-sm text-muted-foreground">{user.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="p-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        user.role === 'superadmin' ? 'bg-purple-500/10 text-purple-500' :
                        user.role === 'admin' ? 'bg-red-500/10 text-red-500' :
                        'bg-secondary text-muted-foreground'
                      }`}>
                        {user.role || 'user'}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        user.status === 'suspended' ? 'bg-red-500/10 text-red-500' : 'bg-emerald-500/10 text-emerald-500'
                      }`}>
                        {user.status || 'active'}
                      </span>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium capitalize ${
                          user.subscription_tier === 'enterprise' ? 'bg-purple-500/10 text-purple-500' :
                          user.subscription_tier === 'business' ? 'bg-emerald-500/10 text-emerald-500' :
                          user.subscription_tier === 'starter' ? 'bg-blue-500/10 text-blue-500' :
                          'bg-secondary text-muted-foreground'
                        }`}>
                          {user.subscription_tier || 'free'}
                        </span>
                        {isSuperadmin && user.role !== 'superadmin' && (
                          <button
                            onClick={() => { setShowTierModal(user); setSelectedTier(user.subscription_tier || 'free'); }}
                            className="p-1 hover:bg-secondary rounded text-muted-foreground hover:text-foreground"
                            title="Change Tier"
                          >
                            <Edit className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    </td>
                    <td className="p-4">{user.business_name || '-'}</td>
                    <td className="p-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => navigate(`/admin/users/${user.user_id}`)}
                          className="p-2 hover:bg-secondary rounded-lg"
                          title="View Details"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        {user.status === 'suspended' ? (
                          <button
                            onClick={() => handleActivate(user.user_id)}
                            className="p-2 hover:bg-emerald-500/10 text-emerald-500 rounded-lg"
                            title="Activate"
                          >
                            <UserCheck className="w-4 h-4" />
                          </button>
                        ) : (
                          <button
                            onClick={() => handleSuspend(user.user_id)}
                            className="p-2 hover:bg-red-500/10 text-red-500 rounded-lg"
                            title="Suspend"
                          >
                            <Ban className="w-4 h-4" />
                          </button>
                        )}
                        {isSuperadmin && user.role !== 'superadmin' && (
                          <button
                            onClick={() => handleDelete(user.user_id, user.email)}
                            className="p-2 hover:bg-red-500/10 text-red-500 rounded-lg"
                            title="Delete Account"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      <Pagination pagination={pagination} setPagination={setPagination} />

      {/* Change Tier Modal */}
      {showTierModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="glass rounded-2xl p-6 max-w-md w-full animate-fade-in">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Change Subscription Tier</h3>
              <button onClick={() => setShowTierModal(null)} className="p-2 hover:bg-secondary rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="mb-4">
              <p className="text-sm text-muted-foreground mb-2">
                Changing tier for: <span className="font-medium text-foreground">{showTierModal.email}</span>
              </p>
              <p className="text-sm text-muted-foreground">
                Current tier: <span className="font-medium text-foreground capitalize">{showTierModal.subscription_tier || 'free'}</span>
              </p>
            </div>
            <div className="mb-6">
              <label className="text-sm font-medium mb-2 block">New Tier</label>
              <select
                value={selectedTier}
                onChange={(e) => setSelectedTier(e.target.value)}
                className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3"
              >
                <option value="free">Free</option>
                <option value="starter">Starter (₦5,000/mo)</option>
                <option value="business">Business (₦10,000/mo)</option>
                <option value="enterprise">Enterprise (₦20,000/mo)</option>
              </select>
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleChangeTier}
                className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white font-medium py-3 rounded-xl transition-colors"
              >
                Change Tier
              </button>
              <button
                onClick={() => setShowTierModal(null)}
                className="flex-1 bg-secondary hover:bg-secondary/80 py-3 rounded-xl transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function AdminUserDetail() {
  // Simplified for brevity - would show full user details
  return <div className="p-8"><h1>User Detail</h1></div>;
}

// ============== BUSINESSES ==============
function AdminBusinesses() {
  const [businesses, setBusinesses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [pagination, setPagination] = useState({ page: 1, pages: 1, total: 0 });

  useEffect(() => {
    fetchBusinesses();
  }, [search, pagination.page]);

  const fetchBusinesses = async () => {
    setLoading(true);
    try {
      let url = `/api/admin/businesses?page=${pagination.page}&limit=20`;
      if (search) url += `&search=${encodeURIComponent(search)}`;
      
      const result = await apiCall(url);
      setBusinesses(result.businesses);
      setPagination(result.pagination);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 lg:p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Businesses</h1>
        <p className="text-muted-foreground">{pagination.total} registered businesses</p>
      </div>

      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search businesses..."
          className="w-full bg-secondary/50 border border-border rounded-xl pl-10 pr-4 py-2"
        />
      </div>

      <div className="glass rounded-2xl overflow-hidden">
        {loading ? (
          <LoadingSpinner />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-secondary/30">
                <tr>
                  <th className="text-left p-4 font-medium">Business</th>
                  <th className="text-left p-4 font-medium">Owner</th>
                  <th className="text-left p-4 font-medium">Industry</th>
                  <th className="text-left p-4 font-medium">Transactions</th>
                  <th className="text-left p-4 font-medium">Tax Readiness</th>
                </tr>
              </thead>
              <tbody>
                {businesses.map((biz) => (
                  <tr key={biz.business_id} className="border-t border-border hover:bg-secondary/20">
                    <td className="p-4">
                      <div>
                        <p className="font-medium">{biz.business_name}</p>
                        <p className="text-xs text-muted-foreground">{biz.business_type}</p>
                      </div>
                    </td>
                    <td className="p-4">
                      <p className="text-sm">{biz.owner_name}</p>
                      <p className="text-xs text-muted-foreground">{biz.owner_email}</p>
                    </td>
                    <td className="p-4">{biz.industry}</td>
                    <td className="p-4">{biz.transaction_count}</td>
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-2 bg-secondary rounded-full overflow-hidden">
                          <div 
                            className={`h-full ${biz.tax_readiness_score >= 70 ? 'bg-emerald-500' : biz.tax_readiness_score >= 40 ? 'bg-yellow-500' : 'bg-red-500'}`}
                            style={{ width: `${biz.tax_readiness_score}%` }}
                          />
                        </div>
                        <span className="text-sm">{biz.tax_readiness_score}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Pagination pagination={pagination} setPagination={setPagination} />
    </div>
  );
}

function AdminBusinessDetail() {
  return <div className="p-8"><h1>Business Detail</h1></div>;
}

// ============== TRANSACTIONS ==============
function AdminTransactions() {
  const [transactions, setTransactions] = useState([]);
  const [totals, setTotals] = useState({ income: 0, expense: 0 });
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState('');
  const [flaggedOnly, setFlaggedOnly] = useState(false);
  const [pagination, setPagination] = useState({ page: 1, pages: 1, total: 0 });

  useEffect(() => {
    fetchTransactions();
  }, [typeFilter, flaggedOnly, pagination.page]);

  const fetchTransactions = async () => {
    setLoading(true);
    try {
      let url = `/api/admin/transactions?page=${pagination.page}&limit=50`;
      if (typeFilter) url += `&type=${typeFilter}`;
      if (flaggedOnly) url += `&flagged=true`;
      
      const result = await apiCall(url);
      setTransactions(result.transactions);
      setTotals(result.totals);
      setPagination(result.pagination);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFlag = async (txId) => {
    const reason = window.prompt('Enter flag reason:');
    if (reason === null) return;
    
    try {
      await apiCall(`/api/admin/transactions/${txId}/flag?reason=${encodeURIComponent(reason)}`, { method: 'POST' });
      toast.success('Transaction flagged');
      fetchTransactions();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleUnflag = async (txId) => {
    try {
      await apiCall(`/api/admin/transactions/${txId}/unflag`, { method: 'POST' });
      toast.success('Flag removed');
      fetchTransactions();
    } catch (error) {
      toast.error(error.message);
    }
  };

  return (
    <div className="p-4 lg:p-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Transactions</h1>
          <p className="text-muted-foreground">{pagination.total} total transactions</p>
        </div>
        <div className="flex gap-4 text-sm">
          <div className="px-4 py-2 bg-emerald-500/10 rounded-xl">
            <span className="text-muted-foreground">Income: </span>
            <span className="font-semibold text-emerald-500">{formatCurrency(totals.income)}</span>
          </div>
          <div className="px-4 py-2 bg-red-500/10 rounded-xl">
            <span className="text-muted-foreground">Expense: </span>
            <span className="font-semibold text-red-500">{formatCurrency(totals.expense)}</span>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="bg-secondary/50 border border-border rounded-xl px-4 py-2"
        >
          <option value="">All Types</option>
          <option value="income">Income</option>
          <option value="expense">Expense</option>
        </select>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={flaggedOnly}
            onChange={(e) => setFlaggedOnly(e.target.checked)}
            className="rounded"
          />
          <span className="text-sm">Flagged Only</span>
        </label>
      </div>

      <div className="glass rounded-2xl overflow-hidden">
        {loading ? (
          <LoadingSpinner />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-secondary/30">
                <tr>
                  <th className="text-left p-4 font-medium">Date</th>
                  <th className="text-left p-4 font-medium">Business</th>
                  <th className="text-left p-4 font-medium">Description</th>
                  <th className="text-left p-4 font-medium">Category</th>
                  <th className="text-right p-4 font-medium">Amount</th>
                  <th className="text-right p-4 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx) => (
                  <tr key={tx.transaction_id} className={`border-t border-border ${tx.flagged ? 'bg-red-500/5' : 'hover:bg-secondary/20'}`}>
                    <td className="p-4 text-sm">{tx.date}</td>
                    <td className="p-4 text-sm">{tx.business_name}</td>
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        {tx.flagged && <Flag className="w-4 h-4 text-red-500" />}
                        <span>{tx.description}</span>
                      </div>
                    </td>
                    <td className="p-4 text-sm">{tx.category}</td>
                    <td className={`p-4 text-right font-semibold ${tx.type === 'income' ? 'text-emerald-500' : 'text-red-500'}`}>
                      {tx.type === 'income' ? '+' : '-'}{formatCurrency(tx.amount)}
                    </td>
                    <td className="p-4 text-right">
                      {tx.flagged ? (
                        <button onClick={() => handleUnflag(tx.transaction_id)} className="text-emerald-500 text-sm hover:underline">
                          Unflag
                        </button>
                      ) : (
                        <button onClick={() => handleFlag(tx.transaction_id)} className="text-red-500 text-sm hover:underline">
                          Flag
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Pagination pagination={pagination} setPagination={setPagination} />
    </div>
  );
}

// ============== TAX ENGINE ==============
function AdminTaxEngine() {
  const { user } = useAuth();
  const [rules, setRules] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [formData, setFormData] = useState({ vat_rate: 0.075, tax_free_threshold: 800000 });

  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    try {
      const result = await apiCall('/api/admin/tax-rules');
      setRules(result);
      setFormData({
        vat_rate: result.vat_rate,
        tax_free_threshold: result.tax_free_threshold
      });
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      await apiCall('/api/admin/tax-rules', {
        method: 'PUT',
        body: JSON.stringify(formData)
      });
      toast.success('Tax rules updated');
      setEditing(false);
      fetchRules();
    } catch (error) {
      toast.error(error.message);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="p-4 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Tax Engine</h1>
          <p className="text-muted-foreground">Configure tax rates and thresholds</p>
        </div>
        {user.role === 'superadmin' && !editing && (
          <button onClick={() => setEditing(true)} className="btn-primary px-4 py-2 rounded-lg flex items-center gap-2">
            <Edit className="w-4 h-4" />
            Edit Rules
          </button>
        )}
      </div>

      <div className="glass rounded-2xl p-6">
        <h3 className="font-semibold text-lg mb-4">Current Tax Rules</h3>
        
        {editing ? (
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">VAT Rate (%)</label>
              <input
                type="number"
                step="0.001"
                value={formData.vat_rate * 100}
                onChange={(e) => setFormData({ ...formData, vat_rate: parseFloat(e.target.value) / 100 })}
                className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3"
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Tax-Free Threshold (₦)</label>
              <input
                type="number"
                value={formData.tax_free_threshold}
                onChange={(e) => setFormData({ ...formData, tax_free_threshold: parseFloat(e.target.value) })}
                className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3"
              />
            </div>
            <div className="flex gap-3">
              <button onClick={handleSave} className="btn-primary px-4 py-2 rounded-lg flex items-center gap-2">
                <Save className="w-4 h-4" />
                Save Changes
              </button>
              <button onClick={() => setEditing(false)} className="bg-secondary px-4 py-2 rounded-lg">
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex justify-between p-4 bg-secondary/30 rounded-xl">
              <span>VAT Rate</span>
              <span className="font-semibold">{(rules?.vat_rate * 100).toFixed(1)}%</span>
            </div>
            <div className="flex justify-between p-4 bg-secondary/30 rounded-xl">
              <span>Tax-Free Threshold</span>
              <span className="font-semibold">{formatCurrency(rules?.tax_free_threshold || 0)}</span>
            </div>
            <div className="flex justify-between p-4 bg-secondary/30 rounded-xl">
              <span>Effective Date</span>
              <span className="font-semibold">{rules?.effective_date || 'N/A'}</span>
            </div>
          </div>
        )}
      </div>

      {/* Income Tax Brackets */}
      <div className="glass rounded-2xl p-6">
        <h3 className="font-semibold text-lg mb-4">Income Tax Brackets</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-secondary/30">
              <tr>
                <th className="text-left p-3 font-medium">Bracket</th>
                <th className="text-right p-3 font-medium">Amount (₦)</th>
                <th className="text-right p-3 font-medium">Rate</th>
              </tr>
            </thead>
            <tbody>
              {rules?.income_tax_brackets?.map((bracket, i) => (
                <tr key={i} className="border-t border-border">
                  <td className="p-3">Bracket {i + 1}</td>
                  <td className="p-3 text-right">{bracket.amount === Infinity || bracket.amount === 'unlimited' ? 'Above' : formatCurrency(bracket.amount)}</td>
                  <td className="p-3 text-right">{(bracket.rate * 100).toFixed(0)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ============== SUBSCRIPTIONS ==============
function AdminSubscriptions() {
  const [subscriptions, setSubscriptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tierFilter, setTierFilter] = useState('');
  const [pagination, setPagination] = useState({ page: 1, pages: 1, total: 0 });

  useEffect(() => {
    fetchSubscriptions();
  }, [tierFilter, pagination.page]);

  const fetchSubscriptions = async () => {
    setLoading(true);
    try {
      let url = `/api/admin/subscriptions?page=${pagination.page}&limit=20`;
      if (tierFilter) url += `&tier=${tierFilter}`;
      
      const result = await apiCall(url);
      setSubscriptions(result.subscriptions);
      setPagination(result.pagination);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 lg:p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Subscriptions</h1>
        <p className="text-muted-foreground">{pagination.total} subscriptions</p>
      </div>

      <select
        value={tierFilter}
        onChange={(e) => setTierFilter(e.target.value)}
        className="bg-secondary/50 border border-border rounded-xl px-4 py-2"
      >
        <option value="">All Tiers</option>
        <option value="starter">Starter</option>
        <option value="business">Business</option>
        <option value="enterprise">Enterprise</option>
      </select>

      <div className="glass rounded-2xl overflow-hidden">
        {loading ? (
          <LoadingSpinner />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-secondary/30">
                <tr>
                  <th className="text-left p-4 font-medium">User</th>
                  <th className="text-left p-4 font-medium">Tier</th>
                  <th className="text-left p-4 font-medium">Status</th>
                  <th className="text-left p-4 font-medium">Billing</th>
                  <th className="text-left p-4 font-medium">Period End</th>
                </tr>
              </thead>
              <tbody>
                {subscriptions.map((sub) => (
                  <tr key={sub.subscription_id} className="border-t border-border hover:bg-secondary/20">
                    <td className="p-4">
                      <p className="font-medium">{sub.user_name}</p>
                      <p className="text-sm text-muted-foreground">{sub.user_email}</p>
                    </td>
                    <td className="p-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        sub.tier === 'enterprise' ? 'bg-purple-500/10 text-purple-500' :
                        sub.tier === 'business' ? 'bg-emerald-500/10 text-emerald-500' :
                        sub.tier === 'starter' ? 'bg-blue-500/10 text-blue-500' :
                        'bg-secondary text-muted-foreground'
                      }`}>
                        {sub.tier_name}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        sub.status === 'active' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-yellow-500/10 text-yellow-500'
                      }`}>
                        {sub.status}
                      </span>
                    </td>
                    <td className="p-4 capitalize">{sub.billing_cycle}</td>
                    <td className="p-4 text-sm">{sub.current_period_end ? new Date(sub.current_period_end).toLocaleDateString() : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Pagination pagination={pagination} setPagination={setPagination} />
    </div>
  );
}

// ============== LOGS ==============
function AdminLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState('');
  const [pagination, setPagination] = useState({ page: 1, pages: 1, total: 0 });

  useEffect(() => {
    fetchLogs();
  }, [actionFilter, pagination.page]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      let url = `/api/admin/logs?page=${pagination.page}&limit=50`;
      if (actionFilter) url += `&action=${actionFilter}`;
      
      const result = await apiCall(url);
      setLogs(result.logs);
      setPagination(result.pagination);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 lg:p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Admin Logs</h1>
        <p className="text-muted-foreground">Audit trail of admin actions</p>
      </div>

      <select
        value={actionFilter}
        onChange={(e) => setActionFilter(e.target.value)}
        className="bg-secondary/50 border border-border rounded-xl px-4 py-2"
      >
        <option value="">All Actions</option>
        <option value="user_update">User Updates</option>
        <option value="user_suspend">User Suspensions</option>
        <option value="transaction_flag">Transaction Flags</option>
        <option value="settings_update">Settings Changes</option>
      </select>

      <div className="glass rounded-2xl overflow-hidden">
        {loading ? (
          <LoadingSpinner />
        ) : logs.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            <Activity className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No logs found</p>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {logs.map((log) => (
              <div key={log.log_id} className="p-4 hover:bg-secondary/20">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium">{log.action}</p>
                    <p className="text-sm text-muted-foreground">
                      by {log.admin_name} • {log.target_type}: {log.target_id}
                    </p>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {new Date(log.timestamp).toLocaleString()}
                  </span>
                </div>
                {log.details && Object.keys(log.details).length > 0 && (
                  <pre className="mt-2 text-xs bg-secondary/30 p-2 rounded overflow-x-auto">
                    {JSON.stringify(log.details, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <Pagination pagination={pagination} setPagination={setPagination} />
    </div>
  );
}

// ============== SETTINGS ==============
function AdminSettings() {
  const { user } = useAuth();
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const result = await apiCall('/api/admin/settings');
      setSettings(result);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await apiCall('/api/admin/settings', {
        method: 'PUT',
        body: JSON.stringify(settings)
      });
      toast.success('Settings saved');
    } catch (error) {
      toast.error(error.message);
    } finally {
      setSaving(false);
    }
  };

  if (user.role !== 'superadmin') {
    return (
      <div className="p-8 text-center">
        <Shield className="w-16 h-16 text-red-500 mx-auto mb-4" />
        <h1 className="text-2xl font-bold mb-2">Superadmin Required</h1>
        <p className="text-muted-foreground">Only superadmins can access system settings.</p>
      </div>
    );
  }

  if (loading) return <LoadingSpinner />;

  return (
    <div className="p-4 lg:p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">System Settings</h1>
        <p className="text-muted-foreground">Global configuration (superadmin only)</p>
      </div>

      <div className="glass rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between p-4 bg-secondary/30 rounded-xl">
          <div>
            <p className="font-medium">Maintenance Mode</p>
            <p className="text-sm text-muted-foreground">Disable access for regular users</p>
          </div>
          <button
            onClick={() => setSettings({ ...settings, maintenance_mode: !settings.maintenance_mode })}
            className={`relative w-12 h-6 rounded-full transition-colors ${settings.maintenance_mode ? 'bg-red-500' : 'bg-secondary'}`}
          >
            <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${settings.maintenance_mode ? 'translate-x-7' : 'translate-x-1'}`} />
          </button>
        </div>

        <div className="flex items-center justify-between p-4 bg-secondary/30 rounded-xl">
          <div>
            <p className="font-medium">Registration Enabled</p>
            <p className="text-sm text-muted-foreground">Allow new user sign ups</p>
          </div>
          <button
            onClick={() => setSettings({ ...settings, registration_enabled: !settings.registration_enabled })}
            className={`relative w-12 h-6 rounded-full transition-colors ${settings.registration_enabled ? 'bg-emerald-500' : 'bg-secondary'}`}
          >
            <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${settings.registration_enabled ? 'translate-x-7' : 'translate-x-1'}`} />
          </button>
        </div>

        <div className="flex items-center justify-between p-4 bg-secondary/30 rounded-xl">
          <div>
            <p className="font-medium">Email Notifications</p>
            <p className="text-sm text-muted-foreground">Enable system email sending</p>
          </div>
          <button
            onClick={() => setSettings({ ...settings, email_notifications_enabled: !settings.email_notifications_enabled })}
            className={`relative w-12 h-6 rounded-full transition-colors ${settings.email_notifications_enabled ? 'bg-emerald-500' : 'bg-secondary'}`}
          >
            <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${settings.email_notifications_enabled ? 'translate-x-7' : 'translate-x-1'}`} />
          </button>
        </div>

        <button onClick={handleSave} disabled={saving} className="btn-primary px-4 py-2 rounded-lg flex items-center gap-2">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          Save Settings
        </button>
      </div>
    </div>
  );
}

// ============== SHARED COMPONENTS ==============
function MetricCard({ icon: Icon, label, value, subtext, color }) {
  const colorClasses = {
    blue: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
    purple: 'bg-purple-500/10 text-purple-500 border-purple-500/20',
    emerald: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
    orange: 'bg-orange-500/10 text-orange-500 border-orange-500/20',
  };

  return (
    <div className={`glass rounded-2xl p-4 border ${colorClasses[color]}`}>
      <div className="flex items-center gap-2 mb-2">
        <Icon className="w-5 h-5" />
        <span className="text-sm text-muted-foreground">{label}</span>
      </div>
      <p className="text-2xl font-bold">{typeof value === 'number' ? value.toLocaleString() : value}</p>
      {subtext && <p className="text-xs text-muted-foreground mt-1">{subtext}</p>}
    </div>
  );
}

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center p-8">
      <div className="w-8 h-8 border-4 border-red-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

function Pagination({ pagination, setPagination }) {
  if (pagination.pages <= 1) return null;

  return (
    <div className="flex items-center justify-center gap-2">
      <button
        onClick={() => setPagination({ ...pagination, page: pagination.page - 1 })}
        disabled={pagination.page === 1}
        className="p-2 rounded-lg hover:bg-secondary disabled:opacity-50"
      >
        <ChevronLeft className="w-5 h-5" />
      </button>
      <span className="text-sm">
        Page {pagination.page} of {pagination.pages}
      </span>
      <button
        onClick={() => setPagination({ ...pagination, page: pagination.page + 1 })}
        disabled={pagination.page === pagination.pages}
        className="p-2 rounded-lg hover:bg-secondary disabled:opacity-50"
      >
        <ChevronRight className="w-5 h-5" />
      </button>
    </div>
  );
}
