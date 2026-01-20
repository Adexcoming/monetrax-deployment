import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth, api } from '../../contexts/AuthContext';
import { formatCurrency } from '../../contexts/SubscriptionContext';
import { 
  Plus, TrendingUp, TrendingDown, DollarSign, Receipt, FileText, 
  Building2, Clock, Target, Lightbulb, ArrowUpRight, ArrowDownRight 
} from 'lucide-react';
import { toast } from 'sonner';

// Summary Card Component
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

// Tax Item Component
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

// Business Setup Modal
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
      const data = await api('/api/business', {
        method: 'POST',
        body: JSON.stringify(formData)
      });
      updateBusiness(data);
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
      <div className="bg-card border border-border rounded-3xl w-full max-w-lg animate-fade-in">
        <div className="p-6 border-b border-border">
          <h2 className="text-xl font-bold">Setup Your Business</h2>
          <p className="text-sm text-muted-foreground">Add your business details to get started</p>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="text-sm font-medium mb-2 block">Business Name *</label>
            <input
              type="text"
              value={formData.business_name}
              onChange={(e) => setFormData({ ...formData, business_name: e.target.value })}
              className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3"
              placeholder="Enter business name"
            />
          </div>
          <div>
            <label className="text-sm font-medium mb-2 block">Business Type</label>
            <select
              value={formData.business_type}
              onChange={(e) => setFormData({ ...formData, business_type: e.target.value })}
              className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3"
            >
              <option>Sole Proprietorship</option>
              <option>Partnership</option>
              <option>Limited Liability Company</option>
              <option>Private Limited Company</option>
            </select>
          </div>
          <div>
            <label className="text-sm font-medium mb-2 block">Industry</label>
            <select
              value={formData.industry}
              onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
              className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3"
            >
              <option>Retail</option>
              <option>Services</option>
              <option>Manufacturing</option>
              <option>Technology</option>
              <option>Food & Beverage</option>
              <option>Fashion & Beauty</option>
              <option>Transport & Logistics</option>
              <option>Other</option>
            </select>
          </div>
          <div>
            <label className="text-sm font-medium mb-2 block">TIN (Tax Identification Number)</label>
            <input
              type="text"
              value={formData.tin}
              onChange={(e) => setFormData({ ...formData, tin: e.target.value })}
              className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3"
              placeholder="Optional"
            />
          </div>
          <div className="flex gap-3 pt-4">
            <button type="button" onClick={onClose} className="flex-1 bg-secondary hover:bg-secondary/80 py-3 rounded-xl font-medium">
              Cancel
            </button>
            <button type="submit" disabled={loading} className="flex-1 btn-primary py-3 rounded-xl font-medium">
              {loading ? 'Creating...' : 'Create Business'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Main Dashboard Page
export default function DashboardPage() {
  const { user, business } = useAuth();
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
          <p className="text-muted-foreground">Here is your business overview for this month</p>
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
