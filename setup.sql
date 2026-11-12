CREATE DATABASE IF NOT EXISTS football_league CHARACTER SET utf8mb4;
USE football_league;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(200) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role ENUM('Admin','Viewer') NOT NULL DEFAULT 'Viewer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pools (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category ENUM('Boys','Girls') NOT NULL,
    name VARCHAR(30) NOT NULL,
    UNIQUE KEY uq_pool (category, name)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS teams (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(80) NOT NULL,
    category ENUM('Boys','Girls') NOT NULL,
    pool_id INT NOT NULL,
    coach VARCHAR(80),
    UNIQUE KEY uq_team (name, category),
    FOREIGN KEY (pool_id) REFERENCES pools(id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS fixtures (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category ENUM('Boys','Girls') NOT NULL,
    pool_id INT NOT NULL,
    match_date DATE NOT NULL,
    match_time TIME NOT NULL,
    home_team_id INT NOT NULL,
    away_team_id INT NOT NULL,
    venue VARCHAR(100) NOT NULL DEFAULT 'College Ground',
    home_score INT NULL,
    away_score INT NULL,
    status ENUM('Scheduled','Completed') NOT NULL DEFAULT 'Scheduled',
    FOREIGN KEY (pool_id) REFERENCES pools(id) ON DELETE CASCADE,
    FOREIGN KEY (home_team_id) REFERENCES teams(id) ON DELETE CASCADE,
    FOREIGN KEY (away_team_id) REFERENCES teams(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS announcements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    posted_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS settings (
    setting_name VARCHAR(50) PRIMARY KEY,
    setting_value VARCHAR(200) NOT NULL
) ENGINE=InnoDB;

INSERT IGNORE INTO pools (category, name) VALUES
    ('Boys', 'Pool A'), ('Boys', 'Pool B'),
    ('Girls', 'Pool A'), ('Girls', 'Pool B');
