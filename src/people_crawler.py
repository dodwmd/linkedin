from linkedin_scraper import Person
from shared_data import log, emit_crawler_update
from linkedin_session import LinkedInSession
from nats_manager import NatsManager
from mysql_manager import MySQLManager
import json


class PeopleCrawler:
    def __init__(self, linkedin_session: LinkedInSession, nats_manager: NatsManager, mysql_manager: MySQLManager):
        self.driver = linkedin_session.get_driver()
        self.nats_manager = nats_manager
        self.mysql_manager = mysql_manager

    async def crawl_profile(self, linkedin_url, is_seed=False):
        log(f"Crawling profile: {linkedin_url}")
        try:
            if not await self._is_profile_scanned(linkedin_url) or is_seed:
                person = Person(linkedin_url, driver=self.driver)
                await self._process_person(person, is_seed)
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
        query = "SELECT COUNT(*) as count FROM linkedin_people WHERE linkedin_url = %s"
        result = await self.mysql_manager.execute_query(query, (linkedin_url,))
        return result[0]['count'] > 0

    async def _process_person(self, person, is_seed=False):
        query = """
            INSERT INTO linkedin_people 
            (name, about, experiences, interests, accomplishments,
            company, job_title, linkedin_url) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            name = VALUES(name), about = VALUES(about), 
            experiences = VALUES(experiences), interests = VALUES(interests),
            accomplishments = VALUES(accomplishments), company = VALUES(company),
            job_title = VALUES(job_title)
        """
        values = (
            person.name, person.about, json.dumps(person.experiences),
            json.dumps(person.interests), json.dumps(person.accomplishments),
            person.company, person.job_title, person.linkedin_url
        )
        await self.mysql_manager.execute_query(query, values)
        await self._emit_crawler_update(person)

    async def _emit_crawler_update(self, person):
        update_data = {
            "type": "person",
            "name": person.name,
            "linkedin_url": person.linkedin_url
        }
        emit_crawler_update(update_data)

    async def _process_contacts(self, person):
        for contact in person.contacts:
            if not await self._is_profile_scanned(contact):
                await self.nats_manager.publish(
                    "linkedin_people_urls", json.dumps({"url": contact})
                )

    async def run(self, initial_url):
        await self.crawl_profile(initial_url)

    async def close(self):
        log("Closing PeopleCrawler...", "debug")
        log("PeopleCrawler closed.")
