"""
Database Seeding Script for CampusConnect – Smart Campus Lost & Found Portal
Generates realistic, production-style demonstration accounts, campus locations,
categories, reports, claims, intelligent matches, handovers, and notifications.
"""

import os
from datetime import datetime, date, timedelta
from app import create_app
from app.extensions import db
from app.models.user import User, Department
from app.models.report import CampusLocation, ItemCategory, LostReport, FoundReport, ReportImage
from app.models.match import ItemMatch
from app.models.claim import Claim
from app.models.handover import Handover
from app.models.message import Conversation, Message
from app.models.notification import Notification, Announcement, AuditLog, SystemSetting
from app.services.matching_service import evaluate_and_store_matches, recalculate_all_matches
from app.services.handover_service import schedule_handover, complete_handover

DEMO_PASSWORD = "CampusPass2026!"

def seed_database():
    app = create_app('development')
    with app.app_context():
        print("🌱 [CampusConnect Seeder] Dropping existing tables and creating clean schema...")
        db.drop_all()
        db.create_all()

        print("1️⃣ Seeding Academic Departments...")
        depts_data = [
            ("Computer Science & Engineering", "CSE"),
            ("Electrical & Electronics Engineering", "EEE"),
            ("Mechanical Engineering", "ME"),
            ("School of Management & Business", "SMB"),
            ("Biological Sciences & Bioengineering", "BSBE"),
            ("Physics & Applied Mathematics", "PAM"),
            ("Humanities & Social Sciences", "HSS"),
            ("Department of Chemistry", "CHEM"),
            ("Civil & Environmental Engineering", "CEE"),
            ("School of Law & Governance", "SLG")
        ]
        departments = []
        for name, code in depts_data:
            d = Department(department_name=name, department_code=code, status='active')
            db.session.add(d)
            departments.append(d)
        db.session.commit()

        print("2️⃣ Seeding Campus Locations with Geographic Coordinates (Amrita Vishwa Vidyapeetham, Nagercoil)...")
        locations_data = [
            ("Amrita Main Academic & Administrative Bhavan", "Academic Block", "Central administrative offices, directorate, and dean offices", 8.22901, 77.41539),
            ("Central Library & Digital Knowledge Centre", "Library", "Central library reading halls, reference stacks, and digital resources", 8.22935, 77.41570),
            ("Computer Science & AI Tech Labs (Amrita Block A)", "Academic Block", "Software engineering, networking, and machine intelligence laboratories", 8.22950, 77.41515),
            ("Mechanical & Civil Engineering Labs", "Laboratory", "Thermal engineering, fluid mechanics, CAD/CAM and prototyping workshop", 8.22860, 77.41480),
            ("Amrita Central Quadrangle & Lawns", "Sports Ground", "Open-air landscaped gathering quad and green central courtyard", 8.22890, 77.41520),
            ("Campus Sports Complex & Outdoor Courts", "Sports Ground", "Basketball court, volleyball, athletic track, and badminton arenas", 8.22790, 77.41550),
            ("Amrita Dining Commons & Food Court", "Canteen & Dining", "Vegetarian dining hall, campus refreshments, and student cafeteria", 8.22880, 77.41610),
            ("Men's Student Residence (Amrita Hostel)", "Hostel", "Undergraduate and postgraduate men's residential quarters", 8.22820, 77.41650),
            ("Amrita Innovation & Robotics Hub", "Academic Block", "Embedded systems, IoT maker space, and entrepreneurship incubator", 8.22960, 77.41460),
            ("Campus Security & Lost Property HQ", "Administrative Office", "Main entrance security gate, pass desk, and official lost property holding desk", 8.22850, 77.41440),
            ("Amrita Grand Auditorium & Seminar Hall", "Academic Block", "Main university auditorium, cultural symposia, and convocation hall", 8.22980, 77.41590),
            ("Women's Student Residence Complex", "Hostel", "Secure campus women's hostel facility and recreation common rooms", 8.23010, 77.41630)
        ]
        locations = []
        for name, cat, desc, lat, lng in locations_data:
            loc = CampusLocation(location_name=name, location_category=cat, description=desc, latitude=lat, longitude=lng, status='active')
            db.session.add(loc)
            locations.append(loc)
        db.session.commit()

        print("3️⃣ Seeding Item Categories...")
        categories_data = [
            ("Electronics", "bi-laptop", "Laptops, tablets, chargers, and electronic gadgets"),
            ("Mobile Phones", "bi-phone", "Smartphones, basic phones, and phone cases"),
            ("Laptops and Accessories", "bi-pc-display", "Notebooks, chargers, adapters, and mice"),
            ("Wallets and Purses", "bi-wallet2", "Leather wallets, coin purses, and cardholders"),
            ("Identity Cards", "bi-person-badge", "University student IDs, driving licenses, and membership cards"),
            ("Books and Notebooks", "bi-book", "Textbooks, course binders, and notebooks"),
            ("Bags", "bi-backpack", "Backpacks, duffel bags, tote bags, and laptop sleeves"),
            ("Keys", "bi-key", "Room keys, vehicle key fobs, and keychains"),
            ("Watches", "bi-watch", "Smartwatches, analog wristwatches, and fitness bands"),
            ("Jewelry", "bi-gem", "Rings, necklaces, bracelets, and earrings"),
            ("Clothing", "bi-tag", "Jackets, hoodies, caps, scarves, and coats"),
            ("Water Bottles", "bi-cup-straw", "Reusable bottles, thermos flasks, and tumblers"),
            ("Stationery", "bi-pen", "Pencil cases, calculators, drawing sets, and rulers"),
            ("Sports Equipment", "bi-trophy", "Rackets, balls, gym accessories, and yoga mats"),
            ("Other", "bi-box", "Miscellaneous belongings not listed in other categories")
        ]
        categories = []
        for name, icon, desc in categories_data:
            c = ItemCategory(category_name=name, icon_class=icon, description=desc, status='active')
            db.session.add(c)
            categories.append(c)
        db.session.commit()

        print("4️⃣ Seeding System Settings...")
        setting = SystemSetting(
            key='CAMPUS_EMAIL_DOMAINS',
            value='campusconnect.edu, student.campusconnect.edu, faculty.campusconnect.edu, amrita.edu, ng.amrita.edu',
            description='Allowed university email domains'
        )
        db.session.add(setting)
        db.session.commit()

        print("5️⃣ Seeding Administrative and User Accounts...")
        # 1 Super Admin
        super_admin = User(
            full_name="Dr. Eleanor Vance",
            email="superadmin@campusconnect.edu",
            institutional_id="ADM-SA-0001",
            department_id=departments[0].id,
            role="super_admin",
            user_type="staff",
            phone="+1 (555) 010-0001",
            email_verified=True,
            account_status="active"
        )
        super_admin.set_password(DEMO_PASSWORD)
        db.session.add(super_admin)

        # 2 Campus Admins
        admin1 = User(
            full_name="Marcus Brody",
            email="admin1@campusconnect.edu",
            institutional_id="ADM-CA-0002",
            department_id=departments[1].id,
            role="admin",
            user_type="staff",
            phone="+1 (555) 010-0002",
            email_verified=True,
            account_status="active"
        )
        admin1.set_password(DEMO_PASSWORD)
        db.session.add(admin1)

        admin2 = User(
            full_name="Sarah Jenkins",
            email="admin2@campusconnect.edu",
            institutional_id="ADM-CA-0003",
            department_id=departments[3].id,
            role="admin",
            user_type="staff",
            phone="+1 (555) 010-0003",
            email_verified=True,
            account_status="active"
        )
        admin2.set_password(DEMO_PASSWORD)
        db.session.add(admin2)
        db.session.commit()

        # 22 Sample Students & Staff Members
        users_list = []
        sample_profiles = [
            ("Alex Rivers", "alex.rivers@student.campusconnect.edu", "STU-2026-1011", 0, "student", 3),
            ("Samantha Hayes", "samantha.hayes@student.campusconnect.edu", "STU-2026-1012", 1, "student", 2),
            ("David Kim", "david.kim@student.campusconnect.edu", "STU-2026-1013", 2, "student", 4),
            ("Maria Garcia", "maria.garcia@student.campusconnect.edu", "STU-2026-1014", 3, "student", 1),
            ("James Wilson", "james.wilson@student.campusconnect.edu", "STU-2026-1015", 4, "student", 2),
            ("Emily Chen", "emily.chen@student.campusconnect.edu", "STU-2026-1016", 0, "student", 3),
            ("Lucas Patel", "lucas.patel@student.campusconnect.edu", "STU-2026-1017", 5, "student", 4),
            ("Chloe Martin", "chloe.martin@student.campusconnect.edu", "STU-2026-1018", 6, "student", 1),
            ("Ethan Taylor", "ethan.taylor@student.campusconnect.edu", "STU-2026-1019", 7, "student", 2),
            ("Olivia Brown", "olivia.brown@student.campusconnect.edu", "STU-2026-1020", 8, "student", 3),
            ("Daniel Jackson", "daniel.jackson@student.campusconnect.edu", "STU-2026-1021", 9, "student", 2),
            ("Sophia Miller", "sophia.miller@student.campusconnect.edu", "STU-2026-1022", 0, "student", 1),
            ("Noah White", "noah.white@student.campusconnect.edu", "STU-2026-1023", 1, "student", 4),
            ("Isabella Harris", "isabella.harris@student.campusconnect.edu", "STU-2026-1024", 2, "student", 2),
            ("Liam Clark", "liam.clark@student.campusconnect.edu", "STU-2026-1025", 3, "student", 3),
            ("Mia Lewis", "mia.lewis@student.campusconnect.edu", "STU-2026-1026", 4, "student", 1),
            ("Benjamin Walker", "benjamin.walker@student.campusconnect.edu", "STU-2026-1027", 5, "student", 3),
            ("Charlotte Hall", "charlotte.hall@student.campusconnect.edu", "STU-2026-1028", 6, "student", 4),
            ("Prof. Robert Lang", "robert.lang@faculty.campusconnect.edu", "FAC-2026-2001", 0, "faculty", None),
            ("Dr. Angela Rossi", "angela.rossi@faculty.campusconnect.edu", "FAC-2026-2002", 4, "faculty", None),
            ("Officer Thomas Burke", "thomas.burke@campusconnect.edu", "STF-2026-3001", 3, "staff", None),
            ("Helen Zhao", "helen.zhao@campusconnect.edu", "STF-2026-3002", 0, "staff", None)
        ]

        for full_name, email, inst_id, dept_idx, utype, year in sample_profiles:
            u = User(
                full_name=full_name,
                email=email,
                institutional_id=inst_id,
                department_id=departments[dept_idx].id,
                role="user",
                user_type=utype,
                year_of_study=year,
                phone="+1 (555) 012-3000",
                email_verified=True,
                account_status="active"
            )
            u.set_password(DEMO_PASSWORD)
            db.session.add(u)
            users_list.append(u)
        db.session.commit()

        print("6️⃣ Seeding Sample Lost Reports (15 Reports)...")
        today = date.today()
        lost_data = [
            ("Black Leather Bifold Wallet", 3, "Lost my black leather wallet containing campus debit card and driver license.", "Bellroy", "Black", None, today - timedelta(days=2), "Around 14:00", 0, "2nd floor quiet room", "Student ID STU-2026-1011 inside, small red thread near stitch"),
            ("Apple iPhone 15 Pro (Blue Titanium)", 1, "Blue Titanium iPhone with a clear Spigen MagSafe protective case.", "Apple", "Blue", "Black", today - timedelta(days=1), "11:30 AM", 1, "Food court table near coffee stall", "Lockscreen is a photo of a golden retriever; lock PIN is 6 digits"),
            ("MacBook Pro 14-inch Space Gray", 2, "Space Gray M2 MacBook Pro in a dark gray padded sleeve.", "Apple", "Gray", "Black", today - timedelta(days=3), "16:00", 2, "Lab 204 workstation 7", "Has a small GitHub sticker and MIT licensed sticker on back"),
            ("Calculus 4th Edition Textbook", 5, "Hardcover multivariable calculus textbook with yellow highlighter notes.", "Stewart", "Blue", "Yellow", today - timedelta(days=4), "Morning lecture", 10, "Auditorium 101 seat 45", "Name 'David Kim' written on inside front cover page"),
            ("Matte Black Stainless Hydro Flask", 11, "32 oz wide mouth Hydro Flask with a flex straw cap.", "Hydro Flask", "Black", None, today - timedelta(days=1), "3:00 PM", 5, "Bench next to squash court 2", "Contains a small scratch near the bottom rim"),
            ("Campus Student ID Card", 4, "Lost official magnetic stripe campus ID card.", "CampusConnect", "White", "Blue", today - timedelta(days=2), "Lunch time", 6, "Tray return station", "Student ID number STU-2026-1014; Name Maria Garcia"),
            ("Sony WH-1000XM5 Wireless Headphones", 0, "Over-ear silver noise-canceling headphones in black zipper case.", "Sony", "Silver", "Black", today - timedelta(days=5), "Evening study session", 0, "4th floor computer lounge", "Includes gold-plated audio adapter inside mesh pocket"),
            ("Graphite Car Key Fob with Carabiner", 7, "Honda key fob attached to a blue metallic climbing carabiner with gym tag.", "Honda", "Black", "Blue", today - timedelta(days=3), "9:00 AM", 4, "Walkway near quad fountain", "Gym barcode tag ending in #8841"),
            ("Casio G-Shock Rugged Watch", 8, "Matte black digital G-Shock sport watch with resin band.", "Casio", "Black", None, today - timedelta(days=6), "17:15", 5, "Locker room bench 12", "Alarm is set for 06:30 AM"),
            ("Navy Patagonia Torrentshell Jacket", 10, "Navy blue lightweight waterproof rain jacket size Medium.", "Patagonia", "Navy", "Gray", today - timedelta(days=2), "After chemistry lecture", 3, "Lecture Hall C hanger", "Small theater ticket stub in right zipped pocket"),
            ("TI-84 Plus CE Graphing Calculator", 12, "Color screen graphing calculator with sliding protective cover.", "Texas Instruments", "Black", "White", today - timedelta(days=7), "13:00", 10, "Room 105", "Cover has initials 'ET' etched into bottom corner"),
            ("North Face Borealis Backpack", 6, "Black and dark green commuter backpack with laptop compartment.", "The North Face", "Black", "Green", today - timedelta(days=4), "15:30", 1, "Under high table in student union lounge", "Contains spiral notebook and a silver umbrella"),
            ("Silver Chain Bracelet with Clasp", 9, "Sterling silver link bracelet with lobster claw clasp.", "Tiffany & Co.", "Silver", None, today - timedelta(days=3), "18:00", 8, "Conference Room B", "Inscribed with date '2023.05' on clasp"),
            ("Wilson Evolution Basketball", 13, "Official size indoor basketball with deep channel design.", "Wilson", "Brown", "Black", today - timedelta(days=8), "Evening pick-up game", 5, "Main gymnasium court A", "Initials 'LK' marked near air valve in black marker"),
            ("Anker 737 Power Bank (24,000mAh)", 0, "Heavy high-capacity portable charger with digital smart display.", "Anker", "Black", "Silver", today - timedelta(days=1), "10:00 AM", 8, "Coworking desk 14", "Shows 84% battery charge on OLED screen")
        ]

        seed_images = [
            "uploads/seed/wallet.jpg",
            "uploads/seed/iphone.jpg",
            "uploads/seed/macbook.jpg",
            "uploads/seed/calculus.jpg",
            "uploads/seed/hydroflask.jpg",
            "uploads/seed/idcard.jpg",
            "uploads/seed/headphones.jpg",
            "uploads/seed/carkey.jpg",
            "uploads/seed/watch.jpg",
            "uploads/seed/jacket.jpg",
            "uploads/seed/calculator.jpg",
            "uploads/seed/backpack.jpg",
            "uploads/seed/bracelet.jpg",
            "uploads/seed/basketball.jpg",
            "uploads/seed/powerbank.jpg"
        ]

        lost_reports = []
        for i, (name, cat_idx, desc, brand, p_col, s_col, d_lost, a_time, loc_idx, add_loc, secret) in enumerate(lost_data):
            code = f"LOST-2026-{(i+1):05d}"
            img = seed_images[i % len(seed_images)]
            r = LostReport(
                report_code=code,
                user_id=users_list[i % len(users_list)].id,
                category_id=categories[cat_idx].id,
                item_name=name,
                description=desc,
                brand=brand,
                primary_color=p_col,
                secondary_color=s_col,
                date_lost=d_lost,
                approximate_time=a_time,
                location_id=locations[loc_idx].id,
                additional_location=add_loc,
                image_path=img,
                identifying_features=secret,
                review_status="approved",
                report_status="active"
            )
            db.session.add(r)
            lost_reports.append(r)
        db.session.commit()

        # Add ReportImage entries for gallery
        for r in lost_reports:
            if r.image_path:
                db.session.add(ReportImage(report_type='lost', report_id=r.id, image_path=r.image_path))
        db.session.commit()

        print("7️⃣ Seeding Sample Found Reports (15 Reports, engineered for strong/moderate matches)...")
        found_data = [
            ("Black Leather Wallet Found in Library", 3, "Black bifold wallet located between armchairs on library 2nd floor.", "Bellroy", "Black", None, today - timedelta(days=2), "14:45", 0, "security_office", "Locker 14 at Security HQ", "Contains student ID card ending in 9041 and 2 keys on blue thread"),
            ("Apple iPhone 15 Pro Found in Food Court", 1, "Blue iPhone with transparent magnetic case discovered on cafeteria table.", "Apple", "Blue", "Black", today - timedelta(days=1), "12:15 PM", 1, "admin_office", "Student Union Info Desk", "Dog lockscreen image; 6-digit passcode"),
            ("MacBook Pro with Stickers", 2, "Space Gray laptop found unattended on 2nd floor laboratory desk.", "Apple", "Gray", "Black", today - timedelta(days=3), "17:00", 2, "security_office", "Central Security Desk", "Back cover contains multiple developer stickers"),
            ("Calculus Multivariable Textbook", 5, "Hardbound blue textbook found on desk in Lecture Hall 101.", "Stewart", "Blue", "Yellow", today - timedelta(days=4), "11:00 AM", 10, "admin_office", "Undergrad Office Desk", "Highlighted in yellow, name written inside"),
            ("Black Metal Water Bottle", 11, "Large matte black insulated drink bottle found near squash courts.", "Hydro Flask", "Black", None, today - timedelta(days=1), "16:00", 5, "finder_possession", "In finder possession (Lucas Patel)", "Scratch mark on bottom edge"),
            ("Campus Identification Card", 4, "Student ID card found near dining hall tray drop.", "CampusConnect", "White", "Blue", today - timedelta(days=2), "13:30", 6, "security_office", "Security Front Window", "Name Maria Garcia, photo verified"),
            ("Sony Over-Ear Noise-Canceling Headphones", 0, "Silver headphones in black carrying case left on workstation table.", "Sony", "Silver", "Black", today - timedelta(days=5), "19:00", 0, "admin_office", "Library 1st Floor Desk", "Contains gold audio jack plug in pouch"),
            ("Honda Car Key with Carabiner", 7, "Single car key fob with blue clip found on central lawn pathway.", "Honda", "Black", "Blue", today - timedelta(days=3), "10:30 AM", 4, "security_office", "Security Key Lockbox 03", "Attached to gym tag with barcode"),
            ("G-Shock Digital Watch", 8, "Black sports watch found in recreation center changing area.", "Casio", "Black", None, today - timedelta(days=6), "18:30", 5, "collection_point", "Gym Front Desk Bin", "Black resin strap with digital display"),
            ("Navy Rain Jacket (Patagonia)", 10, "Navy hooded windbreaker left hanging in lecture hall coat rack.", "Patagonia", "Navy", "Gray", today - timedelta(days=2), "16:00", 3, "admin_office", "Science Admin Office Room 110", "Theater ticket stub found in pocket"),
            ("Scientific Graphing Calculator", 12, "Black handheld graphing calculator found in lecture hall.", "Texas Instruments", "Black", "White", today - timedelta(days=7), "14:15", 10, "collection_point", "Math Dept Office", "Letters etched on cover"),
            ("North Face Backpack", 6, "Dark green and black commuter backpack found under lounge table.", "The North Face", "Black", "Green", today - timedelta(days=4), "16:30", 1, "security_office", "Main Security Holding", "Contains silver umbrella and notebook"),
            ("Silver Wrist Bracelet", 9, "Delicate silver link chain bracelet found on seminar table.", "Tiffany & Co.", "Silver", None, today - timedelta(days=3), "19:00", 8, "admin_office", "Innovation Hub Desk", "Engraving on clasp"),
            ("Basketball in Gym", 13, "Wilson leather basketball found after evening rec hours.", "Wilson", "Brown", "Black", today - timedelta(days=8), "21:00", 5, "collection_point", "Equipment Room B", "Marker initials near valve"),
            ("High-Power Anker Power Bank", 0, "Black heavy portable battery bank found in study pod.", "Anker", "Black", "Silver", today - timedelta(days=1), "11:00 AM", 8, "admin_office", "Innovation Center Reception", "Digital display battery screen")
        ]

        found_reports = []
        for i, (name, cat_idx, desc, brand, p_col, s_col, d_found, a_time, loc_idx, cust_stat, cust_loc, secret) in enumerate(found_data):
            code = f"FOUND-2026-{(i+1):05d}"
            # Choose a different finder so reporter != finder
            finder = users_list[(i + 5) % len(users_list)]
            img = seed_images[i % len(seed_images)]
            r = FoundReport(
                report_code=code,
                user_id=finder.id,
                category_id=categories[cat_idx].id,
                item_name=name,
                description=desc,
                brand=brand,
                primary_color=p_col,
                secondary_color=s_col,
                date_found=d_found,
                approximate_time=a_time,
                location_id=locations[loc_idx].id,
                custody_status=cust_stat,
                custody_location=cust_loc,
                image_path=img,
                identifying_features=secret,
                review_status="approved",
                report_status="active"
            )
            db.session.add(r)
            found_reports.append(r)
        db.session.commit()

        # Add ReportImage entries for gallery
        for r in found_reports:
            if r.image_path:
                db.session.add(ReportImage(report_type='found', report_id=r.id, image_path=r.image_path))
        db.session.commit()

        print("8️⃣ Running Python Intelligent Matching Engine across all reports...")
        matches_count = recalculate_all_matches()
        print(f"   -> Successfully calculated and stored {matches_count} intelligent matches!")

        print("9️⃣ Seeding Sample Claims in various workflow stages...")
        # Claim 1: Approved and Handover Scheduled
        claim1 = Claim(
            claim_code="CLAIM-2026-00001",
            lost_report_id=lost_reports[0].id,
            found_report_id=found_reports[0].id,
            claimant_id=lost_reports[0].user_id,
            ownership_description="I dropped my black Bellroy wallet while studying on the 2nd floor of the library right before my 2 PM class.",
            identifying_answers="Contains my student card STU-2026-1011, driver's license with address in Springfield, and red thread stitch near bottom fold.",
            approximate_purchase_date="November 2024",
            contact_method="email",
            claim_status="approved",
            review_notes="Verified against finder note. Student ID number matches claimant profile perfectly.",
            reviewed_by=admin1.id
        )
        db.session.add(claim1)
        db.session.flush()

        convo1 = Conversation(claim_id=claim1.id)
        db.session.add(convo1)
        db.session.flush()

        msg1 = Message(
            conversation_id=convo1.id,
            sender_id=admin1.id,
            message_text="Hello Alex, we verified your student card details inside the wallet. Your claim is approved. Please confirm your handover appointment.",
            is_read=True,
            created_at=datetime.utcnow() - timedelta(hours=5)
        )
        msg2 = Message(
            conversation_id=convo1.id,
            sender_id=lost_reports[0].user_id,
            message_text="Thank you so much! I will be there at the security office with my passport for secondary identification.",
            is_read=True,
            created_at=datetime.utcnow() - timedelta(hours=3)
        )
        db.session.add(msg1)
        db.session.add(msg2)

        # Schedule Handover for Claim 1
        handover1, _ = schedule_handover(
            claim_id=claim1.id,
            scheduled_location_id=locations[9].id,  # Security HQ
            scheduled_at=datetime.utcnow() + timedelta(days=1, hours=2),
            admin_user=admin1,
            notes="Please ask for Officer Burke at the Security Front Desk and bring physical photo ID."
        )

        # Claim 2: Completed & Returned Item (with QR code and completed status)
        claim2 = Claim(
            claim_code="CLAIM-2026-00002",
            lost_report_id=lost_reports[5].id,
            found_report_id=found_reports[5].id,
            claimant_id=lost_reports[5].user_id,
            ownership_description="Lost my campus ID card at the dining commons tray return.",
            identifying_answers="Name Maria Garcia, photo is wearing black glasses, student number STU-2026-1014.",
            approximate_purchase_date="August 2025",
            contact_method="email",
            claim_status="approved",
            review_notes="In-person photo ID verification completed successfully.",
            reviewed_by=admin2.id
        )
        db.session.add(claim2)
        db.session.flush()

        convo2 = Conversation(claim_id=claim2.id)
        db.session.add(convo2)
        db.session.flush()

        handover2, _ = schedule_handover(
            claim_id=claim2.id,
            scheduled_location_id=locations[9].id,
            scheduled_at=datetime.utcnow() - timedelta(days=1),
            admin_user=admin2,
            notes="Completed handover at Central Security Desk."
        )
        # Complete Handover 2
        complete_handover(handover2.id, admin2)

        # Claim 3: Under Review
        claim3 = Claim(
            claim_code="CLAIM-2026-00003",
            lost_report_id=lost_reports[1].id,
            found_report_id=found_reports[1].id,
            claimant_id=lost_reports[1].user_id,
            ownership_description="Left my blue iPhone 15 Pro on the dining table after lunch.",
            identifying_answers="Gold dog wallpaper on lockscreen; small scratch near speaker grill.",
            approximate_purchase_date="October 2024",
            contact_method="portal",
            claim_status="under_review",
            review_notes="Awaiting admin verification of serial number.",
            reviewed_by=admin1.id
        )
        db.session.add(claim3)
        db.session.flush()
        convo3 = Conversation(claim_id=claim3.id)
        db.session.add(convo3)

        # Claim 4: Additional Evidence Required
        claim4 = Claim(
            claim_code="CLAIM-2026-00004",
            lost_report_id=lost_reports[2].id,
            found_report_id=found_reports[2].id,
            claimant_id=lost_reports[2].user_id,
            ownership_description="Left my MacBook Pro in Lab 204.",
            identifying_answers="Space gray with developer stickers.",
            approximate_purchase_date="March 2024",
            contact_method="email",
            claim_status="evidence_required",
            review_notes="Please provide proof of purchase or original box photo showing serial number.",
            reviewed_by=admin1.id
        )
        db.session.add(claim4)
        db.session.flush()
        convo4 = Conversation(claim_id=claim4.id)
        db.session.add(convo4)

        db.session.commit()

        print("🔟 Seeding Campus Announcements...")
        announcements_data = [
            ("Central Library Annual Lost & Found Collection Drive", "All unclaimed textbooks, stationery, and water bottles currently deposited at the Central Library desk will be transferred to Security HQ this Friday.", "Collection Drive", "all", date.today() + timedelta(days=14), super_admin.id),
            ("Multiple Student ID Cards Deposited at Security Desk", "Twelve university identification cards found near the dining commons and student union have been surrendered to Campus Security HQ. Check the portal to submit claims.", "Security Alert", "students", date.today() + timedelta(days=7), admin1.id),
            ("Updated Handover Hours at Student Union", "The Lost & Found pickup station at the Student Union Helpdesk is now open Monday through Friday from 9:00 AM to 5:00 PM.", "Location Notice", "all", date.today() + timedelta(days=30), admin2.id)
        ]
        for title, desc, cat, aud, exp, creator in announcements_data:
            ann = Announcement(title=title, description=desc, category=cat, target_audience=aud, expires_at=exp, created_by=creator, status='active')
            db.session.add(ann)
        db.session.commit()

        print("1️⃣1️⃣ Seeding Notifications & Audit Logs...")
        notif1 = Notification(
            user_id=lost_reports[0].user_id,
            title="High Confidence Match Found (95%)",
            message=f"An item matching your lost 'Black Leather Bifold Wallet' was reported found in the Main University Library.",
            notification_type="match_found",
            link_url=f"/reports/found/{found_reports[0].id}",
            related_report_id=found_reports[0].id,
            is_read=False
        )
        notif2 = Notification(
            user_id=lost_reports[0].user_id,
            title="Handover Scheduled for Claim CLAIM-2026-00001",
            message="Your appointment has been scheduled for tomorrow at Campus Security HQ. Please confirm your availability.",
            notification_type="handover_scheduled",
            link_url=f"/claims/{claim1.id}",
            related_claim_id=claim1.id,
            is_read=False
        )
        notif3 = Notification(
            user_id=admin1.id,
            title="New Ownership Claim Received",
            message=f"Claimant {lost_reports[0].reporter.full_name} submitted claim for wallet.",
            notification_type="admin_alert",
            link_url=f"/admin/claims/{claim1.id}",
            related_claim_id=claim1.id,
            is_read=True
        )
        db.session.add(notif1)
        db.session.add(notif2)
        db.session.add(notif3)

        audit1 = AuditLog(
            actor_id=admin1.id,
            action="handover_completed",
            entity_type="handover",
            entity_id=str(handover2.id),
            details="Handover REC-2026-00002 marked as completed. Item returned to Maria Garcia."
        )
        db.session.add(audit1)
        db.session.commit()

        print("\n" + "="*70)
        print("🎉 [CampusConnect Database Seeding Complete!]")
        print("="*70)
        print("✅ Super Administrator : superadmin@campusconnect.edu | Password: CampusPass2026!")
        print("✅ Campus Administrator: admin1@campusconnect.edu     | Password: CampusPass2026!")
        print("✅ Campus Administrator: admin2@campusconnect.edu     | Password: CampusPass2026!")
        print("✅ Student Demonstration : alex.rivers@student.campusconnect.edu | Password: CampusPass2026!")
        print(f"✅ Total Users Created   : {User.query.count()}")
        print(f"✅ Total Lost Reports    : {LostReport.query.count()}")
        print(f"✅ Total Found Reports   : {FoundReport.query.count()}")
        print(f"✅ Total Smart Matches   : {ItemMatch.query.count()}")
        print(f"✅ Total Claims          : {Claim.query.count()}")
        print(f"✅ Total Handovers       : {Handover.query.count()}")
        print("="*70 + "\n")

if __name__ == '__main__':
    seed_database()
