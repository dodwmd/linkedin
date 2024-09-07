from linkedin_scraper import Person
import mysql.connector
from mysql.connector import Error
from shared_data import log
from nats_manager import NatsManager
from linkedin_session import LinkedInSession
import json


class PeopleCrawler:
    def __init__(self, linkedin_session: LinkedInSession, nats_manager: NatsManager, db_config):
        self.driver = linkedin_session.get_driver()
        self.nats_manager = nats_manager
        self.db_config = db_config

    async def crawl_profile(self, linkedin_url):
        log(f"Crawling profile: {linkedin_url}")
        try:
            if not await self._is_profile_scanned(linkedin_url):
                person = Person(linkedin_url, driver=self.driver)
                await self._process_person(person)
                await self._process_contacts(person)
                log(f"Profile processed: {linkedin_url}", "debug")
                return person
            else:
                log(f"Profile already scanned, skipping: {linkedin_url}", "debug")
            return None
        except Exception as e:
            log(f"Error crawling profile {linkedin_url}: {str(e)}", "error")
            raise

    async def _is_profile_scanned(self, linkedin_url):
        log(f"Checking if profile has been scanned: {linkedin_url}", "debug")
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            query = "SELECT COUNT(*) FROM linkedin_people WHERE linkedin_url = %s"
            cursor.execute(query, (linkedin_url,))
            result = cursor.fetchone()
            return result[0] > 0
        except Error as e:
            log(f"Error checking if profile is scanned: {e}", "error")
            return False
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    async def _process_person(self, person):
        log(f"Processing person: {person.name}", "debug")
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            query = """INSERT INTO linkedin_people 
                       (name, about, experiences, interests, accomplishments,
                       company, job_title, linkedin_url) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
            values = (
                person.name, person.about, str(person.experiences),
                str(person.interests), str(person.accomplishments),
                person.company, person.job_title, person.linkedin_url
            )
            cursor.execute(query, values)
            connection.commit()
        except Error as e:
            log(f"Error inserting person data: {e}", "error")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    async def _process_contacts(self, person):
        log(f"Processing contacts for: {person.name}", "debug")
        for contact in person.contacts:
            if not await self._is_profile_scanned(contact):
                await self.nats_manager.publish(
                    "linkedin_people_urls", json.dumps({"url": contact})
                )

    async def run(self, initial_url):
        log(f"Starting PeopleCrawler with initial URL: {initial_url}")
        try:
            await self.crawl_profile(initial_url)
        except Exception as e:
            log(f"Error in run method: {str(e)}", "error")
            raise

    async def close(self):
        log("Closing PeopleCrawler...", "debug")
        # No need to close the driver here as it's managed by LinkedInSession
        log("PeopleCrawler closed.")
