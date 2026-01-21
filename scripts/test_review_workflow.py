#!/usr/bin/env python3
"""
Test script to verify the review workflow components.

This tests the database methods and review functionality programmatically
since the interactive CLI can't be tested automatically.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.database import Database
from src.logger import logger
from datetime import datetime


def test_review_workflow():
    """Test the complete review workflow"""
    print("\n" + "=" * 80)
    print("Testing Review Workflow Components")
    print("=" * 80 + "\n")

    db = Database()

    # 1. Check for pending posts
    print("1. Checking for pending posts...")
    pending_posts = db.get_posts(status="pending")
    print(f"   ✓ Found {len(pending_posts)} pending post(s)")

    if not pending_posts:
        print("\n⚠ No pending posts found. Run generate_sample_posts.py first.")
        return False

    # 2. Test retrieving a post
    print("\n2. Testing post retrieval...")
    test_post = pending_posts[0]
    post_id = test_post['id']
    retrieved_post = db.get_post(post_id)
    assert retrieved_post is not None, "Failed to retrieve post"
    print(f"   ✓ Successfully retrieved post {post_id}")
    print(f"   - Content preview: {retrieved_post['content'][:80]}...")

    # 3. Test getting sources
    print("\n3. Testing source retrieval...")
    sources = db.get_sources_for_post(post_id)
    print(f"   ✓ Found {len(sources)} source(s) for post")
    if sources:
        print(f"   - Source: {sources[0].get('source_name', 'Unknown')}")

    # 4. Test getting associated trend
    print("\n4. Testing trend retrieval...")
    if test_post.get('trend_id'):
        trend = db.get_trend(test_post['trend_id'])
        if trend:
            print(f"   ✓ Retrieved associated trend")
            print(f"   - Trend: {trend.get('title', 'Unknown')[:60]}...")
        else:
            print("   ⚠ Trend not found in database")
    else:
        print("   ⚠ Post has no associated trend_id")

    # 5. Test approval workflow (dry run - we'll revert)
    print("\n5. Testing approval workflow...")
    original_status = test_post['status']

    # Approve the post
    success = db.approve_post(post_id, "Test approval")
    assert success, "Failed to approve post"
    print(f"   ✓ Successfully approved post {post_id}")

    # Verify status changed
    updated_post = db.get_post(post_id)
    assert updated_post['status'] == 'approved', "Status not updated to approved"
    print(f"   ✓ Status changed to 'approved'")

    # 6. Test rejection workflow
    print("\n6. Testing rejection workflow...")
    success = db.reject_post(post_id, "Test rejection")
    assert success, "Failed to reject post"
    print(f"   ✓ Successfully rejected post {post_id}")

    # Verify status changed
    updated_post = db.get_post(post_id)
    assert updated_post['status'] == 'rejected', "Status not updated to rejected"
    print(f"   ✓ Status changed to 'rejected'")

    # 7. Test post update/editing
    print("\n7. Testing post editing...")
    original_content = updated_post['content']
    test_content = original_content + "\n\n[EDITED FOR TESTING]"

    success = db.update_post(
        post_id,
        content=test_content,
        reviewed_at=datetime.now().isoformat()
    )
    assert success, "Failed to update post"
    print(f"   ✓ Successfully updated post content")

    # Verify content changed
    edited_post = db.get_post(post_id)
    assert "[EDITED FOR TESTING]" in edited_post['content'], "Content not updated"
    print(f"   ✓ Content successfully modified")

    # 8. Restore original state
    print("\n8. Restoring original state...")
    db.update_post(post_id, content=original_content, status=original_status)
    restored_post = db.get_post(post_id)
    assert restored_post['status'] == original_status, "Failed to restore status"
    assert restored_post['content'] == original_content, "Failed to restore content"
    print(f"   ✓ Post restored to original state")

    # 9. Test filtering by status
    print("\n9. Testing status filtering...")
    all_posts = db.get_posts()
    approved_posts = db.get_posts(status="approved")
    rejected_posts = db.get_posts(status="rejected")
    pending_posts = db.get_posts(status="pending")

    print(f"   ✓ Total posts: {len(all_posts)}")
    print(f"   ✓ Approved: {len(approved_posts)}")
    print(f"   ✓ Rejected: {len(rejected_posts)}")
    print(f"   ✓ Pending: {len(pending_posts)}")

    # 10. Summary
    print("\n" + "=" * 80)
    print("✓ All review workflow tests passed!")
    print("=" * 80)
    print("\nThe review CLI components are working correctly.")
    print("You can now use the interactive CLI with:")
    print("  python -m src.review_cli")
    print()

    return True


if __name__ == "__main__":
    try:
        success = test_review_workflow()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"\n✗ Test failed: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
