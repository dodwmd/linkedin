import os, sys, pytest
from unittest.mock import patch
from tests.mocks import MockNatsManager, MockMySQLManager
# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from web_app import create_app

# Set the default fixture loop scope
@pytest.fixture(scope="function", autouse=True)
def event_loop(request):
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

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
