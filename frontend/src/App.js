import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';

function PrivateRoute({ children }) {
  return localStorage.getItem('access_token')
    ? children
    : <Navigate to="/login" replace />;
}

function Nav() {
  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.replace('/login');
  };
  return (
    <nav style={{
      background: '#1e293b', color: 'white', padding: '0 24px',
      display: 'flex', alignItems: 'center',
      justifyContent: 'space-between', height: '52px', fontSize: '14px'
    }}>
      <span style={{ fontWeight: '600' }}>🌿 Breathe ESG</span>
      <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
        <a href="/dashboard" style={{ color: '#94a3b8', textDecoration: 'none' }}>
          Dashboard
        </a>
        <a href="/upload" style={{ color: '#94a3b8', textDecoration: 'none' }}>
          Upload
        </a>
        <button onClick={logout} style={{
          background: 'transparent', border: '1px solid #475569',
          color: '#94a3b8', padding: '4px 12px', borderRadius: '4px',
          cursor: 'pointer', fontSize: '13px'
        }}>
          Log out
        </button>
      </div>
    </nav>
  );
}

export default function App() {
  const isLoggedIn = !!localStorage.getItem('access_token');
  return (
    <BrowserRouter>
      {isLoggedIn && <Nav />}
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard" element={
          <PrivateRoute><Dashboard /></PrivateRoute>
        } />
        <Route path="/upload" element={
          <PrivateRoute><Upload /></PrivateRoute>
        } />
        <Route path="*" element={
          <Navigate to={isLoggedIn ? "/dashboard" : "/login"} replace />
        } />
      </Routes>
    </BrowserRouter>
  );
}