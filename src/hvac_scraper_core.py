#!/usr/bin/env python3
"""
HVAC Business Scraper - Core Engine
Advanced Google Maps scraping system for HVAC companies
"""

import asyncio
import json
import logging
import random
import re
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse

import aiohttp
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import phonenumbers
from phonenumbers import NumberParseException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class BusinessInfo:
    """Data class for storing business information"""
    name: str
    address: str = ""
    phone: str = ""
    website: str = ""
    star_rating: float = 0.0
    review_count: int = 0
    hours: str = ""
    category: str = ""
    owner_name: str = ""
    additional_contact: str = ""
    location: str = ""
    scraped_at: str = ""
    google_maps_url: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

class HVACBusinessScraper:
    """Advanced HVAC business scraper with anti-detection measures"""
    
    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        self.headless = headless
        self.proxy = proxy
        self.driver = None
        self.session = None
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ]
        
    def setup_driver(self) -> webdriver.Chrome:
        """Setup Chrome driver with anti-detection measures"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        # Anti-detection measures
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument(f"--user-agent={random.choice(self.user_agents)}")
        
        # Performance optimizations
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--disable-javascript")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-extensions")
        
        if self.proxy:
            chrome_options.add_argument(f"--proxy-server={self.proxy}")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Execute script to remove webdriver property
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    async def setup_session(self) -> aiohttp.ClientSession:
        """Setup aiohttp session for API calls"""
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        session = aiohttp.ClientSession(
            headers=headers,
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        return session
    
    def human_delay(self, min_delay: float = 1.0, max_delay: float = 3.0):
        """Add human-like delays between actions"""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
    
    def extract_phone_number(self, text: str) -> str:
        """Extract and validate phone number from text"""
        if not text:
            return ""
        
        # Common phone number patterns
        patterns = [
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\+1[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                phone = match.group(0)
                try:
                    # Validate using phonenumbers library
                    parsed = phonenumbers.parse(phone, "US")
                    if phonenumbers.is_valid_number(parsed):
                        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
                except NumberParseException:
                    continue
        
        return ""
    
    def extract_owner_name(self, business_name: str, reviews_text: str = "") -> str:
        """Extract owner name from business information"""
        owner_patterns = [
            r'Owner[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)[,\s]+Owner',
            r'Response from the owner[:\s]+([A-Z][a-z]+)',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)[,\s]+responded',
        ]
        
        # Check business name for owner indicators
        if any(word in business_name.lower() for word in ['llc', 'inc', 'corp']):
            # Look for personal names in business name
            name_pattern = r'([A-Z][a-z]+\s+[A-Z][a-z]+)'
            match = re.search(name_pattern, business_name)
            if match:
                potential_name = match.group(1)
                # Filter out common business words
                business_words = ['heating', 'cooling', 'hvac', 'air', 'service', 'company', 'systems']
                if not any(word in potential_name.lower() for word in business_words):
                    return potential_name
        
        # Check reviews for owner responses
        for pattern in owner_patterns:
            match = re.search(pattern, reviews_text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return ""
    
    def search_google_maps(self, query: str, max_results: int = 50) -> List[Dict]:
        """Search Google Maps for businesses"""
        logger.info(f"Searching Google Maps for: {query}")
        
        if not self.driver:
            self.driver = self.setup_driver()
        
        try:
            # Navigate to Google Maps
            self.driver.get("https://maps.google.com")
            self.human_delay(2, 4)
            
            # Find search box and enter query
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "searchboxinput"))
            )
            
            search_box.clear()
            search_box.send_keys(query)
            self.human_delay(1, 2)
            search_box.send_keys(Keys.RETURN)
            
            # Wait for results to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-value='Search results']"))
            )
            self.human_delay(3, 5)
            
            businesses = []
            processed_names = set()
            
            # Scroll and collect results
            for scroll_attempt in range(10):  # Limit scrolling attempts
                try:
                    # Find business listings
                    results = self.driver.find_elements(By.CSS_SELECTOR, "[data-result-index]")
                    
                    for result in results:
                        if len(businesses) >= max_results:
                            break
                        
                        try:
                            # Extract basic information
                            name_element = result.find_element(By.CSS_SELECTOR, "[data-value='Search results'] h3")
                            business_name = name_element.text.strip()
                            
                            # Skip duplicates
                            if business_name in processed_names:
                                continue
                            processed_names.add(business_name)
                            
                            # Filter for HVAC-related businesses
                            hvac_keywords = ['hvac', 'heating', 'cooling', 'air conditioning', 'furnace', 'heat pump']
                            if not any(keyword in business_name.lower() for keyword in hvac_keywords):
                                continue
                            
                            # Click on business to get detailed info
                            name_element.click()
                            self.human_delay(2, 4)
                            
                            # Extract detailed information
                            business_info = self.extract_business_details()
                            business_info['name'] = business_name
                            business_info['google_maps_url'] = self.driver.current_url
                            
                            businesses.append(business_info)
                            logger.info(f"Extracted: {business_name}")
                            
                            # Go back to results
                            self.driver.back()
                            self.human_delay(2, 3)
                            
                        except Exception as e:
                            logger.warning(f"Error extracting business info: {str(e)}")
                            continue
                    
                    # Scroll down to load more results
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    self.human_delay(2, 4)
                    
                    # Check if we've reached the end
                    if len(results) == 0:
                        break
                        
                except Exception as e:
                    logger.warning(f"Error during scroll attempt {scroll_attempt}: {str(e)}")
                    break
            
            logger.info(f"Found {len(businesses)} HVAC businesses")
            return businesses
            
        except Exception as e:
            logger.error(f"Error searching Google Maps: {str(e)}")
            return []
    
    def extract_business_details(self) -> Dict:
        """Extract detailed business information from Google Maps business page"""
        details = {
            'address': '',
            'phone': '',
            'website': '',
            'star_rating': 0.0,
            'review_count': 0,
            'hours': '',
            'category': '',
            'owner_name': '',
            'additional_contact': ''
        }
        
        try:
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-value='Search results']"))
            )
            
            # Extract address
            try:
                address_element = self.driver.find_element(By.CSS_SELECTOR, "[data-item-id='address']")
                details['address'] = address_element.text.strip()
            except NoSuchElementException:
                pass
            
            # Extract phone number
            try:
                phone_element = self.driver.find_element(By.CSS_SELECTOR, "[data-item-id*='phone']")
                phone_text = phone_element.text.strip()
                details['phone'] = self.extract_phone_number(phone_text)
            except NoSuchElementException:
                pass
            
            # Extract website
            try:
                website_element = self.driver.find_element(By.CSS_SELECTOR, "[data-item-id='authority']")
                details['website'] = website_element.get_attribute('href') or website_element.text.strip()
            except NoSuchElementException:
                pass
            
            # Extract rating and review count
            try:
                rating_element = self.driver.find_element(By.CSS_SELECTOR, "[jsaction*='pane.rating']")
                rating_text = rating_element.text.strip()
                
                # Parse rating (e.g., "4.5 (123 reviews)")
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    details['star_rating'] = float(rating_match.group(1))
                
                review_match = re.search(r'\((\d+)', rating_text)
                if review_match:
                    details['review_count'] = int(review_match.group(1))
                    
            except NoSuchElementException:
                pass
            
            # Extract business hours
            try:
                hours_element = self.driver.find_element(By.CSS_SELECTOR, "[data-item-id='oh']")
                details['hours'] = hours_element.text.strip()
            except NoSuchElementException:
                pass
            
            # Extract business category
            try:
                category_element = self.driver.find_element(By.CSS_SELECTOR, "[jsaction*='pane.rating.category']")
                details['category'] = category_element.text.strip()
            except NoSuchElementException:
                details['category'] = 'HVAC'
            
            # Try to extract owner name from reviews
            try:
                # Look for owner responses in reviews
                review_elements = self.driver.find_elements(By.CSS_SELECTOR, "[data-review-id]")
                reviews_text = ""
                for review in review_elements[:5]:  # Check first 5 reviews
                    reviews_text += review.text + " "
                
                details['owner_name'] = self.extract_owner_name(details.get('name', ''), reviews_text)
            except Exception:
                pass
            
        except Exception as e:
            logger.warning(f"Error extracting business details: {str(e)}")
        
        return details
    
    async def enrich_business_data(self, business: Dict) -> Dict:
        """Enrich business data with additional information from web sources"""
        if not self.session:
            self.session = await self.setup_session()
        
        enriched = business.copy()
        
        # Try to get additional info from website
        if business.get('website'):
            try:
                async with self.session.get(business['website']) as response:
                    if response.status == 200:
                        content = await response.text()
                        soup = BeautifulSoup(content, 'html.parser')
                        
                        # Look for contact information
                        contact_info = self.extract_contact_from_website(soup)
                        if contact_info:
                            enriched['additional_contact'] = contact_info
                        
                        # Look for owner information
                        if not enriched.get('owner_name'):
                            owner_info = self.extract_owner_from_website(soup)
                            if owner_info:
                                enriched['owner_name'] = owner_info
                                
            except Exception as e:
                logger.warning(f"Error enriching data from website {business.get('website')}: {str(e)}")
        
        return enriched
    
    def extract_contact_from_website(self, soup: BeautifulSoup) -> str:
        """Extract additional contact information from website"""
        contact_info = []
        
        # Look for email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, soup.get_text())
        if emails:
            contact_info.extend([f"Email: {email}" for email in emails[:2]])  # Limit to 2 emails
        
        # Look for additional phone numbers
        phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        phones = re.findall(phone_pattern, soup.get_text())
        validated_phones = []
        for phone in phones:
            validated = self.extract_phone_number(phone)
            if validated and validated not in validated_phones:
                validated_phones.append(validated)
        
        if validated_phones:
            contact_info.extend([f"Phone: {phone}" for phone in validated_phones[:2]])
        
        return "; ".join(contact_info)
    
    def extract_owner_from_website(self, soup: BeautifulSoup) -> str:
        """Extract owner information from website"""
        # Look in about page, team page, etc.
        about_sections = soup.find_all(['div', 'section'], class_=re.compile(r'about|team|owner|founder', re.I))
        
        for section in about_sections:
            text = section.get_text()
            owner_name = self.extract_owner_name("", text)
            if owner_name:
                return owner_name
        
        return ""
    
    async def scrape_location(self, location: str, business_type: str = "HVAC") -> List[BusinessInfo]:
        """Scrape HVAC businesses for a specific location"""
        logger.info(f"Starting scrape for {location}")
        
        # Construct search queries
        queries = [
            f"{business_type} companies in {location}",
            f"heating and cooling {location}",
            f"air conditioning {location}",
            f"furnace repair {location}",
            f"{business_type} contractors {location}"
        ]
        
        all_businesses = []
        processed_names = set()
        
        for query in queries:
            try:
                businesses = self.search_google_maps(query, max_results=20)
                
                for business in businesses:
                    business_name = business.get('name', '')
                    if business_name and business_name not in processed_names:
                        processed_names.add(business_name)
                        
                        # Enrich with additional data
                        enriched_business = await self.enrich_business_data(business)
                        
                        # Create BusinessInfo object
                        business_info = BusinessInfo(
                            name=enriched_business.get('name', ''),
                            address=enriched_business.get('address', ''),
                            phone=enriched_business.get('phone', ''),
                            website=enriched_business.get('website', ''),
                            star_rating=enriched_business.get('star_rating', 0.0),
                            review_count=enriched_business.get('review_count', 0),
                            hours=enriched_business.get('hours', ''),
                            category=enriched_business.get('category', 'HVAC'),
                            owner_name=enriched_business.get('owner_name', ''),
                            additional_contact=enriched_business.get('additional_contact', ''),
                            location=location,
                            scraped_at=datetime.now().isoformat(),
                            google_maps_url=enriched_business.get('google_maps_url', '')
                        )
                        
                        all_businesses.append(business_info)
                
                # Add delay between queries
                self.human_delay(5, 10)
                
            except Exception as e:
                logger.error(f"Error processing query '{query}': {str(e)}")
                continue
        
        logger.info(f"Completed scrape for {location}: {len(all_businesses)} businesses found")
        return all_businesses
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()
            self.driver = None
        
        if self.session:
            asyncio.create_task(self.session.close())
            self.session = None

# Example usage and testing
async def main():
    """Example usage of the HVAC scraper"""
    scraper = HVACBusinessScraper(headless=True)
    
    try:
        # Test scraping a single location
        businesses = await scraper.scrape_location("Kuna, Idaho")
        
        print(f"Found {len(businesses)} HVAC businesses in Kuna, Idaho")
        
        # Display results
        for business in businesses[:5]:  # Show first 5
            print(f"\nBusiness: {business.name}")
            print(f"Phone: {business.phone}")
            print(f"Reviews: {business.review_count}")
            print(f"Rating: {business.star_rating}")
            print(f"Owner: {business.owner_name}")
            
    finally:
        scraper.cleanup()

if __name__ == "__main__":
    asyncio.run(main())

