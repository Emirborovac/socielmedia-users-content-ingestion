#!/usr/bin/env python3
"""
Links Scraper v2 - Startup Script

This script initializes and runs the Links Scraper v2 application.
"""

import os
import sys
import logging
from app import app, initialize_app

def main():
    """Main startup function"""
    print("=" * 60)
    print("🚀 Links Scraper v2 - Enterprise Social Media Monitoring")
    print("=" * 60)
    
    try:
        # Initialize the application
        print("📋 Initializing application...")
        initialize_app()
        print("✅ Application initialized successfully")
        
        print("\n📊 System Information:")
        print(f"   • Port: 2020")
        print(f"   • Environment: {'Development' if app.debug else 'Production'}")
        print(f"   • Database: SQLite")
        print(f"   • Scheduler: {'Enabled' if True else 'Disabled'}")
        
        print("\n🌐 Access URLs:")
        print(f"   • Dashboard: http://localhost:2020")
        print(f"   • Add Account: http://localhost:2020/add-account")
        print(f"   • Accounts: http://localhost:2020/accounts")
        
        print("\n🔧 Before using:")
        print("   • Add your cookies to cookies/cookies.txt")
        print("   • Add Facebook cookies to cookies/facebook.txt")
        print("   • Add YouTube cookies to cookies/youtube.txt")
        
        print("\n🎯 Supported Platforms:")
        print("   • Instagram (instagram.com)")
        print("   • TikTok (tiktok.com)")  
        print("   • X/Twitter (x.com)")
        print("   • Facebook (facebook.com)")
        print("   • YouTube (youtube.com)")
        
        print("\n" + "=" * 60)
        print("🔥 Starting server on http://localhost:2020")
        print("   Press Ctrl+C to stop")
        print("=" * 60)
        
        # Run the Flask app
        app.run(
            host='0.0.0.0',
            port=2020,
            debug=False,
            threaded=True
        )
        
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error starting application: {e}")
        logging.error(f"Startup error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
