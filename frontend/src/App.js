import React, { useState, useEffect, useRef, createContext, useContext } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation, Link } from 'react-router-dom';
import { Toaster, toast } from 'sonner';
import { 
  Shield, Key, Smartphone, Copy, Check, LogOut, Settings, User, ChevronRight, Lock, RefreshCw, 
  AlertTriangle, Eye, EyeOff, TrendingUp, TrendingDown, DollarSign, Receipt, PieChart, 
  Calendar, Plus, FileText, BarChart3, Home, CreditCard, Building2, Sun, Moon, Menu, X,
  ArrowUpRight, ArrowDownRight, Clock, Target, Lightbulb, MessageSquare, Send, Sparkles,
  Upload, Download, Camera, FileSpreadsheet, Loader2, Crown, Zap, Users, Star, CheckCircle2
} from 'lucide-react';
import { LineChart, Line, BarChart, Bar, PieChart as RechartsPie, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import './App.css';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

// Chart colors
const CHART_COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

// ============== CONTEXTS ==============
const AuthContext = createContext(null);
const ThemeContext = createContext(null);

const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};

const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used within ThemeProvider');
  return context;
};

// ============== API HELPER ==============
const api = async (endpoint, options = {}) => {
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

// ============== THEME PROVIDER ==============
function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => localStorage.getItem('monetrax-theme') || 'dark');

  useEffect(() => {
    document.documentElement.classList.toggle('light-theme', theme === 'light');
    localStorage.setItem('monetrax-theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark');

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

// ============== AUTH PROVIDER ==============
function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [mfaRequired, setMfaRequired] = useState(false);
  const [business, setBusiness] = useState(null);

  const checkAuth = async () => {
    try {
      const userData = await api('/api/auth/me');
      setUser(userData);
      setMfaRequired(userData.mfa_enabled && !userData.mfa_verified);
      
      // Fetch business
      try {
        const bizData = await api('/api/business');
        setBusiness(bizData);
      } catch {}
    } catch {
      setUser(null);
      setMfaRequired(false);
      setBusiness(null);
    } finally {
      setLoading(false);
    }
  };

  const login = (userData) => {
    setUser(userData);
    setMfaRequired(userData.mfa_enabled && !userData.mfa_verified);
  };

  const completeMfa = (userData) => {
    setUser(userData);
    setMfaRequired(false);
  };

  const logout = async () => {
    try { await api('/api/auth/logout', { method: 'POST' }); } catch {}
    setUser(null);
    setMfaRequired(false);
    setBusiness(null);
  };

  const updateBusiness = (bizData) => setBusiness(bizData);

  useEffect(() => { checkAuth(); }, []);

  return (
    <AuthContext.Provider value={{ user, loading, mfaRequired, business, login, logout, completeMfa, checkAuth, updateBusiness }}>
      {children}
    </AuthContext.Provider>
  );
}

// ============== SUBSCRIPTION CONTEXT ==============
const SubscriptionContext = createContext(null);

const useSubscription = () => {
  const context = useContext(SubscriptionContext);
  if (!context) throw new Error('useSubscription must be used within SubscriptionProvider');
  return context;
};

function SubscriptionProvider({ children }) {
  const { user } = useAuth();
  const [subscription, setSubscription] = useState(null);
  const [usage, setUsage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [upgradeReason, setUpgradeReason] = useState(null);

  const fetchSubscription = async () => {
    if (!user) {
      setSubscription(null);
      setUsage(null);
      setLoading(false);
      return;
    }
    
    try {
      const [subData, usageData] = await Promise.all([
        api('/api/subscriptions/current'),
        api('/api/subscriptions/usage')
      ]);
      setSubscription(subData);
      setUsage(usageData);
    } catch (error) {
      console.error('Failed to fetch subscription:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubscription();
  }, [user]);

  const checkFeatureAccess = (feature) => {
    if (!subscription) return false;
    return subscription.features?.[feature] === true;
  };

  const checkTransactionLimit = () => {
    if (!usage) return { canAdd: true };
    const { transactions } = usage;
    if (transactions.unlimited) return { canAdd: true };
    return {
      canAdd: transactions.used < transactions.limit,
      used: transactions.used,
      limit: transactions.limit,
      remaining: transactions.remaining
    };
  };

  const promptUpgrade = (reason) => {
    setUpgradeReason(reason);
    setShowUpgradeModal(true);
  };

  const closeUpgradeModal = () => {
    setShowUpgradeModal(false);
    setUpgradeReason(null);
  };

  return (
    <SubscriptionContext.Provider value={{
      subscription,
      usage,
      loading,
      checkFeatureAccess,
      checkTransactionLimit,
      promptUpgrade,
      refreshSubscription: fetchSubscription,
      tier: subscription?.tier || 'free',
      tierName: subscription?.tier_name || 'Free'
    }}>
      {children}
      {showUpgradeModal && (
        <UpgradeModal reason={upgradeReason} onClose={closeUpgradeModal} />
      )}
    </SubscriptionContext.Provider>
  );
}

// ============== UPGRADE MODAL ==============
function UpgradeModal({ reason, onClose }) {
  const navigate = useNavigate();
  
  const reasonMessages = {
    transaction_limit: {
      title: "Transaction Limit Reached",
      message: "You have reached your monthly transaction limit on the Free plan. Upgrade to continue tracking your business finances.",
      icon: Receipt
    },
    ai_insights: {
      title: "AI Insights - Premium Feature",
      message: "Get smart AI-powered financial insights and recommendations to grow your business.",
      icon: Sparkles
    },
    receipt_ocr: {
      title: "Receipt Scanning - Premium Feature",
      message: "Automatically extract transaction data from receipts using AI-powered OCR.",
      icon: Camera
    },
    pdf_reports: {
      title: "PDF Reports - Premium Feature",
      message: "Generate professional PDF tax reports for your business records and compliance.",
      icon: FileText
    },
    default: {
      title: "Upgrade Your Plan",
      message: "Unlock more features and grow your business with a premium subscription.",
      icon: Crown
    }
  };
  
  const { title, message, icon: Icon } = reasonMessages[reason] || reasonMessages.default;

  const handleUpgrade = () => {
    onClose();
    navigate('/subscription');
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50" data-testid="upgrade-modal">
      <div className="bg-card border border-border rounded-3xl w-full max-w-md animate-fade-in">
        <div className="p-6 text-center">
          <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 flex items-center justify-center mx-auto mb-4">
            <Icon className="w-8 h-8 text-emerald-500" />
          </div>
          <h2 className="text-xl font-bold mb-2">{title}</h2>
          <p className="text-muted-foreground mb-6">{message}</p>
          
          <div className="bg-secondary/30 rounded-xl p-4 mb-6 text-left">
            <p className="text-sm font-medium mb-2">Starter Plan includes:</p>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                200 transactions/month
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                AI-powered insights
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                Receipt OCR scanning
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                PDF tax reports
              </li>
            </ul>
            <p className="text-emerald-500 font-semibold mt-3">Starting at ₦5,000/month</p>
          </div>

          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 bg-secondary hover:bg-secondary/80 py-3 rounded-xl font-medium transition-all"
            >
              Maybe Later
            </button>
            <button
              onClick={handleUpgrade}
              className="flex-1 btn-primary py-3 rounded-xl font-medium flex items-center justify-center gap-2"
              data-testid="upgrade-now-btn"
            >
              <Crown className="w-4 h-4" />
              Upgrade Now
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============== CURRENCY FORMATTER ==============
const formatCurrency = (amount) => {
  return new Intl.NumberFormat('en-NG', { 
    style: 'currency', 
    currency: 'NGN', 
    minimumFractionDigits: 0,
    maximumFractionDigits: 0 
  }).format(amount);
};

// ============== MONETRAX LOGO COMPONENT ==============
function MonetaxLogo({ size = 'md', showText = true }) {
  const sizes = { sm: 32, md: 40, lg: 56 };
  const iconSize = sizes[size] || sizes.md;
  
  return (
    <div className="flex items-center gap-3">
      <img 
        src="/logo-icon.svg" 
        alt="Monetrax" 
        style={{ width: iconSize, height: iconSize }}
        className="drop-shadow-sm"
      />
      {showText && (
        <span className="font-bold text-xl tracking-tight">
          <span className="text-[#001F4F] dark:text-white">MONE</span>
          <span className="text-[#22C55E]">TRAX</span>
        </span>
      )}
    </div>
  );
}

// ============== LANDING PAGE ==============
function LandingPage() {
  const { theme, toggleTheme } = useTheme();

  const handleLogin = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + '/dashboard';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="min-h-screen flex flex-col" data-testid="landing-page">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 glass-header">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <MonetaxLogo />
          <div className="flex items-center gap-4">
            <button onClick={toggleTheme} className="p-2 rounded-lg hover:bg-secondary/50 transition-colors">
              {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
            <button onClick={handleLogin} className="btn-primary px-4 py-2 rounded-lg text-sm font-medium">
              Get Started
            </button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <main className="flex-1 flex items-center justify-center px-4 pt-24 pb-12">
        <div className="max-w-4xl text-center animate-fade-in">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 mb-6">
            <Sparkles className="w-4 h-4 text-emerald-500" />
            <span className="text-sm text-emerald-500 font-medium">NRS-Ready Tax Compliance</span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold mb-6 leading-tight">
            Your Personal
            <span className="gradient-text block">Tax Assistant</span>
            & Business Coach
          </h1>

          <p className="text-muted-foreground text-base sm:text-lg mb-10 max-w-2xl mx-auto">
            Simplify bookkeeping and tax compliance for your Nigerian MSME. 
            Track transactions, calculate VAT, and stay NRS-ready with AI-powered insights.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            <button
              onClick={handleLogin}
              data-testid="login-button"
              className="group inline-flex items-center gap-3 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white px-8 py-4 rounded-2xl font-semibold text-lg transition-all duration-300 hover:scale-105 hover:shadow-lg hover:shadow-emerald-500/25"
            >
              <svg className="w-6 h-6" viewBox="0 0 24 24">
                <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Start with Google
              <ChevronRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
            </button>
          </div>

          {/* Features Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { icon: Receipt, title: 'Track Transactions', desc: 'Record income & expenses easily' },
              { icon: PieChart, title: 'Auto Tax Calc', desc: 'VAT & Income Tax computed' },
              { icon: Target, title: 'NRS Ready', desc: 'Tax readiness score tracking' },
              { icon: Sparkles, title: 'AI Insights', desc: 'Smart financial advice' },
            ].map((feature, i) => (
              <div key={i} className="glass rounded-2xl p-6 text-left hover:scale-105 transition-transform duration-300" style={{ animationDelay: `${i * 100}ms` }}>
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500/20 to-teal-600/20 flex items-center justify-center mb-4">
                  <feature.icon className="w-6 h-6 text-emerald-500" />
                </div>
                <h3 className="font-semibold text-foreground mb-1">{feature.title}</h3>
                <p className="text-sm text-muted-foreground">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="py-6 text-center text-sm text-muted-foreground border-t border-border">
        <p>Built for Nigerian MSMEs • Tax compliance made simple</p>
      </footer>
    </div>
  );
}

// ============== AUTH CALLBACK ==============
function AuthCallback() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processAuth = async () => {
      const hash = location.hash;
      const sessionId = new URLSearchParams(hash.replace('#', '?')).get('session_id');

      if (!sessionId) {
        toast.error('Authentication failed');
        navigate('/');
        return;
      }

      try {
        const userData = await api('/api/auth/session', {
          method: 'POST',
          body: JSON.stringify({ session_id: sessionId }),
        });

        login(userData);
        
        if (userData.mfa_enabled && !userData.mfa_verified) {
          navigate('/mfa-verify', { state: { user: userData } });
        } else {
          toast.success(`Welcome, ${userData.name}!`);
          navigate('/dashboard', { state: { user: userData } });
        }
      } catch (error) {
        toast.error(error.message);
        navigate('/');
      }
    };

    processAuth();
  }, [location, navigate, login]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="w-12 h-12 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-muted-foreground">Authenticating...</p>
      </div>
    </div>
  );
}

// ============== MFA VERIFY PAGE ==============
function MFAVerifyPage() {
  const [code, setCode] = useState('');
  const [useBackup, setUseBackup] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { completeMfa } = useAuth();

  const handleVerify = async (e) => {
    e.preventDefault();
    if (code.length < 6) {
      toast.error('Please enter a valid code');
      return;
    }

    setLoading(true);
    try {
      const endpoint = useBackup ? '/api/mfa/backup-codes/verify' : '/api/mfa/totp/authenticate';
      const result = await api(endpoint, { method: 'POST', body: JSON.stringify({ code }) });
      completeMfa(result.user);
      toast.success('Authentication successful!');
      navigate('/dashboard', { state: { user: result.user } });
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4" data-testid="mfa-verify-page">
      <div className="w-full max-w-md">
        <div className="glass rounded-3xl p-8 animate-fade-in">
          <div className="text-center mb-8">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-teal-600/20 flex items-center justify-center mx-auto mb-4">
              <Lock className="w-8 h-8 text-emerald-500" />
            </div>
            <h1 className="text-2xl font-bold mb-2">Two-Factor Authentication</h1>
            <p className="text-muted-foreground text-sm">
              {useBackup ? 'Enter one of your backup codes' : 'Enter the 6-digit code from your authenticator app'}
            </p>
          </div>

          <form onSubmit={handleVerify}>
            <input
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/[^0-9A-Za-z-]/g, ''))}
              placeholder={useBackup ? "XXXX-XXXX" : "000000"}
              className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-4 text-center text-2xl font-mono tracking-widest focus:outline-none focus:ring-2 focus:ring-emerald-500 mb-6"
              maxLength={useBackup ? 9 : 6}
              autoFocus
              data-testid="mfa-code-input"
            />
            <button type="submit" disabled={loading} data-testid="mfa-verify-button" className="w-full btn-primary py-4 rounded-xl font-semibold disabled:opacity-50">
              {loading ? 'Verifying...' : 'Verify'}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button onClick={() => { setUseBackup(!useBackup); setCode(''); }} className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              {useBackup ? 'Use authenticator app instead' : 'Use backup code instead'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============== DASHBOARD LAYOUT ==============
function DashboardLayout({ children }) {
  const { user, logout, business } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { path: '/dashboard', icon: Home, label: 'Dashboard' },
    { path: '/transactions', icon: Receipt, label: 'Transactions' },
    { path: '/tax', icon: FileText, label: 'Tax' },
    { path: '/reports', icon: BarChart3, label: 'Reports' },
    { path: '/subscription', icon: Crown, label: 'Subscription' },
    { path: '/settings', icon: Settings, label: 'Settings' },
  ];

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  return (
    <div className="min-h-screen flex">
      {/* Sidebar - Desktop */}
      <aside className="hidden lg:flex lg:flex-col lg:w-64 border-r border-border bg-card">
        <div className="p-4 border-b border-border">
          <div className="flex items-center gap-3">
            <img src="/logo-icon.svg" alt="Monetrax" className="w-10 h-10" />
            <div>
              <span className="font-bold text-lg">
                <span className="text-[#001F4F] dark:text-white">MONE</span>
                <span className="text-[#22C55E]">TRAX</span>
              </span>
              <p className="text-xs text-muted-foreground truncate max-w-[140px]">{business?.business_name || 'Setup Business'}</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${
                location.pathname === item.path
                  ? 'bg-emerald-500/10 text-emerald-500 font-medium'
                  : 'text-muted-foreground hover:bg-secondary/50 hover:text-foreground'
              }`}
            >
              <item.icon className="w-5 h-5" />
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="p-4 border-t border-border">
          <div className="flex items-center gap-3 mb-4">
            {user?.picture && <img src={user.picture} alt="" className="w-10 h-10 rounded-full" />}
            <div className="flex-1 min-w-0">
              <p className="font-medium text-sm truncate">{user?.name}</p>
              <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={toggleTheme} className="flex-1 p-2 rounded-lg hover:bg-secondary/50 transition-colors flex items-center justify-center">
              {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
            <button onClick={handleLogout} className="flex-1 p-2 rounded-lg hover:bg-secondary/50 transition-colors flex items-center justify-center text-red-500">
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile Header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 glass-header">
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center gap-2">
            <img src="/logo-icon.svg" alt="Monetrax" className="w-8 h-8" />
            <span className="font-bold">
              <span className="text-[#001F4F] dark:text-white">MONE</span>
              <span className="text-[#22C55E]">TRAX</span>
            </span>
          </div>
          <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="p-2">
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 z-40 bg-background pt-16">
          <nav className="p-4 space-y-2">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${
                  location.pathname === item.path ? 'bg-emerald-500/10 text-emerald-500' : 'text-muted-foreground'
                }`}
              >
                <item.icon className="w-5 h-5" />
                {item.label}
              </Link>
            ))}
            <button onClick={handleLogout} className="flex items-center gap-3 px-4 py-3 rounded-xl text-red-500 w-full">
              <LogOut className="w-5 h-5" />
              Logout
            </button>
          </nav>
        </div>
      )}

      {/* Main Content */}
      <main className="flex-1 lg:ml-0 pt-16 lg:pt-0 overflow-auto">
        {children}
      </main>
    </div>
  );
}

