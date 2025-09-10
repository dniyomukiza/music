#!/usr/bin/env python3
"""
Update your Flask app to use enhanced logging
"""

import os
import shutil
from pathlib import Path

def update_routes_file():
    """Update the routes.py file to use enhanced logging"""
    routes_file = "glconnect/routes.py"
    
    if not os.path.exists(routes_file):
        print(f"❌ {routes_file} not found!")
        return False
    
    # Backup original file
    shutil.copy(routes_file, f"{routes_file}.backup")
    print(f"✅ Backed up original {routes_file}")
    
    # Read current content
    with open(routes_file, 'r') as f:
        content = f.read()
    
    # Check if already updated
    if "enhanced_logging" in content:
        print("✅ Enhanced logging already integrated!")
        return True
    
    # Add import at the top
    if "from enhanced_logging import init_enhanced_logging" not in content:
        # Find the last import statement
        lines = content.split('\n')
        import_end = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(('import ', 'from ')):
                import_end = i + 1
        
        # Insert enhanced logging import
        lines.insert(import_end, "from enhanced_logging import init_enhanced_logging")
        content = '\n'.join(lines)
    
    # Replace the basic logging with enhanced logging
    old_logging = '''@bp.before_request
def log_request():
    try:
        with open("visits.txt", "a") as f:
            timestamp = datetime.now(timezone.utc).isoformat()
            f.write(f"{timestamp} | {request.remote_addr} | {request.method} {request.path} | {request.headers.get('User-Agent')}\\n")
    except Exception as ex:
        pass'''
    
    new_logging = '''# Enhanced logging - initialized in create_app()'''
    
    if old_logging in content:
        content = content.replace(old_logging, new_logging)
        print("✅ Replaced basic logging with enhanced logging")
    else:
        print("⚠️  Could not find basic logging to replace")
    
    # Write updated content
    with open(routes_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated {routes_file}")
    return True

def update_init_file():
    """Update the __init__.py file to initialize enhanced logging"""
    init_file = "glconnect/__init__.py"
    
    if not os.path.exists(init_file):
        print(f"❌ {init_file} not found!")
        return False
    
    # Read current content
    with open(init_file, 'r') as f:
        content = f.read()
    
    # Check if already updated
    if "init_enhanced_logging" in content:
        print("✅ Enhanced logging already initialized!")
        return True
    
    # Add import
    if "from enhanced_logging import init_enhanced_logging" not in content:
        # Find where to add the import
        lines = content.split('\n')
        import_end = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(('import ', 'from ')):
                import_end = i + 1
        
        lines.insert(import_end, "from enhanced_logging import init_enhanced_logging")
        content = '\n'.join(lines)
    
    # Add initialization after app creation
    if "init_enhanced_logging(app)" not in content:
        # Find where to add the initialization
        if "return app" in content:
            content = content.replace("return app", "    # Initialize enhanced logging\n    init_enhanced_logging(app)\n\n    return app")
        else:
            print("⚠️  Could not find 'return app' to add logging initialization")
            return False
    
    # Write updated content
    with open(init_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated {init_file}")
    return True

def main():
    print("🔧 Updating your app to use enhanced logging...")
    print("=" * 50)
    
    # Update files
    routes_updated = update_routes_file()
    init_updated = update_init_file()
    
    if routes_updated and init_updated:
        print("\n✅ Enhanced logging successfully integrated!")
        print("\n📊 What's new:")
        print("• Detailed visit logging with device/browser info")
        print("• Feature usage tracking")
        print("• Response time monitoring")
        print("• JSON format for detailed logs")
        print("\n🚀 Restart your app to start collecting enhanced analytics!")
        print("\n📈 Use 'python3 view_analytics.py' to view your analytics")
    else:
        print("\n❌ Some updates failed. Check the errors above.")

if __name__ == "__main__":
    main()
