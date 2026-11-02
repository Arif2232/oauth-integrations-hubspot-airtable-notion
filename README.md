# Connector Lab

A small OAuth integration playground for connecting HubSpot, Airtable, and Notion and browsing the items available to each connection.

**React · FastAPI · Redis · OAuth 2.0**

## What it does

- Connects a HubSpot account and lists contacts, including paginated results.
- Connects Airtable and lists bases and tables; connects Notion and lists searchable pages and databases.
- Uses Redis for short-lived authorization state and one-time credential handoff.
- Shows results in a responsive interface, without logging access tokens or workspace data.

The Airtable and Notion integrations began with a VectorShift-provided starter project. This version adds HubSpot support, improves metadata loading, and refreshes the interface and setup.

## Run locally

You'll need Python 3.10+, Node.js 24+, npm, Redis, and OAuth app credentials for each service you want to use. The app listens on `localhost:3000` and `localhost:8000`.

1. Start Redis:

   ```sh
   redis-server
   ```

2. Set up the API:

   ```sh
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   # Fill in the credentials for the service(s) you want to connect.
   uvicorn main:app --reload
   ```

3. In a separate terminal, start the frontend:

   ```sh
   cd frontend
   npm ci
   npm start
   ```

Open [http://localhost:3000](http://localhost:3000), select an integration, and complete the authorization pop-up. Then select **Load items**.

### OAuth app configuration

Configure the following redirect URL in each provider's developer settings, then put its client ID and secret in `backend/.env`:

| Provider | Redirect URL | Access needed |
| --- | --- | --- |
| HubSpot | `http://localhost:8000/integrations/hubspot/oauth2callback` | `oauth` and `crm.objects.contacts.read` |
| Airtable | `http://localhost:8000/integrations/airtable/oauth2callback` | `data.records:read` and `schema.bases:read` |
| Notion | `http://localhost:8000/integrations/notion/oauth2callback` | A public integration with access to the pages you want to search |

For HubSpot, use an OAuth-enabled app and a separate test or customer account for installation. Provider configuration and access requirements can change; consult the [HubSpot](https://developers.hubspot.com/docs/guides/apps/public-apps/overview), [Airtable](https://airtable.com/developers/web/api/oauth-reference), and [Notion](https://developers.notion.com/docs/authorization) documentation.

## Tests

```sh
cd backend
python -m unittest discover -s tests -v
```

The backend tests mock provider responses; they don't require provider credentials or Redis. Run the frontend test with `cd frontend && npm test`.

## Scope

This is a local demonstration, not a production service. User and workspace names are labels, not authenticated identities. Access tokens are handed to the browser in memory, and Redis may persist its data depending on its configuration. There is no automatic token refresh; reconnect when a token expires. Use test accounts and don't expose the API or Redis to an untrusted network.
