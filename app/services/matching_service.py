import math
from datetime import datetime, date
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.extensions import db
from app.models.report import LostReport, FoundReport, CampusLocation
from app.models.match import ItemMatch

ALGORITHM_VERSION = 'v1.2-tfidf'

def calculate_text_similarity(text1, text2):
    """Calculate cosine similarity using TF-IDF for short or descriptive text."""
    t1 = (text1 or '').strip().lower()
    t2 = (text2 or '').strip().lower()
    
    if not t1 or not t2:
        return 0.0
    if t1 == t2:
        return 1.0
        
    try:
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words='english')
        tfidf_matrix = vectorizer.fit_transform([t1, t2])
        sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        # Word overlap boost
        words1 = set(t1.split())
        words2 = set(t2.split())
        overlap = len(words1.intersection(words2)) / max(len(words1.union(words2)), 1)
        return float(max(sim, overlap))
    except Exception:
        # Fallback to Jaccard similarity
        words1 = set(t1.split())
        words2 = set(t2.split())
        if not words1 or not words2:
            return 0.0
        return float(len(words1.intersection(words2)) / len(words1.union(words2)))

def calculate_color_similarity(lost_p, lost_s, found_p, found_s):
    """Compare primary and secondary colors."""
    lp = (lost_p or '').strip().lower()
    ls = (lost_s or '').strip().lower()
    fp = (found_p or '').strip().lower()
    fs = (found_s or '').strip().lower()
    
    if lp == fp and lp != '':
        score = 0.8
        if ls and fs and ls == fs:
            score = 1.0
        elif not ls and not fs:
            score = 1.0
        return score
    elif lp == fs or (ls and ls == fp):
        return 0.6
    elif ls and fs and ls == fs:
        return 0.4
    return 0.0

def calculate_brand_similarity(brand1, brand2):
    """Compare brands."""
    b1 = (brand1 or '').strip().lower()
    b2 = (brand2 or '').strip().lower()
    
    if not b1 and not b2:
        return 0.5  # Neutral when neither mentions a brand
    if b1 and b2:
        if b1 == b2:
            return 1.0
        if b1 in b2 or b2 in b1:
            return 0.85
        return 0.0
    return 0.2  # One specified, one didn't

def calculate_date_compatibility(lost_date, found_date):
    """Lost date should logically be on or before found date, or very close."""
    if not lost_date or not found_date:
        return 0.5
        
    diff = (found_date - lost_date).days
    if diff == 0:
        return 1.0
    elif 1 <= diff <= 3:
        return 0.9
    elif 4 <= diff <= 7:
        return 0.75
    elif 8 <= diff <= 14:
        return 0.55
    elif 15 <= diff <= 30:
        return 0.35
    elif -2 <= diff < 0:
        # Allow slight uncertainty in report dates (user thought they lost it yesterday)
        return 0.4
    elif diff < -2:
        # Report lost significantly after it was already found is unlikely
        return 0.05
    return 0.2

def calculate_location_proximity(loc1, loc2):
    """Compare locations by ID and geographic coordinates if available."""
    if not loc1 or not loc2:
        return 0.3
        
    if loc1.id == loc2.id:
        return 1.0
        
    # Same category (e.g. both in hostel or both in academic block)
    category_match = (loc1.location_category.lower() == loc2.location_category.lower())
    
    # Check coordinates if both have them
    if loc1.latitude and loc1.longitude and loc2.latitude and loc2.longitude:
        # Approximate Euclidean distance in degrees
        d_lat = loc1.latitude - loc2.latitude
        d_lng = loc1.longitude - loc2.longitude
        dist_approx_km = math.sqrt(d_lat**2 + d_lng**2) * 111.0
        if dist_approx_km < 0.2:
            return 0.95
        elif dist_approx_km < 0.5:
            return 0.8
        elif dist_approx_km < 1.0:
            return 0.5
        elif dist_approx_km < 2.0:
            return 0.3
            
    return 0.5 if category_match else 0.1

