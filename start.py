#!/usr/bin/env python3
"""
Links Scraper v2 - Simple Startup Script
"""

import os
import sys

def main():
    print("=" * 50)
    print("🚀 Links Scraper v2")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('app.py'):
        print("❌ Error: Please run this from the links-scraper-v2 directory")
        print("   cd links-scraper-v2")
        print("   python start.py")
        sys.exit(1)
    
    print("📋 Initializing...")
    
    # Import and run the app
    try:
        from app import app, initialize_app
        
        print("✅ Initializing database and directories...")
        initialize_app()
        
        print("✅ Starting server on port 2020...")
        print("🌐 Open your browser to: http://localhost:2020")
        print("\n📝 Pages available:")
        print("   • Dashboard: http://localhost:2020")
        print("   • Add Account: http://localhost:2020/add-account") 
        print("   • Accounts: http://localhost:2020/accounts")
        print("\n⚠️  Make sure to add cookies to:")
        print("   • cookies/cookies.txt (Instagram, TikTok, X)")
        print("   • cookies/facebook.txt (Facebook)")
        print("   • cookies/youtube.txt (YouTube)")
        print("\n🛑 Press Ctrl+C to stop")
        print("=" * 50)
        
        app.run(host='0.0.0.0', port=2020, debug=False)
        
    except ImportError as e:
        print(f"❌ Error importing modules: {e}")
        print("💡 Try: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
