from datetime import datetime, timedelta
from io import BytesIO
from flask import Blueprint, render_template, request, send_file, current_app, abort
from flask_login import login_required, current_user
from sqlalchemy import func
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from app.extensions import db
from app.models.report import LostReport, FoundReport, ItemCategory, CampusLocation
from app.models.claim import Claim
from app.models.handover import Handover
from app.models.user import Department, User

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')

@analytics_bp.before_request
@login_required
def require_admin():
    if not current_user.is_admin:
        abort(403)

@analytics_bp.route('')
def index():
    days = request.args.get('days', 30, type=int)
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    # Quantitative metrics
    total_lost = LostReport.query.filter(LostReport.created_at >= cutoff).count()
    total_found = FoundReport.query.filter(FoundReport.created_at >= cutoff).count()
    total_claims = Claim.query.filter(Claim.created_at >= cutoff).count()
    total_recovered = Handover.query.filter(Handover.completed_at >= cutoff, Handover.handover_status == 'completed').count()
    
    recovery_rate = round((total_recovered / max(total_lost + total_found, 1)) * 100, 1)

    # Categories
    categories = ItemCategory.query.filter_by(status='active').all()
    cat_names = [c.category_name for c in categories]
    cat_lost_counts = [LostReport.query.filter(LostReport.category_id == c.id, LostReport.created_at >= cutoff).count() for c in categories]
    cat_found_counts = [FoundReport.query.filter(FoundReport.category_id == c.id, FoundReport.created_at >= cutoff).count() for c in categories]

    # Department breakdown (for reports filed by students/staff of that department)
    departments = Department.query.filter_by(status='active').all()
    dept_names = []
    dept_report_counts = []
    for d in departments:
        user_ids = [u.id for u in d.users]
        cnt = (
            LostReport.query.filter(LostReport.user_id.in_(user_ids), LostReport.created_at >= cutoff).count() if user_ids else 0
        )
        if cnt > 0 or len(dept_names) < 8:
            dept_names.append(d.department_code)
            dept_report_counts.append(cnt)

    # Location hotspots
    location_stats = db.session.query(
        CampusLocation.location_name,
        func.count(LostReport.id).label('lost_cnt'),
        func.count(FoundReport.id).label('found_cnt')
    ).outerjoin(LostReport, (CampusLocation.id == LostReport.location_id) & (LostReport.created_at >= cutoff))\
     .outerjoin(FoundReport, (CampusLocation.id == FoundReport.location_id) & (FoundReport.created_at >= cutoff))\
     .group_by(CampusLocation.id)\
     .order_by((func.count(LostReport.id) + func.count(FoundReport.id)).desc())\
     .limit(10).all()

    return render_template(
        'admin/analytics.html',
        days=days,
        total_lost=total_lost,
        total_found=total_found,
        total_claims=total_claims,
        total_recovered=total_recovered,
        recovery_rate=recovery_rate,
        cat_names=cat_names,
        cat_lost_counts=cat_lost_counts,
        cat_found_counts=cat_found_counts,
        dept_names=dept_names,
        dept_report_counts=dept_report_counts,
        location_stats=location_stats
    )

@analytics_bp.route('/export-csv')
def export_csv():
    # Privacy protected export using Pandas
    lost = LostReport.query.all()
    found = FoundReport.query.all()
    
    rows = []
    for r in lost:
        rows.append({
            'Report_Code': r.report_code,
            'Type': 'Lost',
            'Item_Name': r.item_name,
            'Category': r.category.category_name if r.category else '',
            'Location': r.location.location_name if r.location else '',
            'Date': r.date_lost.isoformat() if r.date_lost else '',
            'Color': r.primary_color,
            'Brand': r.brand or '',
            'Review_Status': r.review_status,
            'Report_Status': r.report_status,
            'Created_At': r.created_at.strftime('%Y-%m-%d %H:%M') if r.created_at else ''
        })
        
    for f in found:
        rows.append({
            'Report_Code': f.report_code,
            'Type': 'Found',
            'Item_Name': f.item_name,
            'Category': f.category.category_name if f.category else '',
            'Location': f.location.location_name if f.location else '',
            'Date': f.date_found.isoformat() if f.date_found else '',
            'Color': f.primary_color,
            'Brand': f.brand or '',
            'Review_Status': f.review_status,
            'Report_Status': f.report_status,
            'Created_At': f.created_at.strftime('%Y-%m-%d %H:%M') if f.created_at else ''
        })
        
    df = pd.DataFrame(rows)
    
    buffer = BytesIO()
    df.to_csv(buffer, index=False, encoding='utf-8')
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"CampusConnect_Reports_Export_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    )

@analytics_bp.route('/export-pdf')
def export_pdf():
    # Executive summary PDF with ReportLab
    total_lost = LostReport.query.count()
    total_found = FoundReport.query.count()
    total_claims = Claim.query.count()
    total_recovered = Handover.query.filter_by(handover_status='completed').count()
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    elements = []
    
    # Title
    elements.append(Paragraph("CAMPUSCONNECT EXECUTIVE ANALYTICS SUMMARY", styles['Heading1']))
    elements.append(Paragraph(f"Generated on: {datetime.utcnow().strftime('%B %d, %Y %H:%M UTC')}", styles['Normal']))
    elements.append(Spacer(1, 15))
    
    # KPI Table
    kpi_data = [
        ['Metric', 'Value', 'Status / Benchmark'],
        ['Total Lost Belongings Reported', str(total_lost), 'Active records'],
        ['Total Found Belongings Submitted', str(total_found), 'Active records'],
        ['Ownership Claims Submitted', str(total_claims), 'Processed by admin'],
        ['Items Successfully Returned', str(total_recovered), 'Verified handovers'],
        ['Recovery Success Rate', f"{round((total_recovered/max(total_lost+total_found, 1))*100, 1)}%", 'Campus efficiency KPI']
    ]
    t = Table(kpi_data, colWidths=[200, 100, 200])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#14213D')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F8FAFC'), colors.white])
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))
    
    # Hotspot Locations
    elements.append(Paragraph("Top Campus Lost & Found Locations", styles['Heading2']))
    locs = db.session.query(
        CampusLocation.location_name,
        func.count(LostReport.id) + func.count(FoundReport.id)
    ).outerjoin(LostReport, CampusLocation.id == LostReport.location_id)\
     .outerjoin(FoundReport, CampusLocation.id == FoundReport.location_id)\
     .group_by(CampusLocation.id)\
     .order_by((func.count(LostReport.id) + func.count(FoundReport.id)).desc())\
     .limit(8).all()
     
    loc_data = [['Campus Location', 'Total Incidents Logged']]
    for l in locs:
        loc_data.append([l[0], str(l[1] or 0)])
        
    loc_table = Table(loc_data, colWidths=[320, 180])
    loc_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563EB')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F8FAFC'), colors.white])
    ]))
    elements.append(loc_table)
    
    doc.build(elements)
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"CampusConnect_Executive_Summary_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    )

