import asyncio
from threading import Thread
from shared_data import log, CrawlerState
from flask import flash
from crawler import LinkedInCrawler
from nats_manager import NatsManager
from mysql_manager import MySQLManager
from linkedin_session import LinkedInSession
import os
import threading
import traceback
import concurrent.futures

crawler_thread = None
crawler_state = CrawlerState()
stop_event = threading.Event()

async def run_crawler_async(crawler_state: CrawlerState, stop_event: threading.Event):
    log("Entering run_crawler_async")
    nats_manager = NatsManager()
    mysql_manager = MySQLManager()
    linkedin_session = LinkedInSession(os.getenv('LINKEDIN_EMAIL'), os.getenv('LINKEDIN_PASSWORD'))
    
    try:
        log("Connecting to MySQL")
        await mysql_manager.connect()
        log("Connected to MySQL")
        crawler = LinkedInCrawler(nats_manager, mysql_manager, linkedin_session)
        log("Created LinkedInCrawler instance")
        log("Starting crawler.run")
        await crawler.run(crawler_state, stop_event)
        log("Finished crawler.run")
    except asyncio.CancelledError:
        log("run_crawler_async was cancelled", "warning")
    except Exception as e:
        log(f"Error in run_crawler_async: {str(e)}", "error")
        log(f"Traceback: {traceback.format_exc()}", "error")
    finally:
        log("Disconnecting from MySQL")
        await mysql_manager.disconnect()
        log("Disconnected from MySQL")
        crawler_state.set_stopped()
        stop_event.set()
        log("Exiting run_crawler_async")

def run_crawler_sync(crawler_state: CrawlerState, stop_event: threading.Event):
    try:
        log("Starting run_crawler_sync")
        loop = asyncio.get_event_loop()
        if loop.is_running():
            log("Event loop is already running, using run_coroutine_threadsafe")
            future = asyncio.run_coroutine_threadsafe(run_crawler_async(crawler_state, stop_event), loop)
            try:
                log("Waiting for crawler coroutine to complete")
                result = future.result(timeout=3600)  # Wait for up to 1 hour
                log(f"Crawler coroutine completed successfully with result: {result}")
            except concurrent.futures.TimeoutError:
                log("Crawler coroutine timed out after 1 hour", "warning")
            except concurrent.futures.CancelledError:
                log("Crawler coroutine was cancelled", "warning")
            except Exception as e:
                log(f"Crawler coroutine raised an exception: {str(e)}", "error")
                log(f"Traceback: {traceback.format_exc()}", "error")
        else:
            log("Event loop is not running, using run_until_complete")
            loop.run_until_complete(run_crawler_async(crawler_state, stop_event))
    except Exception as e:
        log(f"Error in run_crawler_sync: {str(e)}", "error")
        log(f"Traceback: {traceback.format_exc()}", "error")
    finally:
        log("run_crawler_sync completed")
        crawler_state.set_stopped()
        stop_event.set()

def start_crawler():
    global crawler_thread, stop_event
    if not crawler_state.is_running():
        if crawler_thread is not None and crawler_thread.is_alive():
            log("Crawler thread is still alive, waiting for it to finish")
            crawler_thread.join(timeout=30)  # Wait up to 30 seconds for the thread to finish
            if crawler_thread.is_alive():
                log("Crawler thread did not finish in time, cannot start a new crawler", "error")
                flash('Cannot start a new crawler, previous crawler is still running', 'error')
                return False
        
        crawler_state.set_running()
        stop_event.clear()
        crawler_thread = Thread(target=run_crawler_sync, args=(crawler_state, stop_event))
        crawler_thread.start()
        log("Crawler thread started")
        flash('Crawler started successfully', 'success')
        return True
    else:
        log("Crawler is already running")
        flash('Crawler is already running', 'info')
        return False

def stop_crawler():
    global crawler_thread
    if crawler_state.is_running():
        crawler_state.set_stop_requested()
        log("Stop request sent to crawler")
        flash('Stop request sent to crawler', 'success')
        
        # Wait for the crawler to actually stop
        stop_event.wait(timeout=30)  # Wait up to 30 seconds for the thread to finish
        
        if not crawler_state.is_running():
            log("Crawler has stopped")
            flash('Crawler has stopped', 'success')
            crawler_thread = None
            return True
        else:
            log("Crawler did not stop within the expected time", "warning")
            flash('Crawler did not stop within the expected time', 'warning')
            return False
    
    log("Crawler is not running")
    flash('Crawler is not running', 'info')
    return False
