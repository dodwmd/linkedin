import pytest
from unittest.mock import patch
from web_app import create_app
from tests.mocks import MockNatsManager, MockMySQLManager


@pytest.fixture
def app():
    app, _ = create_app()
    app.config['TESTING'] = True
    
    with patch('nats_manager.NatsManager', MockNatsManager), \
         patch('mysql_manager.MySQLManager', MockMySQLManager):
        yield app


@pytest.fixture
def client(app):
    return app.test_client()
