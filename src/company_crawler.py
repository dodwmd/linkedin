from linkedin_scraper import Company
import mysql.connector
from mysql.connector import Error
from shared_data import log, emit_crawler_update
from linkedin_session import LinkedInSession
from nats_manager import NatsManager
import json


class CompanyCrawler:
    def __init__(self, linkedin_session: LinkedInSession, nats_manager: NatsManager, db_config):
        self.driver = linkedin_session.get_driver()
        self.nats_manager = nats_manager
        self.db_config = db_config

    async def crawl_company(self, company_url, is_seed=False):
        log(f"Crawling company: {company_url}")
        try:
            if not await self._is_company_scanned(company_url) or is_seed:
                company = Company(company_url, driver=self.driver)
                await self._process_company(company, is_seed)
                await self._process_employees(company)
                log(f"Company processed: {company_url}", "debug")
                return company
            else:
                log(f"Company already scanned, skipping: {company_url}", "debug")
            return None
        except Exception as e:
            log(f"Error crawling company {company_url}: {str(e)}", "error")
            raise

    async def _is_company_scanned(self, company_url):
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            query = ("SELECT COUNT(*) FROM linkedin_companies "
                     "WHERE linkedin_url = %s")
            cursor.execute(query, (company_url,))
            result = cursor.fetchone()
            return result[0] > 0
        except Error as e:
            log(f"Error checking if company is scanned: {e}", "error")
            return False
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    async def _process_company(self, company, is_seed=False):
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            if is_seed:
                # Update existing record or insert new one
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
            else:
                # Insert new record only
                query = """
                    INSERT IGNORE INTO linkedin_companies
                    (name, linkedin_url, website, industry, company_size,
                    headquarters, founded, specialties, about)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
            
            values = (
                company.name, company.linkedin_url, company.website,
                company.industry, company.company_size, company.headquarters,
                company.founded, ', '.join(company.specialties), company.about
            )
            cursor.execute(query, values)
            connection.commit()

            # Emit crawler update event
            await self._emit_crawler_update(company)
        except Error as e:
            log(f"Error inserting company data: {e}", "error")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

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
        # No need to close the driver here as it's managed by LinkedInSession
        log("CompanyCrawler closed.")
