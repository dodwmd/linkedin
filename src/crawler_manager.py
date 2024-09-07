import asyncio
import threading
from shared_data import log, CrawlerState
from nats_manager import NatsManager
from mysql_manager import MySQLManager
from crawler import LinkedInCrawler
from linkedin_session import LinkedInSession
import os

crawler_thread = None
crawler_state = CrawlerState()

def run_crawler():
    async def crawler_task():
        try:
            log("Initializing NATS manager...")
            nats_manager = await NatsManager.get_instance()

            log("Initializing MySQL manager...")
            mysql_manager = MySQLManager()

            log("Initializing LinkedIn session...")
            linkedin_session = LinkedInSession(
                os.getenv('LINKEDIN_EMAIL'),
                os.getenv('LINKEDIN_PASSWORD')
            )
            linkedin_session.login()

            log("Initializing LinkedIn crawler...")
            crawler = LinkedInCrawler(nats_manager, mysql_manager, linkedin_session)

            log("Starting crawler...")
            await crawler.run(crawler_state)
        except Exception as e:
            log(f"Error in crawler task: {str(e)}")
        finally:
            crawler_state.set_stopped()

    asyncio.run(crawler_task())

def start_crawler():
    global crawler_thread
    if not crawler_state.is_running():
        crawler_state.set_running()
        crawler_thread = threading.Thread(target=run_crawler)
        crawler_thread.start()
        return True
    return False

def stop_crawler():
    if crawler_state.is_running():
        crawler_state.set_stop_requested()
        return True
    return False
