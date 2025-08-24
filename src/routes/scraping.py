"""
HVAC Scraping API Routes
RESTful API endpoints for managing scraping jobs and retrieving results
"""

import os
import asyncio
import threading
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file
from werkzeug.exceptions import BadRequest, NotFound
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.models.scraping_job import db, ScrapingJob, BusinessData, JobStatus
from hvac_scraper_core import HVACBusinessScraper, BusinessInfo
from data_processor import HVACDataProcessor

scraping_bp = Blueprint('scraping', __name__)

class ScrapingJobManager:
    """Manages scraping job execution"""
    
    def __init__(self):
        self.active_jobs = {}
    
    def start_job(self, job_id: int):
        """Start a scraping job in a separate thread"""
        if job_id in self.active_jobs:
            return False  # Job already running
        
        thread = threading.Thread(target=self._execute_job, args=(job_id,))
        thread.daemon = True
        self.active_jobs[job_id] = thread
        thread.start()
        return True
    
    def _execute_job(self, job_id: int):
        """Execute a scraping job"""
        try:
            # Get job from database
            job = ScrapingJob.query.get(job_id)
            if not job:
                return
            
            # Update job status
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            db.session.commit()
            
            # Initialize scraper
            scraper = HVACBusinessScraper(headless=True)
            all_businesses = []
            
            try:
                # Scrape each location
                for location in job.locations:
                    businesses = asyncio.run(scraper.scrape_location(location, job.business_type))
                    all_businesses.extend(businesses)
                
                # Store businesses in database
                for business in all_businesses:
                    business_data = BusinessData(
                        job_id=job.id,
                        name=business.name,
                        address=business.address,
                        phone=business.phone,
                        website=business.website,
                        star_rating=business.star_rating,
                        review_count=business.review_count,
                        hours=business.hours,
                        category=business.category,
                        owner_name=business.owner_name,
                        additional_contact=business.additional_contact,
                        location=business.location,
                        google_maps_url=business.google_maps_url,
                        scraped_at=datetime.fromisoformat(business.scraped_at) if business.scraped_at else datetime.utcnow()
                    )
                    db.session.add(business_data)
                
                db.session.commit()
                
                # Process and generate reports
                processor = HVACDataProcessor()
                processor.load_businesses(all_businesses)
                
                # Clean and validate data
                cleaned_data = processor.clean_and_validate_data()
                
                # Filter by criteria
                filtered_data = processor.filter_by_criteria(
                    max_reviews=job.max_reviews,
                    min_quality_score=job.min_quality_score
                )
                
                # Generate reports
                reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
                os.makedirs(reports_dir, exist_ok=True)
                
                job_prefix = f"job_{job.id}_{job.job_name.replace(' ', '_')}"
                
                excel_path = os.path.join(reports_dir, f"{job_prefix}.xlsx")
                csv_path = os.path.join(reports_dir, f"{job_prefix}.csv")
                json_path = os.path.join(reports_dir, f"{job_prefix}.json")
                
                processor.generate_excel_report(excel_path, filtered_data)
                processor.export_csv(csv_path, filtered_data)
                processor.export_json(json_path, filtered_data)
                
                # Update job with results
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                job.total_businesses_found = len(all_businesses)
                job.businesses_meeting_criteria = len(filtered_data)
                job.excel_report_path = excel_path
                job.csv_report_path = csv_path
                job.json_report_path = json_path
                
                # Update business data with calculated scores
                for _, row in filtered_data.iterrows():
                    business_record = BusinessData.query.filter_by(
                        job_id=job.id,
                        name=row['name']
                    ).first()
                    if business_record:
                        business_record.priority_score = row['priority_score']
                        business_record.data_quality_score = row['data_quality_score']
                
                db.session.commit()
                
            finally:
                scraper.cleanup()
                
        except Exception as e:
            # Update job with error
            job = ScrapingJob.query.get(job_id)
            if job:
                job.status = JobStatus.FAILED
                job.completed_at = datetime.utcnow()
                job.error_message = str(e)
                db.session.commit()
        
        finally:
            # Remove from active jobs
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]

# Global job manager instance
job_manager = ScrapingJobManager()

@scraping_bp.route('/jobs', methods=['POST'])
def create_job():
    """Create a new scraping job"""
    try:
        data = request.get_json()
        
        if not data:
            raise BadRequest("No JSON data provided")
        
        # Validate required fields
        required_fields = ['job_name', 'locations']
        for field in required_fields:
            if field not in data:
                raise BadRequest(f"Missing required field: {field}")
        
        # Create new job
        job = ScrapingJob(
            job_name=data['job_name'],
            locations=data['locations'],
            business_type=data.get('business_type', 'HVAC'),
            max_reviews=data.get('max_reviews', 20),
            min_quality_score=data.get('min_quality_score', 40.0),
            config=data.get('config', {})
        )
        
        db.session.add(job)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'job': job.to_dict(),
            'message': 'Job created successfully'
        }), 201
        
    except BadRequest as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@scraping_bp.route('/jobs/<int:job_id>/start', methods=['POST'])
