import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

def test_endpoints():
    """Test both HTTP and HTTPS endpoints"""
    
    host = os.getenv('HOST', '127.0.0.1')
    http_port = os.getenv('HTTP_PORT', '5000')
    https_port = os.getenv('HTTPS_PORT', '5443')
    
    endpoints = []
    
    if os.getenv('ENABLE_HTTP', 'True').lower() == 'true':
        endpoints.append(f"http://{host}:{http_port}")
    
    if os.getenv('ENABLE_HTTPS', 'True').lower() == 'true':
        endpoints.append(f"https://{host}:{https_port}")
    
    for base_url in endpoints:
        print(f"\n🧪 Testing {base_url}")
        print("-" * 40)
        
        try:
            # Test health endpoint
            health_url = f"{base_url}/health"
            response = requests.get(health_url, verify=False, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check: {data['message']}")
            else:
                print(f"❌ Health check failed: {response.status_code}")
            
            # Test auth endpoint with sample data
            auth_url = f"{base_url}/api/v1/auth/login"
            auth_data = {
                "username": "test_user",
                "password": "test_pass"
            }
            
            response = requests.post(
                auth_url, 
                json=auth_data, 
                verify=False, 
                timeout=5
            )
            
            if response.status_code in [200, 400, 401]:  # Expected responses
                print(f"✅ Auth endpoint reachable: {response.status_code}")
            else:
                print(f"❌ Auth endpoint error: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Connection failed - server not running?")
        except Exception as e:
            print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    print("🧪 Testing HTTP/HTTPS endpoints...")
    print("⏳ Make sure your servers are running (python run.py)")
    time.sleep(2)
    test_endpoints()
