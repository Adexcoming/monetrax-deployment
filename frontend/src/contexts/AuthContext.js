import React, { useState, useEffect, createContext, useContext } from 'react';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

// API Helper
export const api = async (endpoint, options = {}) => {
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

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [mfaRequired, setMfaRequired] = useState(false);
  const [business, setBusiness] = useState(null);

  const checkAuth = async () => {
    try {
      const userData = await api('/api/auth/me');
      setUser(userData);
      setMfaRequired(userData.mfa_enabled && !userData.mfa_verified);
      
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

export default AuthContext;
