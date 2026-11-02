import { useEffect, useRef, useState } from 'react';
import { Alert, Box, Button, Chip, CircularProgress, MenuItem, Paper, TextField, Typography } from '@mui/material';
import axios from 'axios';
import { DataForm } from './data-form';

const providers = ['HubSpot', 'Airtable', 'Notion'];

export const IntegrationForm = () => {
  const [user, setUser] = useState('demo-user');
  const [org, setOrg] = useState('demo-workspace');
  const [provider, setProvider] = useState('HubSpot');
  const [credentials, setCredentials] = useState(null);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState('');
  const timer = useRef(null);

  useEffect(() => () => window.clearInterval(timer.current), []);

  const reset = () => {
    setCredentials(null);
    setError('');
  };

  const connect = async () => {
    if (!user.trim() || !org.trim()) {
      setError('Enter a user and workspace before connecting.');
      return;
    }
    const popup = window.open('', 'integration-authorization', 'width=600,height=700');
    if (!popup) {
      setError('Allow pop-ups in your browser to connect an integration.');
      return;
    }
    setConnecting(true);
    setError('');
    const form = new FormData();
    form.append('user_id', user.trim());
    form.append('org_id', org.trim());
    const endpoint = provider.toLowerCase();
    try {
      const response = await axios.post(`http://localhost:8000/integrations/${endpoint}/authorize`, form);
      popup.location.href = response.data;
      timer.current = window.setInterval(async () => {
        if (!popup.closed) return;
        window.clearInterval(timer.current);
        try {
          const result = await axios.post(`http://localhost:8000/integrations/${endpoint}/credentials`, form);
          setCredentials(result.data);
        } catch (err) {
          setError(err.response?.data?.detail || 'Connection was not completed. Please try again.');
        } finally {
          setConnecting(false);
        }
      }, 400);
    } catch (err) {
      popup.close();
      setError(err.response?.data?.detail || 'Could not reach the API. Is the backend running?');
      setConnecting(false);
    }
  };

  return (
    <main className="page">
      <header className="topbar">
        <div className="brand"><span className="brand-mark" aria-hidden="true">↗</span> Connector Lab</div>
        <span className="topbar-label">INTEGRATION PLAYGROUND</span>
      </header>
      <section className="hero">
        <div className="eyebrow"><span /> CONNECT YOUR WORKSPACE</div>
        <h1>Your tools, <em>together.</em></h1>
        <p>Explore OAuth connections and bring metadata from your favorite tools into one place.</p>
      </section>
      <div className="workspace">
        <Paper component="section" elevation={0} className="connect-card">
          <div className="card-heading">
            <div><div className="section-label">01 / CONNECTION</div><h2>Set up an integration</h2></div>
            <Chip label={credentials ? 'Connected' : 'Ready to connect'} size="small" color={credentials ? 'success' : 'default'} />
          </div>
          <p className="card-description">Choose a service and authorize access to view its available items.</p>
          <div className="fields">
            <TextField label="User" value={user} disabled={connecting} fullWidth onChange={e => { setUser(e.target.value); reset(); }} />
            <TextField label="Workspace" value={org} disabled={connecting} fullWidth onChange={e => { setOrg(e.target.value); reset(); }} />
            <TextField select label="Integration" value={provider} disabled={connecting} fullWidth onChange={e => { setProvider(e.target.value); reset(); }}>
              {providers.map(name => <MenuItem key={name} value={name}>{name}</MenuItem>)}
            </TextField>
          </div>
          {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
          <Box sx={{ mt: 3 }}>
            <Button variant="contained" size="large" disableElevation onClick={connect} disabled={connecting || !!credentials}>
              {connecting ? <><CircularProgress size={17} sx={{ mr: 1 }} /> Waiting for authorization</> : credentials ? `${provider} connected` : `Connect ${provider} ↗`}
            </Button>
            {credentials && <Button onClick={reset} sx={{ ml: 1, textTransform: 'none' }}>Disconnect</Button>}
          </Box>
        </Paper>
        <Paper component="section" elevation={0} className="data-card">
          <div className="card-heading"><div><div className="section-label">02 / RESULTS</div><h2>Explore your data</h2></div></div>
          {credentials ? <DataForm key={provider} integrationType={provider} credentials={credentials} /> : (
            <div className="empty-state"><span className="empty-icon" aria-hidden="true">✳</span><Typography component="h3">Nothing connected yet</Typography><p>Once connected, your integration items will appear here.</p></div>
          )}
        </Paper>
      </div>
      <footer>BUILT FOR EXPLORING THE CONNECTIONS BETWEEN YOUR TOOLS <span>✳</span></footer>
    </main>
  );
};
