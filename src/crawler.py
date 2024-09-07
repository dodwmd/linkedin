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
        self.company_crawler = CompanyCrawler(linkedin_session, nats_manager, mysql_manager.db_config)
        self.people_crawler = PeopleCrawler(linkedin_session, nats_manager, mysql_manager.db_config)
        self.loop = asyncio.get_event_loop()

    async def process_company_queue(self, crawler_state):
        await self.nats_manager.subscribe("linkedin_company_urls")

        while not crawler_state.is_stop_requested():
            try:
                subject, message = await self.nats_manager.get_message("linkedin_company_urls", timeout=5)
                if subject is None and message is None:
                    # If queue is empty, try to use a seed profile
                    seed_company = await self._get_seed_company()
                    if seed_company:
                        await self.crawl_company(seed_company, is_seed=True)
                    else:
                        await asyncio.sleep(1)
                    continue

                # Process the company message
                log(f"Received company message: {message}")
                data = json.loads(message)
                company_url = data.get('url')
                is_seed = data.get('is_seed', False)
                await self.crawl_company(company_url, is_seed)

            except Exception as e:
                log(f"Error processing company message: {str(e)}", "error")
            await asyncio.sleep(1)  # Add a small delay to prevent tight looping

    async def process_people_queue(self, crawler_state):
        await self.nats_manager.subscribe("linkedin_people_urls")

        while not crawler_state.is_stop_requested():
            try:
                subject, message = await self.nats_manager.get_message("linkedin_people_urls", timeout=5)
                if subject is None and message is None:
                    # If queue is empty, try to use a seed profile
                    seed_person = await self._get_seed_person()
                    if seed_person:
                        await self.crawl_person(seed_person, is_seed=True)
                    else:
                        await asyncio.sleep(1)
                    continue

                # Process the people message
                log(f"Received people message: {message}")
                data = json.loads(message)
                person_url = data.get('url')
                is_seed = data.get('is_seed', False)
                await self.crawl_person(person_url, is_seed)

            except Exception as e:
                log(f"Error processing people message: {str(e)}", "error")
            await asyncio.sleep(1)  # Add a small delay to prevent tight looping

    async def crawl_company(self, company_url, is_seed=False):
        try:
            log(f"Crawling company: {company_url}")
            company = await self.company_crawler.crawl_company(company_url, is_seed)
            if company:
                log(f"Successfully crawled company: {company.name}")
                increment_companies_scanned()
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
            else:
                log(f"Person already crawled or not found: {person_url}")
        except Exception as e:
            log(f"Error crawling person {person_url}: {str(e)}", "error")

    async def publish_new_url(self, url_type, url):
        subject = f"linkedin_{url_type}_urls"
        message = json.dumps({"url": url})
        await self.nats_manager.publish(subject, message)

    async def is_subscription_empty(self, subject):
        try:
            _, message = await self.nats_manager.get_message(subject, timeout=1)
            if message is None:
                return True
            else:
                # If we got a message, put it back in the queue
                await self.nats_manager.publish(subject, message)
                return False
        except Exception as e:
            log(f"Error checking subscription {subject}: {str(e)}", "error")
            return True  # Assume empty if there's an error

    async def seed_initial_urls(self):
        initial_profile_url = os.getenv('INITIAL_PROFILE_URL')
        initial_company_url = os.getenv('INITIAL_COMPANY_URL')

        if initial_profile_url and await self.is_subscription_empty("linkedin_people_urls"):
            await self.publish_new_url('people', initial_profile_url)
            log(f"Seeded initial profile URL: {initial_profile_url}")

        if initial_company_url and await self.is_subscription_empty("linkedin_company_urls"):
            await self.publish_new_url('company', initial_company_url)
            log(f"Seeded initial company URL: {initial_company_url}")

    async def run(self, crawler_state):
        try:
            await self.nats_manager.connect()
            
            # Subscribe to the subjects before seeding
            await self.nats_manager.subscribe("linkedin_company_urls")
            await self.nats_manager.subscribe("linkedin_people_urls")
            
            # Seed the initial URLs if needed
            await self.seed_initial_urls()

            company_task = self.loop.create_task(self.process_company_queue(crawler_state))
            people_task = self.loop.create_task(self.process_people_queue(crawler_state))
            await asyncio.gather(company_task, people_task)
        except Exception as e:
            log(f"Error in crawler run: {str(e)}", "error")
        finally:
            await self.cleanup()

    async def cleanup(self):
        try:
            await self.nats_manager.close()
            await self.company_crawler.close()
            await self.people_crawler.close()
        except Exception as e:
            log(f"Error during cleanup: {str(e)}", "error")
        finally:
            log("Crawler stopped")

    async def _get_seed_company(self):
        mysql_manager = MySQLManager()
        try:
            mysql_manager.connect()
            query = """
                SELECT url FROM seed_urls
                WHERE type = 'company' AND (last_crawled IS NULL OR last_crawled < DATE_SUB(NOW(), INTERVAL 1 DAY))
                ORDER BY RAND()
                LIMIT 1
            """
            result = mysql_manager.execute_query(query)
            if result:
                return result[0]['url']
            return None
        finally:
            mysql_manager.disconnect()

    async def _get_seed_person(self):
        mysql_manager = MySQLManager()
        try:
            mysql_manager.connect()
            query = """
                SELECT url FROM seed_urls
                WHERE type = 'person' AND (last_crawled IS NULL OR last_crawled < DATE_SUB(NOW(), INTERVAL 1 DAY))
                ORDER BY RAND()
                LIMIT 1
            """
            result = mysql_manager.execute_query(query)
            if result:
                return result[0]['url']
            return None
        finally:
            mysql_manager.disconnect()

def run_crawler(crawler_state: CrawlerState):
    try:
        email = os.getenv('LINKEDIN_EMAIL')
        password = os.getenv('LINKEDIN_PASSWORD')
        
        if not email or not password:
            raise ValueError("LinkedIn credentials not found in environment variables")

        linkedin_session = LinkedInSession(email, password)
        linkedin_session.start()

        driver = linkedin_session.get_driver()

        crawler = LinkedInCrawler(NatsManager(), MySQLManager(), linkedin_session)
        asyncio.run(crawler.run(crawler_state))
        
    except Exception as e:
        log(f"Error in crawler: {str(e)}", "error")
    finally:
        if linkedin_session:
            linkedin_session.close()
        crawler_state.set_stopped()
        log("Crawler stopped")

# Make sure to export both LinkedInCrawler and run_crawler
__all__ = ['LinkedInCrawler', 'run_crawler']
