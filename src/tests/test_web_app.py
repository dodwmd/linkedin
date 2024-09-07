import json
from unittest.mock import patch


def test_nats_health(client):
    response = client.get('/status')
    assert response.status_code == 200
    data = response.get_json()
    assert 'nats_status' in data
    assert data['nats_status'] == 'Connected'


def test_index(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"LinkedIn Crawler Dashboard" in response.data


def test_table_view(client):
    response = client.get('/table/linkedin_people')
    assert response.status_code == 200
    assert b"Table View: linkedin_people" in response.data
    assert b"John Doe" in response.data
    assert b"Jane Smith" in response.data


def test_edit_record(client):
    response = client.get('/edit/linkedin_people/1')
    assert response.status_code == 200
    assert b"Edit Record" in response.data

    response = client.post('/edit/linkedin_people/1', data={
        'name': 'John Doe',
        'linkedin_url': 'https://www.linkedin.com/in/johndoe'
    })
    assert response.status_code == 302  # Redirect after successful edit


def test_delete_record(client):
    response = client.post('/delete/linkedin_people/1')
    assert response.status_code == 302  # Redirect after successful delete


def test_export_csv(client):
    response = client.get('/export/linkedin_people')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv'
    assert response.headers['Content-Disposition'] == 'attachment; filename=linkedin_people.csv'


def test_status(client):
    response = client.get('/status')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'profiles_scanned' in data
    assert 'companies_scanned' in data
    assert 'active_threads' in data
    assert 'queue_size' in data
    assert 'nats_status' in data
    assert 'mysql_status' in data
    assert 'crawler_status' in data


def test_start_crawler(client):
    response = client.post('/start_crawler')
    assert response.status_code == 200
    data = response.get_json()
    assert 'status' in data
    assert "Crawler started successfully" in data['status']


def test_stop_crawler(client):
    response = client.post('/stop_crawler')
    assert response.status_code == 200
    data = response.get_json()
    assert 'status' in data


def test_add_url(client):
    response = client.get('/add_url')
    assert response.status_code == 200
    assert b"Add URL" in response.data

    with patch('mysql_manager.MySQLManager.execute_query') as mock_execute_query:
        response = client.post('/add_url', data={
            'url': 'https://www.linkedin.com/in/testuser3',
            'type': 'person'
        })
        assert response.status_code == 302  # Redirect after successful addition
        mock_execute_query.assert_called_once()
