import json
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from fastapi import HTTPException
from starlette.requests import Request

from integrations import hubspot, notion


class FakeHubSpot:
    def __init__(self, *args, **kwargs):
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def post(self, url, data):
        self.calls.append(('post', url, data))
        return httpx.Response(200, json={'access_token': 'test-token', 'refresh_token': 'not-sent-to-browser'})

    async def get(self, url, headers, params):
        self.calls.append(('get', url, dict(params)))
        if 'after' not in params:
            return httpx.Response(200, json={'results': [{'id': '1', 'properties': {'firstname': 'Ada', 'lastname': 'Lovelace'}}], 'paging': {'next': {'after': 'cursor'}}})
        return httpx.Response(200, json={'results': [{'id': '2', 'properties': {'email': 'grace@example.test'}}]})


class HubSpotTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.storage = {}
        async def put(key, value, expire=None):
            self.storage[key] = value.encode()
        async def get(key):
            return self.storage.get(key)
        async def delete(key):
            self.storage.pop(key, None)
        self.patches = [
            patch.object(hubspot, 'CLIENT_ID', 'client-id'),
            patch.object(hubspot, 'CLIENT_SECRET', 'client-secret'),
            patch.object(hubspot, 'add_key_value_redis', put),
            patch.object(hubspot, 'get_value_redis', get),
            patch.object(hubspot, 'delete_key_redis', delete),
        ]
        for mock in self.patches:
            mock.start()
            self.addCleanup(mock.stop)

    async def test_oauth_exchange_state_and_paginated_contacts(self):
        url = await hubspot.authorize_hubspot('user', 'org')
        query = parse_qs(urlparse(url).query)
        self.assertIn('crm.objects.contacts.read', query['scope'][0])
        state = query['state'][0]
        request = Request({'type': 'http', 'query_string': urlencode({'state': state, 'code': 'code'}).encode()})
        api = FakeHubSpot()
        with patch.object(hubspot.httpx, 'AsyncClient', return_value=api):
            await hubspot.oauth2callback_hubspot(request)
            credentials = await hubspot.get_hubspot_credentials('user', 'org')
            self.assertEqual(credentials, {'access_token': 'test-token'})
            items = await hubspot.get_items_hubspot(json.dumps(credentials))
            self.assertEqual([item.name for item in items], ['Ada Lovelace', 'grace@example.test'])
            self.assertEqual(api.calls[-1][2]['after'], 'cursor')
            with self.assertRaises(HTTPException) as error:
                await hubspot.oauth2callback_hubspot(request)
            self.assertEqual(error.exception.status_code, 400)
            with self.assertRaises(HTTPException):
                await hubspot.get_hubspot_credentials('user', 'org')

    async def test_callback_rejects_unknown_state(self):
        request = Request({'type': 'http', 'query_string': b'state=unknown&code=code'})
        with self.assertRaises(HTTPException) as error:
            await hubspot.oauth2callback_hubspot(request)
        self.assertEqual(error.exception.status_code, 400)


class NotionTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_returns_all_pages_including_databases_without_properties(self):
        def page(item_id, more, cursor=None):
            return {'results': [{'id': item_id, 'object': 'database', 'parent': {'type': 'workspace'}, 'created_time': '2023-01-01', 'last_edited_time': '2023-01-02'}], 'has_more': more, 'next_cursor': cursor}
        responses = [unittest.mock.Mock(status_code=200, json=lambda: page('1', True, 'next')), unittest.mock.Mock(status_code=200, json=lambda: page('2', False))]
        with patch.object(notion.requests, 'post', side_effect=responses) as post:
            items = await notion.get_items_notion('{"access_token":"test-token"}')
        self.assertEqual([item.id for item in items], ['1', '2'])
        self.assertEqual(post.call_args_list[1].kwargs['json'], {'start_cursor': 'next'})


if __name__ == '__main__':
    unittest.main()
