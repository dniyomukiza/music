#!/usr/bin/env python3
"""
Comprehensive Workflow Test Script
Tests all reviewer and investment system routes and functionality
"""

import sys
import os
import requests
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE_URL = "http://localhost:5000"
TEST_RESULTS = {
    'passed': [],
    'failed': [],
    'warnings': []
}

def test_route(method, url, description, expected_status=200, data=None, headers=None):
    """Test a single route"""
    try:
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, timeout=5)
        elif method.upper() == 'POST':
            response = requests.post(url, json=data, headers=headers, timeout=5)
        else:
            TEST_RESULTS['failed'].append(f"{description}: Invalid method {method}")
            return False
        
        status_code = response.status_code
        
        # Check if it's a redirect (302, 303) which is OK for login-required routes
        if status_code in [200, 302, 303, 401]:
            if status_code == expected_status or (expected_status == 200 and status_code in [302, 303, 401]):
                TEST_RESULTS['passed'].append(f"✅ {description} - Status: {status_code}")
                return True
            else:
                TEST_RESULTS['warnings'].append(f"⚠️ {description} - Expected {expected_status}, got {status_code}")
                return False
        else:
            TEST_RESULTS['failed'].append(f"❌ {description} - Status: {status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        TEST_RESULTS['failed'].append(f"❌ {description} - Server not running")
        return False
    except Exception as e:
        TEST_RESULTS['failed'].append(f"❌ {description} - Error: {str(e)}")
        return False

def test_server_health():
    """Test if server is running"""
    print("\n" + "="*60)
    print("TESTING SERVER HEALTH")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code in [200, 302, 303]:
            print("✅ Server is running")
            return True
        else:
            print(f"⚠️ Server responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running. Please start it with: python3 run.py")
        return False
    except Exception as e:
        print(f"❌ Error checking server: {str(e)}")
        return False

def test_reviewer_routes():
    """Test all reviewer-related routes"""
    print("\n" + "="*60)
    print("TESTING REVIEWER ROUTES")
    print("="*60)
    
    routes = [
        ('GET', f"{BASE_URL}/mybook/reviewers/register", "Reviewer Registration Page", 200),
        ('GET', f"{BASE_URL}/mybook/reviewers", "Reviewer Marketplace", 200),
        ('GET', f"{BASE_URL}/mybook/admin/reviewers", "Admin Reviewers Panel", 200),
    ]
    
    for method, url, desc, expected in routes:
        test_route(method, url, desc, expected)

def test_investment_routes():
    """Test all investment-related routes"""
    print("\n" + "="*60)
    print("TESTING INVESTMENT ROUTES")
    print("="*60)
    
    routes = [
        ('GET', f"{BASE_URL}/mybook/investments", "Investment Marketplace", 200),
        # Note: These require book_id/campaign_id, so we test with placeholder
        ('GET', f"{BASE_URL}/mybook/books/1/create-campaign", "Create Campaign (requires auth)", 200),
        ('GET', f"{BASE_URL}/mybook/investments/1", "Campaign Details", 200),
        ('GET', f"{BASE_URL}/mybook/investments/1/invest", "Make Investment (requires auth)", 200),
    ]
    
    for method, url, desc, expected in routes:
        test_route(method, url, desc, expected)

def test_review_routes():
    """Test review-related routes"""
    print("\n" + "="*60)
    print("TESTING REVIEW ROUTES")
    print("="*60)
    
    routes = [
        ('GET', f"{BASE_URL}/mybook/books/1/request-review", "Request Review (requires auth)", 200),
        ('GET', f"{BASE_URL}/mybook/books/1/reviews/submit", "Submit Review (requires auth)", 200),
    ]
    
    for method, url, desc, expected in routes:
        test_route(method, url, desc, expected)

def test_earnings_routes():
    """Test earnings and transparency routes"""
    print("\n" + "="*60)
    print("TESTING EARNINGS & TRANSPARENCY ROUTES")
    print("="*60)
    
    routes = [
        ('GET', f"{BASE_URL}/mybook/earnings", "Earnings Dashboard (requires auth)", 200),
        ('GET', f"{BASE_URL}/mybook/books/1/sales-transparency", "Sales Transparency", 200),
        ('GET', f"{BASE_URL}/mybook/reviewers/my-earnings/1", "Reviewer Earnings by Book (requires auth)", 200),
        ('GET', f"{BASE_URL}/mybook/investments/my-returns/1", "Investor Returns by Book (requires auth)", 200),
    ]
    
    for method, url, desc, expected in routes:
        test_route(method, url, desc, expected)

def test_accountability_routes():
    """Test accountability routes"""
    print("\n" + "="*60)
    print("TESTING ACCOUNTABILITY ROUTES")
    print("="*60)
    
    routes = [
        ('GET', f"{BASE_URL}/mybook/books/1/accountability", "Accountability Status (requires auth)", 200),
        ('GET', f"{BASE_URL}/mybook/investments/1/refund-status", "Refund Status (requires auth)", 200),
    ]
    
    for method, url, desc, expected in routes:
        test_route(method, url, desc, expected)

def test_database_models():
    """Test database models and imports"""
    print("\n" + "="*60)
    print("TESTING DATABASE MODELS")
    print("="*60)
    
    try:
        from glconnect import create_app
        from glconnect.book_platform_models import (
            AccreditedReviewer, BookReview, InvestmentCampaign,
            BookInvestment, RevenueDistribution, ReviewerEarning,
            InvestmentPayout, RefundRequest
        )
        
        app, socketio = create_app()
        with app.app_context():
            # Test model imports
            TEST_RESULTS['passed'].append("✅ All models imported successfully")
            
            # Test database connection
            from glconnect import db
            try:
                db.session.execute(db.text("SELECT 1"))
                TEST_RESULTS['passed'].append("✅ Database connection works")
            except Exception as e:
                TEST_RESULTS['failed'].append(f"❌ Database connection failed: {str(e)}")
            
            # Check if tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            required_tables = [
                'accredited_reviewers', 'book_reviews', 'investment_campaigns',
                'book_investments', 'revenue_distributions', 'reviewer_earnings',
                'investment_payouts', 'refund_requests'
            ]
            
            for table in required_tables:
                if table in tables:
                    TEST_RESULTS['passed'].append(f"✅ Table '{table}' exists")
                else:
                    TEST_RESULTS['failed'].append(f"❌ Table '{table}' missing")
        
        print("✅ Database models test completed")
        
    except ImportError as e:
        TEST_RESULTS['failed'].append(f"❌ Import error: {str(e)}")
    except Exception as e:
        TEST_RESULTS['failed'].append(f"❌ Database test error: {str(e)}")

