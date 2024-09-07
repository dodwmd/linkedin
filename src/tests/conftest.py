import pytest
from unittest.mock import patch
from tests.mocks import MockNatsManager, MockMySQLManager
# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from web_app import create_app


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
