import React, { useState, useEffect, createContext, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth, api } from './AuthContext';
import { 
  Crown, Receipt, Camera, FileText, Sparkles, CheckCircle2 
} from 'lucide-react';

const SubscriptionContext = createContext(null);

export const useSubscription = () => {
  const context = useContext(SubscriptionContext);
  if (!context) throw new Error('useSubscription must be used within SubscriptionProvider');
  return context;
};

// Currency formatter
export const formatCurrency = (amount) => {
  return new Intl.NumberFormat('en-NG', { 
    style: 'currency', 
    currency: 'NGN', 
    minimumFractionDigits: 0,
    maximumFractionDigits: 0 
  }).format(amount);
};

export function SubscriptionProvider({ children }) {
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

// Upgrade Modal Component
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

export default SubscriptionContext;
