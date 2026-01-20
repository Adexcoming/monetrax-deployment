import React, { useState, useEffect } from 'react';
import { useAuth, api } from '../../contexts/AuthContext';
import { useSubscription } from '../../contexts/SubscriptionContext';
import { useTheme } from '../../contexts/ThemeContext';
import { toast } from 'sonner';
import { 
  Settings, Shield, Bell, User, Key, Check, X, 
  Smartphone, Mail, RefreshCw, Loader2, Crown
} from 'lucide-react';

export default function SettingsPage() {
  const { user, business, updateBusiness } = useAuth();
  const { tier, tierName, checkFeatureAccess } = useSubscription();
  const { theme } = useTheme();
  const [activeTab, setActiveTab] = useState('profile');
  const [mfaStatus, setMfaStatus] = useState(null);
  const [setupMfa, setSetupMfa] = useState(null);
  const [verifyCode, setVerifyCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [emailPrefs, setEmailPrefs] = useState({
    tax_deadline_reminders: true,
    subscription_updates: true,
    weekly_summary: false
  });
  const [savingPrefs, setSavingPrefs] = useState(false);

  useEffect(() => {
    fetchMfaStatus();
    fetchEmailPreferences();
  }, []);

  const fetchMfaStatus = async () => {
    try {
      const data = await api('/api/mfa/status');
      setMfaStatus(data);
    } catch (error) {
      console.error('Failed to fetch MFA status:', error);
    }
  };

  const fetchEmailPreferences = async () => {
    try {
      const data = await api('/api/email/preferences');
      setEmailPrefs(data);
    } catch (error) {
      console.error('Failed to fetch email preferences:', error);
    }
  };

  const handleSetupMfa = async () => {
    setLoading(true);
    try {
      const data = await api('/api/mfa/totp/setup', { method: 'POST' });
      setSetupMfa(data);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyMfa = async () => {
    if (verifyCode.length !== 6) {
      toast.error('Please enter a 6-digit code');
      return;
    }
    setLoading(true);
    try {
      await api('/api/mfa/totp/verify', {
        method: 'POST',
        body: JSON.stringify({ code: verifyCode })
      });
      toast.success('MFA enabled successfully!');
      setSetupMfa(null);
      setVerifyCode('');
      fetchMfaStatus();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDisableMfa = async () => {
    if (!window.confirm('Are you sure you want to disable MFA? This will make your account less secure.')) return;
    setLoading(true);
    try {
      await api('/api/mfa/totp/disable', { method: 'POST' });
      toast.success('MFA disabled');
      fetchMfaStatus();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveEmailPrefs = async () => {
    setSavingPrefs(true);
    try {
      await api('/api/email/preferences', {
        method: 'PUT',
        body: JSON.stringify(emailPrefs)
      });
      toast.success('Email preferences saved!');
    } catch (error) {
      toast.error(error.message);
    } finally {
      setSavingPrefs(false);
    }
  };

  const handleSendTestEmail = async () => {
    try {
      await api('/api/email/test', { method: 'POST' });
      toast.success('Test email sent! Check your inbox.');
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleSendTaxReminder = async () => {
    try {
      const result = await api('/api/email/send-tax-reminder', { method: 'POST' });
      if (result.status === 'success') {
        toast.success('Tax reminder email sent!');
      } else {
        toast.info(result.reason || 'No upcoming deadlines');
      }
    } catch (error) {
      toast.error(error.message);
    }
  };

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'notifications', label: 'Notifications', icon: Bell },
  ];

  return (
    <div className="p-4 lg:p-8 space-y-6" data-testid="settings-page">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground">Manage your account and preferences</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-border pb-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
              activeTab === tab.id ? 'bg-emerald-500/10 text-emerald-500' : 'text-muted-foreground hover:bg-secondary/50'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Profile Tab */}
      {activeTab === 'profile' && (
        <div className="space-y-6">
          <div className="glass rounded-2xl p-6">
            <h3 className="font-semibold text-lg mb-4">Account Information</h3>
            <div className="flex items-center gap-4 mb-6">
              {user?.picture && <img src={user.picture} alt="" className="w-16 h-16 rounded-full" />}
              <div>
                <p className="font-medium text-lg">{user?.name}</p>
                <p className="text-muted-foreground">{user?.email}</p>
              </div>
            </div>
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="text-sm text-muted-foreground">User ID</label>
                <p className="font-mono text-sm bg-secondary/30 rounded-lg px-3 py-2">{user?.user_id}</p>
              </div>
              <div>
                <label className="text-sm text-muted-foreground">Subscription</label>
                <div className="flex items-center gap-2">
                  <Crown className="w-4 h-4 text-emerald-500" />
                  <span className="font-medium">{tierName}</span>
                </div>
              </div>
            </div>
          </div>

          {business && (
            <div className="glass rounded-2xl p-6">
              <h3 className="font-semibold text-lg mb-4">Business Information</h3>
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-muted-foreground">Business Name</label>
                  <p className="font-medium">{business.business_name}</p>
                </div>
                <div>
                  <label className="text-sm text-muted-foreground">Business Type</label>
                  <p className="font-medium">{business.business_type}</p>
                </div>
                <div>
                  <label className="text-sm text-muted-foreground">Industry</label>
                  <p className="font-medium">{business.industry}</p>
                </div>
                <div>
                  <label className="text-sm text-muted-foreground">TIN</label>
                  <p className="font-medium">{business.tin || 'Not provided'}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Security Tab */}
      {activeTab === 'security' && (
        <div className="space-y-6">
          <div className="glass rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                  <Smartphone className="w-5 h-5 text-emerald-500" />
                </div>
                <div>
                  <h3 className="font-semibold">Two-Factor Authentication</h3>
                  <p className="text-sm text-muted-foreground">Add an extra layer of security to your account</p>
                </div>
              </div>
              {mfaStatus?.totp_enabled ? (
                <div className="flex items-center gap-2">
                  <span className="text-emerald-500 text-sm flex items-center gap-1">
                    <Check className="w-4 h-4" /> Enabled
                  </span>
                  <button onClick={handleDisableMfa} disabled={loading} className="text-red-500 text-sm hover:underline">
                    Disable
                  </button>
                </div>
              ) : (
                <button onClick={handleSetupMfa} disabled={loading} className="btn-primary px-4 py-2 rounded-lg text-sm">
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Enable MFA'}
                </button>
              )}
            </div>

            {/* MFA Setup Flow */}
            {setupMfa && (
              <div className="mt-6 pt-6 border-t border-border">
                <p className="text-sm text-muted-foreground mb-4">Scan this QR code with your authenticator app:</p>
                <div className="flex flex-col items-center gap-4">
                  <img src={setupMfa.qr_code} alt="MFA QR Code" className="w-48 h-48 rounded-xl" />
                  <div className="text-center">
                    <p className="text-xs text-muted-foreground mb-1">Or enter this code manually:</p>
                    <code className="bg-secondary/50 px-3 py-1 rounded text-sm font-mono">{setupMfa.secret}</code>
                  </div>
                  <div className="flex gap-3 items-center w-full max-w-xs">
                    <input
                      type="text"
                      value={verifyCode}
                      onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                      placeholder="Enter 6-digit code"
                      className="flex-1 bg-secondary/50 border border-border rounded-xl px-4 py-3 text-center font-mono"
                    />
                    <button onClick={handleVerifyMfa} disabled={loading} className="btn-primary px-4 py-3 rounded-xl">
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Verify'}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Notifications Tab */}
      {activeTab === 'notifications' && (
        <div className="space-y-6">
          <div className="glass rounded-2xl p-6">
            <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
              <Mail className="w-5 h-5 text-emerald-500" />
              Email Notifications
            </h3>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between py-3 border-b border-border">
                <div>
                  <p className="font-medium">Tax Deadline Reminders</p>
                  <p className="text-sm text-muted-foreground">Get notified before tax filing deadlines</p>
                </div>
                <button
                  onClick={() => setEmailPrefs({ ...emailPrefs, tax_deadline_reminders: !emailPrefs.tax_deadline_reminders })}
                  className={`relative w-12 h-6 rounded-full transition-colors ${emailPrefs.tax_deadline_reminders ? 'bg-emerald-500' : 'bg-secondary'}`}
                >
                  <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${emailPrefs.tax_deadline_reminders ? 'translate-x-7' : 'translate-x-1'}`} />
                </button>
              </div>

              <div className="flex items-center justify-between py-3 border-b border-border">
                <div>
                  <p className="font-medium">Subscription Updates</p>
                  <p className="text-sm text-muted-foreground">Billing confirmations and plan changes</p>
                </div>
                <button
                  onClick={() => setEmailPrefs({ ...emailPrefs, subscription_updates: !emailPrefs.subscription_updates })}
                  className={`relative w-12 h-6 rounded-full transition-colors ${emailPrefs.subscription_updates ? 'bg-emerald-500' : 'bg-secondary'}`}
                >
                  <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${emailPrefs.subscription_updates ? 'translate-x-7' : 'translate-x-1'}`} />
                </button>
              </div>

              <div className="flex items-center justify-between py-3">
                <div>
                  <p className="font-medium">Weekly Summary</p>
                  <p className="text-sm text-muted-foreground">Weekly digest of your financial activity</p>
                </div>
                <button
                  onClick={() => setEmailPrefs({ ...emailPrefs, weekly_summary: !emailPrefs.weekly_summary })}
                  className={`relative w-12 h-6 rounded-full transition-colors ${emailPrefs.weekly_summary ? 'bg-emerald-500' : 'bg-secondary'}`}
                >
                  <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${emailPrefs.weekly_summary ? 'translate-x-7' : 'translate-x-1'}`} />
                </button>
              </div>
            </div>

            <div className="flex gap-3 mt-6 pt-4 border-t border-border">
              <button onClick={handleSaveEmailPrefs} disabled={savingPrefs} className="btn-primary px-4 py-2 rounded-lg flex items-center gap-2">
                {savingPrefs ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                Save Preferences
              </button>
              <button onClick={handleSendTestEmail} className="bg-secondary hover:bg-secondary/80 px-4 py-2 rounded-lg flex items-center gap-2">
                <Mail className="w-4 h-4" />
                Send Test Email
              </button>
              <button onClick={handleSendTaxReminder} className="bg-secondary hover:bg-secondary/80 px-4 py-2 rounded-lg flex items-center gap-2">
                <Bell className="w-4 h-4" />
                Send Tax Reminder
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
