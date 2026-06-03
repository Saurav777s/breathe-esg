import { useState } from 'react';
import axios from 'axios';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

export default function Login() {
  const [creds, setCreds] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

//   const handleLogin = async (e) => {
//   e.preventDefault();
//   setLoading(true);
//   setError('');
//   try {
//     const res = await axios.post(
//       `${BASE_URL}/auth/token/`,
//       JSON.stringify({ username: creds.username, password: creds.password }),
//       {
//         headers: {
//           'Content-Type': 'application/json',
//           'Accept': 'application/json',
//         }
//       }
//     );
//     const { access, refresh } = res.data;
//     localStorage.setItem('access_token', access);
//     localStorage.setItem('refresh_token', refresh);
//     setTimeout(() => { window.location.replace('/dashboard'); }, 100);
//   } catch (err) {
//     console.error('Login error:', err.response?.status, err.response?.data);
//     setError('Invalid username or password');
//     setLoading(false);
//   }
// };
  const handleLogin = async (e) => {
  e.preventDefault();
  setLoading(true);
  try {
    // DEBUG — check what we're actually sending
    const debugRes = await axios.post(
      `${BASE_URL}/debug-token/`,
      JSON.stringify({ username: creds.username, password: creds.password }),
      { headers: { 'Content-Type': 'application/json' } }
    );
    console.log('DEBUG RESPONSE:', debugRes.data);
    alert(JSON.stringify(debugRes.data, null, 2));
  } catch (err) {
    console.error(err);
    alert('Debug failed: ' + err.message);
  } finally {
    setLoading(false);
  }
};

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center',
      justifyContent: 'center', background: '#f9fafb' }}>
      <div style={{ background: 'white', padding: '2rem', borderRadius: '8px',
        boxShadow: '0 1px 4px rgba(0,0,0,0.1)', width: '320px' }}>
        <h1 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '4px' }}>
          Breathe ESG
        </h1>
        <p style={{ fontSize: '13px', color: '#6b7280', marginBottom: '24px' }}>
          Emissions Data Review Platform
        </p>
        {error && (
          <div style={{ background: '#fef2f2', color: '#b91c1c', padding: '10px',
            borderRadius: '6px', fontSize: '13px', marginBottom: '16px' }}>
            {error}
          </div>
        )}
        <form onSubmit={handleLogin}>
          <div style={{ marginBottom: '12px' }}>
            <label style={{ display: 'block', fontSize: '13px',
              fontWeight: '500', marginBottom: '4px' }}>Username</label>
            <input
              style={{ width: '100%', border: '1px solid #d1d5db', borderRadius: '6px',
                padding: '8px 10px', fontSize: '14px', boxSizing: 'border-box' }}
              value={creds.username}
              onChange={e => setCreds(c => ({ ...c, username: e.target.value }))}
              autoComplete="username"
              required
            />
          </div>
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', fontSize: '13px',
              fontWeight: '500', marginBottom: '4px' }}>Password</label>
            <input
              type="password"
              style={{ width: '100%', border: '1px solid #d1d5db', borderRadius: '6px',
                padding: '8px 10px', fontSize: '14px', boxSizing: 'border-box' }}
              value={creds.password}
              onChange={e => setCreds(c => ({ ...c, password: e.target.value }))}
              autoComplete="current-password"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            style={{ width: '100%', background: '#2563eb', color: 'white',
              border: 'none', borderRadius: '6px', padding: '10px',
              fontSize: '14px', fontWeight: '500', cursor: 'pointer',
              opacity: loading ? 0.6 : 1 }}>
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>
        <p style={{ textAlign: 'center', fontSize: '12px',
          color: '#9ca3af', marginTop: '16px' }}>
          Demo: analyst / breathe2024
        </p>
      </div>
    </div>
  );
}