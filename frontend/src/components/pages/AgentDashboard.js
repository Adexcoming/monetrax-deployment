import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { toast } from 'sonner';
import {
  Users, UserPlus, Crown, TrendingUp, DollarSign, Search,
  Check, X, Loader2, Gift, Tag, Phone, Mail, Building2,
  ChevronRight, RefreshCw, AlertCircle, CheckCircle2
} from 'lucide-react';

// API helper
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

// Format currency
const formatCurrency = (amount) => {
  return new Intl.NumberFormat('en-NG', {
    style: 'currency',
    currency: 'NGN',
    minimumFractionDigits: 0
  }).format(amount);
};

export default function AgentDashboard() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [plans, setPlans] = useState([]);
  const [activeTab, setActiveTab] = useState('dashboard');
  
  // Signup form state
  const [signupForm, setSignupForm] = useState({
    name: '',
    email: '',
    phone: '',
    tier: 'starter',
    agent_initials: '',
    business_name: '',
    business_type: ''
  });
  const [signupLoading, setSignupLoading] = useState(false);
  const [checkResult, setCheckResult] = useState(null);
  const [checkLoading, setCheckLoading] = useState(false);

  useEffect(() => {
    fetchUserAndDashboard();
  }, []);

  const fetchUserAndDashboard = async () => {
    setLoading(true);
    try {
      const userData = await apiCall('/api/auth/me');
      if (!['agent', 'admin', 'superadmin'].includes(userData.role)) {
        toast.error('Agent access required');
        navigate('/dashboard');
        return;
      }
      setUser(userData);
      setSignupForm(prev => ({ ...prev, agent_initials: userData.agent_initials || '' }));
      
      const [dashboardData, plansData] = await Promise.all([
        apiCall('/api/agent/dashboard'),
        apiCall('/api/agent/promotional-plans')
      ]);
      
      setDashboard(dashboardData);
      setPlans(plansData.plans);
    } catch (error) {
      toast.error(error.message);
      navigate('/');
    } finally {
      setLoading(false);
    }
  };

  const handleCheckUser = async () => {
    const identifier = signupForm.email || signupForm.phone;
    if (!identifier) {
      toast.error('Enter email or phone to check eligibility');
      return;
    }
    
    setCheckLoading(true);
    try {
      const result = await apiCall(`/api/agent/check-user/${encodeURIComponent(identifier)}`);
      setCheckResult(result);
      if (!result.eligible_for_promo) {
        toast.warning('User has already used promotional discount');
      }
    } catch (error) {
      toast.error(error.message);
    } finally {
      setCheckLoading(false);
    }
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    
    if (!signupForm.name || (!signupForm.email && !signupForm.phone)) {
      toast.error('Name and either email or phone is required');
      return;
    }
    
    if (!signupForm.agent_initials) {
      toast.error('Agent initials are required');
      return;
    }
    
    setSignupLoading(true);
    try {
      const result = await apiCall('/api/agent/signup-user', {
        method: 'POST',
        body: JSON.stringify(signupForm)
      });
      
      toast.success(`User signed up successfully! Savings: ${formatCurrency(result.savings)}`);
      
      // Reset form
      setSignupForm({
        name: '',
        email: '',
        phone: '',
        tier: 'starter',
        agent_initials: user?.agent_initials || '',
        business_name: '',
        business_type: ''
      });
      setCheckResult(null);
      
      // Refresh dashboard
      fetchUserAndDashboard();
      setActiveTab('dashboard');
    } catch (error) {
      toast.error(error.message);
    } finally {
      setSignupLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="glass-header border-b border-border sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
              <Users className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-lg">Agent Portal</h1>
              <p className="text-xs text-muted-foreground">
                {user?.name} • <span className="text-emerald-500 font-medium">{user?.agent_initials}</span>
              </p>
            </div>
          </div>
          <Link to="/dashboard" className="text-sm text-muted-foreground hover:text-foreground">
            Exit Agent Portal
          </Link>
        </div>
      </header>

      {/* Tabs */}
      <div className="border-b border-border bg-card/50">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex gap-4">
            {[
              { id: 'dashboard', label: 'Dashboard', icon: TrendingUp },
              { id: 'signup', label: 'Sign Up User', icon: UserPlus },
              { id: 'signups', label: 'My Signups', icon: Users }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-emerald-500 text-emerald-500'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && dashboard && (
          <div className="space-y-6">
            {/* Stats Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="glass rounded-2xl p-6">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
                    <Users className="w-5 h-5 text-blue-500" />
                  </div>
                  <span className="text-sm text-muted-foreground">Total Signups</span>
                </div>
                <p className="text-3xl font-bold">{dashboard.statistics.total_signups}</p>
              </div>
              
              <div className="glass rounded-2xl p-6">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                    <Gift className="w-5 h-5 text-emerald-500" />
                  </div>
                  <span className="text-sm text-muted-foreground">Promo Applied</span>
                </div>
                <p className="text-3xl font-bold">{dashboard.statistics.promo_signups}</p>
              </div>
              
              <div className="glass rounded-2xl p-6">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center">
                    <DollarSign className="w-5 h-5 text-purple-500" />
                  </div>
                  <span className="text-sm text-muted-foreground">Total Savings Given</span>
                </div>
                <p className="text-3xl font-bold">{formatCurrency(dashboard.statistics.total_savings_given)}</p>
              </div>
              
              <div className="glass rounded-2xl p-6">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center">
                    <Tag className="w-5 h-5 text-amber-500" />
                  </div>
                  <span className="text-sm text-muted-foreground">Your Tag</span>
                </div>
                <p className="text-3xl font-bold text-emerald-500">{dashboard.agent_initials}</p>
              </div>
            </div>

            {/* Promotional Plans */}
            <div className="glass rounded-2xl p-6">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Crown className="w-5 h-5 text-emerald-500" />
                Promotional Plans
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {plans.map(plan => (
                  <div key={plan.tier} className="border border-border rounded-xl p-4 hover:border-emerald-500/50 transition-colors">
                    <div className="flex justify-between items-start mb-3">
                      <h3 className="font-semibold text-lg">{plan.name}</h3>
                      <span className="px-2 py-1 bg-emerald-500/10 text-emerald-500 text-xs rounded-full font-medium">
                        Save {formatCurrency(plan.savings)}
                      </span>
                    </div>
                    <div className="space-y-1 mb-4">
                      <p className="text-2xl font-bold text-emerald-500">{formatCurrency(plan.promo_price)}</p>
                      <p className="text-sm text-muted-foreground line-through">{formatCurrency(plan.regular_price)}</p>
                    </div>
                    <ul className="space-y-2 text-sm">
                      <li className="flex items-center gap-2">
                        <Check className="w-4 h-4 text-emerald-500" />
                        {plan.features.transactions_per_month === -1 ? 'Unlimited' : plan.features.transactions_per_month} transactions/month
                      </li>
                      {plan.features.ai_insights && (
                        <li className="flex items-center gap-2">
                          <Check className="w-4 h-4 text-emerald-500" />
                          AI Insights
                        </li>
                      )}
                      {plan.features.receipt_ocr && (
                        <li className="flex items-center gap-2">
                          <Check className="w-4 h-4 text-emerald-500" />
                          Receipt OCR
                        </li>
                      )}
                    </ul>
                  </div>
                ))}
              </div>
            </div>

            {/* Recent Signups */}
            {dashboard.recent_signups?.length > 0 && (
              <div className="glass rounded-2xl p-6">
                <h2 className="text-lg font-semibold mb-4">Recent Signups</h2>
                <div className="space-y-3">
                  {dashboard.recent_signups.slice(0, 5).map(signup => (
                    <div key={signup.signup_id} className="flex items-center justify-between p-3 bg-secondary/30 rounded-xl">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-emerald-500/10 flex items-center justify-center">
                          <span className="text-emerald-500 font-medium">{signup.user_name?.charAt(0)}</span>
                        </div>
                        <div>
                          <p className="font-medium">{signup.user_name}</p>
                          <p className="text-xs text-muted-foreground">{signup.user_email || signup.user_phone}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className="px-2 py-1 bg-emerald-500/10 text-emerald-500 text-xs rounded-full font-medium capitalize">
                          {signup.tier}
                        </span>
                        <p className="text-xs text-muted-foreground mt-1">
                          {new Date(signup.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Signup Tab */}
        {activeTab === 'signup' && (
          <div className="max-w-2xl mx-auto">
            <div className="glass rounded-2xl p-6">
              <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-emerald-500" />
                Sign Up New User with Promotional Discount
              </h2>
              
              {/* Eligibility Check */}
              <div className="mb-6 p-4 bg-secondary/30 rounded-xl">
                <p className="text-sm text-muted-foreground mb-3">Check if user is eligible for promotional pricing:</p>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Enter email or phone to check..."
                    value={signupForm.email || signupForm.phone}
                    onChange={(e) => {
                      const val = e.target.value;
                      if (val.includes('@')) {
                        setSignupForm(prev => ({ ...prev, email: val, phone: '' }));
                      } else {
                        setSignupForm(prev => ({ ...prev, phone: val, email: '' }));
                      }
                      setCheckResult(null);
                    }}
                    className="flex-1 bg-background border border-border rounded-lg px-4 py-2"
                  />
                  <button
                    onClick={handleCheckUser}
                    disabled={checkLoading}
                    className="px-4 py-2 bg-secondary hover:bg-secondary/80 rounded-lg flex items-center gap-2"
                  >
                    {checkLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                    Check
                  </button>
                </div>
                
                {checkResult && (
                  <div className={`mt-3 p-3 rounded-lg flex items-center gap-2 ${
                    checkResult.eligible_for_promo 
                      ? 'bg-emerald-500/10 text-emerald-500' 
                      : 'bg-red-500/10 text-red-500'
                  }`}>
                    {checkResult.eligible_for_promo 
                      ? <CheckCircle2 className="w-5 h-5" />
                      : <AlertCircle className="w-5 h-5" />
                    }
                    <span className="text-sm">{checkResult.message}</span>
                  </div>
                )}
              </div>

              <form onSubmit={handleSignup} className="space-y-4">
                {/* Name */}
                <div>
                  <label className="block text-sm font-medium mb-2">Full Name *</label>
                  <input
                    type="text"
                    value={signupForm.name}
                    onChange={(e) => setSignupForm(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="Customer's full name"
                    className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3"
                    required
                  />
                </div>

                {/* Contact */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      <Mail className="w-4 h-4 inline mr-1" />
                      Email
                    </label>
                    <input
                      type="email"
                      value={signupForm.email}
                      onChange={(e) => setSignupForm(prev => ({ ...prev, email: e.target.value }))}
                      placeholder="customer@email.com"
                      className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      <Phone className="w-4 h-4 inline mr-1" />
                      Phone
                    </label>
                    <input
                      type="tel"
                      value={signupForm.phone}
                      onChange={(e) => setSignupForm(prev => ({ ...prev, phone: e.target.value }))}
                      placeholder="08012345678"
                      className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3"
                    />
                  </div>
                </div>

                {/* Plan Selection */}
                <div>
                  <label className="block text-sm font-medium mb-2">Select Plan *</label>
                  <div className="grid grid-cols-3 gap-3">
                    {plans.map(plan => (
                      <button
                        key={plan.tier}
                        type="button"
                        onClick={() => setSignupForm(prev => ({ ...prev, tier: plan.tier }))}
                        className={`p-4 rounded-xl border-2 transition-all ${
                          signupForm.tier === plan.tier
                            ? 'border-emerald-500 bg-emerald-500/10'
                            : 'border-border hover:border-emerald-500/50'
                        }`}
                      >
                        <p className="font-semibold">{plan.name}</p>
                        <p className="text-emerald-500 font-bold">{formatCurrency(plan.promo_price)}</p>
                        <p className="text-xs text-muted-foreground line-through">{formatCurrency(plan.regular_price)}</p>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Agent Initials */}
                <div>
                  <label className="block text-sm font-medium mb-2">
                    <Tag className="w-4 h-4 inline mr-1" />
                    Agent Initials (Your Tag) *
                  </label>
                  <input
                    type="text"
                    value={signupForm.agent_initials}
                    onChange={(e) => setSignupForm(prev => ({ ...prev, agent_initials: e.target.value.toUpperCase() }))}
                    placeholder="e.g., JD"
                    maxLength={5}
                    className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3 uppercase"
                    required
                  />
                  <p className="text-xs text-muted-foreground mt-1">This tag will be associated with the user's account</p>
                </div>

                {/* Business Details (Optional) */}
                <div className="border-t border-border pt-4">
                  <p className="text-sm font-medium mb-3 flex items-center gap-2">
                    <Building2 className="w-4 h-4" />
                    Business Details (Optional)
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <input
                      type="text"
                      value={signupForm.business_name}
                      onChange={(e) => setSignupForm(prev => ({ ...prev, business_name: e.target.value }))}
                      placeholder="Business Name"
                      className="bg-secondary/50 border border-border rounded-xl px-4 py-3"
                    />
                    <select
                      value={signupForm.business_type}
                      onChange={(e) => setSignupForm(prev => ({ ...prev, business_type: e.target.value }))}
                      className="bg-secondary/50 border border-border rounded-xl px-4 py-3"
                    >
                      <option value="">Select Business Type</option>
                      <option value="Retail">Retail</option>
                      <option value="Services">Services</option>
                      <option value="Manufacturing">Manufacturing</option>
                      <option value="Trading">Trading</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>
                </div>

                {/* Submit */}
                <button
                  type="submit"
                  disabled={signupLoading || (checkResult && !checkResult.eligible_for_promo)}
                  className="w-full bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white py-4 rounded-xl font-semibold flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {signupLoading ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <>
                      <UserPlus className="w-5 h-5" />
                      Sign Up User with Promotional Discount
                    </>
                  )}
                </button>
              </form>
            </div>
          </div>
        )}

        {/* Signups List Tab */}
        {activeTab === 'signups' && (
          <SignupsList />
        )}
      </main>
    </div>
  );
}

// Signups List Component
function SignupsList() {
  const [signups, setSignups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pagination, setPagination] = useState({ page: 1, pages: 1, total: 0 });
  const [tierFilter, setTierFilter] = useState('');

  useEffect(() => {
    fetchSignups();
  }, [pagination.page, tierFilter]);

  const fetchSignups = async () => {
    setLoading(true);
    try {
      let url = `/api/agent/signups?page=${pagination.page}&limit=20`;
      if (tierFilter) url += `&tier=${tierFilter}`;
      
      const result = await apiCall(url);
      setSignups(result.signups);
      setPagination(result.pagination);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
      </div>
    );
  }

  return (
    <div className="glass rounded-2xl p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold">All Signups ({pagination.total})</h2>
        <select
          value={tierFilter}
          onChange={(e) => { setTierFilter(e.target.value); setPagination(p => ({ ...p, page: 1 })); }}
          className="bg-secondary/50 border border-border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">All Tiers</option>
          <option value="starter">Starter</option>
          <option value="business">Business</option>
          <option value="enterprise">Enterprise</option>
        </select>
      </div>

      {signups.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <Users className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>No signups yet</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-secondary/30">
              <tr>
                <th className="text-left p-3 font-medium">User</th>
                <th className="text-left p-3 font-medium">Contact</th>
                <th className="text-left p-3 font-medium">Plan</th>
                <th className="text-right p-3 font-medium">Promo Price</th>
                <th className="text-right p-3 font-medium">Savings</th>
                <th className="text-left p-3 font-medium">Date</th>
              </tr>
            </thead>
            <tbody>
              {signups.map(signup => (
                <tr key={signup.signup_id} className="border-t border-border">
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{signup.user_name}</span>
                      <span className="text-xs text-emerald-500 font-medium">{signup.agent_tag}</span>
                    </div>
                    {signup.business_name && (
                      <p className="text-xs text-muted-foreground">{signup.business_name}</p>
                    )}
                  </td>
                  <td className="p-3 text-sm text-muted-foreground">
                    {signup.user_email || signup.user_phone}
                  </td>
                  <td className="p-3">
                    <span className="px-2 py-1 bg-emerald-500/10 text-emerald-500 text-xs rounded-full font-medium capitalize">
                      {signup.tier}
                    </span>
                  </td>
                  <td className="p-3 text-right font-medium">
                    {formatCurrency(signup.promo_price)}
                  </td>
                  <td className="p-3 text-right text-emerald-500 font-medium">
                    {formatCurrency(signup.savings)}
                  </td>
                  <td className="p-3 text-sm text-muted-foreground">
                    {new Date(signup.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {pagination.pages > 1 && (
        <div className="flex justify-center gap-2 mt-6">
          <button
            onClick={() => setPagination(p => ({ ...p, page: Math.max(1, p.page - 1) }))}
            disabled={pagination.page === 1}
            className="px-3 py-1 bg-secondary rounded disabled:opacity-50"
          >
            Previous
          </button>
          <span className="px-3 py-1">
            Page {pagination.page} of {pagination.pages}
          </span>
          <button
            onClick={() => setPagination(p => ({ ...p, page: Math.min(p.pages, p.page + 1) }))}
            disabled={pagination.page === pagination.pages}
            className="px-3 py-1 bg-secondary rounded disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