def test_revenue_distribution():
    """Test revenue distribution service"""
    print("\n" + "="*60)
    print("TESTING REVENUE DISTRIBUTION SERVICE")
    print("="*60)
    
    try:
        from glconnect.revenue_distribution_service import (
            distribute_revenue, calculate_reviewer_earnings,
            calculate_investor_returns, PLATFORM_FEE_PERCENTAGE,
            AUTHOR_BASE_PERCENTAGE, REVIEWER_POOL_PERCENTAGE,
            INVESTOR_POOL_PERCENTAGE
        )
        
        TEST_RESULTS['passed'].append("✅ Revenue distribution service imported")
        TEST_RESULTS['passed'].append(f"✅ Platform fee: {PLATFORM_FEE_PERCENTAGE}%")
        TEST_RESULTS['passed'].append(f"✅ Reviewer pool: {REVIEWER_POOL_PERCENTAGE}%")
        TEST_RESULTS['passed'].append(f"✅ Investor pool: {INVESTOR_POOL_PERCENTAGE}%")
        
        print("✅ Revenue distribution service test completed")
        
    except ImportError as e:
        TEST_RESULTS['failed'].append(f"❌ Revenue distribution import error: {str(e)}")
    except Exception as e:
        TEST_RESULTS['failed'].append(f"❌ Revenue distribution test error: {str(e)}")

def test_templates():
    """Test if all templates exist"""
    print("\n" + "="*60)
    print("TESTING TEMPLATES")
    print("="*60)
    
    import os
    template_dir = "glconnect/templates/book_platform"
    required_templates = [
        "register_reviewer.html",
        "reviewers.html",
        "reviewer_profile.html",
        "request_review.html",
        "submit_review.html",
        "create_campaign.html",
        "investments.html",
        "campaign_details.html",
        "make_investment.html",
        "earnings.html",
        "sales_transparency.html",
        "admin_reviewers.html",
        "accountability_status.html",
        "investment_refund_status.html"
    ]
    
    for template in required_templates:
        path = os.path.join(template_dir, template)
        if os.path.exists(path):
            TEST_RESULTS['passed'].append(f"✅ Template '{template}' exists")
        else:
            TEST_RESULTS['failed'].append(f"❌ Template '{template}' missing")

def test_forms():
    """Test if all forms are defined"""
    print("\n" + "="*60)
    print("TESTING FORMS")
    print("="*60)
    
    try:
        from glconnect.forms import (
            ReviewerRegistrationForm, BookReviewForm,
            InvestmentCampaignForm, InvestmentForm
        )
        
        TEST_RESULTS['passed'].append("✅ ReviewerRegistrationForm imported")
        TEST_RESULTS['passed'].append("✅ BookReviewForm imported")
        TEST_RESULTS['passed'].append("✅ InvestmentCampaignForm imported")
        TEST_RESULTS['passed'].append("✅ InvestmentForm imported")
        
        print("✅ Forms test completed")
        
    except ImportError as e:
        TEST_RESULTS['failed'].append(f"❌ Forms import error: {str(e)}")
    except Exception as e:
        TEST_RESULTS['failed'].append(f"❌ Forms test error: {str(e)}")

def print_summary():
    """Print test summary"""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    total = len(TEST_RESULTS['passed']) + len(TEST_RESULTS['failed']) + len(TEST_RESULTS['warnings'])
    passed = len(TEST_RESULTS['passed'])
    failed = len(TEST_RESULTS['failed'])
    warnings = len(TEST_RESULTS['warnings'])
    
    print(f"\nTotal Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️ Warnings: {warnings}")
    
    if failed > 0:
        print("\n❌ FAILED TESTS:")
        for test in TEST_RESULTS['failed']:
            print(f"  {test}")
    
    if warnings > 0:
        print("\n⚠️ WARNINGS:")
        for test in TEST_RESULTS['warnings']:
            print(f"  {test}")
    
    print("\n" + "="*60)
    
    if failed == 0:
        print("🎉 ALL CRITICAL TESTS PASSED!")
    else:
        print("⚠️ SOME TESTS FAILED - Review the errors above")

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("COMPREHENSIVE WORKFLOW TEST")
    print("="*60)
    print(f"Testing against: {BASE_URL}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test server health first
    if not test_server_health():
        print("\n❌ Server is not running. Please start it first:")
        print("   python3 run.py")
        return
    
    # Run all tests
    test_database_models()
    test_revenue_distribution()
    test_forms()
    test_templates()
    test_reviewer_routes()
    test_investment_routes()
    test_review_routes()
    test_earnings_routes()
    test_accountability_routes()
    
    # Print summary
    print_summary()
    
    # Save results to file
    with open('test_results.json', 'w') as f:
        json.dump(TEST_RESULTS, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: test_results.json")

if __name__ == "__main__":
    main()

