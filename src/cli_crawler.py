import asyncio
import sys
import os
from dotenv import load_dotenv
from nats_manager import NatsManager
from mysql_manager import MySQLManager
from linkedin_session import LinkedInSession
from company_crawler import CompanyCrawler
from people_crawler import PeopleCrawler
from shared_data import log

# Load environment variables from .env file
load_dotenv()

async def run_single_crawl(url):
    nats_manager = NatsManager.get_instance()
    mysql_manager = MySQLManager()
    linkedin_session = None

    try:
        log("Initializing LinkedIn session...")
        linkedin_session = LinkedInSession(
            os.getenv('LINKEDIN_EMAIL'),
            os.getenv('LINKEDIN_PASSWORD')
        )
        log("LinkedIn session initialized.")

        log("Connecting to NATS...")
        await nats_manager.connect()
        log("Connected to NATS.")

        log("Connecting to MySQL...")
        await mysql_manager.connect()
        log("Connected to MySQL.")
        
        log("Starting LinkedIn session...")
        linkedin_session.start()
        log("LinkedIn session started successfully.")

        if "linkedin.com/company/" in url:
            log(f"Crawling company URL: {url}")
            crawler = CompanyCrawler(linkedin_session, nats_manager, mysql_manager)
            result = await crawler.crawl_company(url, is_seed=True)
        elif "linkedin.com/in/" in url:
            log(f"Crawling profile URL: {url}")
            crawler = PeopleCrawler(linkedin_session, nats_manager, mysql_manager)
            result = await crawler.crawl_profile(url, is_seed=True)
        else:
            log(f"Invalid URL: {url}. Must be a LinkedIn company or person profile.", "error")
            return

        if result:
            log(f"Successfully crawled: {url}")
        else:
            log(f"Failed to crawl or already exists: {url}")

    except Exception as e:
        log(f"Error during crawl: {str(e)}", "error")
        import traceback
        log(f"Traceback: {traceback.format_exc()}", "error")
    finally:
        log("Cleaning up resources...")
        if mysql_manager:
            await mysql_manager.disconnect()
        if nats_manager:
            await nats_manager.close()
        if linkedin_session:
            linkedin_session.close()
        log("Resources cleaned up.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python cli_crawler.py <linkedin_url>")
        sys.exit(1)

    url = sys.argv[1]
    
    # Check if required environment variables are set
    required_vars = ['LINKEDIN_EMAIL', 'LINKEDIN_PASSWORD', 'MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE', 'NATS_URL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Error: The following required environment variables are missing: {', '.join(missing_vars)}")
        sys.exit(1)
    
    asyncio.run(run_single_crawl(url))
