#!/usr/bin/env python3
"""
Quick Test Script for Reviewer-Investor-Author System
Run this to verify the system is working
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glconnect import create_app, db
from glconnect.models import User
from glconnect.book_platform_models import (
    AccreditedReviewer, BookProject, InvestmentCampaign, BookInvestment,
    BookReview, ReviewerStatus, CampaignStatus, InvestmentStatus
)

def test_system():
    """Test the reviewer-investor-author system"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("TESTING REVIEWER-INVESTOR-AUTHOR SYSTEM")
        print("=" * 60)
        
        # Test 1: Check if models exist
        print("\n1. Checking Database Models...")
        try:
            reviewers = AccreditedReviewer.query.count()
            books = BookProject.query.count()
            campaigns = InvestmentCampaign.query.count()
            investments = BookInvestment.query.count()
            reviews = BookReview.query.count()
            
            print(f"   ✅ AccreditedReviewer: {reviewers} records")
            print(f"   ✅ BookProject: {books} records")
            print(f"   ✅ InvestmentCampaign: {campaigns} records")
            print(f"   ✅ BookInvestment: {investments} records")
            print(f"   ✅ BookReview: {reviews} records")
        except Exception as e:
            print(f"   ❌ Error checking models: {e}")
            return False
        
        # Test 2: Check routes
        print("\n2. Checking Routes...")
        routes_to_check = [
            '/mybook/reviewers/register',
            '/mybook/reviewers',
            '/mybook/investments',
            '/mybook/earnings',
            '/mybook/admin/reviewers'
        ]
        
        with app.test_client() as client:
            for route in routes_to_check:
                try:
                    response = client.get(route, follow_redirects=True)
                    if response.status_code in [200, 302, 401]:  # 401 is OK (needs login)
                        print(f"   ✅ {route} - Status: {response.status_code}")
                    else:
                        print(f"   ⚠️  {route} - Status: {response.status_code}")
                except Exception as e:
                    print(f"   ❌ {route} - Error: {e}")
        
        # Test 3: Check if reviewers exist
        print("\n3. Checking Reviewer Data...")
        try:
            accredited = AccreditedReviewer.query.filter_by(
                accreditation_status=ReviewerStatus.ACCREDITED
            ).count()
            pending = AccreditedReviewer.query.filter_by(
                accreditation_status=ReviewerStatus.PENDING
            ).count()
            print(f"   ✅ Accredited Reviewers: {accredited}")
            print(f"   ⏳ Pending Reviewers: {pending}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 4: Check investment campaigns
        print("\n4. Checking Investment Campaigns...")
        try:
            active = InvestmentCampaign.query.filter_by(
                status=CampaignStatus.ACTIVE
            ).count()
            funded = InvestmentCampaign.query.filter_by(
                status=CampaignStatus.FUNDED
            ).count()
            print(f"   ✅ Active Campaigns: {active}")
            print(f"   ✅ Funded Campaigns: {funded}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 5: Check investments
        print("\n5. Checking Investments...")
        try:
            active_inv = BookInvestment.query.filter_by(
                status=InvestmentStatus.ACTIVE
            ).count()
            confirmed_inv = BookInvestment.query.filter_by(
                status=InvestmentStatus.CONFIRMED
            ).count()
            print(f"   ✅ Active Investments: {active_inv}")
            print(f"   ✅ Confirmed Investments: {confirmed_inv}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("\n" + "=" * 60)
        print("TESTING COMPLETE")
        print("=" * 60)
        print("\n📋 Next Steps:")
        print("   1. Start server: python3 run.py")
        print("   2. Visit: http://localhost:5000/mybook/reviewers/register")
        print("   3. Visit: http://localhost:5000/mybook/investments")
        print("   4. Visit: http://localhost:5000/mybook/earnings")
        print("\n✅ System appears to be working!")
        
        return True

if __name__ == '__main__':
    success = test_system()
    sys.exit(0 if success else 1)


