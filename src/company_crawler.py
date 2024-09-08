from linkedin_scraper import Company
from shared_data import log, emit_crawler_update
from linkedin_session import LinkedInSession
from nats_manager import NatsManager
from mysql_manager import MySQLManager
import json

class CompanyCrawler:
    def __init__(self, linkedin_session: LinkedInSession, nats_manager: NatsManager, mysql_manager: MySQLManager):
        self.driver = linkedin_session.get_driver()
        self.nats_manager = nats_manager
        self.mysql_manager = mysql_manager

    async def crawl_company(self, linkedin_url, is_seed=False):
        log(f"Crawling company: {linkedin_url}")
        try:
            if not await self._is_company_scanned(linkedin_url) or is_seed:
                company = Company(linkedin_url, driver=self.driver)
                await self._process_company(company, is_seed)
                await self._process_employees(company)
                log(f"Company processed: {linkedin_url}", "debug")
                return company
            else:
                log(f"Company already scanned, skipping: {linkedin_url}", "debug")
            return None
        except Exception as e:
            log(f"Error crawling company {linkedin_url}: {str(e)}", "error")
            raise

    async def _is_company_scanned(self, linkedin_url):
        query = "SELECT COUNT(*) as count FROM linkedin_companies WHERE linkedin_url = %s"
        result = await self.mysql_manager.execute_query(query, (linkedin_url,))
        return result[0]['count'] > 0

    async def _process_company(self, company, is_seed=False):
        query = """
            INSERT INTO linkedin_companies
            (name, linkedin_url, website, industry, company_size,
            headquarters, founded, specialties, about)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            name = VALUES(name), website = VALUES(website),
            industry = VALUES(industry), company_size = VALUES(company_size),
            headquarters = VALUES(headquarters), founded = VALUES(founded),
            specialties = VALUES(specialties), about = VALUES(about)
        """
        values = (
            company.name, company.linkedin_url, company.website,
            company.industry, company.company_size, company.headquarters,
            company.founded, json.dumps(company.specialties), company.about
        )
        await self.mysql_manager.execute_query(query, values)
        await self._emit_crawler_update(company)

    async def _emit_crawler_update(self, company):
        update_data = {
            "type": "company",
            "name": company.name,
            "linkedin_url": company.linkedin_url
        }
        emit_crawler_update(update_data)

    async def _process_employees(self, company):
        for employee in company.employees:
            if employee.linkedin_url:
                await self.nats_manager.publish(
                    "linkedin_people_urls", json.dumps({"url": employee.linkedin_url})
                )

    async def run(self, company_url, is_seed=False):
        await self.crawl_company(company_url, is_seed)

    async def close(self):
        log("Closing CompanyCrawler...", "debug")
        log("CompanyCrawler closed.")
