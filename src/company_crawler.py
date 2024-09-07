from linkedin_scraper import Company
import mysql.connector
from mysql.connector import Error
from shared_data import log


class CompanyCrawler:
    def __init__(self, driver, nats_manager, db_config):
        self.driver = driver
        self.nats_manager = nats_manager
        self.db_config = db_config

    async def crawl_company(self, company_url):
        if not await self._is_company_scanned(company_url):
            company = Company(company_url, driver=self.driver)
            await self._process_company(company)
            await self._process_employees(company)
            return company
        return None

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

    async def _process_company(self, company):
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            query = """
                INSERT INTO linkedin_companies
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
        except Error as e:
            log(f"Error inserting company data: {e}", "error")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    async def _process_employees(self, company):
        for employee in company.employees:
            if employee.linkedin_url:
                await self.nats_manager.publish(
                    "linkedin_people_urls", json.dumps({"url": employee.linkedin_url})
                )

    async def run(self, company_url):
        await self.crawl_company(company_url)

    async def close(self):
        log("Closing CompanyCrawler...", "debug")
        # No need to close the driver here as it's managed by LinkedInSession
        log("CompanyCrawler closed.")
