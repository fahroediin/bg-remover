from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import os
import uuid
from rembg import remove
from PIL import Image
import io
import traceback
import logging
import datetime
import base64
from functools import wraps
import threading
import time
from collections import deque
import json

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Configure CORS from environment variables
cors_origins = os.getenv('CORS_ORIGINS', '*')
if cors_origins != '*':
    # Split comma-separated origins and strip whitespace
    cors_origins = [origin.strip() for origin in cors_origins.split(',')]

CORS(app, origins=cors_origins)

# Configure logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'bg_remover.log')

# Create logs directory if it doesn't exist
logs_dir = 'logs'
os.makedirs(logs_dir, exist_ok=True)

# Configure logging format
log_format = '%(asctime)s - %(levelname)s - %(message)s'
date_format = '%Y-%m-%d %H:%M:%S'

# Setup file handler
file_handler = logging.FileHandler(os.path.join(logs_dir, LOG_FILE))
file_handler.setLevel(getattr(logging, LOG_LEVEL.upper()))
file_handler.setFormatter(logging.Formatter(log_format, date_format))

# Setup console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(log_format, date_format))

# Configure root logger
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger(__name__)

# Logging decorator for API endpoints
def log_api_access(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get client information
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
        user_agent = request.headers.get('User-Agent', 'unknown')
        endpoint = request.endpoint
        method = request.method
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Log the access
        logger.info(f"API_ACCESS | {timestamp} | {method} {endpoint} | IP: {client_ip} | UA: {user_agent[:100]}...")

        # Execute the function
        try:
            result = func(*args, **kwargs)

            # Log successful completion
            if hasattr(result, 'status_code'):
                status_code = result.status_code
            else:
                status_code = 200

            logger.info(f"API_SUCCESS | {timestamp} | {method} {endpoint} | IP: {client_ip} | Status: {status_code}")

            return result

        except Exception as e:
            # Log error
            logger.error(f"API_ERROR | {timestamp} | {method} {endpoint} | IP: {client_ip} | Error: {str(e)}")
            raise

    return wrapper

def log_file_upload(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Check if file was uploaded
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename:
                file_size = len(file.read())
                file.seek(0)  # Reset file pointer
                file_ext = file.filename.split('.')[-1].lower() if '.' in file.filename else 'unknown'

                logger.info(f"FILE_UPLOAD | {timestamp} | IP: {client_ip} | File: {file.filename} | Size: {file_size} bytes | Type: {file_ext}")

        # Check if base64 data was provided
        if request.is_json:
            try:
                data = request.get_json()
                if data and 'image' in data:
                    base64_length = len(data['image'])
                    logger.info(f"BASE64_INPUT | {timestamp} | IP: {client_ip} | Base64 Length: {base64_length} characters")
            except:
                pass

        return func(*args, **kwargs)
    return wrapper

# Konfigurasi Flask dari environment variables
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 16777216))  # 16MB default

# Konfigurasi Rate Limiting dari environment variables
RATE_LIMIT_DEFAULT_PER_HOUR = os.getenv('RATE_LIMIT_DEFAULT_PER_HOUR', '1000')
RATE_LIMIT_DEFAULT_PER_MINUTE = os.getenv('RATE_LIMIT_DEFAULT_PER_MINUTE', '100')
RATE_LIMIT_REMOVE_BG_PER_MINUTE = os.getenv('RATE_LIMIT_REMOVE_BG_PER_MINUTE', '10')
RATE_LIMIT_PREVIEW_PER_MINUTE = os.getenv('RATE_LIMIT_PREVIEW_PER_MINUTE', '15')
RATE_LIMIT_BASE64_PER_MINUTE = os.getenv('RATE_LIMIT_BASE64_PER_MINUTE', '12')
RATE_LIMIT_HEALTH_PER_MINUTE = os.getenv('RATE_LIMIT_HEALTH_PER_MINUTE', '200')
RATE_LIMIT_INFO_PER_MINUTE = os.getenv('RATE_LIMIT_INFO_PER_MINUTE', '60')

# Initialize Limiter dengan konfigurasi dari environment
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[f"{RATE_LIMIT_DEFAULT_PER_HOUR} per hour", f"{RATE_LIMIT_DEFAULT_PER_MINUTE} per minute"]
)

# Konfigurasi folder dari environment variables
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER', 'outputs')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}

# Buat folder jika tidak ada
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Queue System Configuration
MAX_CONCURRENT_JOBS = int(os.getenv('MAX_CONCURRENT_JOBS', '3'))  # Maksimal proses bersamaan
MAX_QUEUE_SIZE = int(os.getenv('MAX_QUEUE_SIZE', '20'))  # Maksimal antrian
QUEUE_TIMEOUT = int(os.getenv('QUEUE_TIMEOUT', '300'))  # Timeout dalam detik

