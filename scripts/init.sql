CREATE TABLE IF NOT EXISTS linkedin_people (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255),
    about TEXT,
    experiences TEXT,
    educations TEXT,
    interests TEXT,
    accomplishments TEXT,
    company VARCHAR(255),
    job_title VARCHAR(255),
    linkedin_url VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS linkedin_companies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255),
    linkedin_url VARCHAR(255) UNIQUE,
    website VARCHAR(255),
    industry VARCHAR(255),
    company_size VARCHAR(255),
    headquarters VARCHAR(255),
    founded VARCHAR(255),
    specialties TEXT,
    about TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS seed_urls (
    id INT AUTO_INCREMENT PRIMARY KEY,
    url VARCHAR(255) NOT NULL UNIQUE,
    type ENUM('company', 'person') NOT NULL,
    last_crawled DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
