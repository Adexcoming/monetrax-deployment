import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { Toaster, toast } from 'sonner';
import { Shield, Key, Smartphone, Copy, Check, LogOut, Settings, User, ChevronRight, Lock, RefreshCw, AlertTriangle, Eye, EyeOff } from 'lucide-react';
import './App.css';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

// Auth Context
const AuthContext = React.createContext(null);

const useAuth = () => {
  const context = React.useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};

// API Helper
const api = async (endpoint, options = {}) => {
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || 'Request failed');
  }
  
  return response.json();
};

// Auth Provider
function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [mfaRequired, setMfaRequired] = useState(false);

  const checkAuth = async () => {
    try {
      const userData = await api('/api/auth/me');
      setUser(userData);
      setMfaRequired(userData.mfa_enabled && !userData.mfa_verified);
    } catch {
      setUser(null);
      setMfaRequired(false);
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
    try {
      await api('/api/auth/logout', { method: 'POST' });
    } catch {}
    setUser(null);
    setMfaRequired(false);
  };

  useEffect(() => {
    checkAuth();
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, mfaRequired, login, logout, completeMfa, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

// Landing Page
function LandingPage() {
  const handleLogin = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + '/dashboard';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="min-h-screen bg-background flex flex-col" data-testid="landing-page">
      {/* Hero Section */}
      <div className="flex-1 flex items-center justify-center px-4">
        <div className="max-w-2xl text-center animate-fade-in">
          <div className="mb-8 inline-flex items-center justify-center">
            <div className="relative">
              <div className="w-20 h-20 rounded-2xl bg-primary/10 flex items-center justify-center">
                <Shield className="w-10 h-10 text-primary" />
              </div>
              <div className="absolute -inset-2 rounded-2xl bg-primary/20 animate-pulse-ring" />
            </div>
          </div>
          
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold mb-6">
            <span className="gradient-text">Multi-Factor</span>
            <br />
            Authentication
          </h1>
          
          <p className="text-muted-foreground text-base sm:text-lg mb-10 max-w-lg mx-auto">
            Secure your account with Google OAuth, TOTP authenticator, and backup codes. 
            Enterprise-grade security made simple.
          </p>
          
          <button
            onClick={handleLogin}
            data-testid="login-button"
            className="group inline-flex items-center gap-3 bg-primary hover:bg-primary/90 text-primary-foreground px-8 py-4 rounded-full font-semibold text-lg transition-all duration-300 hover:scale-105 hover:shadow-lg hover:shadow-primary/25"
          >
            <svg className="w-6 h-6" viewBox="0 0 24 24">
              <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continue with Google
            <ChevronRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
          </button>
          
          {/* Features */}
          <div className="mt-16 grid grid-cols-1 sm:grid-cols-3 gap-6">
            {[
              { icon: Shield, title: 'Google OAuth', desc: 'Secure sign-in with Google' },
              { icon: Smartphone, title: 'TOTP Auth', desc: 'Authenticator app support' },
              { icon: Key, title: 'Backup Codes', desc: 'Recovery codes for emergencies' },
            ].map((feature, i) => (
              <div key={i} className="glass rounded-2xl p-6 animate-fade-in" style={{ animationDelay: `${i * 100}ms` }}>
                <feature.icon className="w-8 h-8 text-primary mb-3 mx-auto" />
                <h3 className="font-semibold text-foreground mb-1">{feature.title}</h3>
                <p className="text-sm text-muted-foreground">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
      
      {/* Footer */}
      <footer className="py-6 text-center text-sm text-muted-foreground">
        Protected by enterprise-grade security
      </footer>
    </div>
  );
}

// Auth Callback
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
        <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-muted-foreground">Authenticating...</p>
      </div>
    </div>
  );
}

// MFA Verification Page
function MFAVerifyPage() {
  const [code, setCode] = useState('');
  const [useBackup, setUseBackup] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { completeMfa, user } = useAuth();

  const handleVerify = async (e) => {
    e.preventDefault();
    if (code.length < 6) {
      toast.error('Please enter a valid code');
      return;
    }

    setLoading(true);
    try {
      const endpoint = useBackup ? '/api/mfa/backup-codes/verify' : '/api/mfa/totp/authenticate';
      const result = await api(endpoint, {
        method: 'POST',
        body: JSON.stringify({ code }),
      });

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
            <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
              <Lock className="w-8 h-8 text-primary" />
            </div>
            <h1 className="text-2xl font-bold mb-2">Two-Factor Authentication</h1>
            <p className="text-muted-foreground text-sm">
              {useBackup 
                ? 'Enter one of your backup codes' 
                : 'Enter the 6-digit code from your authenticator app'}
            </p>
          </div>

          <form onSubmit={handleVerify}>
            <div className="mb-6">
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/[^0-9A-Za-z-]/g, ''))}
                placeholder={useBackup ? "XXXX-XXXX" : "000000"}
                className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-4 text-center text-2xl font-mono tracking-widest focus:outline-none focus:ring-2 focus:ring-primary"
                maxLength={useBackup ? 9 : 6}
                autoFocus
                data-testid="mfa-code-input"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              data-testid="mfa-verify-button"
              className="w-full bg-primary hover:bg-primary/90 text-primary-foreground py-4 rounded-xl font-semibold transition-all disabled:opacity-50"
            >
              {loading ? 'Verifying...' : 'Verify'}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => {
                setUseBackup(!useBackup);
                setCode('');
              }}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
              data-testid="toggle-backup-code"
            >
              {useBackup ? 'Use authenticator app instead' : 'Use backup code instead'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Dashboard Page
function DashboardPage() {
  const { user, logout, checkAuth } = useAuth();
  const navigate = useNavigate();
  const [mfaStatus, setMfaStatus] = useState(null);
  const [showSetup, setShowSetup] = useState(false);
  const [showBackupCodes, setShowBackupCodes] = useState(false);
  const [backupCodes, setBackupCodes] = useState([]);

  useEffect(() => {
    fetchMfaStatus();
  }, []);

  const fetchMfaStatus = async () => {
    try {
      const status = await api('/api/mfa/status');
      setMfaStatus(status);
    } catch (error) {
      console.error('Failed to fetch MFA status:', error);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-background" data-testid="dashboard-page">
      {/* Header */}
      <header className="border-b border-border">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <Shield className="w-5 h-5 text-primary" />
            </div>
            <span className="font-bold text-lg">MFA Auth</span>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3">
              {user?.picture && (
                <img src={user.picture} alt="" className="w-8 h-8 rounded-full" />
              )}
              <span className="text-sm font-medium hidden sm:block">{user?.name}</span>
            </div>
            <button
              onClick={handleLogout}
              data-testid="logout-button"
              className="p-2 hover:bg-secondary rounded-lg transition-colors"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold mb-2">Security Settings</h1>
          <p className="text-muted-foreground">Manage your account security and two-factor authentication</p>
        </div>

        <div className="grid gap-6">
          {/* MFA Status Card */}
          <div className="glass rounded-2xl p-6 animate-fade-in">
            <div className="flex items-start justify-between mb-6">
              <div className="flex items-center gap-4">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${mfaStatus?.mfa_enabled ? 'bg-primary/10' : 'bg-destructive/10'}`}>
                  <Shield className={`w-6 h-6 ${mfaStatus?.mfa_enabled ? 'text-primary' : 'text-destructive'}`} />
                </div>
                <div>
                  <h2 className="font-semibold text-lg">Two-Factor Authentication</h2>
                  <p className="text-sm text-muted-foreground">
                    {mfaStatus?.mfa_enabled ? 'Your account is protected with 2FA' : 'Add an extra layer of security'}
                  </p>
                </div>
              </div>
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${mfaStatus?.mfa_enabled ? 'bg-primary/10 text-primary' : 'bg-destructive/10 text-destructive'}`}>
                {mfaStatus?.mfa_enabled ? 'Enabled' : 'Disabled'}
              </span>
            </div>

            {!mfaStatus?.mfa_enabled ? (
              <button
                onClick={() => setShowSetup(true)}
                data-testid="enable-mfa-button"
                className="w-full bg-primary hover:bg-primary/90 text-primary-foreground py-3 rounded-xl font-medium transition-all"
              >
                Enable Two-Factor Authentication
              </button>
            ) : (
              <div className="space-y-4">
                {/* TOTP Status */}
                <div className="flex items-center justify-between p-4 bg-secondary/30 rounded-xl">
                  <div className="flex items-center gap-3">
                    <Smartphone className="w-5 h-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium text-sm">Authenticator App</p>
                      <p className="text-xs text-muted-foreground">TOTP enabled</p>
                    </div>
                  </div>
                  <Check className="w-5 h-5 text-primary" />
                </div>

                {/* Backup Codes Status */}
                <div className="flex items-center justify-between p-4 bg-secondary/30 rounded-xl">
                  <div className="flex items-center gap-3">
                    <Key className="w-5 h-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium text-sm">Backup Codes</p>
                      <p className="text-xs text-muted-foreground">{mfaStatus?.backup_codes_count || 0} codes remaining</p>
                    </div>
                  </div>
                  <button
                    onClick={() => setShowBackupCodes(true)}
                    data-testid="view-backup-codes-button"
                    className="text-primary text-sm font-medium hover:underline"
                  >
                    Manage
                  </button>
                </div>

                {/* Warning if low on backup codes */}
                {mfaStatus?.backup_codes_count <= 3 && (
                  <div className="flex items-center gap-3 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-xl">
                    <AlertTriangle className="w-5 h-5 text-yellow-500" />
                    <p className="text-sm text-yellow-500">You're running low on backup codes. Consider generating new ones.</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Account Info Card */}
          <div className="glass rounded-2xl p-6 animate-fade-in" style={{ animationDelay: '100ms' }}>
            <div className="flex items-center gap-4 mb-6">
              <div className="w-12 h-12 rounded-xl bg-secondary flex items-center justify-center">
                <User className="w-6 h-6 text-muted-foreground" />
              </div>
              <div>
                <h2 className="font-semibold text-lg">Account Information</h2>
                <p className="text-sm text-muted-foreground">Your account details</p>
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-secondary/30 rounded-xl">
                <span className="text-sm text-muted-foreground">Email</span>
                <span className="font-medium text-sm">{user?.email}</span>
              </div>
              <div className="flex items-center justify-between p-4 bg-secondary/30 rounded-xl">
                <span className="text-sm text-muted-foreground">Name</span>
                <span className="font-medium text-sm">{user?.name}</span>
              </div>
              <div className="flex items-center justify-between p-4 bg-secondary/30 rounded-xl">
                <span className="text-sm text-muted-foreground">User ID</span>
                <span className="font-mono text-xs text-muted-foreground">{user?.user_id}</span>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* MFA Setup Modal */}
      {showSetup && (
        <MFASetupModal 
          onClose={() => {
            setShowSetup(false);
            fetchMfaStatus();
            checkAuth();
          }} 
          onBackupCodes={setBackupCodes}
        />
      )}

      {/* Backup Codes Modal */}
      {showBackupCodes && (
        <BackupCodesModal 
          onClose={() => setShowBackupCodes(false)}
          codes={backupCodes}
          setCodes={setBackupCodes}
        />
      )}
    </div>
  );
}

// MFA Setup Modal
function MFASetupModal({ onClose, onBackupCodes }) {
  const [step, setStep] = useState(1);
  const [setupData, setSetupData] = useState(null);
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [backupCodes, setBackupCodes] = useState([]);
  const [showSecret, setShowSecret] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    initSetup();
  }, []);

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
      const result = await api('/api/mfa/totp/verify', {
        method: 'POST',
        body: JSON.stringify({ code }),
      });

      setBackupCodes(result.backup_codes);
      onBackupCodes(result.backup_codes);
      toast.success('MFA enabled successfully!');
      setStep(2);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  const copySecret = () => {
    navigator.clipboard.writeText(setupData?.secret);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast.success('Secret copied to clipboard');
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50" data-testid="mfa-setup-modal">
      <div className="bg-card border border-border rounded-3xl w-full max-w-md max-h-[90vh] overflow-y-auto animate-fade-in">
        <div className="p-6">
          {step === 1 ? (
            <>
              <div className="text-center mb-6">
                <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
                  <Smartphone className="w-8 h-8 text-primary" />
                </div>
                <h2 className="text-xl font-bold mb-2">Setup Authenticator App</h2>
                <p className="text-sm text-muted-foreground">
                  Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.)
                </p>
              </div>

              {setupData?.qr_code && (
                <div className="bg-white p-4 rounded-xl mb-6 mx-auto w-fit">
                  <img src={setupData.qr_code} alt="QR Code" className="w-48 h-48" data-testid="qr-code" />
                </div>
              )}

              <div className="mb-6">
                <p className="text-xs text-muted-foreground mb-2 text-center">Or enter this secret manually:</p>
                <div className="flex items-center gap-2 bg-secondary/50 rounded-xl p-3">
                  <input
                    type={showSecret ? "text" : "password"}
                    value={setupData?.secret || ''}
                    readOnly
                    className="flex-1 bg-transparent font-mono text-sm focus:outline-none"
                  />
                  <button onClick={() => setShowSecret(!showSecret)} className="p-1 hover:bg-secondary rounded">
                    {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                  <button onClick={copySecret} className="p-1 hover:bg-secondary rounded">
                    {copied ? <Check className="w-4 h-4 text-primary" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <form onSubmit={handleVerify}>
                <p className="text-sm text-muted-foreground mb-2">Enter the 6-digit code from your app:</p>
                <input
                  type="text"
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="000000"
                  className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3 text-center text-xl font-mono tracking-widest focus:outline-none focus:ring-2 focus:ring-primary mb-4"
                  data-testid="totp-setup-input"
                />
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={onClose}
                    className="flex-1 bg-secondary hover:bg-secondary/80 py-3 rounded-xl font-medium transition-all"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={loading || code.length !== 6}
                    data-testid="verify-totp-button"
                    className="flex-1 bg-primary hover:bg-primary/90 text-primary-foreground py-3 rounded-xl font-medium transition-all disabled:opacity-50"
                  >
                    {loading ? 'Verifying...' : 'Enable MFA'}
                  </button>
                </div>
              </form>
            </>
          ) : (
            <>
              <div className="text-center mb-6">
                <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
                  <Key className="w-8 h-8 text-primary" />
                </div>
                <h2 className="text-xl font-bold mb-2">Save Your Backup Codes</h2>
                <p className="text-sm text-muted-foreground">
                  Store these codes securely. Each code can only be used once.
                </p>
              </div>

              <div className="bg-secondary/30 rounded-xl p-4 mb-6">
                <div className="grid grid-cols-2 gap-2">
                  {backupCodes.map((code, i) => (
                    <div key={i} className="font-mono text-sm bg-secondary/50 rounded-lg px-3 py-2 text-center">
                      {code}
                    </div>
                  ))}
                </div>
              </div>

              <button
                onClick={() => {
                  navigator.clipboard.writeText(backupCodes.join('\n'));
                  toast.success('Backup codes copied!');
                }}
                className="w-full bg-secondary hover:bg-secondary/80 py-3 rounded-xl font-medium transition-all flex items-center justify-center gap-2 mb-3"
              >
                <Copy className="w-4 h-4" />
                Copy All Codes
              </button>

              <button
                onClick={onClose}
                data-testid="finish-setup-button"
                className="w-full bg-primary hover:bg-primary/90 text-primary-foreground py-3 rounded-xl font-medium transition-all"
              >
                Done
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// Backup Codes Modal
function BackupCodesModal({ onClose, codes, setCodes }) {
  const [loading, setLoading] = useState(false);
  const [backupCodes, setBackupCodes] = useState(codes);
  const [showRegenerate, setShowRegenerate] = useState(false);

  const regenerateCodes = async () => {
    setLoading(true);
    try {
      const result = await api('/api/mfa/backup-codes/regenerate', { method: 'POST' });
      setBackupCodes(result.codes);
      setCodes(result.codes);
      toast.success('New backup codes generated!');
      setShowRegenerate(false);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50" data-testid="backup-codes-modal">
      <div className="bg-card border border-border rounded-3xl w-full max-w-md animate-fade-in">
        <div className="p-6">
          <div className="text-center mb-6">
            <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
              <Key className="w-8 h-8 text-primary" />
            </div>
            <h2 className="text-xl font-bold mb-2">Backup Codes</h2>
            <p className="text-sm text-muted-foreground">
              Use these codes if you lose access to your authenticator app
            </p>
          </div>

          {backupCodes.length > 0 ? (
            <div className="bg-secondary/30 rounded-xl p-4 mb-6">
              <div className="grid grid-cols-2 gap-2">
                {backupCodes.map((code, i) => (
                  <div key={i} className="font-mono text-sm bg-secondary/50 rounded-lg px-3 py-2 text-center">
                    {code}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground mb-6">
              <p>No backup codes to display.</p>
              <p className="text-sm">Generate new codes below.</p>
            </div>
          )}

          {showRegenerate ? (
            <div className="bg-destructive/10 border border-destructive/20 rounded-xl p-4 mb-4">
              <p className="text-sm text-destructive mb-3">
                <strong>Warning:</strong> This will invalidate all existing backup codes.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowRegenerate(false)}
                  className="flex-1 bg-secondary hover:bg-secondary/80 py-2 rounded-lg font-medium text-sm"
                >
                  Cancel
                </button>
                <button
                  onClick={regenerateCodes}
                  disabled={loading}
                  className="flex-1 bg-destructive hover:bg-destructive/90 text-destructive-foreground py-2 rounded-lg font-medium text-sm"
                >
                  {loading ? 'Generating...' : 'Confirm'}
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setShowRegenerate(true)}
              data-testid="regenerate-codes-button"
              className="w-full bg-secondary hover:bg-secondary/80 py-3 rounded-xl font-medium transition-all flex items-center justify-center gap-2 mb-3"
            >
              <RefreshCw className="w-4 h-4" />
              Generate New Codes
            </button>
          )}

          {backupCodes.length > 0 && (
            <button
              onClick={() => {
                navigator.clipboard.writeText(backupCodes.join('\n'));
                toast.success('Backup codes copied!');
              }}
              className="w-full bg-secondary hover:bg-secondary/80 py-3 rounded-xl font-medium transition-all flex items-center justify-center gap-2 mb-3"
            >
              <Copy className="w-4 h-4" />
              Copy All Codes
            </button>
          )}

          <button
            onClick={onClose}
            className="w-full bg-primary hover:bg-primary/90 text-primary-foreground py-3 rounded-xl font-medium transition-all"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// Protected Route
function ProtectedRoute({ children }) {
  const { user, loading, mfaRequired } = useAuth();
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
        <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) return null;
  if (mfaRequired && location.pathname !== '/mfa-verify') return null;

  return children;
}

// App Router
function AppRouter() {
  const location = useLocation();

  // Check for session_id in URL hash (OAuth callback)
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/mfa-verify" element={<ProtectedRoute><MFAVerifyPage /></ProtectedRoute>} />
      <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

// Main App
function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Toaster 
          position="top-center" 
          toastOptions={{
            style: {
              background: 'hsl(222.2 84% 6%)',
              border: '1px solid hsl(217.2 32.6% 17.5%)',
              color: 'hsl(210 40% 98%)',
            },
          }}
        />
        <AppRouter />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