// ============== DASHBOARD PAGE ==============
function DashboardPage() {
  const { user, business, updateBusiness } = useAuth();
  const [summary, setSummary] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showBusinessSetup, setShowBusinessSetup] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [summaryData, txData] = await Promise.all([
        api('/api/summary?period=month'),
        api('/api/transactions?limit=5')
      ]);
      setSummary(summaryData);
      setTransactions(txData);
      
      if (!business) {
        setShowBusinessSetup(true);
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="w-12 h-12 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-4 lg:p-8 space-y-6" data-testid="dashboard-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Welcome back, {user?.name?.split(' ')[0]}! 👋</h1>
          <p className="text-muted-foreground">Here's your business overview for this month</p>
        </div>
        <Link to="/transactions" className="btn-primary px-4 py-2 rounded-lg inline-flex items-center gap-2">
          <Plus className="w-4 h-4" />
          Add Transaction
        </Link>
      </div>

      {/* Business Setup Banner */}
      {!business && (
        <div className="bg-gradient-to-r from-emerald-500/10 to-teal-600/10 border border-emerald-500/20 rounded-2xl p-6">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/20 flex items-center justify-center">
              <Building2 className="w-6 h-6 text-emerald-500" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-lg mb-1">Set up your business</h3>
              <p className="text-muted-foreground text-sm mb-4">Add your business details to start tracking finances and calculating taxes.</p>
              <button onClick={() => setShowBusinessSetup(true)} className="btn-primary px-4 py-2 rounded-lg text-sm">
                Setup Business
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tax Readiness Score */}
      <div className="glass rounded-2xl p-6 border-2 border-emerald-500/30">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center">
              <Target className="w-6 h-6 text-emerald-500" />
            </div>
            <div>
              <h2 className="font-semibold text-lg">NRS Readiness Score</h2>
              <p className="text-sm text-muted-foreground">Your tax compliance status</p>
            </div>
          </div>
          <div className="text-right">
            <span className="text-3xl font-bold text-emerald-500">{summary?.tax_readiness_score || 0}%</span>
            <p className="text-xs text-muted-foreground">
              {(summary?.tax_readiness_score || 0) >= 80 ? 'NRS-Ready! 🎯' : (summary?.tax_readiness_score || 0) >= 50 ? 'Getting There 📈' : 'Keep Going 💪'}
            </p>
          </div>
        </div>
        <div className="h-3 bg-secondary rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-emerald-500 to-teal-500 transition-all duration-500"
            style={{ width: `${summary?.tax_readiness_score || 0}%` }}
          />
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard icon={TrendingUp} label="Income" value={summary?.income || 0} color="blue" trend={12} />
        <SummaryCard icon={TrendingDown} label="Expenses" value={summary?.expenses || 0} color="red" trend={-5} />
        <SummaryCard icon={DollarSign} label="Profit" value={summary?.profit || 0} color="green" />
        <SummaryCard icon={Receipt} label="Tax Due" value={summary?.total_tax_due || 0} color="orange" />
      </div>

      {/* Two Column Layout */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Tax Breakdown */}
        <div className="glass rounded-2xl p-6">
          <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5 text-emerald-500" />
            Tax Breakdown
          </h3>
          <div className="space-y-3">
            <TaxItem label="VAT Collected (7.5%)" value={summary?.vat_collected || 0} />
            <TaxItem label="VAT Paid (Credit)" value={summary?.vat_paid || 0} negative />
            <TaxItem label="Net VAT Due" value={summary?.net_vat || 0} highlight />
            <div className="border-t border-border pt-3 mt-3">
              <TaxItem label="Est. Income Tax" value={summary?.estimated_income_tax || 0} />
            </div>
            <div className="border-t border-border pt-3">
              <TaxItem label="Total Tax Liability" value={summary?.total_tax_due || 0} highlight />
            </div>
          </div>
        </div>

        {/* Recent Transactions */}
        <div className="glass rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-lg flex items-center gap-2">
              <Clock className="w-5 h-5 text-emerald-500" />
              Recent Transactions
            </h3>
            <Link to="/transactions" className="text-sm text-emerald-500 hover:underline">View All</Link>
          </div>
          {transactions.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Receipt className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No transactions yet</p>
              <Link to="/transactions" className="text-emerald-500 text-sm hover:underline">Add your first transaction</Link>
            </div>
          ) : (
            <div className="space-y-3">
              {transactions.map((tx) => (
                <div key={tx.transaction_id} className="flex items-center justify-between p-3 rounded-xl bg-secondary/30">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${tx.type === 'income' ? 'bg-emerald-500/10' : 'bg-red-500/10'}`}>
                      {tx.type === 'income' ? <ArrowUpRight className="w-5 h-5 text-emerald-500" /> : <ArrowDownRight className="w-5 h-5 text-red-500" />}
                    </div>
                    <div>
                      <p className="font-medium text-sm">{tx.description}</p>
                      <p className="text-xs text-muted-foreground">{tx.category} • {tx.date}</p>
                    </div>
                  </div>
                  <span className={`font-semibold ${tx.type === 'income' ? 'text-emerald-500' : 'text-red-500'}`}>
                    {tx.type === 'income' ? '+' : '-'}{formatCurrency(tx.amount)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Tax Tip */}
      <div className="bg-gradient-to-r from-yellow-500/10 to-orange-500/10 border border-yellow-500/20 rounded-2xl p-6">
        <div className="flex items-start gap-4">
          <Lightbulb className="w-6 h-6 text-yellow-500 flex-shrink-0" />
          <div>
            <h4 className="font-semibold text-yellow-600 mb-1">💡 Tax Tip of the Day</h4>
            <p className="text-sm text-muted-foreground">
              The first ₦800,000 of your annual income is tax-free under the 2025 reforms! Keep accurate records to maximize your savings and stay compliant with NRS requirements.
            </p>
          </div>
        </div>
      </div>

      {/* Business Setup Modal */}
      {showBusinessSetup && <BusinessSetupModal onClose={() => { setShowBusinessSetup(false); fetchData(); }} />}
    </div>
  );
}

function SummaryCard({ icon: Icon, label, value, color, trend }) {
  const colorClasses = {
    blue: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
    red: 'bg-red-500/10 text-red-500 border-red-500/20',
    green: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
    orange: 'bg-orange-500/10 text-orange-500 border-orange-500/20',
  };

  return (
    <div className={`glass rounded-2xl p-4 border ${colorClasses[color]}`}>
      <div className="flex items-center gap-2 mb-2">
        <Icon className="w-5 h-5" />
        <span className="text-sm text-muted-foreground">{label}</span>
      </div>
      <p className="text-xl font-bold">{formatCurrency(value)}</p>
      {trend && (
        <p className={`text-xs mt-1 ${trend > 0 ? 'text-emerald-500' : 'text-red-500'}`}>
          {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}% from last month
        </p>
      )}
    </div>
  );
}

function TaxItem({ label, value, negative, highlight }) {
  return (
    <div className={`flex items-center justify-between ${highlight ? 'font-semibold' : ''}`}>
      <span className="text-muted-foreground">{label}</span>
      <span className={negative ? 'text-red-500' : highlight ? 'text-emerald-500' : ''}>
        {negative ? '-' : ''}{formatCurrency(Math.abs(value))}
      </span>
    </div>
  );
}

// ============== BUSINESS SETUP MODAL ==============
function BusinessSetupModal({ onClose }) {
  const { updateBusiness } = useAuth();
  const [formData, setFormData] = useState({
    business_name: '',
    business_type: 'Sole Proprietorship',
    industry: 'Retail',
    tin: '',
    annual_turnover: 0
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.business_name.trim()) {
      toast.error('Please enter your business name');
      return;
    }

    setLoading(true);
    try {
      const result = await api('/api/business', {
        method: 'POST',
        body: JSON.stringify(formData)
      });
      updateBusiness(result);
      toast.success('Business created successfully!');
      onClose();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-card border border-border rounded-3xl w-full max-w-md animate-fade-in">
        <div className="p-6">
          <div className="text-center mb-6">
            <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 flex items-center justify-center mx-auto mb-4">
              <Building2 className="w-8 h-8 text-emerald-500" />
            </div>
            <h2 className="text-xl font-bold mb-2">Setup Your Business</h2>
            <p className="text-sm text-muted-foreground">Add your business details to get started</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm text-muted-foreground mb-1 block">Business Name *</label>
              <input
                type="text"
                value={formData.business_name}
                onChange={(e) => setFormData({ ...formData, business_name: e.target.value })}
                className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                placeholder="e.g., Ade Fashion Store"
                required
              />
            </div>

            <div>
              <label className="text-sm text-muted-foreground mb-1 block">Business Type</label>
              <select
                value={formData.business_type}
                onChange={(e) => setFormData({ ...formData, business_type: e.target.value })}
                className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                <option>Sole Proprietorship</option>
                <option>Partnership</option>
                <option>Limited Liability Company</option>
                <option>Cooperative</option>
              </select>
            </div>

            <div>
              <label className="text-sm text-muted-foreground mb-1 block">Industry</label>
              <select
                value={formData.industry}
                onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
                className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                <option>Retail</option>
                <option>Fashion</option>
                <option>Food & Beverage</option>
                <option>Technology</option>
                <option>Services</option>
                <option>Manufacturing</option>
                <option>Agriculture</option>
                <option>Construction</option>
                <option>Healthcare</option>
                <option>Education</option>
                <option>Other</option>
              </select>
            </div>

            <div>
              <label className="text-sm text-muted-foreground mb-1 block">TIN (Tax ID) - Optional</label>
              <input
                type="text"
                value={formData.tin}
                onChange={(e) => setFormData({ ...formData, tin: e.target.value })}
                className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                placeholder="Enter your TIN if you have one"
              />
            </div>

            <div className="flex gap-3 pt-4">
              <button type="button" onClick={onClose} className="flex-1 bg-secondary hover:bg-secondary/80 py-3 rounded-xl font-medium transition-all">
                Cancel
              </button>
              <button type="submit" disabled={loading} className="flex-1 btn-primary py-3 rounded-xl font-medium disabled:opacity-50">
                {loading ? 'Creating...' : 'Create Business'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

// ============== TRANSACTIONS PAGE ==============
function TransactionsPage() {
  const { usage, checkFeatureAccess, promptUpgrade, refreshSubscription, tier, tierName } = useSubscription();
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showScanModal, setShowScanModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetchTransactions();
  }, [filter]);

  const fetchTransactions = async () => {
    setLoading(true);
    try {
      const params = filter !== 'all' ? `?type=${filter}` : '';
      const data = await api(`/api/transactions${params}`);
      setTransactions(data);
    } catch (error) {
      console.error('Failed to fetch transactions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = async () => {
    try {
      const response = await fetch(`${API_URL}/api/transactions/export/csv`, {
        credentials: 'include'
      });
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `monetrax_transactions_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      toast.success('Transactions exported!');
    } catch (error) {
      toast.error('Export failed');
    }
  };

  const handleScanReceipt = () => {
    if (!checkFeatureAccess('receipt_ocr')) {
      promptUpgrade('receipt_ocr');
      return;
    }
    setShowScanModal(true);
  };

  const handleAddTransaction = () => {
    // Check if limit reached before showing modal
    if (usage?.transactions?.limit_exceeded) {
      promptUpgrade('transaction_limit');
      return;
    }
    setShowAddModal(true);
  };

  // Calculate usage percentage for progress bar
  const usagePercentage = usage?.transactions?.usage_percentage || 0;
  const isNearLimit = usagePercentage >= 80;
  const isAtLimit = usage?.transactions?.limit_exceeded;

  return (
    <div className="p-4 lg:p-8 space-y-6" data-testid="transactions-page">
      {/* Usage Banner */}
      {tier === 'free' && usage && (
        <div className={`glass rounded-xl p-4 ${isAtLimit ? 'border border-red-500/50 bg-red-500/5' : isNearLimit ? 'border border-yellow-500/50 bg-yellow-500/5' : ''}`} data-testid="usage-banner">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Receipt className={`w-4 h-4 ${isAtLimit ? 'text-red-500' : isNearLimit ? 'text-yellow-500' : 'text-muted-foreground'}`} />
              <span className="text-sm font-medium">
                {usage.transactions.used} / {usage.transactions.limit} transactions this month
              </span>
            </div>
            {(isNearLimit || isAtLimit) && (
              <Link to="/subscription" className="text-xs text-emerald-500 hover:underline flex items-center gap-1">
                <Crown className="w-3 h-3" />
                Upgrade
              </Link>
            )}
          </div>
          <div className="h-2 bg-secondary rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all ${isAtLimit ? 'bg-red-500' : isNearLimit ? 'bg-yellow-500' : 'bg-emerald-500'}`}
              style={{ width: `${Math.min(100, usagePercentage)}%` }}
            />
          </div>
          {isAtLimit && (
            <p className="text-xs text-red-500 mt-2">
              You have reached your monthly limit. Upgrade to add more transactions.
            </p>
          )}
        </div>
      )}

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Transactions</h1>
          <p className="text-muted-foreground">Manage your income and expenses</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button 
            onClick={handleScanReceipt} 
            className={`bg-secondary hover:bg-secondary/80 px-4 py-2 rounded-lg inline-flex items-center gap-2 text-sm ${!checkFeatureAccess('receipt_ocr') ? 'opacity-70' : ''}`} 
            data-testid="scan-receipt-btn"
          >
            <Camera className="w-4 h-4" />
            Scan Receipt
            {!checkFeatureAccess('receipt_ocr') && <Crown className="w-3 h-3 text-yellow-500" />}
          </button>
          <button onClick={() => setShowImportModal(true)} className="bg-secondary hover:bg-secondary/80 px-4 py-2 rounded-lg inline-flex items-center gap-2 text-sm" data-testid="import-csv-btn">
            <Upload className="w-4 h-4" />
            Import CSV
          </button>
          <button onClick={handleExportCSV} className="bg-secondary hover:bg-secondary/80 px-4 py-2 rounded-lg inline-flex items-center gap-2 text-sm" data-testid="export-csv-btn">
            <Download className="w-4 h-4" />
            Export
          </button>
          <button onClick={() => setShowAddModal(true)} className="btn-primary px-4 py-2 rounded-lg inline-flex items-center gap-2 text-sm" data-testid="add-transaction-btn">
            <Plus className="w-4 h-4" />
            Add Transaction
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2">
        {['all', 'income', 'expense'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              filter === f ? 'bg-emerald-500 text-white' : 'bg-secondary/50 text-muted-foreground hover:bg-secondary'
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {/* Transactions List */}
      <div className="glass rounded-2xl overflow-hidden">
        {loading ? (
          <div className="p-8 text-center">
            <div className="w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto" />
          </div>
        ) : transactions.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            <Receipt className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No transactions found</p>
            <button onClick={() => setShowAddModal(true)} className="text-emerald-500 text-sm hover:underline mt-2">
              Add your first transaction
            </button>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {transactions.map((tx) => (
              <div key={tx.transaction_id} className="flex items-center justify-between p-4 hover:bg-secondary/30 transition-colors">
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${tx.type === 'income' ? 'bg-emerald-500/10' : 'bg-red-500/10'}`}>
                    {tx.type === 'income' ? <ArrowUpRight className="w-6 h-6 text-emerald-500" /> : <ArrowDownRight className="w-6 h-6 text-red-500" />}
                  </div>
                  <div>
                    <p className="font-medium">{tx.description}</p>
                    <p className="text-sm text-muted-foreground">{tx.category} • {tx.date}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className={`font-semibold ${tx.type === 'income' ? 'text-emerald-500' : 'text-red-500'}`}>
                    {tx.type === 'income' ? '+' : '-'}{formatCurrency(tx.amount)}
                  </p>
                  {tx.vat_amount > 0 && (
                    <p className="text-xs text-muted-foreground">VAT: {formatCurrency(tx.vat_amount)}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add Transaction Modal */}
      {showAddModal && <AddTransactionModal onClose={() => { setShowAddModal(false); fetchTransactions(); }} />}
      
      {/* Scan Receipt Modal */}
      {showScanModal && <ScanReceiptModal onClose={() => { setShowScanModal(false); fetchTransactions(); }} />}
      
      {/* Import CSV Modal */}
      {showImportModal && <ImportCSVModal onClose={() => { setShowImportModal(false); fetchTransactions(); }} />}
    </div>
  );
}

// ============== SCAN RECEIPT MODAL ==============
function ScanReceiptModal({ onClose }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      const reader = new FileReader();
      reader.onloadend = () => setPreview(reader.result);
      reader.readAsDataURL(selectedFile);
    }
  };

  const handleScan = async () => {
    if (!file) return;
    
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch(`${API_URL}/api/receipts/scan`, {
        method: 'POST',
        credentials: 'include',
        body: formData
      });
      
      const data = await response.json();
      setResult(data);
      
      if (data.success && data.parsed_data) {
        toast.success('Receipt scanned successfully!');
      } else {
        toast.info(data.message || 'Could not parse receipt');
      }
    } catch (error) {
      toast.error('Scan failed');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTransaction = async () => {
    if (!result?.parsed_data) return;
    
    try {
      await api('/api/transactions', {
        method: 'POST',
        body: JSON.stringify({
          type: 'expense',
          category: result.parsed_data.category_suggestion || 'Other Expense',
          amount: result.parsed_data.total || 0,
          description: result.parsed_data.merchant || 'Receipt scan',
          date: result.parsed_data.date || new Date().toISOString().split('T')[0],
          is_taxable: true
        })
      });
      toast.success('Transaction created!');
      onClose();
    } catch (error) {
      toast.error(error.message);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50" data-testid="scan-receipt-modal">
      <div className="bg-card border border-border rounded-3xl w-full max-w-md animate-fade-in">
        <div className="p-6">
          <div className="text-center mb-6">
            <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 flex items-center justify-center mx-auto mb-4">
              <Camera className="w-8 h-8 text-emerald-500" />
            </div>
            <h2 className="text-xl font-bold mb-2">Scan Receipt</h2>
            <p className="text-sm text-muted-foreground">Upload a receipt image to extract transaction data</p>
          </div>

          {!result ? (
            <>
              <div 
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-border rounded-xl p-8 text-center cursor-pointer hover:border-emerald-500/50 transition-colors mb-4"
              >
                {preview ? (
                  <img src={preview} alt="Receipt" className="max-h-48 mx-auto rounded-lg" />
                ) : (
                  <>
                    <Upload className="w-12 h-12 mx-auto mb-3 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">Click to upload receipt image</p>
                    <p className="text-xs text-muted-foreground mt-1">JPEG, PNG, WebP supported</p>
                  </>
                )}
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileChange}
                className="hidden"
              />

              <div className="flex gap-3">
                <button onClick={onClose} className="flex-1 bg-secondary hover:bg-secondary/80 py-3 rounded-xl font-medium">Cancel</button>
                <button 
                  onClick={handleScan} 
                  disabled={!file || loading}
                  className="flex-1 btn-primary py-3 rounded-xl font-medium disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Camera className="w-4 h-4" />}
                  {loading ? 'Scanning...' : 'Scan Receipt'}
                </button>
              </div>
            </>
          ) : (
            <>
              {result.parsed_data ? (
                <div className="space-y-4 mb-6">
                  <div className="p-4 bg-secondary/30 rounded-xl">
                    <p className="text-sm text-muted-foreground">Merchant</p>
                    <p className="font-semibold">{result.parsed_data.merchant}</p>
                  </div>
                  <div className="p-4 bg-secondary/30 rounded-xl">
                    <p className="text-sm text-muted-foreground">Total Amount</p>
                    <p className="text-2xl font-bold text-emerald-500">{formatCurrency(result.parsed_data.total)}</p>
                  </div>
                  {result.parsed_data.date && (
                    <div className="p-4 bg-secondary/30 rounded-xl">
                      <p className="text-sm text-muted-foreground">Date</p>
                      <p className="font-semibold">{result.parsed_data.date}</p>
                    </div>
                  )}
                  <div className="p-4 bg-secondary/30 rounded-xl">
                    <p className="text-sm text-muted-foreground">Suggested Category</p>
                    <p className="font-semibold">{result.parsed_data.category_suggestion}</p>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground mb-6">
                  <AlertTriangle className="w-12 h-12 mx-auto mb-3 text-yellow-500" />
                  <p>{result.message || 'Could not parse receipt data'}</p>
                </div>
              )}

              <div className="flex gap-3">
                <button onClick={() => { setResult(null); setFile(null); setPreview(null); }} className="flex-1 bg-secondary hover:bg-secondary/80 py-3 rounded-xl font-medium">
                  Scan Another
                </button>
                {result.parsed_data && (
                  <button onClick={handleCreateTransaction} className="flex-1 btn-primary py-3 rounded-xl font-medium">
                    Create Transaction
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ============== IMPORT CSV MODAL ==============
function ImportCSVModal({ onClose }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const fileInputRef = useRef(null);

  const handleImport = async () => {
    if (!file) return;
    
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch(`${API_URL}/api/transactions/import/csv`, {
        method: 'POST',
        credentials: 'include',
        body: formData
      });
      
      const data = await response.json();
      setResult(data);
      
      if (data.success) {
        toast.success(`Imported ${data.imported} transactions!`);
      }
    } catch (error) {
      toast.error('Import failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50" data-testid="import-csv-modal">
      <div className="bg-card border border-border rounded-3xl w-full max-w-md animate-fade-in">
        <div className="p-6">
          <div className="text-center mb-6">
            <div className="w-16 h-16 rounded-2xl bg-blue-500/10 flex items-center justify-center mx-auto mb-4">
              <FileSpreadsheet className="w-8 h-8 text-blue-500" />
            </div>
            <h2 className="text-xl font-bold mb-2">Import Transactions</h2>
            <p className="text-sm text-muted-foreground">Upload a CSV file with your transactions</p>
          </div>

          {!result ? (
            <>
              <div className="bg-secondary/30 rounded-xl p-4 mb-4 text-sm">
                <p className="font-medium mb-2">CSV Format:</p>
                <code className="text-xs text-muted-foreground">date,type,category,amount,description,is_taxable</code>
                <p className="text-xs text-muted-foreground mt-2">Example: 2026-01-20,income,Sales,50000,Product sales,true</p>
              </div>

              <div 
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-border rounded-xl p-8 text-center cursor-pointer hover:border-blue-500/50 transition-colors mb-4"
              >
                {file ? (
                  <div>
                    <FileSpreadsheet className="w-12 h-12 mx-auto mb-3 text-blue-500" />
                    <p className="font-medium">{file.name}</p>
                    <p className="text-xs text-muted-foreground">{(file.size / 1024).toFixed(1)} KB</p>
                  </div>
                ) : (
                  <>
                    <Upload className="w-12 h-12 mx-auto mb-3 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">Click to upload CSV file</p>
                  </>
                )}
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                onChange={(e) => setFile(e.target.files[0])}
                className="hidden"
              />

              <div className="flex gap-3">
                <button onClick={onClose} className="flex-1 bg-secondary hover:bg-secondary/80 py-3 rounded-xl font-medium">Cancel</button>
                <button 
                  onClick={handleImport} 
                  disabled={!file || loading}
                  className="flex-1 btn-primary py-3 rounded-xl font-medium disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                  {loading ? 'Importing...' : 'Import'}
                </button>
              </div>
            </>
          ) : (
            <>
              <div className="text-center py-4 mb-6">
                {result.imported > 0 ? (
                  <>
                    <Check className="w-16 h-16 mx-auto mb-3 text-emerald-500" />
                    <p className="text-2xl font-bold text-emerald-500">{result.imported}</p>
                    <p className="text-muted-foreground">transactions imported</p>
                  </>
                ) : (
                  <>
                    <AlertTriangle className="w-16 h-16 mx-auto mb-3 text-yellow-500" />
                    <p className="text-muted-foreground">No transactions imported</p>
                  </>
                )}
                
                {result.errors?.length > 0 && (
                  <div className="mt-4 text-left bg-red-500/10 rounded-xl p-4 max-h-32 overflow-y-auto">
                    <p className="text-sm font-medium text-red-500 mb-2">Errors ({result.total_errors}):</p>
                    {result.errors.map((err, i) => (
                      <p key={i} className="text-xs text-red-400">{err}</p>
                    ))}
                  </div>
                )}
              </div>

              <button onClick={onClose} className="w-full btn-primary py-3 rounded-xl font-medium">
                Done
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ============== ADD TRANSACTION MODAL ==============
function AddTransactionModal({ onClose }) {
  const { checkTransactionLimit, promptUpgrade, refreshSubscription } = useSubscription();
  const [formData, setFormData] = useState({
    type: 'income',
    category: 'Sales',
    amount: '',
    description: '',
    date: new Date().toISOString().split('T')[0],
    is_taxable: true,
    payment_method: 'Cash'
  });
  const [loading, setLoading] = useState(false);
  const [categories, setCategories] = useState({ income: [], expense: [] });

  useEffect(() => {
    fetchCategories();
  }, []);

  const fetchCategories = async () => {
    try {
      const data = await api('/api/categories');
      setCategories(data);
    } catch {}
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.amount || !formData.description) {
      toast.error('Please fill in all required fields');
      return;
    }

    // Check transaction limit before submitting
    const limitCheck = checkTransactionLimit();
    if (!limitCheck.canAdd) {
      onClose();
      promptUpgrade('transaction_limit');
      return;
    }

    setLoading(true);
    try {
      await api('/api/transactions', {
        method: 'POST',
        body: JSON.stringify({ ...formData, amount: parseFloat(formData.amount) })
      });
      toast.success('Transaction added successfully!');
      refreshSubscription(); // Refresh usage count
      onClose();
    } catch (error) {
      // Check if it's a transaction limit error
      if (error.message?.includes('transaction_limit_exceeded') || error.message?.includes('monthly limit')) {
        onClose();
        promptUpgrade('transaction_limit');
      } else {
        toast.error(error.message);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50" data-testid="add-transaction-modal">
      <div className="bg-card border border-border rounded-3xl w-full max-w-md max-h-[90vh] overflow-y-auto animate-fade-in">
        <div className="p-6">
          <div className="text-center mb-6">
            <h2 className="text-xl font-bold mb-2">Add Transaction</h2>
            <p className="text-sm text-muted-foreground">Record a new income or expense</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Type Selector */}
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setFormData({ ...formData, type: 'income', category: 'Sales' })}
                className={`p-4 rounded-xl border-2 transition-all ${formData.type === 'income' ? 'border-emerald-500 bg-emerald-500/10' : 'border-border'}`}
              >
                <ArrowUpRight className={`w-6 h-6 mx-auto mb-2 ${formData.type === 'income' ? 'text-emerald-500' : 'text-muted-foreground'}`} />
                <span className={`font-medium ${formData.type === 'income' ? 'text-emerald-500' : ''}`}>Income</span>
              </button>
              <button
                type="button"
                onClick={() => setFormData({ ...formData, type: 'expense', category: 'Supplies' })}
                className={`p-4 rounded-xl border-2 transition-all ${formData.type === 'expense' ? 'border-red-500 bg-red-500/10' : 'border-border'}`}
              >
                <ArrowDownRight className={`w-6 h-6 mx-auto mb-2 ${formData.type === 'expense' ? 'text-red-500' : 'text-muted-foreground'}`} />
                <span className={`font-medium ${formData.type === 'expense' ? 'text-red-500' : ''}`}>Expense</span>
              </button>
            </div>

            <div>
              <label className="text-sm text-muted-foreground mb-1 block">Amount (₦) *</label>
              <input
                type="number"
                value={formData.amount}
                onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3 text-lg font-semibold focus:outline-none focus:ring-2 focus:ring-emerald-500"
                placeholder="0"
                required
              />
            </div>

            <div>
              <label className="text-sm text-muted-foreground mb-1 block">Category</label>
              <select
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                {(categories[formData.type] || []).map((cat) => (
                  <option key={cat.name} value={cat.name}>{cat.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-sm text-muted-foreground mb-1 block">Description *</label>
              <input
                type="text"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                placeholder="e.g., Product sales"
                required
              />
            </div>

            <div>
              <label className="text-sm text-muted-foreground mb-1 block">Date</label>
              <input
                type="date"
                value={formData.date}
                onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>

            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="taxable"
                checked={formData.is_taxable}
                onChange={(e) => setFormData({ ...formData, is_taxable: e.target.checked })}
                className="w-5 h-5 rounded border-border text-emerald-500 focus:ring-emerald-500"
              />
              <label htmlFor="taxable" className="text-sm">Subject to VAT (7.5%)</label>
            </div>

            <div className="flex gap-3 pt-4">
              <button type="button" onClick={onClose} className="flex-1 bg-secondary hover:bg-secondary/80 py-3 rounded-xl font-medium transition-all">
                Cancel
              </button>
              <button type="submit" disabled={loading} className="flex-1 btn-primary py-3 rounded-xl font-medium disabled:opacity-50">
                {loading ? 'Adding...' : 'Add Transaction'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

// ============== TAX PAGE ==============
function TaxPage() {
  const [taxSummary, setTaxSummary] = useState(null);
  const [calendar, setCalendar] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTaxData();
  }, []);

  const fetchTaxData = async () => {
    setLoading(true);
    try {
      const [summaryData, calendarData] = await Promise.all([
        api('/api/tax/summary'),
        api('/api/tax/calendar')
      ]);
      setTaxSummary(summaryData);
      setCalendar(calendarData);
    } catch (error) {
      console.error('Failed to fetch tax data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="w-12 h-12 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-4 lg:p-8 space-y-6" data-testid="tax-page">
      <div>
        <h1 className="text-2xl font-bold">Tax Overview</h1>
        <p className="text-muted-foreground">Monitor your tax obligations and deadlines</p>
      </div>

      {/* Tax Summary */}
      <div className="grid lg:grid-cols-2 gap-6">
        <div className="glass rounded-2xl p-6">
          <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5 text-emerald-500" />
            Tax Summary ({taxSummary?.period})
          </h3>
          <div className="space-y-4">
            <div className="p-4 bg-secondary/30 rounded-xl">
              <p className="text-sm text-muted-foreground mb-1">Total Revenue</p>
              <p className="text-2xl font-bold">{formatCurrency(taxSummary?.total_income || 0)}</p>
            </div>
            <div className="p-4 bg-secondary/30 rounded-xl">
              <p className="text-sm text-muted-foreground mb-1">Total Expenses</p>
              <p className="text-2xl font-bold">{formatCurrency(taxSummary?.total_expenses || 0)}</p>
            </div>
            <div className="p-4 bg-emerald-500/10 rounded-xl border border-emerald-500/20">
              <p className="text-sm text-muted-foreground mb-1">Taxable Profit</p>
              <p className="text-2xl font-bold text-emerald-500">{formatCurrency(taxSummary?.profit || 0)}</p>
            </div>
          </div>
        </div>

        <div className="glass rounded-2xl p-6">
          <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
            <Receipt className="w-5 h-5 text-emerald-500" />
            Tax Obligations
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between p-3 bg-secondary/30 rounded-xl">
              <span className="text-muted-foreground">VAT Collected</span>
              <span className="font-semibold">{formatCurrency(taxSummary?.vat_collected || 0)}</span>
            </div>
            <div className="flex justify-between p-3 bg-secondary/30 rounded-xl">
              <span className="text-muted-foreground">VAT Paid (Credit)</span>
              <span className="font-semibold text-red-500">-{formatCurrency(taxSummary?.vat_paid || 0)}</span>
            </div>
            <div className="flex justify-between p-3 bg-blue-500/10 rounded-xl border border-blue-500/20">
              <span className="text-blue-500">Net VAT Due</span>
              <span className="font-semibold text-blue-500">{formatCurrency(taxSummary?.net_vat || 0)}</span>
            </div>
            <div className="flex justify-between p-3 bg-secondary/30 rounded-xl">
              <span className="text-muted-foreground">Income Tax</span>
              <span className="font-semibold">{formatCurrency(taxSummary?.income_tax || 0)}</span>
            </div>
            <div className="flex justify-between p-4 bg-orange-500/10 rounded-xl border border-orange-500/20">
              <span className="text-orange-500 font-semibold">Total Tax Liability</span>
              <span className="font-bold text-orange-500">{formatCurrency(taxSummary?.total_tax_liability || 0)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Tax Calendar */}
      <div className="glass rounded-2xl p-6">
        <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
          <Calendar className="w-5 h-5 text-emerald-500" />
          Upcoming Deadlines
        </h3>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {calendar?.deadlines.map((deadline, i) => (
            <div key={i} className="p-4 bg-secondary/30 rounded-xl">
              <div className="flex items-center gap-2 mb-2">
                <Clock className="w-4 h-4 text-orange-500" />
                <span className="text-sm font-medium">{deadline.name}</span>
              </div>
              <p className="text-lg font-bold">{new Date(deadline.date).toLocaleDateString('en-NG', { day: 'numeric', month: 'short', year: 'numeric' })}</p>
              <p className="text-xs text-muted-foreground mt-1">{deadline.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Tax Tips */}
      <div className="glass rounded-2xl p-6">
        <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
          <Lightbulb className="w-5 h-5 text-yellow-500" />
          Tax Tips
        </h3>
        <div className="grid sm:grid-cols-2 gap-3">
          {calendar?.tips.map((tip, i) => (
            <div key={i} className="p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-xl">
              <p className="text-sm">{tip}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ============== REPORTS PAGE ==============
function ReportsPage() {
  const [report, setReport] = useState(null);
  const [chartsData, setChartsData] = useState(null);
  const [aiInsights, setAiInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [insightLevel, setInsightLevel] = useState('standard');
  const [insightQuery, setInsightQuery] = useState('');
  const [loadingInsight, setLoadingInsight] = useState(false);
  const { theme } = useTheme();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [reportData, chartData] = await Promise.all([
        api('/api/reports/income-statement'),
        api('/api/analytics/charts?period=6months')
      ]);
      setReport(reportData);
      setChartsData(chartData);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleExportPDF = async () => {
    try {
      const response = await fetch(`${API_URL}/api/reports/export/pdf?report_type=income-statement`, {
        credentials: 'include'
      });
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `monetrax_tax_report_${new Date().getFullYear()}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      toast.success('PDF exported!');
    } catch (error) {
      toast.error('Export failed');
    }
  };

  const handleGetInsights = async () => {
    if (!insightQuery.trim()) {
      toast.error('Please enter a question');
      return;
    }
    
    setLoadingInsight(true);
    try {
      const data = await api('/api/ai/insights/v2', {
        method: 'POST',
        body: JSON.stringify({ query: insightQuery, level: insightLevel, include_charts: true })
      });
      setAiInsights(data);
    } catch (error) {
      toast.error('Failed to get insights');
    } finally {
      setLoadingInsight(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="w-12 h-12 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  // Prepare chart data
  const incomeChartData = Object.entries(report?.income?.categories || {}).map(([name, value]) => ({ name, value }));
  const expenseChartData = Object.entries(report?.expenses?.categories || {}).map(([name, value]) => ({ name, value }));
  const monthlyData = chartsData?.monthly_data || [];

  return (
    <div className="p-4 lg:p-8 space-y-6" data-testid="reports-page">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Reports & Analytics</h1>
          <p className="text-muted-foreground">Financial statements, charts, and AI insights</p>
        </div>
        <button onClick={handleExportPDF} className="btn-primary px-4 py-2 rounded-lg inline-flex items-center gap-2" data-testid="export-pdf-btn">
          <Download className="w-4 h-4" />
          Export PDF Report
        </button>
      </div>

      {/* Charts Section */}
      {monthlyData.length > 0 && (
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Revenue vs Expenses Line Chart */}
          <div className="glass rounded-2xl p-6">
            <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-emerald-500" />
              Revenue vs Expenses Trend
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={monthlyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={theme === 'dark' ? '#374151' : '#e5e7eb'} />
                  <XAxis dataKey="month" tick={{ fill: theme === 'dark' ? '#9ca3af' : '#6b7280', fontSize: 12 }} />
                  <YAxis tick={{ fill: theme === 'dark' ? '#9ca3af' : '#6b7280', fontSize: 12 }} tickFormatter={(v) => `₦${(v/1000).toFixed(0)}k`} />
                  <Tooltip 
                    contentStyle={{ background: theme === 'dark' ? '#1f2937' : '#fff', border: '1px solid #374151', borderRadius: '8px' }}
                    formatter={(value) => [`₦${value.toLocaleString()}`, '']}
                  />
                  <Legend />
                  <Line type="monotone" dataKey="income" stroke="#10b981" strokeWidth={2} dot={{ fill: '#10b981' }} name="Revenue" />
                  <Line type="monotone" dataKey="expense" stroke="#ef4444" strokeWidth={2} dot={{ fill: '#ef4444' }} name="Expenses" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Profit Trend Bar Chart */}
          <div className="glass rounded-2xl p-6">
            <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-emerald-500" />
              Monthly Profit
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={monthlyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={theme === 'dark' ? '#374151' : '#e5e7eb'} />
                  <XAxis dataKey="month" tick={{ fill: theme === 'dark' ? '#9ca3af' : '#6b7280', fontSize: 12 }} />
                  <YAxis tick={{ fill: theme === 'dark' ? '#9ca3af' : '#6b7280', fontSize: 12 }} tickFormatter={(v) => `₦${(v/1000).toFixed(0)}k`} />
                  <Tooltip 
                    contentStyle={{ background: theme === 'dark' ? '#1f2937' : '#fff', border: '1px solid #374151', borderRadius: '8px' }}
                    formatter={(value) => [`₦${value.toLocaleString()}`, 'Profit']}
                  />
                  <Bar dataKey="profit" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* Category Pie Charts */}
      {(incomeChartData.length > 0 || expenseChartData.length > 0) && (
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Income by Category */}
          {incomeChartData.length > 0 && (
            <div className="glass rounded-2xl p-6">
              <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
                <PieChart className="w-5 h-5 text-blue-500" />
                Revenue by Category
              </h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <RechartsPie>
                    <Pie
                      data={incomeChartData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="value"
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    >
                      {incomeChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => `₦${value.toLocaleString()}`} />
                  </RechartsPie>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Expenses by Category */}
          {expenseChartData.length > 0 && (
            <div className="glass rounded-2xl p-6">
              <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
                <PieChart className="w-5 h-5 text-red-500" />
                Expenses by Category
              </h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <RechartsPie>
                    <Pie
                      data={expenseChartData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="value"
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    >
                      {expenseChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={CHART_COLORS[(index + 4) % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => `₦${value.toLocaleString()}`} />
                  </RechartsPie>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>
      )}

      {/* AI Insights Section */}
      <div className="glass rounded-2xl p-6">
        <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-purple-500" />
          AI-Powered Insights
        </h3>
        
        {/* Level Selector */}
        <div className="flex flex-wrap gap-2 mb-4">
          {[
            { value: 'basic', label: 'Basic', desc: 'Quick summary' },
            { value: 'standard', label: 'Standard', desc: 'Detailed analysis' },
            { value: 'premium', label: 'Premium', desc: 'Full report' }
          ].map((level) => (
            <button
              key={level.value}
              onClick={() => setInsightLevel(level.value)}
              className={`px-4 py-2 rounded-lg text-sm transition-all ${
                insightLevel === level.value 
                  ? 'bg-purple-500 text-white' 
                  : 'bg-secondary/50 text-muted-foreground hover:bg-secondary'
              }`}
            >
              {level.label}
            </button>
          ))}
        </div>

        {/* Query Input */}
        <div className="flex gap-3 mb-6">
          <input
            type="text"
            value={insightQuery}
            onChange={(e) => setInsightQuery(e.target.value)}
            placeholder="Ask about your finances... e.g., 'How can I reduce expenses?' or 'What's my tax situation?'"
            className="flex-1 bg-secondary/50 border border-border rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-purple-500"
            onKeyPress={(e) => e.key === 'Enter' && handleGetInsights()}
          />
          <button 
            onClick={handleGetInsights}
            disabled={loadingInsight}
            className="bg-purple-500 hover:bg-purple-600 text-white px-6 py-3 rounded-xl font-medium flex items-center gap-2 disabled:opacity-50"
          >
            {loadingInsight ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            {loadingInsight ? 'Analyzing...' : 'Get Insights'}
          </button>
        </div>

        {/* AI Response */}
        {aiInsights && (
          <div className="space-y-4 animate-fade-in">
            {/* Metrics */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-4 bg-emerald-500/10 rounded-xl">
                <p className="text-xs text-muted-foreground">Revenue</p>
                <p className="text-lg font-bold text-emerald-500">{formatCurrency(aiInsights.metrics?.income || 0)}</p>
              </div>
              <div className="p-4 bg-red-500/10 rounded-xl">
                <p className="text-xs text-muted-foreground">Expenses</p>
                <p className="text-lg font-bold text-red-500">{formatCurrency(aiInsights.metrics?.expenses || 0)}</p>
              </div>
              <div className="p-4 bg-blue-500/10 rounded-xl">
                <p className="text-xs text-muted-foreground">Profit</p>
                <p className="text-lg font-bold text-blue-500">{formatCurrency(aiInsights.metrics?.profit || 0)}</p>
              </div>
              <div className="p-4 bg-purple-500/10 rounded-xl">
                <p className="text-xs text-muted-foreground">Profit Margin</p>
                <p className="text-lg font-bold text-purple-500">{aiInsights.metrics?.profit_margin || 0}%</p>
              </div>
            </div>

            {/* AI Analysis */}
            <div className="p-4 bg-purple-500/10 border border-purple-500/20 rounded-xl">
              <div className="flex items-start gap-3">
                <Sparkles className="w-5 h-5 text-purple-500 flex-shrink-0 mt-0.5" />
                <div className="prose prose-sm max-w-none">
                  <p className="text-foreground whitespace-pre-wrap">{aiInsights.insight}</p>
                </div>
              </div>
            </div>

            {/* Chart Recommendations */}
            {aiInsights.chart_recommendations?.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {aiInsights.chart_recommendations.map((rec, i) => (
                  <div key={i} className="px-3 py-2 bg-secondary/50 rounded-lg text-sm flex items-center gap-2">
                    {rec.type === 'line' && <TrendingUp className="w-4 h-4 text-emerald-500" />}
                    {rec.type === 'bar' && <BarChart3 className="w-4 h-4 text-blue-500" />}
                    {rec.type === 'pie' && <PieChart className="w-4 h-4 text-purple-500" />}
                    <span>{rec.title}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Income Statement */}
      <div className="glass rounded-2xl p-6">
        <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
          <FileText className="w-5 h-5 text-emerald-500" />
          Income Statement - {report?.business_name}
        </h3>

        <div className="space-y-6">
          {/* Income */}
          <div>
            <h4 className="font-medium text-emerald-500 mb-3">Revenue</h4>
            <div className="space-y-2">
              {Object.entries(report?.income?.categories || {}).map(([category, amount]) => (
                <div key={category} className="flex justify-between p-3 bg-secondary/30 rounded-lg">
                  <span>{category}</span>
                  <span className="font-medium">{formatCurrency(amount)}</span>
                </div>
              ))}
              <div className="flex justify-between p-3 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                <span className="font-semibold">Total Revenue</span>
                <span className="font-bold text-emerald-500">{formatCurrency(report?.income?.total || 0)}</span>
              </div>
            </div>
          </div>

          {/* Expenses */}
          <div>
            <h4 className="font-medium text-red-500 mb-3">Expenses</h4>
            <div className="space-y-2">
              {Object.entries(report?.expenses?.categories || {}).map(([category, amount]) => (
                <div key={category} className="flex justify-between p-3 bg-secondary/30 rounded-lg">
                  <span>{category}</span>
                  <span className="font-medium">{formatCurrency(amount)}</span>
                </div>
              ))}
              <div className="flex justify-between p-3 bg-red-500/10 rounded-lg border border-red-500/20">
                <span className="font-semibold">Total Expenses</span>
                <span className="font-bold text-red-500">{formatCurrency(report?.expenses?.total || 0)}</span>
              </div>
            </div>
          </div>

          {/* Summary */}
          <div className="border-t border-border pt-4 space-y-3">
            <div className="flex justify-between p-3 bg-secondary/30 rounded-lg">
              <span>Gross Profit</span>
              <span className="font-semibold">{formatCurrency(report?.gross_profit || 0)}</span>
            </div>
            <div className="flex justify-between p-3 bg-secondary/30 rounded-lg">
              <span>Tax Provisions</span>
              <span className="font-semibold text-orange-500">-{formatCurrency(report?.tax_provisions?.total || 0)}</span>
            </div>
            <div className="flex justify-between p-4 bg-emerald-500/10 rounded-xl border-2 border-emerald-500/30">
              <span className="font-bold text-lg">Net Profit</span>
              <span className="font-bold text-lg text-emerald-500">{formatCurrency(report?.net_profit || 0)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============== SETTINGS PAGE ==============
function SettingsPage() {
  const { user, business, checkAuth } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [mfaStatus, setMfaStatus] = useState(null);
  const [showMfaSetup, setShowMfaSetup] = useState(false);

  useEffect(() => {
    fetchMfaStatus();
  }, []);

  const fetchMfaStatus = async () => {
    try {
      const status = await api('/api/mfa/status');
      setMfaStatus(status);
    } catch {}
  };

  return (
    <div className="p-4 lg:p-8 space-y-6" data-testid="settings-page">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground">Manage your account and preferences</p>
      </div>

      {/* Profile */}
      <div className="glass rounded-2xl p-6">
        <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
          <User className="w-5 h-5 text-emerald-500" />
          Profile
        </h3>
        <div className="flex items-center gap-4 mb-4">
          {user?.picture && <img src={user.picture} alt="" className="w-16 h-16 rounded-full" />}
          <div>
            <p className="font-semibold text-lg">{user?.name}</p>
            <p className="text-muted-foreground">{user?.email}</p>
          </div>
        </div>
      </div>

      {/* Business Info */}
      {business && (
        <div className="glass rounded-2xl p-6">
          <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
            <Building2 className="w-5 h-5 text-emerald-500" />
            Business
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between p-3 bg-secondary/30 rounded-lg">
              <span className="text-muted-foreground">Business Name</span>
              <span className="font-medium">{business.business_name}</span>
            </div>
            <div className="flex justify-between p-3 bg-secondary/30 rounded-lg">
              <span className="text-muted-foreground">Type</span>
              <span className="font-medium">{business.business_type}</span>
            </div>
            <div className="flex justify-between p-3 bg-secondary/30 rounded-lg">
              <span className="text-muted-foreground">Industry</span>
              <span className="font-medium">{business.industry}</span>
            </div>
            {business.tin && (
              <div className="flex justify-between p-3 bg-secondary/30 rounded-lg">
                <span className="text-muted-foreground">TIN</span>
                <span className="font-mono">{business.tin}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Appearance */}
      <div className="glass rounded-2xl p-6">
        <h3 className="font-semibold text-lg mb-4">Appearance</h3>
        <div className="flex items-center justify-between p-4 bg-secondary/30 rounded-xl">
          <div className="flex items-center gap-3">
            {theme === 'dark' ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
            <span>Theme</span>
          </div>
          <button onClick={toggleTheme} className="px-4 py-2 bg-secondary rounded-lg text-sm font-medium">
            {theme === 'dark' ? 'Dark' : 'Light'}
          </button>
        </div>
      </div>

      {/* Security */}
      <div className="glass rounded-2xl p-6">
        <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
          <Shield className="w-5 h-5 text-emerald-500" />
          Security
        </h3>
        <div className="flex items-center justify-between p-4 bg-secondary/30 rounded-xl">
          <div>
            <p className="font-medium">Two-Factor Authentication</p>
            <p className="text-sm text-muted-foreground">{mfaStatus?.mfa_enabled ? 'Enabled - Your account is protected' : 'Add extra security to your account'}</p>
          </div>
          {!mfaStatus?.mfa_enabled ? (
            <button onClick={() => setShowMfaSetup(true)} className="btn-primary px-4 py-2 rounded-lg text-sm" data-testid="enable-mfa-btn">
              Enable
            </button>
          ) : (
            <span className="px-3 py-1 bg-emerald-500/10 text-emerald-500 rounded-full text-sm font-medium">Active</span>
          )}
        </div>
      </div>

      {/* MFA Setup Modal */}
      {showMfaSetup && <MFASetupModal onClose={() => { setShowMfaSetup(false); fetchMfaStatus(); checkAuth(); }} />}
    </div>
  );
}

// ============== MFA SETUP MODAL ==============
function MFASetupModal({ onClose }) {
  const [step, setStep] = useState(1);
  const [setupData, setSetupData] = useState(null);
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [backupCodes, setBackupCodes] = useState([]);

  useEffect(() => {
    initSetup();
    const handleEscape = (e) => { if (e.key === 'Escape' && step === 1) onClose(); };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [step, onClose]);

  const initSetup = async () => {
    try {
      const data = await api('/api/mfa/totp/setup', { method: 'POST' });
      setSetupData(data);
    } catch (error) {
      toast.error('Failed to initialize setup');
      onClose();
    }
  };

  const handleVerify = async (e) => {
    e.preventDefault();
    if (code.length !== 6) {
      toast.error('Please enter a 6-digit code');
      return;
    }

    setLoading(true);
    try {
      const result = await api('/api/mfa/totp/verify', { method: 'POST', body: JSON.stringify({ code }) });
      setBackupCodes(result.backup_codes);
      toast.success('MFA enabled successfully!');
      setStep(2);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-card border border-border rounded-3xl w-full max-w-md max-h-[90vh] overflow-y-auto animate-fade-in">
        <div className="p-6">
          {step === 1 ? (
            <>
              <div className="text-center mb-6">
                <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 flex items-center justify-center mx-auto mb-4">
                  <Smartphone className="w-8 h-8 text-emerald-500" />
                </div>
                <h2 className="text-xl font-bold mb-2">Setup Authenticator</h2>
                <p className="text-sm text-muted-foreground">Scan with Google Authenticator or Authy</p>
              </div>

              {setupData?.qr_code && (
                <div className="bg-white p-4 rounded-xl mb-6 mx-auto w-fit">
                  <img src={setupData.qr_code} alt="QR Code" className="w-48 h-48" />
                </div>
              )}

              <form onSubmit={handleVerify}>
                <p className="text-sm text-muted-foreground mb-2">Enter the 6-digit code:</p>
                <input
                  type="text"
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="000000"
                  className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3 text-center text-xl font-mono tracking-widest focus:outline-none focus:ring-2 focus:ring-emerald-500 mb-4"
                />
                <div className="flex gap-3">
                  <button type="button" onClick={onClose} className="flex-1 bg-secondary hover:bg-secondary/80 py-3 rounded-xl font-medium">Cancel</button>
                  <button type="submit" disabled={loading || code.length !== 6} className="flex-1 btn-primary py-3 rounded-xl font-medium disabled:opacity-50">
                    {loading ? 'Verifying...' : 'Enable MFA'}
                  </button>
                </div>
              </form>
            </>
          ) : (
            <>
              <div className="text-center mb-6">
                <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 flex items-center justify-center mx-auto mb-4">
                  <Key className="w-8 h-8 text-emerald-500" />
                </div>
                <h2 className="text-xl font-bold mb-2">Save Backup Codes</h2>
                <p className="text-sm text-muted-foreground">Store these codes securely</p>
              </div>

              <div className="bg-secondary/30 rounded-xl p-4 mb-6">
                <div className="grid grid-cols-2 gap-2">
                  {backupCodes.map((code, i) => (
                    <div key={i} className="font-mono text-sm bg-secondary/50 rounded-lg px-3 py-2 text-center">{code}</div>
                  ))}
                </div>
              </div>

              <button
                onClick={() => { navigator.clipboard.writeText(backupCodes.join('\n')); toast.success('Copied!'); }}
                className="w-full bg-secondary hover:bg-secondary/80 py-3 rounded-xl font-medium mb-3 flex items-center justify-center gap-2"
              >
                <Copy className="w-4 h-4" /> Copy All Codes
              </button>
              <button onClick={onClose} className="w-full btn-primary py-3 rounded-xl font-medium">Done</button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ============== SUBSCRIPTION PAGE ==============
function SubscriptionPage() {
  const [plans, setPlans] = useState([]);
  const [currentSubscription, setCurrentSubscription] = useState(null);
  const [loading, setLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState(null);
  const [billingCycle, setBillingCycle] = useState('monthly');
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    fetchPlansAndSubscription();
    handleReturnFromStripe();
  }, []);

  const fetchPlansAndSubscription = async () => {
    setLoading(true);
    try {
      const [plansData, subData] = await Promise.all([
        api('/api/subscriptions/plans'),
        api('/api/subscriptions/current')
      ]);
      setPlans(plansData.plans);
      setCurrentSubscription(subData);
    } catch (error) {
      console.error('Failed to fetch subscription data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleReturnFromStripe = async () => {
    const params = new URLSearchParams(location.search);
    const sessionId = params.get('session_id');
    const status = params.get('status');

    if (sessionId && status === 'success') {
      // Poll for payment status
      let attempts = 0;
      const maxAttempts = 10;
      
      const checkStatus = async () => {
        try {
          const result = await api(`/api/subscriptions/checkout/status/${sessionId}`);
          if (result.payment_status === 'paid' || result.status === 'complete') {
            toast.success('Payment successful! Your subscription has been activated.');
            setCurrentSubscription(result.subscription || await api('/api/subscriptions/current'));
            navigate('/subscription', { replace: true });
            return true;
          }
        } catch (error) {
          console.error('Status check failed:', error);
        }
        return false;
      };

      const pollStatus = async () => {
        while (attempts < maxAttempts) {
          const success = await checkStatus();
          if (success) return;
          attempts++;
          await new Promise(r => setTimeout(r, 2000));
        }
        toast.error('Could not verify payment. Please refresh the page.');
      };

      pollStatus();
    } else if (status === 'cancelled') {
      toast.info('Checkout was cancelled');
      navigate('/subscription', { replace: true });
    }
  };

  const handleSubscribe = async (tier) => {
    if (tier === 'free') return;
    
    setCheckoutLoading(tier);
    try {
      const result = await api('/api/subscriptions/checkout', {
        method: 'POST',
        body: JSON.stringify({
          tier,
          billing_cycle: billingCycle,
          origin_url: window.location.origin
        })
      });
      
      if (result.checkout_url) {
        window.location.href = result.checkout_url;
      }
    } catch (error) {
      toast.error(error.message || 'Failed to create checkout session');
    } finally {
      setCheckoutLoading(null);
    }
  };

  const handleCancelSubscription = async () => {
    if (!window.confirm('Are you sure you want to cancel your subscription? You will lose access to premium features at the end of your billing period.')) {
      return;
    }
    
    try {
      await api('/api/subscriptions/cancel', { method: 'POST' });
      toast.success('Subscription cancelled. You will retain access until the end of your billing period.');
      fetchPlansAndSubscription();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const getTierIcon = (tier) => {
    switch (tier) {
      case 'free': return <Zap className="w-6 h-6" />;
      case 'starter': return <Star className="w-6 h-6" />;
      case 'business': return <Crown className="w-6 h-6" />;
      case 'enterprise': return <Users className="w-6 h-6" />;
      default: return <Zap className="w-6 h-6" />;
    }
  };

  const getTierColor = (tier, highlight) => {
    if (highlight) return 'border-emerald-500 bg-emerald-500/5';
    switch (tier) {
      case 'free': return 'border-border';
      case 'starter': return 'border-blue-500/30';
      case 'business': return 'border-emerald-500';
      case 'enterprise': return 'border-purple-500/30';
      default: return 'border-border';
    }
  };

  const getButtonStyle = (tier, isCurrentTier, highlight) => {
    if (isCurrentTier) return 'bg-secondary text-muted-foreground cursor-not-allowed';
    if (highlight) return 'btn-primary';
    if (tier === 'enterprise') return 'bg-purple-500 hover:bg-purple-600 text-white';
    return 'bg-secondary hover:bg-secondary/80';
  };

  const featureLabels = {
    transactions_per_month: 'Transactions/month',
    ai_insights: 'AI Insights',
    receipt_ocr: 'Receipt OCR',
    pdf_reports: 'PDF Reports',
    csv_export: 'CSV Export',
    priority_support: 'Priority Support',
    multi_user: 'Multi-user Access',
    custom_categories: 'Custom Categories'
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="w-12 h-12 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-4 lg:p-8 space-y-8" data-testid="subscription-page">
      {/* Header */}
      <div className="text-center max-w-2xl mx-auto">
        <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 flex items-center justify-center mx-auto mb-4">
          <Crown className="w-8 h-8 text-emerald-500" />
        </div>
        <h1 className="text-3xl font-bold mb-2">Choose Your Plan</h1>
        <p className="text-muted-foreground">
          Unlock powerful features to grow your business with the right subscription tier.
        </p>
      </div>

      {/* Current Subscription Banner */}
      {currentSubscription && currentSubscription.tier !== 'free' && (
        <div className="glass rounded-2xl p-6 max-w-4xl mx-auto" data-testid="current-subscription-banner">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                currentSubscription.tier === 'business' ? 'bg-emerald-500/10 text-emerald-500' :
                currentSubscription.tier === 'enterprise' ? 'bg-purple-500/10 text-purple-500' :
                'bg-blue-500/10 text-blue-500'
              }`}>
                {getTierIcon(currentSubscription.tier)}
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Current Plan</p>
                <p className="text-xl font-bold">{currentSubscription.tier_name}</p>
                {currentSubscription.current_period_end && (
                  <p className="text-xs text-muted-foreground">
                    {currentSubscription.status === 'cancelling' ? 'Cancels' : 'Renews'} on {new Date(currentSubscription.current_period_end).toLocaleDateString()}
                  </p>
                )}
              </div>
            </div>
            {currentSubscription.status !== 'cancelling' && currentSubscription.tier !== 'free' && (
              <button
                onClick={handleCancelSubscription}
                className="text-sm text-red-500 hover:text-red-400 transition-colors"
                data-testid="cancel-subscription-btn"
              >
                Cancel Subscription
              </button>
            )}
          </div>
        </div>
      )}

      {/* Billing Toggle */}
      <div className="flex items-center justify-center gap-4">
        <span className={`text-sm ${billingCycle === 'monthly' ? 'text-foreground font-medium' : 'text-muted-foreground'}`}>Monthly</span>
        <button
          onClick={() => setBillingCycle(billingCycle === 'monthly' ? 'yearly' : 'monthly')}
          className={`relative w-14 h-7 rounded-full transition-colors ${billingCycle === 'yearly' ? 'bg-emerald-500' : 'bg-secondary'}`}
          data-testid="billing-cycle-toggle"
        >
          <div className={`absolute top-1 w-5 h-5 bg-white rounded-full transition-transform ${billingCycle === 'yearly' ? 'translate-x-8' : 'translate-x-1'}`} />
        </button>
        <span className={`text-sm ${billingCycle === 'yearly' ? 'text-foreground font-medium' : 'text-muted-foreground'}`}>
          Yearly <span className="text-emerald-500 text-xs">(Save 17%)</span>
        </span>
      </div>

      {/* Pricing Cards */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-7xl mx-auto">
        {plans.map((plan) => {
          const isCurrentTier = currentSubscription?.tier === plan.tier;
          const price = billingCycle === 'yearly' ? plan.price_yearly : plan.price_monthly;
          
          return (
            <div
              key={plan.tier}
              className={`glass rounded-2xl overflow-hidden border-2 transition-all hover:scale-[1.02] ${getTierColor(plan.tier, plan.highlight)} ${plan.highlight ? 'ring-2 ring-emerald-500/20' : ''}`}
              data-testid={`plan-card-${plan.tier}`}
            >
              {plan.highlight && (
                <div className="bg-emerald-500 text-white text-center py-2 text-sm font-medium">
                  Most Popular
                </div>
              )}
              
              <div className="p-6">
                {/* Plan Header */}
                <div className="flex items-center gap-3 mb-4">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                    plan.tier === 'free' ? 'bg-secondary text-muted-foreground' :
                    plan.tier === 'starter' ? 'bg-blue-500/10 text-blue-500' :
                    plan.tier === 'business' ? 'bg-emerald-500/10 text-emerald-500' :
                    'bg-purple-500/10 text-purple-500'
                  }`}>
                    {getTierIcon(plan.tier)}
                  </div>
                  <div>
                    <h3 className="font-bold text-lg">{plan.name}</h3>
                    <p className="text-xs text-muted-foreground">{plan.description}</p>
                  </div>
                </div>

                {/* Price */}
                <div className="mb-6">
                  <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-bold">
                      {price === 0 ? 'Free' : formatCurrency(price)}
                    </span>
                    {price > 0 && (
                      <span className="text-muted-foreground text-sm">/{billingCycle === 'yearly' ? 'year' : 'month'}</span>
                    )}
                  </div>
                  {billingCycle === 'yearly' && price > 0 && (
                    <p className="text-xs text-muted-foreground mt-1">
                      (₦{Math.round(price / 12).toLocaleString()}/month)
                    </p>
                  )}
                </div>

                {/* Features */}
                <ul className="space-y-3 mb-6">
                  {Object.entries(plan.features).map(([feature, value]) => (
                    <li key={feature} className="flex items-center gap-2 text-sm">
                      {value === true || value === -1 || value > 0 ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                      ) : (
                        <X className="w-4 h-4 text-muted-foreground shrink-0" />
                      )}
                      <span className={value ? '' : 'text-muted-foreground'}>
                        {feature === 'transactions_per_month' 
                          ? value === -1 ? 'Unlimited transactions' : `${value} ${featureLabels[feature]}`
                          : featureLabels[feature]}
                      </span>
                    </li>
                  ))}
                </ul>

                {/* CTA Button */}
                <button
                  onClick={() => handleSubscribe(plan.tier)}
                  disabled={isCurrentTier || checkoutLoading === plan.tier || plan.tier === 'free'}
                  className={`w-full py-3 rounded-xl font-medium transition-all flex items-center justify-center gap-2 ${getButtonStyle(plan.tier, isCurrentTier, plan.highlight)}`}
                  data-testid={`subscribe-btn-${plan.tier}`}
                >
                  {checkoutLoading === plan.tier ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Processing...
                    </>
                  ) : isCurrentTier ? (
                    <>
                      <Check className="w-4 h-4" />
                      Current Plan
                    </>
                  ) : plan.tier === 'free' ? (
                    'Free Forever'
                  ) : (
                    <>
                      <CreditCard className="w-4 h-4" />
                      {currentSubscription?.tier === 'free' ? 'Subscribe' : 'Upgrade'}
                    </>
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* FAQ Section */}
      <div className="max-w-3xl mx-auto mt-12">
        <h2 className="text-xl font-bold text-center mb-6">Frequently Asked Questions</h2>
        <div className="space-y-4">
          <div className="glass rounded-xl p-4">
            <h3 className="font-medium mb-2">Can I upgrade or downgrade anytime?</h3>
            <p className="text-sm text-muted-foreground">Yes! You can upgrade to a higher tier at any time. Downgrades take effect at the end of your current billing period.</p>
          </div>
          <div className="glass rounded-xl p-4">
            <h3 className="font-medium mb-2">What payment methods do you accept?</h3>
            <p className="text-sm text-muted-foreground">We accept all major credit and debit cards through our secure Stripe payment system.</p>
          </div>
          <div className="glass rounded-xl p-4">
            <h3 className="font-medium mb-2">Is there a free trial?</h3>
            <p className="text-sm text-muted-foreground">Our Free tier is always available with basic features. Upgrade when you are ready to unlock more powerful tools.</p>
          </div>
          <div className="glass rounded-xl p-4">
            <h3 className="font-medium mb-2">What happens if I cancel?</h3>
            <p className="text-sm text-muted-foreground">You will retain access to your paid features until the end of your billing period, then your account will revert to the Free tier.</p>
          </div>
        </div>
      </div>

      {/* Trust Badges */}
      <div className="flex flex-wrap items-center justify-center gap-6 text-muted-foreground text-sm pt-8">
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-emerald-500" />
          <span>Secure Payment</span>
        </div>
        <div className="flex items-center gap-2">
          <RefreshCw className="w-4 h-4 text-emerald-500" />
          <span>Cancel Anytime</span>
        </div>
        <div className="flex items-center gap-2">
          <CreditCard className="w-4 h-4 text-emerald-500" />
          <span>Powered by Stripe</span>
        </div>
      </div>
    </div>
  );
}

// ============== PROTECTED ROUTE ==============
function ProtectedRoute({ children }) {
  const { user, loading, mfaRequired, business } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && !user) {
      navigate('/');
    } else if (!loading && mfaRequired && location.pathname !== '/mfa-verify') {
      navigate('/mfa-verify');
    }
  }, [user, loading, mfaRequired, navigate, location.pathname]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) return null;
  if (mfaRequired && location.pathname !== '/mfa-verify') return null;

  return <DashboardLayout>{children}</DashboardLayout>;
}

// ============== APP ROUTER ==============
function AppRouter() {
  const location = useLocation();

  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/mfa-verify" element={<MFAVerifyPage />} />
      <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      <Route path="/transactions" element={<ProtectedRoute><TransactionsPage /></ProtectedRoute>} />
      <Route path="/tax" element={<ProtectedRoute><TaxPage /></ProtectedRoute>} />
      <Route path="/reports" element={<ProtectedRoute><ReportsPage /></ProtectedRoute>} />
      <Route path="/subscription" element={<ProtectedRoute><SubscriptionPage /></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

// ============== MAIN APP ==============
function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <SubscriptionProvider>
            <Toaster 
              position="top-center" 
              toastOptions={{
                style: { background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', color: 'hsl(var(--foreground))' },
              }}
            />
            <AppRouter />
          </SubscriptionProvider>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;
