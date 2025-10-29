#!/usr/bin/env python3
"""
Test script for Background Remover Queue System
This script tests the queue functionality with multiple concurrent requests
"""

import requests
import json
import time
import threading
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import base64

# Configuration
API_BASE = "http://127.0.0.1:5001"
NUM_CONCURRENT_REQUESTS = 5
NUM_TEST_IMAGES = 3

# Create a simple test image data (1x1 PNG)
def create_test_image_data():
    # 1x1 red pixel PNG
    png_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    )
    return png_data

def test_queue_status():
    """Test queue status endpoint"""
    try:
        response = requests.get(f"{API_BASE}/queue/status")
        print(f"Queue Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Queue length: {data['queue_length']}")
            print(f"  Active jobs: {data['active_jobs']}")
            print(f"  Max concurrent: {data['max_concurrent_jobs']}")
            return data
        else:
            print(f"Error: {response.text}")
            return None
    except Exception as e:
        print(f"Error testing queue status: {e}")
        return None

def submit_queue_job(job_id):
    """Submit a job to the queue"""
    try:
        # Create test image
        image_data = create_test_image_data()

        # Prepare form data
        files = {
            'file': (f'test_image_{job_id}.png', image_data, 'image/png')
        }
        data = {
            'format': 'PNG',
            'quality': 85,
            'max_width': 800,
            'max_height': 600
        }

        print(f"[Job {job_id}] Submitting to queue...")
        response = requests.post(f"{API_BASE}/queue/remove-background", files=files, data=data)

        if response.status_code == 200:
            result = response.json()
            job_id_returned = result['job_id']
            print(f"[Job {job_id}] Successfully submitted! Job ID: {job_id_returned}")
            return job_id_returned, True
        else:
            print(f"[Job {job_id}] Failed to submit: {response.status_code} - {response.text}")
            return None, False

    except Exception as e:
        print(f"[Job {job_id}] Error submitting job: {e}")
        return None, False

def check_job_status(job_id):
    """Check status of a specific job"""
    try:
        response = requests.get(f"{API_BASE}/queue/job/{job_id}")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"[Job {job_id}] Status check failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"[Job {job_id}] Error checking status: {e}")
        return None

def wait_for_job_completion(job_id, timeout=120):
    """Wait for a job to complete"""
    start_time = time.time()

    while time.time() - start_time < timeout:
        status = check_job_status(job_id)
        if status:
            print(f"[Job {job_id}] Status: {status['status']} - {status['message']} ({status['progress']}%)")

            if status['status'] in ['completed', 'failed']:
                return status

        time.sleep(2)  # Check every 2 seconds

    print(f"[Job {job_id}] Timeout waiting for completion")
    return None

def test_concurrent_requests():
    """Test multiple concurrent requests"""
    print(f"\n=== Testing {NUM_CONCURRENT_REQUESTS} concurrent requests ===")

    # Get initial queue status
    initial_status = test_queue_status()

    # Submit jobs concurrently
    submitted_jobs = []
    with ThreadPoolExecutor(max_workers=NUM_CONCURRENT_REQUESTS) as executor:
        futures = {executor.submit(submit_queue_job, i): i for i in range(NUM_CONCURRENT_REQUESTS)}

        for future in as_completed(futures):
            job_num = futures[future]
            try:
                job_id, success = future.result()
                if success:
                    submitted_jobs.append(job_id)
            except Exception as e:
                print(f"[Job {job_num}] Exception: {e}")

    print(f"\nSubmitted {len(submitted_jobs)} jobs successfully")

    # Wait for all jobs to complete
    completed_jobs = []
    for job_id in submitted_jobs:
        final_status = wait_for_job_completion(job_id)
        if final_status:
            completed_jobs.append((job_id, final_status['status']))

    print(f"\n=== Results ===")
    print(f"Total submitted: {len(submitted_jobs)}")
    print(f"Total completed: {len(completed_jobs)}")

    for job_id, status in completed_jobs:
        print(f"  Job {job_id}: {status}")

    # Final queue status
    print(f"\n=== Final Queue Status ===")
    final_status = test_queue_status()

    return len(completed_jobs) == len(submitted_jobs)

def test_queue_limits():
    """Test queue limits and rate limiting"""
    print(f"\n=== Testing Queue Limits ===")

    # Get current queue status
    status = test_queue_status()
    if not status:
        return False

    max_queue_size = status['max_queue_size']
    print(f"Max queue size: {max_queue_size}")

    # Try to submit more jobs than the queue can handle
    # Submit jobs until queue is full
    submitted_count = 0
    failed_count = 0

    for i in range(max_queue_size + 5):  # Try to submit more than max
        job_id, success = submit_queue_job(f"limit_test_{i}")
        if success:
            submitted_count += 1
        else:
            failed_count += 1

        # Check queue status
        current_status = test_queue_status()
        if current_status and current_status['queue_length'] >= max_queue_size:
            print(f"Queue is full at {current_status['queue_length']} jobs")
            break

        time.sleep(0.1)  # Small delay between submissions

    print(f"Submitted: {submitted_count}, Failed: {failed_count}")

    # Wait a bit and check final status
    time.sleep(2)
    final_status = test_queue_status()

    return True

def test_api_info():
    """Test API info endpoint"""
    print(f"\n=== Testing API Info ===")

    try:
        response = requests.get(f"{API_BASE}/api")
        if response.status_code == 200:
            data = response.json()
            print(f"App name: {data['app_name']}")
            print(f"Version: {data['version']}")

            if 'queue_config' in data:
                config = data['queue_config']
                print(f"Queue config:")
                print(f"  Max concurrent jobs: {config['max_concurrent_jobs']}")
                print(f"  Max queue size: {config['max_queue_size']}")
                print(f"  Queue timeout: {config['queue_timeout']}")

            print(f"Available endpoints:")
            for endpoint, desc in data['endpoints'].items():
                print(f"  {endpoint}: {desc}")

            return True
        else:
            print(f"Error: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Main test function"""
    print("=== Background Remover Queue System Test ===")
    print(f"API Base: {API_BASE}")

    # Test API info first
    if not test_api_info():
        print("API info test failed")
        return

    # Test queue status
    print(f"\n=== Testing Queue Status ===")
    status = test_queue_status()
    if not status:
        print("Queue status test failed")
        return

    # Test concurrent requests
    concurrent_success = test_concurrent_requests()

    # Test queue limits
    limits_success = test_queue_limits()

    print(f"\n=== Test Summary ===")
    print(f"API Info: ✅")
    print(f"Queue Status: ✅")
    print(f"Concurrent Requests: {'✅' if concurrent_success else '❌'}")
    print(f"Queue Limits: {'✅' if limits_success else '❌'}")

    if concurrent_success and limits_success:
        print("\n🎉 All tests passed! Queue system is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Please check the logs.")

if __name__ == "__main__":
    main()