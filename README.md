# Background Remover API

Aplikasi Flask untuk menghapus background dari gambar foto dengan fokus pada objek utama.

## Fitur

- Upload file gambar langsung
- Support base64 encoding
- Automatic background removal menggunakan rembg library
- Support multiple image formats (PNG, JPG, JPEG, GIF, BMP, TIFF, WEBP)
- Output dalam format PNG dengan transparansi
- Auto-cleanup file lama

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Jalankan aplikasi:
```bash
python app.py
```

## API Endpoints

### 1. Upload File
- **URL**: `POST /remove-background`
- **Content-Type**: `multipart/form-data`
- **Parameter**: `file` (image file)
- **Response**: Image file dengan background dihapus

### 2. Base64
- **URL**: `POST /remove-background-base64`
- **Content-Type**: `application/json`
- **Body**:
```json
{
  "image": "base64_encoded_image"
}
```
- **Response**:
```json
{
  "success": true,
  "image": "base64_encoded_result",
  "mimetype": "image/png"
}
```

### 3. Health Check
- **URL**: `GET /health`
- **Response**: API status

## Example Usage

### Menggunakan curl (File Upload)
```bash
curl -X POST -F "file=@your_image.jpg" http://127.0.0.1:5001/remove-background --output result.png
```

### Menggunakan curl (Base64)
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"image":"base64_encoded_image"}' \
  http://127.0.0.1:5001/remove-background-base64
```

### Menggunakan Python requests
```python
import requests

# Upload file
with open('your_image.jpg', 'rb') as f:
    response = requests.post(
        'http://127.0.0.1:5001/remove-background',
        files={'file': f}
    )

if response.status_code == 200:
    with open('result.png', 'wb') as f:
        f.write(response.content)
    print("Background removed successfully!")
```

## Supported Image Formats

- PNG
- JPG/JPEG
- GIF
- BMP
- TIFF
- WEBP

## Output Format

- Format: PNG dengan transparansi
- Background: Transparan
- Object: Dipertahankan dengan kualitas tinggi

## Notes

- File akan otomatis dihapus setelah 1 jam
- Maximum processing time tergantung pada ukuran gambar
- Server berjalan pada port 5001 (dapat diubah di app.py)# bg-remover
