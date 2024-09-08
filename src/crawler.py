import os
from nats_manager import NatsManager
from shared_data import log, increment_profiles_scanned, increment_companies_scanned, CrawlerState
from mysql_manager import MySQLManager
from company_crawler import CompanyCrawler
from people_crawler import PeopleCrawler
from linkedin_session import LinkedInSession
import asyncio
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class LinkedInCrawler:
    def __init__(self, nats_manager: NatsManager, mysql_manager: MySQLManager, linkedin_session: LinkedInSession):
        self.nats_manager = nats_manager
        self.mysql_manager = mysql_manager
        self.linkedin_session = linkedin_session
        self.company_crawler = CompanyCrawler(linkedin_session, nats_manager, mysql_manager)
        self.people_crawler = PeopleCrawler(linkedin_session, nats_manager, mysql_manager)

    async def run(self, crawler_state: CrawlerState):
        try:
            await self.nats_manager.connect()
            
            company_task = asyncio.create_task(self.process_company_queue(crawler_state))
            people_task = asyncio.create_task(self.process_people_queue(crawler_state))
            
            await asyncio.gather(company_task, people_task)
        except Exception as e:
            log(f"Error in crawler run: {str(e)}", "error")
        finally:
            await self.cleanup()
            crawler_state.set_stopped()

    async def process_company_queue(self, crawler_state):
        async def company_message_handler(msg):
            try:
                data = json.loads(msg.data.decode())
                company_url = data.get('url')
                is_seed = data.get('is_seed', False)
                await self.crawl_company(company_url, is_seed)
            except Exception as e:
                log(f"Error processing company message: {str(e)}", "error")

        await self.nats_manager.subscribe("linkedin_company_urls", company_message_handler)

        while not crawler_state.is_stop_requested():
            try:
                # If queue is empty, try to use a seed profile
                seed_company = await self._get_seed_company()
                if seed_company:
                    await self.crawl_company(seed_company, is_seed=True)
                await asyncio.sleep(1)  # Add a small delay to prevent overwhelming the system
            except Exception as e:
                log(f"Error in company queue processing: {str(e)}", "error")

    async def process_people_queue(self, crawler_state):
        async def people_message_handler(msg):
            try:
                data = json.loads(msg.data.decode())
                person_url = data.get('url')
                is_seed = data.get('is_seed', False)
                await self.crawl_person(person_url, is_seed)
            except Exception as e:
                log(f"Error processing people message: {str(e)}", "error")

        await self.nats_manager.subscribe("linkedin_people_urls", people_message_handler)

        while not crawler_state.is_stop_requested():
            try:
                # If queue is empty, try to use a seed profile
                seed_person = await self._get_seed_person()
                if seed_person:
                    await self.crawl_person(seed_person, is_seed=True)
                await asyncio.sleep(1)  # Add a small delay to prevent overwhelming the system
            except Exception as e:
                log(f"Error in people queue processing: {str(e)}", "error")

    async def crawl_company(self, company_url, is_seed=False):
        try:
            log(f"Crawling company: {company_url}")
            company = await self.company_crawler.crawl_company(company_url, is_seed)
            if company:
                log(f"Successfully crawled company: {company.name}")
                increment_companies_scanned()
                if is_seed:
                    await self._update_seed_url_crawled(company_url)
            else:
                log(f"Company already crawled or not found: {company_url}")
        except Exception as e:
            log(f"Error crawling company {company_url}: {str(e)}", "error")

    async def crawl_person(self, person_url, is_seed=False):
        try:
            log(f"Crawling person: {person_url}")
            person = await self.people_crawler.crawl_profile(person_url, is_seed)
            if person:
                log(f"Successfully crawled person: {person.name}")
                increment_profiles_scanned()
                if is_seed:
                    await self._update_seed_url_crawled(person_url)
            else:
                log(f"Person already crawled or not found: {person_url}")
        except Exception as e:
            log(f"Error crawling person {person_url}: {str(e)}", "error")

    async def cleanup(self):
        try:
            await self.nats_manager.close()
            await self.company_crawler.close()
            await self.people_crawler.close()
        except Exception as e:
            log(f"Error during cleanup: {str(e)}", "error")

    async def _get_seed_company(self):
        try:
            # First, check if there are any messages in the NATS queue
            response = await self.nats_manager.request("linkedin_company_urls", b'', timeout=1)
            if response:
                data = json.loads(response.data.decode())
                return data.get('url')

            # If NATS queue is empty, fetch from MySQL
            query = """
                SELECT url FROM seed_urls 
                WHERE type = 'company' AND last_crawled IS NULL
                ORDER BY RAND() LIMIT 1
            """
            result = await self.mysql_manager.execute_query(query)
            if result:
                return result[0]['url']
        except Exception as e:
            log(f"Error getting seed company: {str(e)}", "error")
        return None

    async def _get_seed_person(self):
        try:
            # First, check if there are any messages in the NATS queue
            response = await self.nats_manager.request("linkedin_people_urls", b'', timeout=1)
            if response:
                data = json.loads(response.data.decode())
                return data.get('url')

            # If NATS queue is empty, fetch from MySQL
            query = """
                SELECT url FROM seed_urls 
                WHERE type = 'person' AND last_crawled IS NULL
                ORDER BY RAND() LIMIT 1
            """
            result = await self.mysql_manager.execute_query(query)
            if result:
                return result[0]['url']
        except Exception as e:
            log(f"Error getting seed person: {str(e)}", "error")
        return None

    async def _update_seed_url_crawled(self, url):
        query = """
            UPDATE seed_urls 
            SET last_crawled = CURRENT_TIMESTAMP 
            WHERE url = %s
        """
        await self.mysql_manager.execute_query(query, (url,))

