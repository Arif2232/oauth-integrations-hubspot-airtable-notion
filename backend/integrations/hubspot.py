import json
import os
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse

from integrations.integration_item import IntegrationItem
from redis_client import add_key_value_redis, delete_key_redis, get_value_redis

CLIENT_ID = os.getenv('HUBSPOT_CLIENT_ID', '')
CLIENT_SECRET = os.getenv('HUBSPOT_CLIENT_SECRET', '')
REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'


async def authorize_hubspot(user_id, org_id):
    if not CLIENT_ID or not CLIENT_SECRET:
        raise HTTPException(status_code=503, detail='HubSpot OAuth credentials are not configured.')
    state = secrets.token_urlsafe(32)
    await add_key_value_redis(
        f'hubspot_state:{state}', json.dumps({'user_id': user_id, 'org_id': org_id}), expire=600
    )
    query = urlencode({
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'scope': 'oauth crm.objects.contacts.read',
        'state': state,
    })
    return f'https://app.hubspot.com/oauth/authorize?{query}'


async def oauth2callback_hubspot(request: Request):
    if request.query_params.get('error'):
        raise HTTPException(status_code=400, detail='HubSpot authorization was declined.')
    state = request.query_params.get('state')
    code = request.query_params.get('code')
    if not state or not code:
        raise HTTPException(status_code=400, detail='Missing OAuth state or code.')
    state_key = f'hubspot_state:{state}'
    saved_state = await get_value_redis(state_key)
    if not saved_state:
        raise HTTPException(status_code=400, detail='OAuth state is invalid or expired.')
    await delete_key_redis(state_key)
    state_data = json.loads(saved_state)
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                'https://api.hubapi.com/oauth/2026-03/token',
                data={
                    'grant_type': 'authorization_code',
                    'client_id': CLIENT_ID,
                    'client_secret': CLIENT_SECRET,
                    'redirect_uri': REDIRECT_URI,
                    'code': code,
                },
            )
        if response.is_error or not response.json().get('access_token'):
            raise HTTPException(status_code=502, detail='HubSpot token exchange failed.')
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail='Could not reach HubSpot.') from exc
    await add_key_value_redis(
        f"hubspot_credentials:{state_data['org_id']}:{state_data['user_id']}",
        json.dumps({'access_token': response.json()['access_token']}),
        expire=600,
    )
    return HTMLResponse('<html><body><script>window.close()</script>Connected. You can close this window.</body></html>')


async def get_hubspot_credentials(user_id, org_id):
    key = f'hubspot_credentials:{org_id}:{user_id}'
    credentials = await get_value_redis(key)
    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found. Please reconnect.')
    await delete_key_redis(key)
    return json.loads(credentials)


async def get_items_hubspot(credentials):
    try:
        access_token = json.loads(credentials)['access_token']
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=400, detail='Invalid credentials.') from exc
    items = []
    after = None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            while True:
                params = {'limit': 100, 'properties': 'firstname,lastname,email'}
                if after:
                    params['after'] = after
                response = await client.get(
                    'https://api.hubapi.com/crm/objects/2026-03/contacts',
                    headers={'Authorization': f'Bearer {access_token}'},
                    params=params,
                )
                if response.is_error:
                    raise HTTPException(status_code=502, detail='HubSpot could not load contacts. Please reconnect.')
                page = response.json()
                for contact in page['results']:
                    properties = contact.get('properties', {})
                    name = ' '.join(filter(None, [properties.get('firstname'), properties.get('lastname')]))
                    items.append(IntegrationItem(
                        id=contact['id'], type='Contact',
                        name=name or properties.get('email') or 'Unnamed contact',
                        creation_time=contact.get('createdAt'),
                        last_modified_time=contact.get('updatedAt'),
                    ))
                after = page.get('paging', {}).get('next', {}).get('after')
                if not after:
                    return items
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail='Could not reach HubSpot.') from exc
