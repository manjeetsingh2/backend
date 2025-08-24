import os
import threading
import time
from dotenv import load_dotenv
from ssl_helper import create_ssl_context

# Load environment variables
load_dotenv()

from app import create_app

def run_http_server():
    """Run HTTP server"""
    if os.getenv('ENABLE_HTTP', 'True').lower() != 'true':
        return
    
    app = create_app()
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('HTTP_PORT', 5000))
    
    print(f"🌐 HTTP Server: http://{host}:{port}")
    print(f"   Health: http://{host}:{port}/health")
    print(f"   Auth: http://{host}:{port}/api/v1/auth/login")
    
    app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)

def run_https_server():
    """Run HTTPS server"""
    if os.getenv('ENABLE_HTTPS', 'True').lower() != 'true':
        return
    
    ssl_context = create_ssl_context()
    if not ssl_context:
        print("❌ HTTPS disabled - SSL context creation failed")
        return
    
    app = create_app()
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('HTTPS_PORT', 5443))
    
    print(f"🔒 HTTPS Server: https://{host}:{port}")
    print(f"   Health: https://{host}:{port}/health")
    print(f"   Auth: https://{host}:{port}/api/v1/auth/login")
    
    app.run(host=host, port=port, debug=False, ssl_context=ssl_context, use_reloader=False, threaded=True)

def main():
    """Main function to start both servers"""
    print("=" * 50)
    print("🚀 Starting Crop Target API Servers")
    print("=" * 50)
    
    enable_http = os.getenv('ENABLE_HTTP', 'True').lower() == 'true'
    enable_https = os.getenv('ENABLE_HTTPS', 'True').lower() == 'true'
    
    if not enable_http and not enable_https:
        print("❌ Error: Both HTTP and HTTPS are disabled!")
        return
    
    threads = []
    
    # Start HTTP server in background thread
    if enable_http:
        http_thread = threading.Thread(target=run_http_server, daemon=True)
        http_thread.start()
        threads.append(http_thread)
        time.sleep(1)  # Give HTTP server time to start
    
    # Start HTTPS server in main thread or background
    if enable_https:
        if enable_http:
            # Run HTTPS in background if HTTP is also enabled
            https_thread = threading.Thread(target=run_https_server, daemon=True)
            https_thread.start()
            threads.append(https_thread)
        else:
            # Run HTTPS in main thread if it's the only server
            run_https_server()
            return
    
    if threads:
        print("\n" + "=" * 50)
        print("✅ All servers started successfully!")
        print("💡 Press Ctrl+C to stop all servers")
        print("=" * 50)
        
        try:
            # Keep main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down servers...")

if __name__ == '__main__':
    main()
