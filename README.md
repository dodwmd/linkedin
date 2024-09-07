# LinkedIn Crawler

## Description
This project is a sophisticated LinkedIn crawler designed to extract and analyze data from LinkedIn profiles and company pages. It uses a combination of web scraping techniques and the LinkedIn API to gather information, which is then stored and processed for various analytical purposes.

## Features
- Asynchronous crawling of LinkedIn profiles and company pages
- Real-time data processing using NATS messaging system
- Data storage in MySQL database
- Web-based dashboard for monitoring and controlling the crawler
- WebSocket support for real-time updates
- Dockerized application for easy deployment and scaling

## Technologies Used
- Python 3.9
- Flask (Web framework)
- Flask-SocketIO (WebSocket support)
- Selenium (Web scraping)
- NATS (Messaging system)
- MySQL (Database)
- Docker (Containerization)
- Uvicorn (ASGI server)

## Prerequisites
- Docker and Docker Compose
- Python 3.9+
- Chrome browser (for Selenium)

## Setup and Installation
1. Clone the repository:
   ```
   git clone https://github.com/yourusername/linkedin-crawler.git
   cd linkedin-crawler
   ```

2. Create a `.env` file in the root directory and add the following environment variables:
   ```
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

4. Access the web dashboard at `http://localhost:9988`

## Usage
1. Start the crawler from the web dashboard
2. Add target URLs for LinkedIn profiles or company pages
3. Monitor the crawling progress and view statistics in real-time
4. Export collected data as needed

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