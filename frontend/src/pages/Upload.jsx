// src/pages/Upload.jsx
import { useState } from 'react';
import API from '../api/client';

const SOURCE_TYPES = [
  { value: 'sap_fuel_procurement', label: 'SAP Fuel & Procurement (CSV)' },
  { value: 'utility_electricity', label: 'Utility Electricity (CSV)' },
  { value: 'travel_corporate', label: 'Corporate Travel (JSON)' },
];

export default function Upload() {
  const [sourceType, setSourceType] = useState('');
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file || !sourceType) return;

    setUploading(true);
    setError('');
    const form = new FormData();
    form.append('file', file);
    form.append('source_type', sourceType);

    try {
      const r = await API.post('/upload/', form, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setResult(r.data);
    } catch (err) {
      setError(err.response?.data?.error || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="p-6 max-w-xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Upload Data</h1>
      <form onSubmit={handleUpload} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Source Type</label>
          <select
            value={sourceType}
            onChange={e => setSourceType(e.target.value)}
            className="w-full border rounded px-3 py-2"
            required
          >
            <option value="">Select source…</option>
            {SOURCE_TYPES.map(s => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">File</label>
          <input type="file"
            accept=".csv,.json"
            onChange={e => setFile(e.target.files[0])}
            className="w-full border rounded px-3 py-2"
            required
          />
        </div>
        <button type="submit"
          disabled={uploading}
          className="w-full bg-blue-600 text-white py-2 rounded font-medium disabled:opacity-50">
          {uploading ? 'Processing…' : 'Upload & Process'}
        </button>
      </form>

      {error && (
        <div className="mt-4 bg-red-50 border border-red-200 p-4 rounded text-red-700">
          {error}
        </div>
      )}

      {result && (
        <div className="mt-4 bg-green-50 border border-green-200 p-4 rounded">
          <p className="font-medium text-green-800">
            ✓ Processed {result.row_count} rows
          </p>
          {result.error_count > 0 && (
            <p className="text-yellow-700 text-sm mt-1">
              ⚠ {result.error_count} rows had warnings
            </p>
          )}
          {result.error_log?.slice(0, 5).map((e, i) => (
            <p key={i} className="text-xs text-gray-600 mt-1">
              Row {e.row}: {JSON.stringify(e.warnings)}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}