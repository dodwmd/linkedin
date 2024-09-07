class MockNATS:
    def __init__(self):
        self.is_connected = False
        self.subscriptions = {}

    async def connect(self):
        self.is_connected = True

    async def close(self):
        self.is_connected = False

    async def subscribe(self, subject, cb=None, **kwargs):
        self.subscriptions[subject] = cb

    async def publish(self, subject, payload):
        if subject in self.subscriptions and self.subscriptions[subject]:
            await self.subscriptions[subject](subject, payload)

class MockNatsManager:
    def __init__(self):
        self.nc = MockNATS()

    def connect(self):
        self.nc.is_connected = True

    def close(self):
        self.nc.is_connected = False

    def subscribe(self, subject, cb=None, **kwargs):
        self.nc.subscriptions[subject] = cb

    def publish(self, subject, payload):
        if subject in self.nc.subscriptions and self.nc.subscriptions[subject]:
            self.nc.subscriptions[subject](subject, payload)

    @classmethod
    def get_instance(cls):
        instance = cls()
        instance.connect()
        return instance

class MockMySQLManager:
    def __init__(self):
        self.connected = False
        self.data = {
            'linkedin_people': [
                {
                    'id': 1,
                    'name': 'John Doe',
                    'linkedin_url': 'https://www.linkedin.com/in/johndoe'
                },
                {
                    'id': 2,
                    'name': 'Jane Smith',
                    'linkedin_url': 'https://www.linkedin.com/in/janesmith'
                },
            ],
            'linkedin_companies': [
                {
                    'id': 1,
                    'name': 'Acme Corp',
                    'linkedin_url': 'https://www.linkedin.com/company/acmecorp'
                },
                {
                    'id': 2,
                    'name': 'Tech Inc',
                    'linkedin_url': 'https://www.linkedin.com/company/techinc'
                },
            ],
        }

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.connected = False

    def execute_query(self, query, params=None):
        if not self.connected:
            raise Exception("Not connected to the database")

        query = query.strip().lower()
        
        if query.startswith("select * from"):
            table_name = query.split()[-1]
            return self.data.get(table_name, [])
        elif query.startswith("select count(*) from"):
            table_name = query.split()[-1]
            return [{'count': len(self.data.get(table_name, []))}]
        elif query.startswith("show tables"):
            return [{'Tables_in_db': table} for table in self.data.keys()]
        elif query.startswith("show columns from"):
            table_name = query.split()[-1]
            if table_name in self.data:
                return [{'Field': key} for key in self.data[table_name][0].keys()]
            return []
        elif query.startswith("show table status"):
            table_name = query.split("like")[-1].strip().strip("'")
            return [{
                'Name': table_name,
                'Rows': len(self.data.get(table_name, [])),
                'Data_length': 1024,
                'Index_length': 512,
            }]
        else:
            return []

    def connection(self):
        class MockConnection:
            def commit(self):
                pass
        return MockConnection()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

class MockLinkedInCrawler:
    def __init__(self, nats_manager, mysql_manager):
        self.nats_manager = nats_manager
        self.mysql_manager = mysql_manager

    async def run(self, crawler_state):
        # Simplified run method for testing
        pass
