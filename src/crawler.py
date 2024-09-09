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
import threading
import traceback

# Load environment variables from .env file
load_dotenv()

class LinkedInCrawler:
    def __init__(self, nats_manager: NatsManager, mysql_manager: MySQLManager, linkedin_session: LinkedInSession):
        self.nats_manager = nats_manager
        self.mysql_manager = mysql_manager
        self.linkedin_session = linkedin_session
        self.company_crawler = CompanyCrawler(linkedin_session, nats_manager, mysql_manager)
        self.people_crawler = PeopleCrawler(linkedin_session, nats_manager, mysql_manager)

    async def run(self, crawler_state: CrawlerState, stop_event: threading.Event):
        try:
            log("Crawler run started")
            log("Connecting to NATS")
            await self.nats_manager.connect()
            log("Connected to NATS")
            
            log("Creating company task")
            company_task = asyncio.create_task(self.process_company_queue(crawler_state, stop_event))
            log("Creating people task")
            people_task = asyncio.create_task(self.process_people_queue(crawler_state, stop_event))
            
            log("Tasks created, waiting for completion")
            while not crawler_state.is_stop_requested() and not stop_event.is_set():
                done, pending = await asyncio.wait([company_task, people_task], timeout=1)
                
                for task in done:
                    try:
                        result = task.result()
                        log(f"Task completed: {result}")
                    except Exception as e:
                        log(f"Task raised an exception: {str(e)}", "error")
                        log(f"Traceback: {traceback.format_exc()}", "error")
                
                if not pending:
                    log("All tasks completed")
                    break
            
            if crawler_state.is_stop_requested() or stop_event.is_set():
                log("Stop requested, cancelling pending tasks")
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        log(f"Task was cancelled: {task}")
        except asyncio.CancelledError:
            log("Crawler run was cancelled")
        except Exception as e:
            log(f"Error in crawler run: {str(e)}", "error")
            log(f"Traceback: {traceback.format_exc()}", "error")
        finally:
            log("Cleaning up crawler")
            await self.cleanup()
            crawler_state.set_stopped()
            stop_event.set()
            log("Crawler run finished")

    async def process_company_queue(self, crawler_state: CrawlerState, stop_event: threading.Event):
        log("Starting process_company_queue")
        while not crawler_state.is_stop_requested() and not stop_event.is_set():
            try:
                seed_company = await self._get_seed_company()
                if seed_company:
                    await self.crawl_company(seed_company, is_seed=True)
                else:
                    await asyncio.sleep(1)  # Sleep if no seed company found
                
                # Check for stop request more frequently
                if crawler_state.is_stop_requested() or stop_event.is_set():
                    log("Stop requested, exiting company queue processing")
                    break
            except Exception as e:
                log(f"Error in company queue processing: {str(e)}", "error")
        log("Company queue processing finished")

    async def process_people_queue(self, crawler_state: CrawlerState, stop_event: threading.Event):
        log("Starting process_people_queue")
        while not crawler_state.is_stop_requested() and not stop_event.is_set():
            try:
                seed_person = await self._get_seed_person()
                if seed_person:
                    await self.crawl_person(seed_person, is_seed=True)
                else:
                    await asyncio.sleep(1)  # Sleep if no seed person found
                
                # Check for stop request more frequently
                if crawler_state.is_stop_requested() or stop_event.is_set():
                    log("Stop requested, exiting people queue processing")
                    break
            except Exception as e:
                log(f"Error in people queue processing: {str(e)}", "error")
        log("People queue processing finished")

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
            if self.nats_manager.is_connected():
                await self.nats_manager.close()
            await self.company_crawler.close()
            await self.people_crawler.close()
        except Exception as e:
            log(f"Error during cleanup: {str(e)}", "error")

    async def _get_seed_company(self):
        try:
            # First, check if there are any messages in the NATS queue
            response = await self.nats_manager.request("linkedin_company_urls", b'', timeout=1)
            if response and response.data:
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
            if response and response.data:
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