# Queue System Implementation
class JobQueue:
    def __init__(self):
        self.queue = deque()
        self.active_jobs = {}  # job_id -> job_info
        self.completed_jobs = {}  # job_id -> job_info (completed/failed)
        self.lock = threading.Lock()
        self.job_counter = 0

    def add_job(self, job_type, client_ip, file_info=None):
        """Add job to queue"""
        with self.lock:
            # Check if queue is full
            if len(self.queue) >= MAX_QUEUE_SIZE:
                return None, "Queue is full. Please try again later."

            # Check if too many jobs from same IP
            active_jobs_from_ip = sum(1 for job in self.active_jobs.values() if job['client_ip'] == client_ip)
            if active_jobs_from_ip >= 2:  # Max 2 jobs per IP
                return None, "Too many concurrent requests from your IP. Please wait."

            self.job_counter += 1
            job_id = f"job_{self.job_counter}_{int(time.time())}"

            job_info = {
                'id': job_id,
                'type': job_type,
                'client_ip': client_ip,
                'file_info': file_info or {},
                'status': 'queued',
                'created_at': datetime.datetime.now(),
                'started_at': None,
                'completed_at': None,
                'progress': 0,
                'message': 'Job queued...'
            }

            self.queue.append(job_id)
            self.active_jobs[job_id] = job_info

            logger.info(f"QUEUE_JOB_ADDED | {job_id} | {job_type} | IP: {client_ip} | Queue position: {len(self.queue)}")

            return job_id, None

    def get_next_job(self):
        """Get next job from queue"""
        with self.lock:
            if not self.queue:
                return None

            # Check if we can start a new job
            if len([j for j in self.active_jobs.values() if j['status'] == 'processing']) >= MAX_CONCURRENT_JOBS:
                return None

            job_id = self.queue.popleft()
            job_info = self.active_jobs.get(job_id)

            if job_info:
                job_info['status'] = 'processing'
                job_info['started_at'] = datetime.datetime.now()
                job_info['message'] = 'Processing...'
                logger.info(f"QUEUE_JOB_STARTED | {job_id} | Active jobs: {len([j for j in self.active_jobs.values() if j['status'] == 'processing'])}")

            return job_id

    def update_job_progress(self, job_id, progress, message=None):
        """Update job progress"""
        with self.lock:
            job_info = self.active_jobs.get(job_id)
            if job_info:
                job_info['progress'] = progress
                if message:
                    job_info['message'] = message

    def complete_job(self, job_id, success=True, error_message=None):
        """Mark job as completed"""
        with self.lock:
            job_info = self.active_jobs.get(job_id)
            if job_info:
                job_info['status'] = 'completed' if success else 'failed'
                job_info['completed_at'] = datetime.datetime.now()
                job_info['progress'] = 100

                if success:
                    job_info['message'] = 'Job completed successfully!'
                else:
                    job_info['message'] = error_message or 'Job failed'

                # Move to completed jobs
                self.completed_jobs[job_id] = job_info
                del self.active_jobs[job_id]

                # Keep only last 100 completed jobs
                if len(self.completed_jobs) > 100:
                    oldest_job = min(self.completed_jobs.keys(),
                                   key=lambda k: self.completed_jobs[k]['completed_at'])
                    del self.completed_jobs[oldest_job]

                logger.info(f"QUEUE_JOB_COMPLETED | {job_id} | Success: {success}")

    def get_job_status(self, job_id):
        """Get job status"""
        with self.lock:
            job_info = self.active_jobs.get(job_id) or self.completed_jobs.get(job_id)
            if job_info:
                return {
                    'id': job_info['id'],
                    'status': job_info['status'],
                    'progress': job_info['progress'],
                    'message': job_info['message'],
                    'created_at': job_info['created_at'].isoformat(),
                    'started_at': job_info['started_at'].isoformat() if job_info['started_at'] else None,
                    'completed_at': job_info['completed_at'].isoformat() if job_info['completed_at'] else None,
                    'queue_position': self.queue.index(job_id) + 1 if job_id in self.queue else 0
                }
            return None

    def get_queue_status(self):
        """Get overall queue status"""
        with self.lock:
            processing_jobs = [j for j in self.active_jobs.values() if j['status'] == 'processing']
            queued_jobs = [j for j in self.active_jobs.values() if j['status'] == 'queued']

            return {
                'queue_length': len(self.queue),
                'active_jobs': len(processing_jobs),
                'queued_jobs': len(queued_jobs),
                'max_concurrent_jobs': MAX_CONCURRENT_JOBS,
                'max_queue_size': MAX_QUEUE_SIZE,
                'total_completed_today': len([j for j in self.completed_jobs.values()
                                            if j['completed_at'] and
                                            j['completed_at'].date() == datetime.datetime.now().date()]),
                'recent_jobs': [
                    {
                        'id': j['id'],
                        'status': j['status'],
                        'progress': j['progress'],
                        'message': j['message']
                    }
                    for j in list(self.active_jobs.values())[:10]  # Show first 10 active jobs
                ]
            }

# Global queue instance
job_queue = JobQueue()

# Background job processor function
def process_background_removal_job(job_id, image_data, filename, optimization_params, output_format):
    """Process background removal job"""
    try:
        # Update progress
        job_queue.update_job_progress(job_id, 10, "Validating image...")

        # Validasi image dengan PIL
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(image_data))
            img.verify()
        except Exception as img_e:
            job_queue.complete_job(job_id, False, f'Invalid image file: {str(img_e)}')
            return

        # Reset BytesIO untuk rembg
        img_data_for_rembg = io.BytesIO(image_data)

        # Update progress
        job_queue.update_job_progress(job_id, 30, "Removing background...")

        # Proses background removal
        logger.info(f"Processing image job {job_id}: {filename}")
        raw_output_data = remove(img_data_for_rembg.read())

        # Update progress
        job_queue.update_job_progress(job_id, 60, "Optimizing output...")

        # Get original image info
        original_info = get_image_info(image_data)

        # Check if this is a preview job
        is_preview = optimization_params.get('is_preview', False)
        is_base64 = job_queue.active_jobs.get(job_id, {}).get('is_base64', False)

        # Set appropriate dimensions for preview jobs
        max_width = optimization_params.get('max_width')
        max_height = optimization_params.get('max_height')

        if is_preview:
            # For preview jobs, cap at smaller sizes
            max_width = min(max_width or 800, 800)
            max_height = min(max_height or 600, 600)

        # Optimize the output
        optimized_output_data = optimize_image(
            raw_output_data,
            output_format=output_format,
            quality=optimization_params.get('quality', 85),
            max_width=max_width,
            max_height=max_height
        )

        # Get optimized image info
        optimized_info = get_image_info(optimized_output_data)

        # Update progress
        job_queue.update_job_progress(job_id, 80, "Saving result...")

        # Generate unique filename
        file_id = job_id.replace('job_', '')  # Use job_id as identifier
        output_filename = f"{file_id}_output.{output_format.lower() if output_format != 'JPG' else 'jpg'}"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)

        # Simpan hasil
        with open(output_path, 'wb') as f:
            f.write(optimized_output_data)

        # Store job result info for retrieval
        job_queue.active_jobs[job_id]['result_info'] = {
            'output_path': output_path,
            'original_info': original_info,
            'optimized_info': optimized_info,
            'filename': filename,
            'output_format': output_format,
            'is_preview': is_preview,
            'is_base64': is_base64
        }

        # For base64 jobs, store the result in memory as well
        if is_base64:
            with open(output_path, 'rb') as f:
                result_base64 = base64.b64encode(f.read()).decode('utf-8')
            job_queue.active_jobs[job_id]['result_base64'] = result_base64

        # Update progress
        job_queue.update_job_progress(job_id, 100, "Job completed successfully!")

        # Complete job
        job_queue.complete_job(job_id, True)

    except Exception as e:
        logger.error(f"Error processing job {job_id}: {str(e)}")
        job_queue.complete_job(job_id, False, f'Processing failed: {str(e)}')

