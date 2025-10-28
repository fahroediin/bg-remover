import requests
import base64
import json

def test_api_with_file(image_path):
    """Test API dengan file upload"""
    url = "http://127.0.0.1:5001/remove-background"

    try:
        with open(image_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(url, files=files)

            if response.status_code == 200:
                # Simpan hasil
                with open('result_file.png', 'wb') as result_file:
                    result_file.write(response.content)
                print(f"✅ Success! Result saved as result_file.png")
                print(f"File size: {len(response.content)} bytes")
            else:
                print(f"❌ Error: {response.status_code}")
                print(response.text)

    except FileNotFoundError:
        print(f"❌ File not found: {image_path}")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_api_with_base64(image_path):
    """Test API dengan base64"""
    url = "http://127.0.0.1:5001/remove-background-base64"

    try:
        # Baca dan encode gambar ke base64
        with open(image_path, 'rb') as f:
            image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')

        # Kirim request
        payload = {"image": image_base64}
        response = requests.post(url, json=payload)

        if response.status_code == 200:
            result = response.json()
            if result['success']:
                # Decode dan simpan hasil
                result_data = base64.b64decode(result['image'])
                with open('result_base64.png', 'wb') as result_file:
                    result_file.write(result_data)
                print(f"✅ Success! Result saved as result_base64.png")
                print(f"Result size: {len(result_data)} bytes")
            else:
                print(f"❌ Error in processing: {result}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)

    except FileNotFoundError:
        print(f"❌ File not found: {image_path}")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_health():
    """Test health endpoint"""
    url = "http://127.0.0.1:5001/health"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print("✅ Health check passed:", response.json())
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {e}")

if __name__ == "__main__":
    print("Background Remover API Test Client")
    print("=================================")

    # Test health
    print("\n1. Testing health endpoint...")
    test_health()

    # Ganti dengan path gambar test Anda
    test_image = "test_image.jpg"  # Ganti dengan path gambar Anda

    print(f"\n2. Testing with file upload (using {test_image})...")
    test_api_with_file(test_image)

    print(f"\n3. Testing with base64 (using {test_image})...")
    test_api_with_base64(test_image)

    print("\nTest completed!")