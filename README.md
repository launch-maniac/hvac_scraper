# HVAC Business Scraper 🏠🔧

> Professional lead generation tool for HVAC businesses with automated Google Maps scraping and intelligent contact discovery.

[![Deploy to Google Cloud](https://github.com/launch-maniac/hvac_scraper/actions/workflows/deploy.yml/badge.svg)](https://github.com/launch-maniac/hvac_scraper/actions/workflows/deploy.yml)
[![Tests](https://github.com/launch-maniac/hvac_scraper/actions/workflows/tests.yml/badge.svg)](https://github.com/launch-maniac/hvac_scraper/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Features

- **Automated Lead Generation** - Find HVAC companies with low review counts
- **Contact Discovery** - Extract phone numbers and owner names  
- **Professional Reports** - Excel spreadsheets ready for sales teams
- **Multi-User Support** - Team access with role-based permissions
- **Google Workspace SSO** - Seamless integration with existing accounts
- **Mobile Optimized** - Perfect for sales teams on the go

## 🚀 Quick Start

### Option 1: Deploy to Google Cloud
```bash
./scripts/deploy-to-gcp.sh
```

### Option 2: Local Development
```bash
git clone https://github.com/launch-maniac/hvac_scraper.git
cd hvac_scraper
./scripts/start.sh
```

### Option 3: Deploy to Your Server
```bash
./scripts/deploy-to-n8n-server.sh
```

## 📊 Results

Based on real usage data:
- **24+ HVAC companies** with phone numbers per search
- **87.5% success rate** for finding owner names
- **0-3 review companies** prioritized for highest conversion
- **Professional Excel reports** ready for CRM import

## 🔐 Default Login

- **Username**: Jake
- **Password**: JakeWhitbeck

*Change these credentials in production!*

## 🛠️ Tech Stack

- **Backend**: Python, Flask, SQLAlchemy
- **Frontend**: HTML5, Tailwind CSS, JavaScript
- **Scraping**: Selenium, Chrome WebDriver
- **Database**: SQLite (development), PostgreSQL (production)
- **Deployment**: Docker, Google Cloud Run, GitHub Actions

## 📖 Documentation

- [Deployment Guide](docs/deployment.md)
- [User Manual](docs/user-guide.md)
- [API Reference](docs/api-reference.md)
- [Troubleshooting](docs/troubleshooting.md)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Made with ❤️ for HVAC sales teams**
