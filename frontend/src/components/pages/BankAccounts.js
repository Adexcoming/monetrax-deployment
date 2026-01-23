import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import {
  Building2, Link2, Unlink, RefreshCw, Download, ChevronRight,
  Loader2, AlertCircle, CheckCircle2, Clock, ArrowUpRight, ArrowDownLeft,
  CreditCard, TrendingUp, Plus, X, ExternalLink, Filter, Search
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
    throw new Error(typeof error.detail === 'object' ? error.detail.message : error.detail || 'Request failed');
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

export default function BankAccounts() {
  const [status, setStatus] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [institutions, setInstitutions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [linkingAccount, setLinkingAccount] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState(null);
  const [showLinkModal, setShowLinkModal] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [statusData, accountsData, institutionsData] = await Promise.all([
        apiCall('/api/bank/status'),
        apiCall('/api/bank/accounts'),
        apiCall('/api/bank/supported-institutions')
      ]);
      setStatus(statusData);
      setAccounts(accountsData.accounts);
      setInstitutions(institutionsData.institutions);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLinkAccount = async () => {
    if (!status?.configured) {
      toast.error('Bank integration is not yet configured. Please check back later.');
      return;
    }

    if (!status?.can_link_more) {
      toast.error(`You've reached the maximum of ${status.max_accounts} linked accounts on your plan. Upgrade to link more.`);
      return;
    }

    setLinkingAccount(true);
    try {
      const result = await apiCall('/api/bank/link/initiate', {
        method: 'POST',
        body: JSON.stringify({ account_type: 'financial_data' })
      });
      
      // Open Mono Connect widget or redirect
      if (result.mono_url) {
        window.open(result.mono_url, '_blank');
        toast.info('Complete the bank linking process in the new window');
      } else {
        toast.info('Use Mono Connect widget with public key: ' + result.public_key);
      }
      
      setShowLinkModal(true);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLinkingAccount(false);
    }
  };

  const handleExchangeCode = async (code) => {
    try {
      const result = await apiCall('/api/bank/link/exchange', {
        method: 'POST',
        body: JSON.stringify({ code })
      });
      
      toast.success('Bank account linked successfully!');
      setShowLinkModal(false);
      fetchData();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleSyncAccount = async (accountId) => {
    if (!status?.can_manual_sync) {
      toast.error(`You've reached your daily sync limit of ${status.manual_syncs_limit}. Upgrade for more.`);
      return;
    }

    try {
      const result = await apiCall(`/api/bank/accounts/${accountId}/sync`, {
        method: 'POST'
      });
      
      toast.success(`Synced ${result.transactions_synced} new transactions`);
      fetchData();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleUnlinkAccount = async (accountId) => {
    if (!window.confirm('Are you sure you want to unlink this bank account? Your transaction history will be preserved.')) {
      return;
    }

    try {
      await apiCall(`/api/bank/accounts/${accountId}`, { method: 'DELETE' });
      toast.success('Bank account unlinked');
      fetchData();
      setSelectedAccount(null);
    } catch (error) {
      toast.error(error.message);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Building2 className="w-7 h-7 text-emerald-500" />
            Bank Accounts
          </h1>
          <p className="text-muted-foreground">
            Link your bank accounts to automatically sync transactions
          </p>
        </div>
        <button
          onClick={handleLinkAccount}
          disabled={linkingAccount || !status?.can_link_more}
          className="px-4 py-2 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white rounded-xl font-medium flex items-center gap-2 disabled:opacity-50"
        >
          {linkingAccount ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Plus className="w-4 h-4" />
          )}
          Link Bank Account
        </button>
      </div>

      {/* Status Card */}
      <div className="glass rounded-2xl p-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-secondary/30 rounded-xl">
            <p className="text-3xl font-bold text-emerald-500">{accounts.length}</p>
            <p className="text-sm text-muted-foreground">Linked Accounts</p>
            <p className="text-xs text-muted-foreground mt-1">
              {status?.max_accounts === -1 ? 'Unlimited' : `of ${status?.max_accounts}`}
            </p>
          </div>
          <div className="text-center p-4 bg-secondary/30 rounded-xl">
            <p className="text-3xl font-bold">{status?.manual_syncs_today || 0}</p>
            <p className="text-sm text-muted-foreground">Syncs Today</p>
            <p className="text-xs text-muted-foreground mt-1">
              {status?.manual_syncs_limit === -1 ? 'Unlimited' : `of ${status?.manual_syncs_limit}`}
            </p>
          </div>
          <div className="text-center p-4 bg-secondary/30 rounded-xl">
            <p className="text-lg font-semibold capitalize">{status?.sync_frequency || 'daily'}</p>
            <p className="text-sm text-muted-foreground">Auto-Sync</p>
          </div>
          <div className="text-center p-4 bg-secondary/30 rounded-xl">
            <p className="text-lg font-semibold capitalize">{status?.tier || 'free'}</p>
            <p className="text-sm text-muted-foreground">Your Plan</p>
          </div>
        </div>
      </div>

      {/* Not Configured Warning */}
      {!status?.configured && (
        <div className="glass rounded-2xl p-6 border-2 border-yellow-500/30 bg-yellow-500/5">
          <div className="flex items-start gap-4">
            <AlertCircle className="w-6 h-6 text-yellow-500 flex-shrink-0" />
            <div>
              <h3 className="font-semibold text-yellow-500">Bank Integration Coming Soon</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Bank account linking is being set up. You&apos;ll be able to automatically sync transactions from 20+ Nigerian banks including Access, GTBank, First Bank, UBA, and more.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Linked Accounts */}
      {accounts.length > 0 ? (
        <div className="grid gap-4">
          {accounts.map(account => (
            <div
              key={account.linked_account_id}
              className={`glass rounded-2xl p-6 cursor-pointer transition-all hover:ring-2 hover:ring-emerald-500/50 ${
                selectedAccount?.linked_account_id === account.linked_account_id ? 'ring-2 ring-emerald-500' : ''
              }`}
              onClick={() => setSelectedAccount(
                selectedAccount?.linked_account_id === account.linked_account_id ? null : account
              )}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                    <Building2 className="w-6 h-6 text-emerald-500" />
                  </div>
                  <div>
                    <h3 className="font-semibold">{account.institution_name}</h3>
                    <p className="text-sm text-muted-foreground">
                      {account.account_name} • ****{account.account_number}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xl font-bold">{formatCurrency(account.balance)}</p>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Clock className="w-3 h-3" />
                    {account.last_synced ? new Date(account.last_synced).toLocaleString() : 'Never synced'}
                  </div>
                </div>
              </div>

              {/* Status badges */}
              <div className="flex items-center gap-2 mt-4">
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  account.status === 'active' ? 'bg-emerald-500/10 text-emerald-500' :
                  account.status === 'reauth_required' ? 'bg-yellow-500/10 text-yellow-500' :
                  'bg-red-500/10 text-red-500'
                }`}>
                  {account.status === 'active' ? 'Connected' : 
                   account.status === 'reauth_required' ? 'Re-auth Required' : 
                   account.status}
                </span>
                <span className="px-2 py-1 bg-secondary rounded-full text-xs">
                  {account.account_type}
                </span>
              </div>

              {/* Expanded Actions */}
              {selectedAccount?.linked_account_id === account.linked_account_id && (
                <div className="mt-4 pt-4 border-t border-border flex flex-wrap gap-2">
                  <button
                    onClick={(e) => { e.stopPropagation(); handleSyncAccount(account.linked_account_id); }}
                    disabled={!status?.can_manual_sync}
                    className="px-4 py-2 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-500 rounded-lg flex items-center gap-2 disabled:opacity-50"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Sync Now
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); setSelectedAccount(account); }}
                    className="px-4 py-2 bg-secondary hover:bg-secondary/80 rounded-lg flex items-center gap-2"
                  >
                    <CreditCard className="w-4 h-4" />
                    View Transactions
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleUnlinkAccount(account.linked_account_id); }}
                    className="px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-500 rounded-lg flex items-center gap-2"
                  >
                    <Unlink className="w-4 h-4" />
                    Unlink
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="glass rounded-2xl p-12 text-center">
          <Building2 className="w-16 h-16 mx-auto mb-4 text-muted-foreground/50" />
          <h3 className="text-lg font-semibold mb-2">No Bank Accounts Linked</h3>
          <p className="text-muted-foreground mb-6">
            Link your bank account to automatically import transactions
          </p>
          <button
            onClick={handleLinkAccount}
            disabled={!status?.configured}
            className="px-6 py-3 bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-xl font-medium disabled:opacity-50"
          >
            Link Your First Account
          </button>
        </div>
      )}

      {/* Supported Banks */}
      <div className="glass rounded-2xl p-6">
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-emerald-500" />
          Supported Banks ({institutions.length})
        </h3>
        <div className="flex flex-wrap gap-3">
          {institutions.slice(0, 12).map(bank => (
            <div
              key={bank.code}
              className="px-3 py-2 bg-secondary/50 rounded-lg text-sm flex items-center gap-2"
            >
              <Building2 className="w-4 h-4 text-emerald-500" />
              {bank.name}
            </div>
          ))}
          {institutions.length > 12 && (
            <div className="px-3 py-2 bg-secondary/50 rounded-lg text-sm text-muted-foreground">
              +{institutions.length - 12} more
            </div>
          )}
        </div>
      </div>

      {/* Link Account Modal */}
      {showLinkModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="glass rounded-2xl p-6 max-w-md w-full">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Link Bank Account</h3>
              <button onClick={() => setShowLinkModal(false)} className="p-2 hover:bg-secondary rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Complete the bank linking process in the popup window. Once done, paste the authorization code below:
              </p>
              
              <input
                type="text"
                placeholder="Paste authorization code here..."
                className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && e.target.value) {
                    handleExchangeCode(e.target.value);
                  }
                }}
              />
              
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    const input = document.querySelector('input[placeholder*="authorization"]');
                    if (input?.value) handleExchangeCode(input.value);
                  }}
                  className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white py-3 rounded-xl font-medium"
                >
                  Complete Linking
                </button>
                <button
                  onClick={() => setShowLinkModal(false)}
                  className="px-6 bg-secondary hover:bg-secondary/80 py-3 rounded-xl"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Transactions Panel */}
      {selectedAccount && (
        <BankTransactionsPanel
          account={selectedAccount}
          onClose={() => setSelectedAccount(null)}
        />
      )}
    </div>
  );
}

// Bank Transactions Panel Component
function BankTransactionsPanel({ account, onClose }) {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({ type: '', imported: '' });
  const [selectedTxs, setSelectedTxs] = useState([]);
  const [importing, setImporting] = useState(false);

  useEffect(() => {
    fetchTransactions();
  }, [account.linked_account_id, filter]);

  const fetchTransactions = async () => {
    setLoading(true);
    try {
      let url = `/api/bank/accounts/${account.linked_account_id}/transactions?limit=100`;
      if (filter.type) url += `&tx_type=${filter.type}`;
      if (filter.imported !== '') url += `&imported=${filter.imported}`;
      
      const result = await apiCall(url);
      setTransactions(result.transactions);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleImportSelected = async () => {
    if (selectedTxs.length === 0) {
      toast.error('Select transactions to import');
      return;
    }

    setImporting(true);
    try {
      const result = await apiCall('/api/bank/transactions/import-bulk', {
        method: 'POST',
        body: JSON.stringify({ transaction_ids: selectedTxs })
      });
      
      toast.success(`Imported ${result.imported_count} transactions to Monetrax`);
      setSelectedTxs([]);
      fetchTransactions();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setImporting(false);
    }
  };

  const handleImportSingle = async (txId) => {
    try {
      await apiCall(`/api/bank/transactions/${txId}/import`, { method: 'POST' });
      toast.success('Transaction imported to Monetrax');
      fetchTransactions();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const toggleSelect = (txId) => {
    setSelectedTxs(prev => 
      prev.includes(txId) 
        ? prev.filter(id => id !== txId)
        : [...prev, txId]
    );
  };

  const selectAll = () => {
    const importable = transactions.filter(tx => !tx.imported_to_monetrax);
    if (selectedTxs.length === importable.length) {
      setSelectedTxs([]);
    } else {
      setSelectedTxs(importable.map(tx => tx.bank_transaction_id));
    }
  };

  return (
    <div className="glass rounded-2xl p-6 mt-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold">
            {account.institution_name} Transactions
          </h3>
          <p className="text-sm text-muted-foreground">
            ****{account.account_number}
          </p>
        </div>
        <button onClick={onClose} className="p-2 hover:bg-secondary rounded-lg">
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4 mb-4">
        <select
          value={filter.type}
          onChange={(e) => setFilter({ ...filter, type: e.target.value })}
          className="bg-secondary/50 border border-border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">All Types</option>
          <option value="credit">Credits (Income)</option>
          <option value="debit">Debits (Expenses)</option>
        </select>
        <select
          value={filter.imported}
          onChange={(e) => setFilter({ ...filter, imported: e.target.value })}
          className="bg-secondary/50 border border-border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">All Transactions</option>
          <option value="false">Not Imported</option>
          <option value="true">Already Imported</option>
        </select>
        
        {selectedTxs.length > 0 && (
          <button
            onClick={handleImportSelected}
            disabled={importing}
            className="ml-auto px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg flex items-center gap-2"
          >
            {importing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            Import {selectedTxs.length} Selected
          </button>
        )}
      </div>

      {/* Select All */}
      {transactions.some(tx => !tx.imported_to_monetrax) && (
        <div className="mb-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={selectedTxs.length === transactions.filter(tx => !tx.imported_to_monetrax).length && selectedTxs.length > 0}
              onChange={selectAll}
              className="rounded"
            />
            <span className="text-sm">Select all importable transactions</span>
          </label>
        </div>
      )}

      {/* Transactions List */}
      {loading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-emerald-500" />
        </div>
      ) : transactions.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <CreditCard className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No transactions found</p>
        </div>
      ) : (
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {transactions.map(tx => (
            <div
              key={tx.bank_transaction_id}
              className={`flex items-center gap-4 p-4 rounded-xl border transition-colors ${
                tx.imported_to_monetrax 
                  ? 'border-emerald-500/30 bg-emerald-500/5' 
                  : 'border-border hover:bg-secondary/30'
              }`}
            >
              {!tx.imported_to_monetrax && (
                <input
                  type="checkbox"
                  checked={selectedTxs.includes(tx.bank_transaction_id)}
                  onChange={() => toggleSelect(tx.bank_transaction_id)}
                  className="rounded"
                />
              )}
              
              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                tx.type === 'credit' ? 'bg-emerald-500/10' : 'bg-red-500/10'
              }`}>
                {tx.type === 'credit' ? (
                  <ArrowDownLeft className="w-5 h-5 text-emerald-500" />
                ) : (
                  <ArrowUpRight className="w-5 h-5 text-red-500" />
                )}
              </div>
              
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{tx.narration}</p>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>{tx.date}</span>
                  <span>•</span>
                  <span className="px-1.5 py-0.5 bg-secondary rounded">{tx.category}</span>
                </div>
              </div>
              
              <div className="text-right">
                <p className={`font-semibold ${tx.type === 'credit' ? 'text-emerald-500' : 'text-red-500'}`}>
                  {tx.type === 'credit' ? '+' : '-'}{formatCurrency(tx.amount)}
                </p>
                {tx.imported_to_monetrax ? (
                  <span className="text-xs text-emerald-500 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" />
                    Imported
                  </span>
                ) : (
                  <button
                    onClick={() => handleImportSingle(tx.bank_transaction_id)}
                    className="text-xs text-emerald-500 hover:underline"
                  >
                    Import
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
