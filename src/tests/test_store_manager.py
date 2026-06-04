"""
Tests for orders manager
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""

import json
import uuid
import pytest
from store_manager import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health(client):
    result = client.get('/health-check')
    assert result.status_code == 200
    assert result.get_json() == {'status':'ok'}

def test_stock_flow(client):
    created_product_id = None
    created_order_id = None

    # 1. Créez un article (`POST /products`)
    unique_sku = f"12345-{uuid.uuid4().hex[:8]}"
    product_data = {'name': 'Some Item', 'sku': unique_sku, 'price': 99.90}

    try:
        response = client.post('/products',
                            data=json.dumps(product_data),
                            content_type='application/json')
        assert response.status_code == 201
        data = response.get_json()
        created_product_id = data['product_id']
        assert created_product_id > 0

        # 2. Ajoutez 5 unités au stock de cet article (`POST /stocks`)
        stock_data = {'product_id': created_product_id, 'quantity': 5}
        response = client.post('/stocks',
                                data=json.dumps(stock_data),
                                content_type='application/json')
        assert response.status_code == 201

        # 3. Vérifiez le stock, votre article devra avoir 5 unités dans le stock (`GET /stocks/:id`)
        response = client.get(f"/stocks/{created_product_id}")
        assert response.status_code == 200
        stock_info = response.get_json()
        assert stock_info['quantity'] == 5

        # 4. Faites une commande de l'article que vous avez crée, 2 unités (`POST /orders`)
        order_data = {
            'user_id': 1,
            'items': [{'product_id': created_product_id, 'quantity': 2}]
        }
        response = client.post('/orders',
                                data=json.dumps(order_data),
                                content_type='application/json')
        assert response.status_code == 201
        order_info = response.get_json()
        created_order_id = order_info['order_id']

        # 5. Vérifiez le stock encore une fois (`GET /stocks/:id`)
        response = client.get(f"/stocks/{created_product_id}")
        assert response.status_code == 200
        stock_info = response.get_json()
        assert stock_info['quantity'] == 3

        # 6. Étape extra: supprimez la commande et vérifiez le stock de nouveau. Le stock devrait augmenter après la suppression de la commande.
        response = client.delete(f'/orders/{created_order_id}')
        assert response.status_code == 200
        assert response.get_json() == {'deleted': True}

        response = client.get(f"/stocks/{created_product_id}")
        assert response.status_code == 200
        stock_info = response.get_json()
        assert stock_info['quantity'] == 5
    finally:
        if created_order_id is not None:
            client.delete(f'/orders/{created_order_id}')
        if created_product_id is not None:
            client.delete(f'/products/{created_product_id}')
    