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
from functools import wraps

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

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

# Add static file serving
@app.route('/static/<path:filename>')
@log_api_access
def serve_static(filename):
    return send_from_directory('static', filename)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
        'rate_limits': {
            'default': f'{RATE_LIMIT_DEFAULT_PER_HOUR} per hour, {RATE_LIMIT_DEFAULT_PER_MINUTE} per minute',
            'remove_background': f'{RATE_LIMIT_REMOVE_BG_PER_MINUTE} per minute',
            'remove_background_preview': f'{RATE_LIMIT_PREVIEW_PER_MINUTE} per minute',
            'remove_background_base64': f'{RATE_LIMIT_BASE64_PER_MINUTE} per minute',
            'health': f'{RATE_LIMIT_HEALTH_PER_MINUTE} per minute',
            'info': f'{RATE_LIMIT_INFO_PER_MINUTE} per minute'
        },
        'endpoints': {
            'remove_background': '/remove-background (POST) - Download hasil sebagai file',
            'remove_background_preview': '/remove-background-preview (POST) - Preview hasil di browser',
            'remove_background_base64': '/remove-background-base64 (POST) - Input/output base64',
            'health': '/health (GET)',
            'info': '/api (GET)'
        }
    })

@app.route('/health')
@limiter.limit(f"{RATE_LIMIT_HEALTH_PER_MINUTE} per minute")
@log_api_access
def health():
    return jsonify({'status': 'healthy', 'service': 'background-remover'})

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

        # Generate unique filename
        file_id = str(uuid.uuid4())
        input_filename = f"{file_id}_input.png"
        output_filename = f"{file_id}_output.png"
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
            output_data = remove(img_data_for_rembg.read())

            # Simpan hasil
            with open(output_path, 'wb') as f:
                f.write(output_data)

            # Kembalikan hasil sebagai file
            response = send_file(
                output_path,
                as_attachment=True,
                download_name=f"removed_bg_{file.filename.rsplit('.', 1)[0]}.png",
                mimetype='image/png'
            )

            # Tambahkan headers untuk memastikan download bekerja dengan baik di browser
            response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
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
    Endpoint untuk background removal yang mengembalikan image untuk preview di browser
    bukan sebagai file download
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

        try:
            # Baca file gambar
            image_data = file.read()

            # Validasi bahwa image_data tidak kosong
            if not image_data or len(image_data) == 0:
                return jsonify({'error': 'File is empty or corrupted'}), 400

            # Validasi bahwa data terlihat seperti data gambar (cek header magic)
            if len(image_data) < 8:
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
            print(f"Processing image for preview: {file.filename}")
            output_data = remove(img_data_for_rembg.read())

            # Kembalikan hasil sebagai image yang bisa ditampilkan di browser
            return send_file(
                io.BytesIO(output_data),
                mimetype='image/png',
                as_attachment=False,
                download_name=None
            )

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

    except Exception as e:
        print(f"Server error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/remove-background-base64', methods=['POST'])
@limiter.limit(f"{RATE_LIMIT_BASE64_PER_MINUTE} per minute")
@log_api_access
@log_file_upload
def remove_background_base64():
    try:
        data = request.get_json()

        if not data or 'image' not in data:
            return jsonify({'error': 'No image data provided'}), 400

        import base64

        # Decode base64
        try:
            image_data = base64.b64decode(data['image'])
        except:
            return jsonify({'error': 'Invalid base64 data'}), 400

        # Validasi bahwa image_data tidak kosong
        if not image_data or len(image_data) == 0:
            return jsonify({'error': 'Base64 image data is empty or corrupted'}), 400

        # Validasi bahwa data terlihat seperti data gambar (cek header magic)
        if len(image_data) < 8:
            return jsonify({'error': 'Base64 data too small to be a valid image'}), 400

        # Validasi image dengan PIL sebelum memproses dengan rembg
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(image_data))
            img.verify()  # Verifikasi bahwa ini adalah gambar valid
        except Exception as img_e:
            return jsonify({'error': f'Invalid base64 image: {str(img_e)}'}), 400

        # Reset BytesIO untuk rembg (karena verify() mengkonsumsi stream)
        img_data_for_rembg = io.BytesIO(image_data)

        # Generate unique filename
        file_id = str(uuid.uuid4())
        output_filename = f"{file_id}_output.png"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)

        try:
            # Proses background removal
            print("Processing base64 image")
            output_data = remove(img_data_for_rembg.read())

            # Simpan hasil
            with open(output_path, 'wb') as f:
                f.write(output_data)

            # Encode hasil ke base64
            with open(output_path, 'rb') as f:
                result_base64 = base64.b64encode(f.read()).decode('utf-8')

            return jsonify({
                'success': True,
                'image': result_base64,
                'mimetype': 'image/png'
            })

        except OSError as e:
            # Handle specific OS errors like Invalid argument
            print(f"OS Error processing base64 image: {str(e)}")
            error_msg = f'Failed to process image: {str(e)}'
            if 'Invalid argument' in str(e) or e.errno == 22:
                error_msg = 'Failed to process image: Invalid image data or corrupted file'
            return jsonify({'error': error_msg}), 500
        except Exception as e:
            print(f"Error processing image: {str(e)}")
            return jsonify({'error': f'Failed to process image: {str(e)}'}), 500

        finally:
            # Cleanup output file
            if os.path.exists(output_path):
                os.remove(output_path)

    except Exception as e:
        print(f"Server error: {str(e)}")
        print(traceback.format_exc())
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