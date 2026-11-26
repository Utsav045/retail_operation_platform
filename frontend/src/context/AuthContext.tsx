import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';

export interface AuthUser {
  id: number;
  email: string;
  name: string;
  role: string;
}

interface AuthContextType {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem('brightleaf_auth_token');
  });

  const [user, setUser] = useState<AuthUser | null>(() => {
    const saved = localStorage.getItem('brightleaf_auth_user');
    try {
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    // If token exists, verify or refresh profile
    if (token) {
      api
        .getMe(token)
        .then((profile) => {
          setUser(profile);
          localStorage.setItem('brightleaf_auth_user', JSON.stringify(profile));
        })
        .catch(() => {
          // Token expired or invalid
          setToken(null);
          setUser(null);
          localStorage.removeItem('brightleaf_auth_token');
          localStorage.removeItem('brightleaf_auth_user');
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [token]);

  const login = async (email: string, password: string) => {
    const res = await api.login(email, password);
    setToken(res.access_token);
    setUser(res.user);
    localStorage.setItem('brightleaf_auth_token', res.access_token);
    localStorage.setItem('brightleaf_auth_user', JSON.stringify(res.user));
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('brightleaf_auth_token');
    localStorage.removeItem('brightleaf_auth_user');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token && !!user,
        login,
        logout,
        loading,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