# Queue worker thread
def queue_worker():
    """Background worker that processes jobs from queue"""
    logger.info("Queue worker thread started")

    while True:
        try:
            job_id = job_queue.get_next_job()
            if job_id:
                job_info = job_queue.active_jobs.get(job_id)
                if job_info:
                    logger.info(f"Worker processing job: {job_id}")
                    # Start processing in a separate thread to allow concurrent processing
                    processing_thread = threading.Thread(
                        target=process_background_removal_job,
                        args=(job_id, job_info.get('image_data'), job_info.get('filename'),
                              job_info.get('optimization_params', {}), job_info.get('output_format', 'PNG'))
                    )
                    processing_thread.start()
                else:
                    logger.warning(f"Job {job_id} not found in active jobs")

            time.sleep(1)  # Check for new jobs every second

        except Exception as e:
            logger.error(f"Queue worker error: {str(e)}")
            time.sleep(5)  # Wait before retrying

# Start queue worker thread
worker_thread = threading.Thread(target=queue_worker, daemon=True)
worker_thread.start()

# Add static file serving
@app.route('/static/<path:filename>')
@log_api_access
def serve_static(filename):
    return send_from_directory('static', filename)

# Favicon route
@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.png', mimetype='image/png')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def optimize_image(image_data, output_format='PNG', quality=85, max_width=None, max_height=None):
    """
    Optimize image data with format, quality, and size options

    Args:
        image_data: Raw image data from rembg
        output_format: 'PNG', 'JPEG', or 'WEBP'
        quality: 1-100 for JPEG/WEBP quality
        max_width: Maximum width (None to keep original)
        max_height: Maximum height (None to keep original)

    Returns:
        Optimized image data
    """
    try:
        # Open image with PIL
        img = Image.open(io.BytesIO(image_data))
        original_size = len(image_data)

        # Convert to RGB if needed for JPEG
        if output_format.upper() in ['JPEG', 'JPG'] and img.mode in ['RGBA', 'LA']:
            # Create white background for JPEG
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
            else:
                background.paste(img)
            img = background
        elif output_format.upper() == 'WEBP' and img.mode in ['RGBA', 'LA']:
            # WEBP supports transparency, keep original mode
            pass
        elif output_format.upper() == 'PNG':
            # PNG supports transparency, keep original mode
            pass

        # Resize if max dimensions specified
        if max_width or max_height:
            img.thumbnail((max_width or img.width, max_height or img.height), Image.Resampling.LANCZOS)

        # Save with optimization
        output_io = io.BytesIO()

        if output_format.upper() in ['JPEG', 'JPG']:
            img.save(output_io, format='JPEG', quality=quality, optimize=True, progressive=True)
        elif output_format.upper() == 'WEBP':
            img.save(output_io, format='WEBP', quality=quality, optimize=True, method=6)
        else:  # PNG
            img.save(output_io, format='PNG', optimize=True, compress_level=6)

        output_io.seek(0)
        result = output_io.getvalue()

        # Log compression results for monitoring
        compression_ratio = ((1 - len(result) / original_size) * 100)
        print(f"Image optimized: {original_size} -> {len(result)} bytes ({compression_ratio:.1f}% reduction)")

        return result

    except Exception as e:
        print(f"Error optimizing image: {str(e)}")
        # Return original data if optimization fails
        return image_data

def get_image_info(image_data):
    """Get image information for display"""
    try:
        img = Image.open(io.BytesIO(image_data))
        return {
            'width': img.width,
            'height': img.height,
            'mode': img.mode,
            'format': img.format or 'Unknown',
            'size_bytes': len(image_data),
            'size_mb': round(len(image_data) / (1024 * 1024), 2)
        }
    except:
        return {
            'width': 'Unknown',
            'height': 'Unknown',
            'mode': 'Unknown',
            'format': 'Unknown',
            'size_bytes': len(image_data) if image_data else 0,
            'size_mb': round(len(image_data) / (1024 * 1024), 2) if image_data else 0
        }

# Error handler for rate limiting
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        'error': 'Rate limit exceeded',
        'message': f'Too many requests. {e.description}',
        'retry_after': str(e.retry_after) if hasattr(e, 'retry_after') else None
    }), 429

@app.route('/')
@limiter.limit(f"{RATE_LIMIT_INFO_PER_MINUTE} per minute")
@log_api_access
def index():
    logger.info("WEB_PAGE_REQUEST | Background Remover web page accessed")
    return send_file('index.html')

