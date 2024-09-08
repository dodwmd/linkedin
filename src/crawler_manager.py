from threading import Thread
from shared_data import log, CrawlerState
from flask import flash
from crawler import LinkedInCrawler
from nats_manager import NatsManager
from mysql_manager import MySQLManager
from linkedin_session import LinkedInSession
import asyncio
import os

crawler_thread = None
crawler_state = CrawlerState()

def start_crawler():
    global crawler_thread
    if not crawler_state.is_running():
        crawler_state.set_running()
        crawler_thread = Thread(target=run_crawler_sync, args=(crawler_state,))
        crawler_thread.start()
        log("Crawler started")
        flash('Crawler started successfully', 'success')
        return True
    log("Crawler is already running")
    flash('Crawler is already running', 'info')
    return False

def stop_crawler():
    if crawler_state.is_running():
        crawler_state.set_stop_requested()
        log("Stop request sent to crawler")
        flash('Stop request sent to crawler', 'success')
        
        # Wait for the crawler to actually stop
        if crawler_thread:
            crawler_thread.join(timeout=30)  # Wait up to 30 seconds for the thread to finish
        
        if not crawler_state.is_running():
            log("Crawler has stopped")
            flash('Crawler has stopped', 'success')
            return True
        else:
            log("Crawler did not stop within the expected time", "warning")
            flash('Crawler did not stop within the expected time', 'warning')
            return False
    
    log("Crawler is not running")
    flash('Crawler is not running', 'info')
    return False

def run_crawler_sync(crawler_state: CrawlerState):
    crawler = LinkedInCrawler(NatsManager.get_instance(), MySQLManager(), LinkedInSession(os.getenv('LINKEDIN_EMAIL'), os.getenv('LINKEDIN_PASSWORD')))
    asyncio.run(crawler.run(crawler_state))
