# 🕸️ LinkedIn Crawler

## 📝 Description
This project is a sophisticated LinkedIn crawler designed to extract and analyze data from LinkedIn profiles and company pages. It uses a combination of web scraping techniques and the LinkedIn API to gather information, which is then stored and processed for various analytical purposes.

This project was developed entirely through AI-assisted programming, using prompts to generate and refine the code. The development process was facilitated by [Cursor](https://cursor.sh/), an AI-powered IDE that enhances coding productivity through intelligent code completion and generation.

## 🤖 AI-Assisted Development
- All code in this project was generated and refined using AI prompts.
- The development process showcases the potential of AI-assisted programming in creating complex applications.
- Cursor IDE was instrumental in streamlining the development workflow and providing intelligent coding assistance.

## 🆕 Recent Updates
- Added a CLI utility for running single crawls
- Updated to use the latest ChromeDriver version from Chrome for Testing
- Improved error handling and logging throughout the application
- Updated GitHub Actions workflow to use latest versions of actions/checkout (v4) and actions/setup-python (v5)
- Integrated linkedin_scraper package for more robust profile scraping

## 🌟 Features
- Asynchronous crawling of LinkedIn profiles and company pages
- CLI utility for single profile/company crawls
- Real-time data processing using NATS messaging system
- Data storage in MySQL database
- Web-based dashboard for monitoring and controlling the crawler
- WebSocket support for real-time updates
- Dockerized application for easy deployment and scaling

## 🛠️ Technologies Used
- Python 3.12
- Flask (Web framework)
- Flask-SocketIO (WebSocket support)
- Selenium (Web scraping)
- NATS (Messaging system)
- MySQL (Database)
- Docker (Containerization)
- Gunicorn with eventlet worker (ASGI server)

## 📋 Prerequisites
- Docker and Docker Compose
- Python 3.12+
- Chrome browser (for Selenium)

## 🚀 Setup and Installation
1. Clone the repository:
   ```
   git clone https://github.com/dodwmd/linkedin.git
   cd linkedin
   ```

2. Create a `.env` file in the root directory and add the following environment variables:
   ```
   LINKEDIN_EMAIL=your_linkedin_email
   LINKEDIN_PASSWORD=your_linkedin_password
   NATS_URL=nats://nats:4222
   MYSQL_HOST=mysql
   MYSQL_USER=your_mysql_user
   MYSQL_PASSWORD=your_mysql_password
   MYSQL_DATABASE=linkedin_crawler
   ```

3. Build and run the Docker containers:
   ```
   docker-compose up --build
   ```

4. Access the web dashboard at `http://localhost:8080`

## 📘 Usage
### Web Dashboard
1. Start the crawler from the web dashboard
2. Add target URLs for LinkedIn profiles or company pages
3. Monitor the crawling progress and view statistics in real-time
4. Export collected data as needed

### CLI Utility
To run a single crawl using the CLI utility:

```
docker-compose run --rm app python src/cli_crawler.py <linkedin_url>
```

Replace `<linkedin_url>` with the URL of the LinkedIn profile or company page you want to crawl.

## Project Structure
- `src/`: Contains the main application code
  - `app.py`: Main application entry point
  - `web_app.py`: Flask application setup
  - `routes.py`: API routes and view functions
  - `crawler.py`: LinkedIn crawler implementation
  - `nats_manager.py`: NATS messaging system manager
  - `mysql_manager.py`: MySQL database manager
- `linkedin_scraper/`: Custom LinkedIn scraping package
- `templates/`: HTML templates for the web dashboard
- `Dockerfile`: Docker configuration for the application
- `docker-compose.yml`: Docker Compose configuration for all services
- `requirements.txt`: Python dependencies

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer
This tool is for educational purposes only. Ensure you comply with LinkedIn's terms of service and robots.txt file when using this crawler.