def compute_match_score(lost, found):
    """
    Computes weighted match score between a LostReport and a FoundReport.
    Weights:
      Category: 25%
      Name similarity: 20%
      Color similarity: 15%
      Brand similarity: 10%
      Description similarity: 10%
      Location proximity: 10%
      Date compatibility: 10%
    """
    # 1. Category (25%)
    cat_score = 1.0 if lost.category_id == found.category_id else 0.0
    if cat_score == 0.0:
        # If categories differ drastically, match is highly unlikely
        return 0.0, "Different item categories."
        
    # 2. Name similarity (20%)
    name_score = calculate_text_similarity(lost.item_name, found.item_name)
    
    # 3. Color similarity (15%)
    color_score = calculate_color_similarity(
        lost.primary_color, lost.secondary_color,
        found.primary_color, found.secondary_color
    )
    
    # 4. Brand similarity (10%)
    brand_score = calculate_brand_similarity(lost.brand, found.brand)
    
    # 5. Description similarity (10%)
    desc_score = calculate_text_similarity(lost.description, found.description)
    
    # 6. Location proximity (10%)
    loc_score = calculate_location_proximity(lost.location, found.location)
    
    # 7. Date compatibility (10%)
    date_score = calculate_date_compatibility(lost.date_lost, found.date_found)
    
    # Weighted total
    weights = {
        'category': 0.25,
        'name': 0.20,
        'color': 0.15,
        'brand': 0.10,
        'description': 0.10,
        'location': 0.10,
        'date': 0.10
    }
    
    raw_score = (
        cat_score * weights['category'] +
        name_score * weights['name'] +
        color_score * weights['color'] +
        brand_score * weights['brand'] +
        desc_score * weights['description'] +
        loc_score * weights['location'] +
        date_score * weights['date']
    )
    
    total_percentage = round(raw_score * 100, 1)
    
    # Construct explanation
    reasons = []
    if cat_score == 1.0:
        cat_name = lost.category.category_name if getattr(lost, 'category', None) else 'Compatible'
        reasons.append(f"Matching category '{cat_name}'")
    if name_score >= 0.7:
        reasons.append(f"Highly similar title ('{lost.item_name}')")
    elif name_score >= 0.4:
        reasons.append(f"Related title ('{found.item_name}')")
    if color_score >= 0.8:
        reasons.append(f"Matching color '{lost.primary_color}'")
    if brand_score >= 0.8 and lost.brand:
        reasons.append(f"Matching brand '{lost.brand}'")
    if loc_score >= 0.8:
        loc_name = found.location.location_name if getattr(found, 'location', None) else 'Campus'
        reasons.append(f"Reported at or near {loc_name}")
    if date_score >= 0.8:
        reasons.append(f"Compatible timeframe ({lost.date_lost} vs {found.date_found})")
        
    explanation = "; ".join(reasons) if reasons else "Compatible item attributes identified."
    return total_percentage, explanation

def evaluate_and_store_matches(report, is_lost=True):
    """
    Evaluates matches for a newly approved or updated report against active candidate reports.
    Stores results in the item_matches table.
    """
    if report.review_status != 'approved' or report.report_status not in ['active', 'pending']:
        return []
        
    matches_created_or_updated = []
    
    if is_lost:
        # Compare this lost report against all approved, active found reports
        found_reports = FoundReport.query.filter_by(
            review_status='approved',
            report_status='active',
            category_id=report.category_id
        ).all()
        
        for found in found_reports:
            # Skip if reporter is the finder
            if found.user_id == report.user_id:
                continue
                
            score, explanation = compute_match_score(report, found)
            if score >= 40.0:  # Threshold for display
                match = ItemMatch.query.filter_by(
                    lost_report_id=report.id,
                    found_report_id=found.id
                ).first()
                
                if not match:
                    match = ItemMatch(
                        lost_report_id=report.id,
                        found_report_id=found.id,
                        match_score=score,
                        match_explanation=explanation,
                        algorithm_version=ALGORITHM_VERSION,
                        match_status='potential'
                    )
                    db.session.add(match)
                else:
                    match.match_score = score
                    match.match_explanation = explanation
                    match.algorithm_version = ALGORITHM_VERSION
                matches_created_or_updated.append(match)
    else:
        # Compare this found report against all approved, active lost reports
        lost_reports = LostReport.query.filter_by(
            review_status='approved',
            report_status='active',
            category_id=report.category_id
        ).all()
        
        for lost in lost_reports:
            if lost.user_id == report.user_id:
                continue
                
            score, explanation = compute_match_score(lost, report)
            if score >= 40.0:
                match = ItemMatch.query.filter_by(
                    lost_report_id=lost.id,
                    found_report_id=report.id
                ).first()
                
                if not match:
                    match = ItemMatch(
                        lost_report_id=lost.id,
                        found_report_id=report.id,
                        match_score=score,
                        match_explanation=explanation,
                        algorithm_version=ALGORITHM_VERSION,
                        match_status='potential'
                    )
                    db.session.add(match)
                else:
                    match.match_score = score
                    match.match_explanation = explanation
                    match.algorithm_version = ALGORITHM_VERSION
                matches_created_or_updated.append(match)
                
    db.session.commit()
    return matches_created_or_updated

def recalculate_all_matches():
    """Admin tool to re-run matching across all approved active reports."""
    lost_reports = LostReport.query.filter_by(review_status='approved', report_status='active').all()
    count = 0
    for lost in lost_reports:
        matches = evaluate_and_store_matches(lost, is_lost=True)
        count += len(matches)
    return count

