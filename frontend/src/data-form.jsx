import { useState } from 'react';
import { Alert, Box, Button, CircularProgress } from '@mui/material';
import axios from 'axios';

export const DataForm = ({ integrationType, credentials }) => {
  const [items, setItems] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const form = new FormData();
      form.append('credentials', JSON.stringify(credentials));
      const response = await axios.post(`http://localhost:8000/integrations/${integrationType.toLowerCase()}/load`, form);
      setItems(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not load items. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <p className="card-description">Load items available to your {integrationType} connection.</p>
      <Box sx={{ mt: 2 }}><Button variant="outlined" onClick={load} disabled={loading}>{loading ? <><CircularProgress size={16} sx={{ mr: 1 }} /> Loading</> : 'Load items'}</Button></Box>
      {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
      {items && <div className="results" aria-live="polite">
        <div className="result-count">{items.length} {items.length === 1 ? 'ITEM' : 'ITEMS'} FOUND</div>
        {items.length === 0 ? <p>No items were found for this connection.</p> : items.map(item => (
          <div className="result-row" key={`${item.type}-${item.id}`}>
            <span className="result-icon" aria-hidden="true">↗</span>
            <div><strong>{item.name || 'Untitled'}</strong><small>{item.type} · {item.id}</small></div>
          </div>
        ))}
      </div>}
    </>
  );
};
