import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../services/api';

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await authApi.login(username, password);
      navigate('/');
    } catch {
      setError('Invalid username or password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-primary-900 flex items-center justify-center">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-white flex items-center justify-center gap-3">
            <svg className="w-8 h-8 text-accent-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            TrafficVision
          </h1>
          <p className="mt-2 text-primary-400 text-sm">AI Traffic Violation System · Sign In</p>
        </div>

        {/* Card */}
        <div className="bg-primary-800 border border-primary-700 rounded-2xl p-8 shadow-2xl">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-primary-300 mb-1.5">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoFocus
                className="w-full bg-primary-900 border border-primary-600 rounded-lg px-4 py-2.5 text-white placeholder-primary-500 focus:outline-none focus:ring-2 focus:ring-accent-indigo-500 focus:border-transparent text-sm"
                placeholder="admin"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-primary-300 mb-1.5">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full bg-primary-900 border border-primary-600 rounded-lg px-4 py-2.5 text-white placeholder-primary-500 focus:outline-none focus:ring-2 focus:ring-accent-indigo-500 focus:border-transparent text-sm"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <div className="bg-accent-critical-950/50 border border-accent-critical-700 rounded-lg px-4 py-2.5 text-accent-critical-300 text-xs">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-accent-indigo-600 hover:bg-accent-indigo-500 disabled:bg-accent-indigo-800 disabled:cursor-not-allowed text-white font-medium py-2.5 rounded-lg transition-colors text-sm"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <p className="mt-5 text-center text-xs text-primary-500">Default: admin / admin123</p>
        </div>
      </div>
    </div>
  );
}