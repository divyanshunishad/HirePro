import requests
import json
from datetime import datetime

def test_endpoint(endpoint, method="GET", params=None):
    base_url = "https://hirepro-x72c.onrender.com"  # Updated Production URL
    url = f"{base_url}{endpoint}"
    print(f"\nTesting {method} {url}")
    try:
        response = requests.request(method, url, params=params)
        print(f"Status Code: {response.status_code}")
        try:
            print("Response:", json.dumps(response.json(), indent=2))
        except:
            print("Response:", response.text)
        return response
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def main():
    print(f"Starting API tests at {datetime.now()}")
    
    # Test health endpoint first
    print("\n=== Testing Health Endpoint ===")
    health_response = test_endpoint("/health")
    
    if health_response and health_response.status_code == 200:
        print("\nHealth check passed, proceeding with other tests...")
        
        # Test regular jobs endpoint
        print("\n=== Testing Regular Jobs Endpoint ===")
        test_endpoint("/api/regular-jobs")
        
        # Test regular jobs with search
        print("\n=== Testing Regular Jobs with Search ===")
        test_endpoint("/api/regular-jobs", params={"search": "python"})
        
        # Test regular jobs with location
        print("\n=== Testing Regular Jobs with Location ===")
        test_endpoint("/api/regular-jobs", params={"location": "remote"})
    else:
        print("\nHealth check failed. The service might be down or not properly deployed.")
    
    print(f"\nTests completed at {datetime.now()}")

if __name__ == "__main__":
    main() 