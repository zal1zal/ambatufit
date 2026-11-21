import asyncio
from fastapi.testclient import TestClient
from integration.server import app
from integration.adapters.ambatunoutrish import AmbatuNoutrishAdapter
from integration.adapters.ambatomove import AmbatoMoveAdapter
from app.config import Settings
import httpx
import pytest


def test_missing_partners_do_not_return_synthetic_live_data():
    assert asyncio.run(AmbatuNoutrishAdapter().get_foods()) == ([], 'not_configured')
    assert asyncio.run(AmbatoMoveAdapter().get_gyms()) == ([], 'not_configured')


def test_mobile_endpoints_require_bearer_without_shipping_service_secret(demo_user_token):
    with TestClient(app) as client:
        for route in ('nutrition/foods', 'fitness/gyms'):
            denied = client.get(f'/integration/v1/{route}')
            assert denied.status_code == 401
            assert denied.json()['error']['request_id']
            response = client.get(f'/integration/v1/{route}', headers={'Authorization': f'Bearer {demo_user_token}'})
            assert response.status_code == 200
            assert response.json() == {'items': [], 'total': 0, 'provider_status': 'not_configured'}


def test_dotenv_settings_activate_confirmed_adapter_without_environment_export(monkeypatch):
    from integration.adapters import ambatomove
    from pathlib import Path
    env_file = Path(__file__).resolve().parents[1] / 'var' / 'integration-test.env'
    env_file.parent.mkdir(exist_ok=True)
    env_file.write_text('INTEGRATION_MODE=live\nPARTNER_CONTRACTS_CONFIRMED=true\nGYM_PROVIDER_BASE_URL=https://partner.test\nGYM_PROVIDER_API_KEY=test-key\n')
    monkeypatch.delenv('INTEGRATION_MODE', raising=False)
    try:
        configured = Settings(_env_file=env_file)
    finally:
        env_file.unlink()
    monkeypatch.setattr(ambatomove, 'settings', configured)
    original_client = httpx.AsyncClient
    def handle(request):
        assert request.headers['X-API-Key'] == 'test-key'
        return httpx.Response(200, json={'items': [{'id': 'demo-gym', 'name': 'Synthetic facility'}]})
    monkeypatch.setattr(ambatomove.httpx, 'AsyncClient', lambda **kwargs: original_client(transport=httpx.MockTransport(handle), **kwargs))
    items, status = asyncio.run(AmbatoMoveAdapter(configured.GYM_PROVIDER_BASE_URL, configured.GYM_PROVIDER_API_KEY).get_gyms())
    assert status == 'available'
    assert items[0]['latitude'] is None
    assert items[0]['longitude'] is None
    assert items[0]['opening_hours'] is None


@pytest.mark.parametrize('status,body', [(429, {}), (503, {}), (200, {'items': 'invalid'}), (200, {'items': [{'name': 'Missing ID'}]})])
def test_provider_errors_and_malformed_payloads_remain_unavailable(monkeypatch, status, body):
    from integration.adapters import ambatunoutrish
    monkeypatch.setattr(ambatunoutrish.settings, 'INTEGRATION_MODE', 'live')
    monkeypatch.setattr(ambatunoutrish.settings, 'PARTNER_CONTRACTS_CONFIRMED', True)
    original_client = httpx.AsyncClient
    monkeypatch.setattr(ambatunoutrish.httpx, 'AsyncClient', lambda **kwargs: original_client(transport=httpx.MockTransport(lambda req: httpx.Response(status, json=body)), **kwargs))
    assert asyncio.run(AmbatuNoutrishAdapter('https://partner.test').get_foods()) == ([], 'unavailable')
