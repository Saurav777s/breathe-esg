// src/pages/Dashboard.jsx
import { useEffect, useState } from 'react';
import API from '../api/client';

const SCOPE_COLORS = {
  scope1: '#ef4444',
  scope2: '#f59e0b',
  scope3: '#3b82f6',
};

const STATUS_BADGE = {
  pending_review: 'bg-yellow-100 text-yellow-800',
  flagged: 'bg-red-100 text-red-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-gray-100 text-gray-800',
  locked: 'bg-purple-100 text-purple-800',
};

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [records, setRecords] = useState([]);
  const [filters, setFilters] = useState({ status: '', scope: '', source_type: '' });
  const [selected, setSelected] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchRecords = async () => {
  setLoading(true);
  try {
    const params = Object.fromEntries(
      Object.entries(filters).filter(([, v]) => v)
    );
    const r = await API.get('/records/', { params });
    setRecords(r.data);
  } catch (err) {
    console.error('fetchRecords failed:', err.response?.status, err.response?.data);
  } finally {
    setLoading(false);
  }
};

useEffect(() => {
  // eslint-disable-next-line react-hooks/exhaustive-deps
  API.get('/dashboard/').then(r => setSummary(r.data)).catch(console.error);
  fetchRecords();
}, [filters]); // eslint-disable-line react-hooks/exhaustive-deps

 const bulkAction = async (action) => {
  try {
    await API.post('/records/bulk-review/', { ids: selected, action });
    setSelected([]);
    fetchRecords();
  } catch (err) {
    alert('Bulk action failed: ' + (err.response?.data?.error || err.message));
  }
};

const reviewRecord = async (id, action) => {
  try {
    await API.post(`/records/${id}/review/`, { action });
    fetchRecords();
  } catch (err) {
    alert('Review failed: ' + (err.response?.data?.error || err.message));
  }
};
  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Emissions Review Dashboard</h1>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Total Records', value: summary.total_records },
            { label: 'Pending Review', value: summary.pending_review, color: 'text-yellow-600' },
            { label: 'Flagged', value: summary.flagged, color: 'text-red-600' },
            { label: 'Total CO₂e (kg)', value: summary.total_co2e_kg?.toFixed(0) ?? '—' },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-white rounded-lg border p-4 shadow-sm">
              <p className="text-sm text-gray-500">{label}</p>
              <p className={`text-2xl font-bold ${color || 'text-gray-900'}`}>{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 mb-4 flex-wrap">
        {[
          { key: 'status', label: 'Status', options: ['pending_review', 'flagged', 'approved', 'rejected', 'locked'] },
          { key: 'scope', label: 'Scope', options: ['scope1', 'scope2', 'scope3'] },
          { key: 'source_type', label: 'Source', options: ['sap_fuel_procurement', 'utility_electricity', 'travel_corporate'] },
        ].map(({ key, label, options }) => (
          <select
            key={key}
            className="border rounded px-3 py-1.5 text-sm"
            value={filters[key]}
            onChange={e => setFilters(f => ({ ...f, [key]: e.target.value }))}
          >
            <option value="">All {label}s</option>
            {options.map(o => <option key={o} value={o}>{o.replace(/_/g, ' ')}</option>)}
          </select>
        ))}
      </div>

      {/* Bulk Actions */}
      {selected.length > 0 && (
        <div className="flex gap-2 mb-3 items-center bg-blue-50 p-3 rounded">
          <span className="text-sm font-medium">{selected.length} selected</span>
          <button onClick={() => bulkAction('approve')}
            className="bg-green-600 text-white px-3 py-1 rounded text-sm">
            Bulk Approve
          </button>
          <button onClick={() => bulkAction('reject')}
            className="bg-red-600 text-white px-3 py-1 rounded text-sm">
            Bulk Reject
          </button>
        </div>
      )}

      {/* Records Table */}
      <div className="bg-white rounded-lg border shadow-sm overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="p-3 text-left w-8">
                <input type="checkbox"
                  onChange={e => setSelected(e.target.checked ? records.map(r => r.id) : [])}
                />
              </th>
              {['Scope', 'Category', 'Source', 'Date', 'Value', 'CO₂e (kg)', 'Status', 'Actions'].map(h => (
                <th key={h} className="p-3 text-left font-medium text-gray-600">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={9} className="p-8 text-center text-gray-400">Loading…</td></tr>
            ) : records.map(r => (
              <tr key={r.id} className="border-b hover:bg-gray-50">
                <td className="p-3">
                  <input type="checkbox"
                    checked={selected.includes(r.id)}
                    onChange={e => setSelected(s => e.target.checked
                      ? [...s, r.id] : s.filter(x => x !== r.id)
                    )}
                  />
                </td>
                <td className="p-3">
                  <span style={{ color: SCOPE_COLORS[r.scope] }} className="font-medium">
                    {r.scope}
                  </span>
                </td>
                <td className="p-3 text-gray-600">{r.category.replace(/_/g, ' ')}</td>
                <td className="p-3 text-gray-500">{r.source_type.replace(/_/g, ' ')}</td>
                <td className="p-3">{r.activity_start}</td>
                <td className="p-3 font-mono">{parseFloat(r.activity_value).toFixed(2)} {r.activity_unit}</td>
                <td className="p-3 font-mono">{r.co2e_kg ? parseFloat(r.co2e_kg).toFixed(2) : '—'}</td>
                <td className="p-3">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_BADGE[r.status]}`}>
                    {r.status.replace(/_/g, ' ')}
                  </span>
                  {r.flag_reason && (
                    <p className="text-xs text-red-500 mt-1">{r.flag_reason}</p>
                  )}
                </td>
                <td className="p-3">
                  {['pending_review', 'flagged'].includes(r.status) && (
                    <div className="flex gap-1">
                      <button onClick={() => reviewRecord(r.id, 'approve')}
                        className="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs">
                        ✓ Approve
                      </button>
                      <button onClick={() => reviewRecord(r.id, 'reject')}
                        className="bg-red-100 text-red-700 px-2 py-0.5 rounded text-xs">
                        ✗ Reject
                      </button>
                      <button onClick={() => reviewRecord(r.id, 'flag')}
                        className="bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded text-xs">
                        ⚠ Flag
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}