@app.route('/api')
@limiter.limit(f"{RATE_LIMIT_INFO_PER_MINUTE} per minute")
@log_api_access
def api_info():
    logger.info("API_INFO_REQUEST | Background Remover API info accessed")
    return jsonify({
        'message': 'Background Remover API',
        'version': os.getenv('APP_VERSION', '1.0.0'),
        'app_name': os.getenv('APP_NAME', 'Background Remover API'),
        'queue_config': {
            'max_concurrent_jobs': MAX_CONCURRENT_JOBS,
            'max_queue_size': MAX_QUEUE_SIZE,
            'queue_timeout': QUEUE_TIMEOUT
        },
        'rate_limits': {
            'default': f'{RATE_LIMIT_DEFAULT_PER_HOUR} per hour, {RATE_LIMIT_DEFAULT_PER_MINUTE} per minute',
            'remove_background': f'{RATE_LIMIT_REMOVE_BG_PER_MINUTE} per minute',
            'remove_background_preview': f'{RATE_LIMIT_PREVIEW_PER_MINUTE} per minute',
            'remove_background_base64': f'{RATE_LIMIT_BASE64_PER_MINUTE} per minute',
            'health': f'{RATE_LIMIT_HEALTH_PER_MINUTE} per minute',
            'info': f'{RATE_LIMIT_INFO_PER_MINUTE} per minute'
        },
        'endpoints': {
            'remove_background': '/remove-background (POST) - Direct processing - Download hasil sebagai file',
            'remove_background_preview': '/remove-background-preview (POST) - Direct processing - Preview hasil di browser',
            'remove_background_base64': '/remove-background-base64 (POST) - Direct processing - Input/output base64',
            'queue_remove_background': '/queue/remove-background (POST) - Queue-based processing - Download hasil sebagai file',
            'queue_remove_background_base64': '/queue/remove-background-base64 (POST) - Queue-based processing - Input/output base64',
            'queue_status': '/queue/status (GET) - Get current queue status',
            'job_status': '/queue/job/<job_id> (GET) - Get specific job status',
            'job_result': '/queue/job/<job_id>/result (GET) - Download job result',
            'health': '/health (GET)',
            'info': '/api (GET)'
        }
    })

@app.route('/health')
@limiter.limit(f"{RATE_LIMIT_HEALTH_PER_MINUTE} per minute")
@log_api_access
def health():
    return jsonify({'status': 'healthy', 'service': 'background-remover'})

@app.route('/queue/status')
@limiter.limit(f"{RATE_LIMIT_INFO_PER_MINUTE} per minute")
@log_api_access
def queue_status():
    """Get current queue status"""
    status = job_queue.get_queue_status()
    return jsonify(status)

@app.route('/queue/job/<job_id>')
@limiter.limit(f"{RATE_LIMIT_INFO_PER_MINUTE} per minute")
@log_api_access
def job_status(job_id):
    """Get specific job status"""
    job_info = job_queue.get_job_status(job_id)
    if job_info:
        return jsonify(job_info)
    else:
        return jsonify({'error': 'Job not found'}), 404

@app.route('/queue/job/<job_id>/result')
@limiter.limit(f"{RATE_LIMIT_REMOVE_BG_PER_MINUTE} per minute")
@log_api_access
def get_job_result(job_id):
    """Download job result"""
    # Check if job is completed and has result
    job_info = job_queue.completed_jobs.get(job_id)
    if not job_info or job_info['status'] != 'completed':
        return jsonify({'error': 'Job not completed or not found'}), 404

    result_info = job_info.get('result_info')
    if not result_info:
        return jsonify({'error': 'Job result not available'}), 404

    # Check if this is a base64 job
    is_base64 = job_info.get('is_base64', False)

    if is_base64:
        # For base64 jobs, return the result as base64 JSON
        try:
            output_path = result_info['output_path']
            output_format = result_info['output_format']

            if not os.path.exists(output_path):
                return jsonify({'error': 'Result file not found'}), 404

            # Read the output file and convert to base64
            with open(output_path, 'rb') as f:
                result_base64 = base64.b64encode(f.read()).decode('utf-8')

            # Calculate compression info
            original_info = result_info['original_info']
            optimized_info = result_info['optimized_info']
            compression_ratio = 0
            if original_info['size_bytes'] > 0:
                compression_ratio = round((1 - optimized_info['size_bytes'] / original_info['size_bytes']) * 100, 1)

            return jsonify({
                'success': True,
                'image': result_base64,
                'mimetype': f'image/{output_format.lower()}',
                'info': {
                    'original_size': original_info['size_bytes'],
                    'optimized_size': optimized_info['size_bytes'],
                    'compression_ratio': compression_ratio,
                    'width': optimized_info['width'],
                    'height': optimized_info['height'],
                    'format': output_format,
                    'quality': result_info.get('optimization_params', {}).get('quality', 85)
                }
            })

        except Exception as e:
            logger.error(f"Error serving base64 result for job {job_id}: {str(e)}")
            return jsonify({'error': 'Failed to get result'}), 500

    else:
        # For file jobs, return the file as download
        output_path = result_info['output_path']
        filename = result_info['filename']
        output_format = result_info['output_format']

        if not os.path.exists(output_path):
            return jsonify({'error': 'Result file not found'}), 404

        try:
            # Determine file extension for download
            download_ext = 'jpg' if output_format == 'JPG' else output_format.lower()
            download_name = f"removed_bg_{filename.rsplit('.', 1)[0]}.{download_ext}"

            # Return the file
            response = send_file(
                output_path,
                as_attachment=True,
                download_name=download_name,
                mimetype=f'image/{output_format.lower()}'
            )

            # Add optimization info headers
            original_info = result_info['original_info']
            optimized_info = result_info['optimized_info']
            response.headers['X-Original-Size'] = str(original_info['size_bytes'])
            response.headers['X-Optimized-Size'] = str(optimized_info['size_bytes'])
            response.headers['X-Compression-Ratio'] = str(round((1 - optimized_info['size_bytes'] / original_info['size_bytes']) * 100, 1)) if original_info['size_bytes'] > 0 else '0'
            response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition, X-Original-Size, X-Optimized-Size, X-Compression-Ratio'

            logger.info(f"QUEUE_RESULT_DOWNLOADED | {job_id} | {download_name}")

            return response

        except Exception as e:
            logger.error(f"Error serving result for job {job_id}: {str(e)}")
            return jsonify({'error': 'Failed to download result'}), 500