def start_job(job_id):
    """Start a scraping job"""
    try:
        job = ScrapingJob.query.get(job_id)
        if not job:
            raise NotFound("Job not found")
        
        if job.status != JobStatus.PENDING:
            return jsonify({
                'success': False,
                'error': f'Job cannot be started. Current status: {job.status.value}'
            }), 400
        
        # Start the job
        if job_manager.start_job(job_id):
            return jsonify({
                'success': True,
                'message': 'Job started successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Job is already running'
            }), 400
            
    except NotFound as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@scraping_bp.route('/jobs', methods=['GET'])
def list_jobs():
    """List all scraping jobs"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status_filter = request.args.get('status')
        
        query = ScrapingJob.query
        
        if status_filter:
            try:
                status_enum = JobStatus(status_filter)
                query = query.filter(ScrapingJob.status == status_enum)
            except ValueError:
                return jsonify({'success': False, 'error': 'Invalid status filter'}), 400
        
        jobs = query.order_by(ScrapingJob.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'jobs': [job.to_dict() for job in jobs.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': jobs.total,
                'pages': jobs.pages,
                'has_next': jobs.has_next,
                'has_prev': jobs.has_prev
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@scraping_bp.route('/jobs/<int:job_id>', methods=['GET'])
def get_job(job_id):
    """Get details of a specific job"""
    try:
        job = ScrapingJob.query.get(job_id)
        if not job:
            raise NotFound("Job not found")
        
        return jsonify({
            'success': True,
            'job': job.to_dict()
        })
        
    except NotFound as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@scraping_bp.route('/jobs/<int:job_id>/businesses', methods=['GET'])
def get_job_businesses(job_id):
    """Get businesses found by a specific job"""
    try:
        job = ScrapingJob.query.get(job_id)
        if not job:
            raise NotFound("Job not found")
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        location_filter = request.args.get('location')
        max_reviews = request.args.get('max_reviews', type=int)
        
        query = BusinessData.query.filter_by(job_id=job_id)
        
        if location_filter:
            query = query.filter(BusinessData.location.ilike(f'%{location_filter}%'))
        
        if max_reviews is not None:
            query = query.filter(BusinessData.review_count <= max_reviews)
        
        businesses = query.order_by(BusinessData.priority_score.asc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'businesses': [business.to_dict() for business in businesses.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': businesses.total,
                'pages': businesses.pages,
                'has_next': businesses.has_next,
                'has_prev': businesses.has_prev
            }
        })
        
    except NotFound as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@scraping_bp.route('/jobs/<int:job_id>/reports/<report_type>', methods=['GET'])
def download_report(job_id, report_type):
    """Download a generated report"""
    try:
        job = ScrapingJob.query.get(job_id)
        if not job:
            raise NotFound("Job not found")
        
        if job.status != JobStatus.COMPLETED:
            return jsonify({
                'success': False,
                'error': 'Job has not completed yet'
            }), 400
        
        # Get the appropriate file path
        file_path = None
        filename = None
        
        if report_type == 'excel':
            file_path = job.excel_report_path
            filename = f"{job.job_name}_report.xlsx"
        elif report_type == 'csv':
            file_path = job.csv_report_path
            filename = f"{job.job_name}_data.csv"
        elif report_type == 'json':
            file_path = job.json_report_path
            filename = f"{job.job_name}_data.json"
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid report type. Use: excel, csv, or json'
            }), 400
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': 'Report file not found'
            }), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename
        )
        
    except NotFound as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@scraping_bp.route('/jobs/<int:job_id>/cancel', methods=['POST'])
def cancel_job(job_id):
    """Cancel a running job"""
    try:
        job = ScrapingJob.query.get(job_id)
        if not job:
            raise NotFound("Job not found")
        
        if job.status not in [JobStatus.PENDING, JobStatus.RUNNING]:
            return jsonify({
                'success': False,
                'error': f'Job cannot be cancelled. Current status: {job.status.value}'
            }), 400
        
        # Update job status
        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        db.session.commit()
        
        # Remove from active jobs if running
        if job_id in job_manager.active_jobs:
            del job_manager.active_jobs[job_id]
        
        return jsonify({
            'success': True,
            'message': 'Job cancelled successfully'
        })
        
    except NotFound as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@scraping_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get overall statistics"""
    try:
        total_jobs = ScrapingJob.query.count()
        completed_jobs = ScrapingJob.query.filter_by(status=JobStatus.COMPLETED).count()
        running_jobs = ScrapingJob.query.filter_by(status=JobStatus.RUNNING).count()
        failed_jobs = ScrapingJob.query.filter_by(status=JobStatus.FAILED).count()
        
        total_businesses = BusinessData.query.count()
        
        # Recent activity
        recent_jobs = ScrapingJob.query.order_by(ScrapingJob.created_at.desc()).limit(5).all()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_jobs': total_jobs,
                'completed_jobs': completed_jobs,
                'running_jobs': running_jobs,
                'failed_jobs': failed_jobs,
                'total_businesses': total_businesses,
                'active_jobs': len(job_manager.active_jobs)
            },
            'recent_jobs': [job.to_dict() for job in recent_jobs]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

