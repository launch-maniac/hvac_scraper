"""
Scraping Job Model
Database model for managing HVAC scraping jobs
"""

from datetime import datetime
from enum import Enum
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import JSON
import json

db = SQLAlchemy()

class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ScrapingJob(db.Model):
    """Model for tracking scraping jobs"""
    __tablename__ = 'scraping_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    job_name = db.Column(db.String(200), nullable=False)
    locations = db.Column(JSON, nullable=False)  # List of locations to scrape
    business_type = db.Column(db.String(100), default='HVAC')
    max_reviews = db.Column(db.Integer, default=20)
    min_quality_score = db.Column(db.Float, default=40.0)
    
    # Job status and timing
    status = db.Column(db.Enum(JobStatus), default=JobStatus.PENDING)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Results
    total_businesses_found = db.Column(db.Integer, default=0)
    businesses_meeting_criteria = db.Column(db.Integer, default=0)
    
    # File paths for generated reports
    excel_report_path = db.Column(db.String(500), nullable=True)
    csv_report_path = db.Column(db.String(500), nullable=True)
    json_report_path = db.Column(db.String(500), nullable=True)
    
    # Error information
    error_message = db.Column(db.Text, nullable=True)
    
    # Configuration
    config = db.Column(JSON, nullable=True)  # Additional configuration options
    
    def to_dict(self):
        """Convert job to dictionary"""
        return {
            'id': self.id,
            'job_name': self.job_name,
            'locations': self.locations,
            'business_type': self.business_type,
            'max_reviews': self.max_reviews,
            'min_quality_score': self.min_quality_score,
            'status': self.status.value if self.status else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'total_businesses_found': self.total_businesses_found,
            'businesses_meeting_criteria': self.businesses_meeting_criteria,
            'excel_report_path': self.excel_report_path,
            'csv_report_path': self.csv_report_path,
            'json_report_path': self.json_report_path,
            'error_message': self.error_message,
            'config': self.config
        }

class BusinessData(db.Model):
    """Model for storing scraped business data"""
    __tablename__ = 'business_data'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('scraping_jobs.id'), nullable=False)
    
    # Business information
    name = db.Column(db.String(300), nullable=False)
    address = db.Column(db.String(500), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    website = db.Column(db.String(500), nullable=True)
    
    # Review and rating data
    star_rating = db.Column(db.Float, default=0.0)
    review_count = db.Column(db.Integer, default=0)
    
    # Additional information
    hours = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=True)
    owner_name = db.Column(db.String(200), nullable=True)
    additional_contact = db.Column(db.Text, nullable=True)
    
    # Location and metadata
    location = db.Column(db.String(200), nullable=False)
    google_maps_url = db.Column(db.String(1000), nullable=True)
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Quality metrics
    priority_score = db.Column(db.Integer, default=0)
    data_quality_score = db.Column(db.Float, default=0.0)
    
    # Relationship
    job = db.relationship('ScrapingJob', backref=db.backref('businesses', lazy=True))
    
    def to_dict(self):
        """Convert business to dictionary"""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'name': self.name,
            'address': self.address,
            'phone': self.phone,
            'website': self.website,
            'star_rating': self.star_rating,
            'review_count': self.review_count,
            'hours': self.hours,
            'category': self.category,
            'owner_name': self.owner_name,
            'additional_contact': self.additional_contact,
            'location': self.location,
            'google_maps_url': self.google_maps_url,
            'scraped_at': self.scraped_at.isoformat() if self.scraped_at else None,
            'priority_score': self.priority_score,
            'data_quality_score': self.data_quality_score
        }