@app.route('/queue/remove-background', methods=['POST'])
@limiter.limit(f"{RATE_LIMIT_REMOVE_BG_PER_MINUTE} per minute")
@log_api_access
@log_file_upload
def queue_remove_background():
    """Queue-based background removal endpoint"""
    try:
        # Cek apakah file ada di request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']

        # Cek apakah file dipilih
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Validasi file
        if not allowed_file(file.filename):
            return jsonify({
                'error': 'File type not allowed',
                'allowed_types': list(ALLOWED_EXTENSIONS)
            }), 400

        # Get client IP
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))

        # Read image data
        image_data = file.read()

        # Validasi image data
        if not image_data or len(image_data) == 0:
            return jsonify({'error': 'File is empty or corrupted'}), 400

        if len(image_data) < 8:
            return jsonify({'error': 'File too small to be a valid image'}), 400

        # Get optimization parameters
        output_format = request.form.get('format', 'PNG').upper()
        quality = int(request.form.get('quality', 85))
        max_width = request.form.get('max_width')
        max_height = request.form.get('max_height')

        # Validate format
        if output_format not in ['PNG', 'JPEG', 'JPG', 'WEBP']:
            output_format = 'PNG'

        # Validate quality
        quality = max(1, min(100, quality))

        # Parse dimensions
        if max_width:
            try:
                max_width = int(max_width) if max_width and max_width.strip() else None
            except:
                max_width = None

        if max_height:
            try:
                max_height = int(max_height) if max_height and max_height.strip() else None
            except:
                max_height = None

        # Create optimization params
        optimization_params = {
            'format': output_format,
            'quality': quality,
            'max_width': max_width,
            'max_height': max_height
        }

        # Add job to queue
        file_info = {
            'name': file.filename,
            'size': len(image_data),
            'type': file.content_type or 'unknown'
        }

        job_id, error = job_queue.add_job('background_removal', client_ip, file_info)

        if error:
            return jsonify({'error': error}), 429  # Too Many Requests

        # Store job data
        if job_id in job_queue.active_jobs:
            job_queue.active_jobs[job_id]['image_data'] = image_data
            job_queue.active_jobs[job_id]['filename'] = file.filename
            job_queue.active_jobs[job_id]['optimization_params'] = optimization_params
            job_queue.active_jobs[job_id]['output_format'] = output_format

        logger.info(f"QUEUE_JOB_CREATED | {job_id} | {file.filename} | IP: {client_ip}")

        return jsonify({
            'job_id': job_id,
            'message': 'Job added to queue successfully',
            'status_url': f'/queue/job/{job_id}',
            'result_url': f'/queue/job/{job_id}/result',
            'queue_status': job_queue.get_queue_status()
        })

    except Exception as e:
        logger.error(f"Error queuing job: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/queue/remove-background-base64', methods=['POST'])
@limiter.limit(f"{RATE_LIMIT_BASE64_PER_MINUTE} per minute")
@log_api_access
@log_file_upload
def queue_remove_background_base64():
    """Queue-based background removal for base64 input"""
    try:
        data = request.get_json()

        if not data or 'image' not in data:
            return jsonify({'error': 'No image data provided'}), 400

        # Get client IP
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))

        # Decode base64
        try:
            image_data = base64.b64decode(data['image'])
        except:
            return jsonify({'error': 'Invalid base64 data'}), 400

        # Validasi image data
        if not image_data or len(image_data) == 0:
            return jsonify({'error': 'Base64 image data is empty or corrupted'}), 400

        if len(image_data) < 8:
            return jsonify({'error': 'Base64 data too small to be a valid image'}), 400

        # Get optimization parameters
        output_format = data.get('format', 'PNG').upper()
        quality = int(data.get('quality', 85))
        max_width = data.get('max_width')
        max_height = data.get('max_height')

        # Validate format
        if output_format not in ['PNG', 'JPEG', 'JPG', 'WEBP']:
            output_format = 'PNG'

        # Validate quality
        quality = max(1, min(100, quality))

        # Parse dimensions
        if max_width:
            try:
                max_width = int(max_width) if str(max_width).strip() else None
            except:
                max_width = None

        if max_height:
            try:
                max_height = int(max_height) if str(max_height).strip() else None
            except:
                max_height = None

        # Create optimization params
        optimization_params = {
            'format': output_format,
            'quality': quality,
            'max_width': max_width,
            'max_height': max_height
        }

        # Add job to queue
        file_info = {
            'name': 'base64_input',
            'size': len(image_data),
            'type': 'base64'
        }

        job_id, error = job_queue.add_job('background_removal_base64', client_ip, file_info)

        if error:
            return jsonify({'error': error}), 429  # Too Many Requests

        # Store job data
        if job_id in job_queue.active_jobs:
            job_queue.active_jobs[job_id]['image_data'] = image_data
            job_queue.active_jobs[job_id]['filename'] = 'base64_input'
            job_queue.active_jobs[job_id]['optimization_params'] = optimization_params
            job_queue.active_jobs[job_id]['output_format'] = output_format
            job_queue.active_jobs[job_id]['is_base64'] = True
            job_queue.active_jobs[job_id]['original_base64'] = data['image']

        logger.info(f"QUEUE_JOB_CREATED_BASE64 | {job_id} | IP: {client_ip}")

        return jsonify({
            'job_id': job_id,
            'message': 'Base64 job added to queue successfully',
            'status_url': f'/queue/job/{job_id}',
            'result_url': f'/queue/job/{job_id}/result'  # For base64, we'll need to modify result endpoint
        })

    except Exception as e:
        logger.error(f"Error queuing base64 job: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/remove-background', methods=['POST'])
@limiter.limit(f"{RATE_LIMIT_REMOVE_BG_PER_MINUTE} per minute")
@log_api_access
@log_file_upload
def remove_background():
    try:
        # Cek apakah file ada di request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']

        # Cek apakah file dipilih
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Validasi file
        if not allowed_file(file.filename):
            return jsonify({
                'error': 'File type not allowed',
                'allowed_types': list(ALLOWED_EXTENSIONS)
            }), 400

        # Get optimization parameters from form
        output_format = request.form.get('format', 'PNG').upper()
        quality = int(request.form.get('quality', 85))
        max_width = request.form.get('max_width')
        max_height = request.form.get('max_height')

        # Validate format
        if output_format not in ['PNG', 'JPEG', 'JPG', 'WEBP']:
            output_format = 'PNG'

        # Validate quality
        quality = max(1, min(100, quality))

        # Parse dimensions
        if max_width:
            try:
                max_width = int(max_width) if max_width and max_width.strip() else None
            except:
                max_width = None

        if max_height:
            try:
                max_height = int(max_height) if max_height and max_height.strip() else None
            except:
                max_height = None

        print(f"Processing with optimization: {output_format}, quality={quality}, size={max_width}x{max_height}")

        # Generate unique filename
        file_id = str(uuid.uuid4())
        input_filename = f"{file_id}_input.png"
        output_filename = f"{file_id}_output.{output_format.lower() if output_format != 'JPG' else 'jpg'}"
        input_path = os.path.join(UPLOAD_FOLDER, input_filename)
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)

        try:
            # Baca file gambar
            image_data = file.read()

            # Validasi bahwa image_data tidak kosong
            print(f"DEBUG: Image data length: {len(image_data) if image_data else 0}")
            if not image_data or len(image_data) == 0:
                return jsonify({'error': 'File is empty or corrupted'}), 400

            # Validasi bahwa data terlihat seperti data gambar (cek header magic)
            if len(image_data) < 8:
                print(f"DEBUG: Image data too small: {len(image_data)} bytes")
                return jsonify({'error': 'File too small to be a valid image'}), 400

            # Validasi image dengan PIL sebelum memproses dengan rembg
            try:
                from PIL import Image
                img = Image.open(io.BytesIO(image_data))
                img.verify()  # Verifikasi bahwa ini adalah gambar valid
            except Exception as img_e:
                return jsonify({'error': f'Invalid image file: {str(img_e)}'}), 400

            # Reset BytesIO untuk rembg (karena verify() mengkonsumsi stream)
            img_data_for_rembg = io.BytesIO(image_data)

            # Proses background removal
            print(f"Processing image: {file.filename}")
            raw_output_data = remove(img_data_for_rembg.read())

            # Get original image info
            original_info = get_image_info(image_data)
            print(f"Original image: {original_info}")

            # Optimize the output
            optimized_output_data = optimize_image(
                raw_output_data,
                output_format=output_format,
                quality=quality,
                max_width=max_width,
                max_height=max_height
            )

            # Get optimized image info
            optimized_info = get_image_info(optimized_output_data)
            print(f"Optimized image: {optimized_info}")

            # Simpan hasil
            with open(output_path, 'wb') as f:
                f.write(optimized_output_data)

            # Determine file extension for download
            download_ext = 'jpg' if output_format == 'JPG' else output_format.lower()
            download_name = f"removed_bg_{file.filename.rsplit('.', 1)[0]}.{download_ext}"

            # Kembalikan hasil sebagai file
            response = send_file(
                output_path,
                as_attachment=True,
                download_name=download_name,
                mimetype=f'image/{output_format.lower()}'
            )

            # Add optimization info headers
            response.headers['X-Original-Size'] = str(original_info['size_bytes'])
            response.headers['X-Optimized-Size'] = str(optimized_info['size_bytes'])
            response.headers['X-Compression-Ratio'] = str(round((1 - optimized_info['size_bytes'] / original_info['size_bytes']) * 100, 1)) if original_info['size_bytes'] > 0 else '0'

            # Tambahkan headers untuk memastikan download bekerja dengan baik di browser
            response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition, X-Original-Size, X-Optimized-Size, X-Compression-Ratio'
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'

            return response

        except OSError as e:
            # Handle specific OS errors like Invalid argument
            print(f"OS Error processing image: {str(e)}")
            error_msg = f'Failed to process image: {str(e)}'
            if 'Invalid argument' in str(e) or e.errno == 22:
                error_msg = 'Failed to process image: Invalid image data or corrupted file'
            return jsonify({'error': error_msg}), 500
        except Exception as e:
            print(f"Error processing image: {str(e)}")
            return jsonify({'error': f'Failed to process image: {str(e)}'}), 500

        finally:
            # Cleanup input file
            if os.path.exists(input_path):
                os.remove(input_path)

    except Exception as e:
        print(f"Server error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/remove-background-preview', methods=['POST'])
@limiter.limit(f"{RATE_LIMIT_PREVIEW_PER_MINUTE} per minute")
@log_api_access
@log_file_upload
def remove_background_preview():
    """
    Endpoint untuk background removal yang otomatis menggunakan queue
    Jika tidak ada antrian, langsung proses. Jika ada antrian, kembalikan job ID.
    """
    try:
        # Cek apakah file ada di request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']

        # Cek apakah file dipilih
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Validasi file
        if not allowed_file(file.filename):
            return jsonify({
                'error': 'File type not allowed',
                'allowed_types': list(ALLOWED_EXTENSIONS)
            }), 400

        # Get client IP
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))

        # Get optimization parameters from form
        output_format = request.form.get('format', 'PNG').upper()
        quality = int(request.form.get('quality', 85))
        max_width = request.form.get('max_width')
        max_height = request.form.get('max_height')

        # Validate format
        if output_format not in ['PNG', 'JPEG', 'JPG', 'WEBP']:
            output_format = 'PNG'

        # Validate quality
        quality = max(1, min(100, quality))

        # Parse dimensions
        if max_width:
            try:
                max_width = int(max_width) if max_width and max_width.strip() else None
            except:
                max_width = None

        if max_height:
            try:
                max_height = int(max_height) if max_height and max_height.strip() else None
            except:
                max_height = None

        # Read image data
        image_data = file.read()

        # Validasi image data
        if not image_data or len(image_data) == 0:
            return jsonify({'error': 'File is empty or corrupted'}), 400

        if len(image_data) < 8:
            return jsonify({'error': 'File too small to be a valid image'}), 400

        # Check if we can process immediately (no active jobs or under limit)
        status = job_queue.get_queue_status()

        # For small images and no queue, process immediately
        if (status['active_jobs'] < MAX_CONCURRENT_JOBS and
            status['queue_length'] == 0 and
            len(image_data) < 5 * 1024 * 1024):  # Less than 5MB
            try:
                # Validasi image dengan PIL
                from PIL import Image
                img = Image.open(io.BytesIO(image_data))
                img.verify()
            except Exception as img_e:
                return jsonify({'error': f'Invalid image file: {str(img_e)}'}), 400

            # Reset BytesIO untuk rembg
            img_data_for_rembg = io.BytesIO(image_data)

            # Proses langsung
            print(f"Processing image directly (no queue): {file.filename}")
            raw_output_data = remove(img_data_for_rembg.read())

            # Optimize for preview (cap at smaller sizes)
            preview_max_width = min(max_width or 800, 800)
            preview_max_height = min(max_height or 600, 600)

            optimized_output_data = optimize_image(
                raw_output_data,
                output_format=output_format,
                quality=quality,
                max_width=preview_max_width,
                max_height=preview_max_height
            )

            optimized_info = get_image_info(optimized_output_data)

            # Return image directly
            response = send_file(
                io.BytesIO(optimized_output_data),
                mimetype=f'image/{output_format.lower()}',
                as_attachment=False,
                download_name=None
            )

            response.headers['X-Image-Width'] = str(optimized_info['width'])
            response.headers['X-Image-Height'] = str(optimized_info['height'])
            response.headers['X-Image-Size'] = str(optimized_info['size_bytes'])
            response.headers['X-Processing-Type'] = 'direct'

            logger.info(f"DIRECT_PROCESSING | {file.filename} | IP: {client_ip}")

            return response

        # Add to queue if we can't process immediately
        else:
            # Create optimization params
            optimization_params = {
                'format': output_format,
                'quality': quality,
                'max_width': max_width,
                'max_height': max_height,
                'is_preview': True  # Mark as preview job
            }

            file_info = {
                'name': file.filename,
                'size': len(image_data),
                'type': file.content_type or 'unknown'
            }

            job_id, error = job_queue.add_job('background_removal_preview', client_ip, file_info)

            if error:
                return jsonify({'error': error}), 429

            # Store job data
            if job_id in job_queue.active_jobs:
                job_queue.active_jobs[job_id]['image_data'] = image_data
                job_queue.active_jobs[job_id]['filename'] = file.filename
                job_queue.active_jobs[job_id]['optimization_params'] = optimization_params
                job_queue.active_jobs[job_id]['output_format'] = output_format

            logger.info(f"QUEUE_JOB_CREATED_PREVIEW | {job_id} | {file.filename} | IP: {client_ip}")

            return jsonify({
                'job_id': job_id,
                'message': 'Job added to queue successfully',
                'status_url': f'/queue/job/{job_id}',
                'result_url': f'/queue/job/{job_id}/result',
                'queue_position': status['queue_length'] + 1,
                'processing_type': 'queued'
            })

    except Exception as e:
        logger.error(f"Error in preview endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/read-file', methods=['POST'])
@limiter.limit(f"{RATE_LIMIT_BASE64_PER_MINUTE} per minute")
@log_api_access
@log_file_upload
def read_file():
    try:
        data = request.get_json()

        if not data or 'file_path' not in data:
            return jsonify({'error': 'No file path provided'}), 400

        file_path = data['file_path']
        logger.info(f"FILE_READ_REQUEST | Attempting to read file: {file_path}")

        # Security: Validate file path to prevent directory traversal
        import os
        import re

        # Basic path validation - only allow certain extensions and no directory traversal
        if '..' in file_path or file_path.startswith('/') or ':' not in file_path:
            return jsonify({'error': 'Invalid file path format'}), 400

        # Only allow .txt files for security
        if not file_path.lower().endswith('.txt'):
            return jsonify({'error': 'Only .txt files are allowed'}), 400

        # Check if file exists and is within reasonable size
        try:
            if not os.path.exists(file_path):
                return jsonify({'error': f'File not found: {file_path}'}), 404

            file_size = os.path.getsize(file_path)
            if file_size > 16 * 1024 * 1024:  # 16MB limit
                return jsonify({'error': 'File too large (max 16MB)'}), 400

            if file_size == 0:
                return jsonify({'error': 'File is empty'}), 400

        except Exception as e:
            logger.error(f"FILE_ACCESS_ERROR | {str(e)}")
            return jsonify({'error': f'Cannot access file: {str(e)}'}), 500

        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            logger.info(f"FILE_READ_SUCCESS | File read successfully: {file_path} ({file_size} bytes)")

            return jsonify({
                'success': True,
                'content': content,
                'file_size': file_size
            })

        except UnicodeDecodeError:
            return jsonify({'error': 'File encoding error. Please ensure the file is UTF-8 encoded.'}), 400
        except Exception as e:
            logger.error(f"FILE_READ_ERROR | {str(e)}")
            return jsonify({'error': f'Error reading file: {str(e)}'}), 500

    except Exception as e:
        logger.error(f"SERVER_ERROR | {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/remove-background-base64', methods=['POST'])
@limiter.limit(f"{RATE_LIMIT_BASE64_PER_MINUTE} per minute")
@log_api_access
@log_file_upload
def remove_background_base64():
    """
    Endpoint untuk background removal dengan base64 yang otomatis menggunakan queue
    Jika tidak ada antrian, langsung proses. Jika ada antrian, kembalikan job ID.
    """
    try:
        data = request.get_json()

        if not data or 'image' not in data:
            return jsonify({'error': 'No image data provided'}), 400

        # Get client IP
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))

        # Get optimization parameters
        output_format = data.get('format', 'PNG').upper()
        quality = int(data.get('quality', 85))
        max_width = data.get('max_width')
        max_height = data.get('max_height')

        # Validate format
        if output_format not in ['PNG', 'JPEG', 'JPG', 'WEBP']:
            output_format = 'PNG'

        # Validate quality
        quality = max(1, min(100, quality))

        # Parse dimensions
        if max_width:
            try:
                max_width = int(max_width) if str(max_width).strip() else None
            except:
                max_width = None

        if max_height:
            try:
                max_height = int(max_height) if str(max_height).strip() else None
            except:
                max_height = None

        # Decode base64
        try:
            image_data = base64.b64decode(data['image'])
        except:
            return jsonify({'error': 'Invalid base64 data'}), 400

        # Validasi image data
        if not image_data or len(image_data) == 0:
            return jsonify({'error': 'Base64 image data is empty or corrupted'}), 400

        if len(image_data) < 8:
            return jsonify({'error': 'Base64 data too small to be a valid image'}), 400

        # Check if we can process immediately
        status = job_queue.get_queue_status()

        # For small images and no queue, process immediately
        if (status['active_jobs'] < MAX_CONCURRENT_JOBS and
            status['queue_length'] == 0 and
            len(image_data) < 5 * 1024 * 1024):  # Less than 5MB
            try:
                # Validasi image dengan PIL
                from PIL import Image
                img = Image.open(io.BytesIO(image_data))
                img.verify()
            except Exception as img_e:
                return jsonify({'error': f'Invalid base64 image: {str(img_e)}'}), 400

            # Reset BytesIO untuk rembg
            img_data_for_rembg = io.BytesIO(image_data)

            # Proses langsung
            print("Processing base64 image directly (no queue)")
            raw_output_data = remove(img_data_for_rembg.read())

            # Get original image info
            original_info = get_image_info(image_data)

            # Optimize the output
            optimized_output_data = optimize_image(
                raw_output_data,
                output_format=output_format,
                quality=quality,
                max_width=max_width,
                max_height=max_height
            )

            # Get optimized image info
            optimized_info = get_image_info(optimized_output_data)

            # Encode hasil ke base64
            result_base64 = base64.b64encode(optimized_output_data).decode('utf-8')

            # Calculate compression info
            compression_ratio = 0
            if original_info['size_bytes'] > 0:
                compression_ratio = round((1 - optimized_info['size_bytes'] / original_info['size_bytes']) * 100, 1)

            logger.info(f"DIRECT_PROCESSING_BASE64 | IP: {client_ip} | Size: {len(image_data)} bytes")

            return jsonify({
                'success': True,
                'image': result_base64,
                'mimetype': f'image/{output_format.lower()}',
                'processing_type': 'direct',
                'info': {
                    'original_size': original_info['size_bytes'],
                    'optimized_size': optimized_info['size_bytes'],
                    'compression_ratio': compression_ratio,
                    'width': optimized_info['width'],
                    'height': optimized_info['height'],
                    'format': output_format,
                    'quality': quality
                }
            })

        # Add to queue if we can't process immediately
        else:
            # Create optimization params
            optimization_params = {
                'format': output_format,
                'quality': quality,
                'max_width': max_width,
                'max_height': max_height
            }

            file_info = {
                'name': 'base64_input',
                'size': len(image_data),
                'type': 'base64'
            }

            job_id, error = job_queue.add_job('background_removal_base64', client_ip, file_info)

            if error:
                return jsonify({'error': error}), 429

            # Store job data
            if job_id in job_queue.active_jobs:
                job_queue.active_jobs[job_id]['image_data'] = image_data
                job_queue.active_jobs[job_id]['filename'] = 'base64_input'
                job_queue.active_jobs[job_id]['optimization_params'] = optimization_params
                job_queue.active_jobs[job_id]['output_format'] = output_format
                job_queue.active_jobs[job_id]['is_base64'] = True
                job_queue.active_jobs[job_id]['original_base64'] = data['image']

            logger.info(f"QUEUE_JOB_CREATED_BASE64 | {job_id} | IP: {client_ip}")

            return jsonify({
                'job_id': job_id,
                'message': 'Base64 job added to queue successfully',
                'status_url': f'/queue/job/{job_id}',
                'result_url': f'/queue/job/{job_id}/result',
                'queue_position': status['queue_length'] + 1,
                'processing_type': 'queued'
            })

    except Exception as e:
        logger.error(f"Error in base64 endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500

# Cleanup function untuk menghapus file lama
def cleanup_old_files():
    import time
    current_time = time.time()

    for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if os.path.isfile(file_path):
                # Hapus file yang lebih tua dari 1 jam
                if current_time - os.path.getmtime(file_path) > 3600:
                    try:
                        os.remove(file_path)
                        print(f"Cleaned up old file: {filename}")
                    except Exception as e:
                        print(f"Error cleaning up {filename}: {e}")

if __name__ == '__main__':
    # Cleanup files lama saat startup
    cleanup_old_files()

    # Log startup
    app_name = os.getenv('APP_NAME', 'Background Remover API')
    app_version = os.getenv('APP_VERSION', '1.0.0')
    host = os.getenv('HOST', '0.0.0.0')
    port = os.getenv('PORT', '5001')

    logger.info(f"APP_STARTUP | {app_name} v{app_version} starting on {host}:{port}")
    logger.info(f"LOG_CONFIG | Level: {LOG_LEVEL} | File: {LOG_FILE}")
    logger.info(f"FOLDERS | Upload: {UPLOAD_FOLDER} | Output: {OUTPUT_FOLDER}")
    logger.info("API_ENDPOINTS | /remove-background, /remove-background-preview, /remove-background-base64, /health, /")

    print("Starting Background Remover API...")
    print("Available endpoints:")
    print("  POST /remove-background - Upload file untuk menghapus background (download file)")
    print("  POST /remove-background-preview - Upload file untuk preview hasil di browser")
    print("  POST /remove-background-base64 - Kirim base64 untuk menghapus background")
    print("  GET /health - Check API health")
    print("  GET / - API info")
    print(f"  GET /static/* - Static files (CSS, JS)")
    print(f"Logging to: {os.path.join(logs_dir, LOG_FILE)}")

    # Konfigurasi server dari environment variables
    debug_mode = os.getenv('DEBUG', 'True').lower() == 'true'
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5001))

    app.run(debug=debug_mode, host=host, port=port)