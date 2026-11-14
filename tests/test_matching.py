import pytest
from datetime import date, timedelta
from app.models.report import LostReport, FoundReport, CampusLocation, ItemCategory
from app.services.matching_service import (
    compute_match_score,
    calculate_text_similarity,
    calculate_color_similarity,
    calculate_brand_similarity,
    calculate_date_compatibility
)

def test_text_similarity():
    # Identical text
    assert calculate_text_similarity("Apple iPhone 15 Pro", "Apple iPhone 15 Pro") == 1.0
    # Overlapping title
    score = calculate_text_similarity("Black Leather Bellroy Wallet", "Black Leather Wallet Found")
    assert score >= 0.5
    # Completely disjoint text
    score_disjoint = calculate_text_similarity("Basketball", "MacBook Pro")
    assert score_disjoint == 0.0

def test_color_similarity():
    # Exact match
    assert calculate_color_similarity("Black", None, "Black", None) == 1.0
    # Cross match (primary matches secondary)
    assert calculate_color_similarity("Black", "Blue", "Blue", "Black") > 0.5
    # No match
    assert calculate_color_similarity("Red", None, "Green", None) == 0.0

def test_brand_similarity():
    assert calculate_brand_similarity("Sony", "Sony") == 1.0
    assert calculate_brand_similarity("Apple", "Apple Inc.") >= 0.85
    assert calculate_brand_similarity(None, None) == 0.5  # Neutral
    assert calculate_brand_similarity("Sony", "Dell") == 0.0

def test_date_compatibility():
    today = date.today()
    # Lost today, found today
    assert calculate_date_compatibility(today, today) == 1.0
    # Lost 2 days before found
    assert calculate_date_compatibility(today - timedelta(days=2), today) >= 0.8
    # Lost substantially after found (illogical)
    assert calculate_date_compatibility(today + timedelta(days=5), today) <= 0.2

def test_overall_match_score_calculation(app):
    with app.app_context():
        loc = CampusLocation.query.first()
        cat = ItemCategory.query.first()

        lost = LostReport(
            id=1,
            report_code="LOST-001",
            user_id=1,
            category_id=cat.id,
            item_name="Sony WH-1000XM5 Headphones",
            description="Silver over-ear wireless headphones left in study hall.",
            brand="Sony",
            primary_color="Silver",
            secondary_color="Black",
            date_lost=date.today() - timedelta(days=1),
            location=loc,
            location_id=loc.id
        )

        # High similarity found report
        found_strong = FoundReport(
            id=2,
            report_code="FOUND-001",
            user_id=2,
            category_id=cat.id,
            item_name="Sony Over-Ear Headphones",
            description="Silver wireless headphones found on study hall desk.",
            brand="Sony",
            primary_color="Silver",
            secondary_color="Black",
            date_found=date.today(),
            location=loc,
            location_id=loc.id
        )

        score_strong, expl_strong = compute_match_score(lost, found_strong)
        assert score_strong >= 80.0
        assert "Sony" in expl_strong
        assert "Silver" in expl_strong

        # Disjoint category report
        found_different_cat = FoundReport(
            id=3,
            report_code="FOUND-002",
            user_id=3,
            category_id=999,  # Mismatch category
            item_name="Sony WH-1000XM5 Headphones",
            description="Same name but wrong category",
            primary_color="Silver",
            date_found=date.today(),
            location=loc,
            location_id=loc.id
        )
        score_zero, expl_zero = compute_match_score(lost, found_different_cat)
        assert score_zero == 0.0

