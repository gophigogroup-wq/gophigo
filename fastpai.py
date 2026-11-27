from fastapi import FastAPI, Form, Depends, HTTPException, status, Request, Response, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, Field, Session, create_engine, select
import hashlib, secrets, os, uuid, cloudinary, cloudinary.uploader, requests
import qrcode
import base64
from io import BytesIO
from datetime import datetime, timedelta, timezone
import json
app = FastAPI()

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

database_url = os.environ.get("DATABASE_URL")
if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    sqlite_url = database_url
else:
    sqlite_url = "sqlite:///gophigo.db"
engine = create_engine(sqlite_url)
from sqlalchemy import text
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE author ADD COLUMN slug VARCHAR;"))
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE author ADD COLUMN is_hidden BOOLEAN DEFAULT FALSE;"))
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE purchase ADD COLUMN created_at TIMESTAMP;"))
        conn.commit()
    except Exception:
        pass
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE purchase ADD COLUMN created_at TIMESTAMP;"))
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE author ADD COLUMN book_id VARCHAR;"))
        conn.commit()
    except Exception:
        pass  
    try:
        conn.execute(text("ALTER TABLE product ADD COLUMN religion VARCHAR;"))
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE product ADD COLUMN year_of_study VARCHAR;"))
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE product ADD COLUMN language VARCHAR;"))
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE product ADD COLUMN sub_category VARCHAR;"))
        conn.commit()
    except Exception:
        pass

    try:
        conn.execute(text("ALTER TABLE product ADD COLUMN year_of_study VARCHAR;"))
        conn.commit()
    except Exception:
        pass
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE product ADD COLUMN religion VARCHAR;"))
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE product ADD COLUMN year_of_study VARCHAR;"))
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE product ADD COLUMN language VARCHAR;"))
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE product ADD COLUMN sub_category VARCHAR;"))
        conn.commit()
    except Exception:
        pass
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE purchase ADD COLUMN snippe_ref VARCHAR;"))
        conn.commit()
    except Exception:
        pass
with engine.connect() as conn:
     try:
        conn.execute(text("ALTER TABLE purchase ADD COLUMN scanned BOOLEAN DEFAULT FALSE;"))
        conn.commit()
     except Exception:
         pass
with engine.connect() as conn:
    for stmt in [
        "ALTER TABLE product ADD COLUMN media_type VARCHAR;",
        "ALTER TABLE product ADD COLUMN trailer_url VARCHAR;",
        "ALTER TABLE product ADD COLUMN duration VARCHAR;",
        "ALTER TABLE product ADD COLUMN cast_or_artist VARCHAR;",
        "ALTER TABLE purchase ADD COLUMN amount_paid FLOAT;",
        "ALTER TABLE purchase ADD COLUMN supporter_tier VARCHAR DEFAULT 'Standard';",
    ]:
        try:
            conn.execute(text(stmt))
            conn.commit()
        except Exception:
            pass
with engine.connect() as conn:
    for stmt in [
        "ALTER TABLE purchase ADD COLUMN referrer_id INTEGER;",
        "ALTER TABLE purchase ADD COLUMN referral_commission FLOAT DEFAULT 0.0;",
    ]:
        try:
            conn.execute(text(stmt))
            conn.commit()
        except Exception:
            pass  
with engine.connect() as conn:
    for stmt in [
        "ALTER TABLE author ADD COLUMN phone_number VARCHAR;",
        "ALTER TABLE author ADD COLUMN author_reg_no VARCHAR;",
        "ALTER TABLE author ADD COLUMN nida_number VARCHAR;",
        "ALTER TABLE author ADD COLUMN nida_doc_url VARCHAR;",
        "ALTER TABLE author ADD COLUMN tin_number VARCHAR;",
        "ALTER TABLE author ADD COLUMN tin_doc_url VARCHAR;",
        "ALTER TABLE author ADD COLUMN kyc_status VARCHAR DEFAULT 'Pending Verification';",
    ]:
        try:
            conn.execute(text(stmt))
            conn.commit()
        except Exception:
            pass
class Author(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    fullname: str; email: str; password: str; book_title: str
    slug: str | None = Field(default=None, index=True) # NEW: For /book/the-book-title links
    book_id: str | None = Field(default=None, index=True, unique=True)
    ebook_price: float = Field(default=0.0); paperback_price: float = Field(default=0.0)
    book_format: str = Field(default="Ebook"); membership_status: str = "Pending" 
    book_status: str = Field(default="Pending Review"); reset_token: str | None = Field(default=None)
    cover_image: str | None = Field(default=None); pdf_file: str | None = Field(default=None) 
    is_read: bool = Field(default=False)
    is_hidden: bool = Field(default=False) # NEW: For soft delete
    phone_number: str | None = Field(default=None)
    author_reg_no: str | None = Field(default=None, index=True, unique=True)  # e.g., GOP-AUTH-2026-0001
    nida_number: str | None = Field(default=None)
    nida_doc_url: str | None = Field(default=None)
    tin_number: str | None = Field(default=None)
    tin_doc_url: str | None = Field(default=None)
    kyc_status: str = Field(default="Pending Verification")  # Pending Verification, Verified
class Product(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    author_id: int = Field(foreign_key="author.id") # Links to the Author/Seller
    title: str
    category: str = Field(default="Book") # Book, Newspaper, Manual, Ticket
    institution: str | None = Field(default=None) # e.g., CBE, UDSM (for Manuals)
    course_code: str | None = Field(default=None) # e.g., BUS 101 (for Manuals)
    price: float = Field(default=0.0)
    description: str | None = Field(default=None)
    cover_image: str | None = Field(default=None)
    file_url: str | None = Field(default=None) # The PDF or Audio/Video link
    product_code: str | None = Field(default=None, index=True, unique=True) # e.g., GOP-2026-0001
    status: str = Field(default="Approved") # Approved, Pending, Flagged
    is_hidden: bool = Field(default=False)
    religion: str | None = Field(default=None) 
    sub_category: str | None = Field(default=None)
    year_of_study: str | None = Field(default=None) # First Year, Second Year, etc.
    language: str | None = Field(default=None)
    media_type: str | None = Field(default=None)      # Single Track, Full Album / EP, Feature Movie, Series / Episode, Comedy / Podcast
    trailer_url: str | None = Field(default=None)     # Free 30s audio hook or 60s video trailer
    duration: str | None = Field(default=None)        # e.g., 3:45 or 1h 55m
    cast_or_artist: str | None = Field(default=None)  # Featured artists or movie cast
    
class Customer(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    fullname: str; email: str; password: str; reset_token: str | None = Field(default=None)

class Purchase(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    customer_id: int; author_id: int; book_title: str
    pdf_file: str | None = Field(default=None)
    format_bought: str = Field(default="Ebook")
    phone_number: str | None = Field(default=None)
    region: str | None = Field(default=None)
    shipping_address: str | None = Field(default=None)
    reference: str | None = Field(default=None, index=True)
    snippe_ref: str | None = Field(default=None)
    scanned: bool = Field(default=False)
    status: str = Field(default="pending")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    amount_paid: float | None = Field(default=None)
    supporter_tier: str | None = Field(default="Standard")
    referrer_id: int | None = Field(default=None)
    referral_commission: float = Field(default=0.0)
class Employee(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    fullname: str; email: str; password: str; role: str 
    must_change_password: bool = Field(default=True); reset_token: str | None = Field(default=None)
class ProductTrack(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.id")
    track_number: int = Field(default=1)
    track_title: str
    duration: str | None = Field(default=None)
    file_url: str

class Review(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    author_id: int; customer_id: int; rating: int; comment: str
SQLModel.metadata.create_all(engine)

with Session(engine) as session:
    # Check if this is the first time we are migrating
    if not session.exec(select(Product)).first():
        authors = session.exec(select(Author)).all()
        for a in authors:
            new_product = Product(
                author_id=a.id,
                title=a.book_title,
                category="Book",
                price=a.ebook_price,
                cover_image=a.cover_image,
                file_url=a.pdf_file,
                product_code=a.book_id or f"GOP-2026-{a.id:04d}",
                status="Approved"
            )
            session.add(new_product)
        session.commit()
FOOTER = '<footer style="background-color: #2c3e50; color: white; text-align: center; padding: 20px; margin-top: 50px; font-family: Arial;"><p>&copy; 2026 Gophigo store. All rights reserved.</p></footer>'

with Session(engine) as session:
    # Check if this is the first time we are migrating
    if not session.exec(select(Product)).first():
        authors = session.exec(select(Author)).all()
        for a in authors:
            # Migrate the old book into the new Product table
            new_product = Product(
                author_id=a.id,
                title=a.book_title,
                category="Book",
                price=a.ebook_price,
                cover_image=a.cover_image,
                file_url=a.pdf_file,
                product_code=a.book_id or f"GOP-2026-{a.id:04d}",
                status=a.book_status
            )
            session.add(new_product)
        session.commit()
        
def get_navbar(request: Request):
    a = request.cookies.get("author_email")
    c = request.cookies.get("customer_email")
    e = request.cookies.get("employee_email")
    ad = request.cookies.get("admin_session")
    links = ''
    
    if a:
        with Session(engine) as session:
            author = session.exec(select(Author).where(Author.email == a)).first()
            author_name = author.fullname if author else "Author"
            
        links += f'<a href="/author-dashboard" style="color: #f39c12; text-decoration: none; margin-left: 20px; font-weight: bold;">{author_name} Dashboard</a>'
        links += '<a href="/register" style="color: #3498db; text-decoration: none; margin-left: 20px; font-weight: bold;">Upload New Product</a>'
        links += '<a href="/author-reports" style="color: #9b59b6; text-decoration: none; margin-left: 20px; font-weight: bold;">Earnings Report</a>'
        links += '<a href="/logout" style="color: #e74c3c; text-decoration: none; margin-left: 20px;">Logout</a>'
    elif c:
        links += '<a href="/my-library" style="color: #2ecc71; text-decoration: none; margin-left: 20px; font-weight: bold;">My Library</a><a href="/customer-logout" style="color: #e74c3c; text-decoration: none; margin-left: 20px;">Logout</a>'
    elif e:
        links += '<a href="/employee-dashboard" style="color: #f39c12; text-decoration: none; margin-left: 20px; font-weight: bold;">Staff Dashboard</a><a href="/employee-logout" style="color: #e74c3c; text-decoration: none; margin-left: 20px;">Logout</a>'
    elif ad:
        links += '<a href="/admin" style="color: #e74c3c; text-decoration: none; margin-left: 20px; font-weight: bold;">Admin Dashboard</a><a href="/admin-logout" style="color: #e74c3c; text-decoration: none; margin-left: 20px;">Logout</a>'
    else:
        links += '<a href="/author-portal" style="color: white; text-decoration: none; margin-left: 20px;">Author Portal</a><a href="/customer-login" style="color: white; text-decoration: none; margin-left: 20px;">Customer Login</a><a href="/employee-login" style="color: #f39c12; text-decoration: none; margin-left: 20px; font-weight: bold;">Staff Login</a>'
        
    return f'<nav style="background-color: #2c3e50; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; font-family: Poppins, sans-serif;"><div style="font-size: 24px; font-weight: bold;"><a href="/" style="color: white; text-decoration: none;">🛍️ Gophigo Store</a></div><div>{links}</div></nav>'

@app.get("/", response_class=HTMLResponse)
def store(request: Request, search: str = None, category: str = "Book"):
    with Session(engine) as session:
        query = select(Product).where(Product.status == "Approved", Product.is_hidden == False)
        query = query.where(Product.category == category)

        if search:
            query = query.where(Product.title.contains(search))

        products = session.exec(query).all()

        html = """
        <html><head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            body { font-family: Poppins, sans-serif; margin: 0; background-color: #f4f4f4; }
            .store-header { text-align: center; padding: 20px; background: white; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
            .search-bar { max-width: 500px; margin: 15px auto 0; display: flex; gap: 10px; padding: 0 15px; }
            .search-bar input { flex: 1; padding: 12px; border: 1px solid #ccc; border-radius: 5px; font-size: 16px; }
            .search-bar button { background: #3498db; color: white; padding: 12px 25px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }
            .category-tabs { display: flex; justify-content: center; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; padding: 0 10px; }
            .cat-btn { padding: 10px 20px; border-radius: 30px; text-decoration: none; font-weight: bold; font-size: 14px; transition: 0.2s; }
            .cat-btn.active { background: #2c3e50; color: white; }
            .cat-btn.inactive { background: white; color: #7f8c8d; border: 1px solid #ddd; }
            .book-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 18px; padding: 15px; max-width: 1200px; margin: auto; }
            .book-card { background: white; border-radius: 10px; padding: 15px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.08); display: flex; flex-direction: column; justify-content: space-between; transition: transform 0.2s; position: relative; }
            .book-card:hover { transform: translateY(-5px); }
            .book-card img { width: 100%; height: 220px; object-fit: cover; border-radius: 6px; margin-bottom: 10px; }
            .book-title { color: #2c3e50; margin: 0 0 5px; font-size: 16px; font-weight: 600; line-height: 1.25; }
            .book-author { color: #7f8c8d; margin: 0 0 8px; font-size: 13px; }
            .btn-buy { display: block; width: 100%; padding: 10px; border-radius: 6px; text-decoration: none; font-weight: bold; color: white; margin-top: 6px; font-size: 14px; box-sizing: border-box; }
            .btn-preview { display: block; width: 100%; padding: 8px; border-radius: 6px; border: none; background: #1a252f; color: #f1c40f; font-weight: bold; cursor: pointer; font-size: 13px; margin-top: 4px; }
            .modal-backdrop { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.85); z-index: 9999; align-items: center; justify-content: center; padding: 20px; }
            .modal-box { background: #1a252f; color: white; padding: 20px; border-radius: 12px; max-width: 650px; width: 100%; text-align: center; position: relative; }
        </style>
        </head><body>
        """ + get_navbar(request) + f"""
        <div class="store-header">
            <h1 style="color: #2c3e50; margin: 0; font-size: 24px;">Gophigo Store</h1>
            <form action="/" method="GET" class="search-bar">
                <input type="hidden" name="category" value="{category}">
                <input type="text" name="search" placeholder="Search..." value="{search or ''}">
                <button type="submit">Search</button>
            </form>
        </div>
        
        <div class="category-tabs">
            <a href="/?category=Book" class="cat-btn {'active' if category == 'Book' else 'inactive'}">📚 Books</a>
            <a href="/?category=Media" class="cat-btn {'active' if category == 'Media' else 'inactive'}">🎬 Movies & Music</a>
            <a href="/?category=Manual" class="cat-btn {'active' if category == 'Manual' else 'inactive'}">🏫 University Manuals</a>
            <a href="/?category=Law" class="cat-btn {'active' if category == 'Law' else 'inactive'}">⚖️ Laws & Manuals</a>
            <a href="/?category=Ticket" class="cat-btn {'active' if category == 'Ticket' else 'inactive'}">🎟️ Tickets</a>
            <a href="/?category=Newspaper" class="cat-btn {'active' if category == 'Newspaper' else 'inactive'}">📰 News & Articles</a>
            <a href="/?category=Religious" class="cat-btn {'active' if category == 'Religious' else 'inactive'}">🙏 Religious</a>
        </div>

        <div class="book-grid">
        """

        if not products:
            html += "<p style='text-align:center; grid-column:1/-1; color:#7f8c8d;'>No products found in this category.</p>"

        for p in products:
            author = session.get(Author, p.author_id)
            author_name = p.cast_or_artist or (author.fullname if author else "Gophigo")

            reviews = session.exec(select(Review).where(Review.author_id == p.author_id)).all()
            avg = sum(r.rating for r in reviews) / len(reviews) if reviews else 0
            stars = "⭐" * int(round(avg)) if reviews else "New Release"

            price_display = f"{p.price:,.0f}"
            preview_btn = ""

            if p.category == "Manual":
                extra_info = f"{p.institution or ''} | {p.course_code or ''}"
            elif p.category == "Law":
                extra_info = "⚖️ Law & Manual"
            elif p.category == "Newspaper":
                extra_info = "📰 News & Article"
            elif p.category == "Ticket":
                extra_info = "🎟️ Event Ticket"
            elif p.category == "Media":
                m_type = p.media_type or "Premiere Media"
                dur = f" • {p.duration}" if p.duration else ""
                extra_info = f"🎬 {m_type}{dur}"
                if p.trailer_url:
                    safe_title = p.title.replace("'", "\\'")
                    preview_btn = f"<button type='button' class='btn-preview' onclick=\"openPreview('{p.trailer_url}', '{safe_title}')\">▶ Free Preview / Trailer</button>"
            else:
                extra_info = p.category

            html += f"""
            <div class="book-card">
                <div>
                    <img src="{p.cover_image}" alt="{p.title}">
                    <h3 class="book-title">{p.title}</h3>
                    <p class="book-author">{author_name}</p>
                    <p style="color:#f1c40f; margin:0 0 8px; font-size:13px;">{stars}</p>
                </div>
                <div>
                    <span style="background:#eef2f7; color:#2c3e50; padding:4px 10px; border-radius:20px; font-size:11px; font-weight:600; display:inline-block; margin-bottom:8px;">{extra_info}</span>
                    {preview_btn}
                    <a href="/checkout-product/{p.id}" class="btn-buy" style="background:#3498db;">Unlock ({price_display} TZS)</a>
                </div>
            </div>
            """

        modal_html = """
        <div id="previewModal" class="modal-backdrop" onclick="if(event.target===this) closePreview();">
            <div class="modal-box">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <h3 id="previewTitle" style="margin:0; color:#f1c40f;">Free Preview</h3>
                    <button onclick="closePreview()" style="background:#e74c3c; color:white; border:none; padding:6px 12px; border-radius:5px; cursor:pointer; font-weight:bold;">✕ Close</button>
                </div>
                <div id="previewContainer"></div>
            </div>
        </div>
        <script>
            function openPreview(url, title) {
                document.getElementById('previewTitle').innerText = '🎬 Preview: ' + title;
                var isAudio = url.match(/\\.(mp3|wav|m4a|ogg)(\\?|$)/i);
                var container = document.getElementById('previewContainer');
                if (isAudio) {
                    container.innerHTML = '<audio controls autoplay controlsList="nodownload" style="width:100%; margin:20px 0;"><source src="' + url + '"></audio>';
                } else {
                    container.innerHTML = '<video controls autoplay controlsList="nodownload" style="width:100%; max-height:420px; border-radius:8px;"><source src="' + url + '"></video>';
                }
                document.getElementById('previewModal').style.display = 'flex';
            }
            function closePreview() {
                document.getElementById('previewContainer').innerHTML = '';
                document.getElementById('previewModal').style.display = 'none';
            }
        </script>
        """
        return html + f"</div>{modal_html}{FOOTER}</body></html>"

@app.get("/checkout-product/{product_id}", response_class=HTMLResponse)
def checkout_product(request: Request, product_id: int):
    try:
        customer_email = request.cookies.get("customer_email")
        if not customer_email:
            return RedirectResponse(url=f"/customer-login?next=/checkout-product/{product_id}", status_code=303)

        with Session(engine) as session:
            p = session.get(Product, product_id)
            if not p:
                return HTMLResponse(content="<h1 style='text-align:center; padding:50px;'>Product not found.</h1><a href='/'>Back to Store</a>", status_code=404)

            cover = p.cover_image if p.cover_image else "https://via.placeholder.com/180x250?text=No+Cover"
            base_price = float(p.price or 0)

            # Top Supporters Wall (fans who supported above standard price)
            vip_purchases = session.exec(
                select(Purchase).where(
                    Purchase.book_title == p.title,
                    Purchase.author_id == p.author_id,
                    Purchase.status == "paid",
                    Purchase.supporter_tier != "Standard"
                )
            ).all()

            supporters_html = ""
            if vip_purchases:
                badges = ""
                for vp in vip_purchases[-10:]:
                    fan = session.get(Customer, vp.customer_id)
                    fan_name = fan.fullname if fan else "VIP Fan"
                    icon = "👑" if vp.supporter_tier == "Executive Producer" else "⭐"
                    badges += f"<span style='background:#fff8e1; border:1px solid #f1c40f; color:#7f6000; padding:4px 10px; border-radius:20px; font-size:12px; font-weight:bold; display:inline-block; margin:3px;'>{icon} {fan_name} ({vp.supporter_tier})</span>"
                supporters_html = f"<div style='margin:15px 0; padding:12px; background:#fafafa; border-radius:8px; border:1px solid #eee;'><p style='margin:0 0 6px; font-size:12px; font-weight:bold; color:#2c3e50;'>🏆 Top Supporters Wall</p>{badges}</div>"

            # VIP tier selector for Media creators
            if p.category == "Media" and base_price > 0:
                vip_price = base_price * 2
                exec_price = base_price * 5
                tier_selector = f"""
                <div style="margin-bottom:15px; text-align:left;">
                    <label style="font-weight:bold; font-size:14px;">Choose Access Tier:</label>
                    <select name="supporter_tier" id="tierSelect" onchange="updatePayBtn()" style="width:100%; padding:11px; border:1px solid #ccc; border-radius:5px; margin-top:5px; font-size:15px;">
                        <option value="Standard" data-amount="{base_price:.0f}">🎬 Standard Access — {base_price:,.0f} TZS</option>
                        <option value="VIP Supporter" data-amount="{vip_price:.0f}">⭐ VIP Supporter (Wall Shoutout) — {vip_price:,.0f} TZS</option>
                        <option value="Executive Producer" data-amount="{exec_price:.0f}">👑 Executive Producer (Gold Badge) — {exec_price:,.0f} TZS</option>
                    </select>
                </div>
                <script>
                    function updatePayBtn() {{
                        var sel = document.getElementById('tierSelect');
                        var amt = Number(sel.options[sel.selectedIndex].getAttribute('data-amount')).toLocaleString();
                        document.getElementById('paySubmitBtn').innerText = 'Pay ' + amt + ' TZS via Mobile Money';
                    }}
                </script>
                """
            else:
                tier_selector = '<input type="hidden" name="supporter_tier" value="Standard">'

            trailer_embed = ""
            if p.category == "Media" and p.trailer_url:
                trailer_embed = f"<p style='margin:8px 0;'><a href='{p.trailer_url}' target='_blank' style='color:#e67e22; font-weight:bold; font-size:13px;'>▶ Watch / Listen to Free Teaser First</a></p>"

            return f"""
            <html><body style="font-family:Poppins, Arial, sans-serif; background:#f4f4f4; margin:0;">
                {get_navbar(request)}
                <div style="padding:40px 15px;">
                    <div style="background:white; padding:30px; border-radius:10px; max-width:440px; margin:auto; text-align:center; box-shadow:0 4px 15px rgba(0,0,0,0.08);">
                        <h2 style="margin-top:0; color:#2c3e50;">Checkout</h2>
                        <img src="{cover}" style="width:170px; height:230px; object-fit:cover; margin:12px 0; border-radius:6px;">
                        <h3 style="margin:5px 0;">{p.title}</h3>
                        <p style="color:#7f8c8d; font-size:13px; margin:0;">{p.media_type or p.category}</p>
                        {trailer_embed}
                        {supporters_html}
                        <form action="/pay-product/{p.id}" method="POST" style="margin-top:15px;">
                            {tier_selector}
                            <div style="margin-bottom: 15px; text-align: left;">
                                <label style="font-weight: bold; font-size:14px;">Mobile Money Number (M-Pesa / Tigo / Airtel / Halopesa):</label>
                                <input type="text" name="phone" placeholder="e.g. 0754123456" required style="width: 100%; padding: 12px; border: 1px solid #ccc; border-radius: 5px; margin-top: 5px; font-size: 16px; box-sizing:border-box;">
                            </div>
                            <button id="paySubmitBtn" type="submit" style="background:#2ecc71; color:white; padding:15px; border:none; border-radius:6px; display:block; width:100%; font-size:16px; font-weight:bold; cursor:pointer;">Pay {base_price:,.0f} TZS via Mobile Money</button>
                        </form>
                    </div>
                </div>
                {FOOTER}
            </body></html>
            """
    except Exception as e:
        import traceback
        return HTMLResponse(content=f"<h1>Checkout Debug Error</h1><pre>{traceback.format_exc()}</pre>", status_code=500)


@app.post("/pay-product/{product_id}")
def process_payment_product(request: Request, product_id: int, phone: str = Form(...), supporter_tier: str = Form("Standard")):
    customer_email = request.cookies.get("customer_email")
    if not customer_email:
        return RedirectResponse(url="/customer-login", status_code=303)

    with Session(engine) as session:
        c = session.exec(select(Customer).where(Customer.email == customer_email)).first()
        p = session.get(Product, product_id)

        if not p or not c:
            return HTMLResponse(content="<h1>Error: Product or Customer not found.</h1>", status_code=400)

        multiplier = 5.0 if supporter_tier == "Executive Producer" else (2.0 if supporter_tier == "VIP Supporter" else 1.0)
        final_amount = float(p.price) * multiplier
        purchase_ref = str(uuid.uuid4())

        purchase = Purchase(
            customer_id=c.id,
            author_id=p.author_id,
            book_title=p.title,
            pdf_file=p.file_url,
            format_bought=p.category,
            phone_number=phone,
            reference=purchase_ref,
            amount_paid=final_amount,
            supporter_tier=supporter_tier,
            status="pending",
        )
        session.add(purchase)
        session.commit()

        api_key = os.environ.get("SNIPPE_API_KEY")
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        name_parts = c.fullname.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else "Customer"

        clean_phone = phone.strip()
        if clean_phone.startswith("0"):
            clean_phone = "255" + clean_phone[1:]

        payload = {
            "phone_number": clean_phone,
            "webhook_url": "https://www.gophigo.co.tz/snippe-webhook",
            "customer": {"firstname": first_name, "lastname": last_name, "email": c.email},
            "business_name": "Gophigo Store",
            "details": {"amount": int(final_amount), "currency": "TZS", "description": f"Gophigo ({supporter_tier}): {p.title}"},
            "metadata": {"purchase_reference": purchase_ref}
        }

        try:
            response = requests.post("https://api.snippe.sh/v1/payments", json=payload, headers=headers, timeout=15)

            if response.status_code in [200, 201]:
                data = response.json()
                snippe_ref = data.get("data", {}).get("reference")
                if snippe_ref:
                    purchase.snippe_ref = snippe_ref
                    session.add(purchase)
                    session.commit()
                payment_url = data.get("data", {}).get("checkout_url") or data.get("data", {}).get("payment_url")

                if payment_url:
                    return RedirectResponse(url=payment_url, status_code=303)

                return HTMLResponse(content=f'<html><body style="font-family:Arial; text-align:center; padding:50px;"><h1 style="color:#2ecc71;">Payment Prompt Sent!</h1><p>We have sent a payment request of <strong>{final_amount:,.0f} TZS</strong> to <strong>{phone}</strong>.</p><p>Please check your phone and enter your mobile money PIN to complete the purchase.</p><p style="color:#7f8c8d;">Reference: {purchase_ref}</p><br><a href="/my-library" style="background:#3498db; color:white; padding:12px 25px; text-decoration:none; border-radius:5px;">I have paid - Go to My Library</a></body></html>', status_code=200)
            else:
                purchase.status = "failed"
                session.add(purchase)
                session.commit()
                return HTMLResponse(content=f"<h1>Snippe Error</h1><p>{response.text}</p>", status_code=400)

        except Exception as e:
            return HTMLResponse(content=f"<h1>Connection Error</h1><p>{str(e)}</p>", status_code=500)

@app.get("/shipping-address/{author_id}", response_class=HTMLResponse)
def shipping_address_form(request: Request, author_id: int):
    return '<html><body style="font-family:Arial; background:#f4f4f4;">' + get_navbar(request) + f'<div style="padding:50px;"><div style="background:white; padding:30px; border-radius:8px; max-width:400px; margin:auto;"><h2>Shipping Details</h2><p>Where should we deliver your paperback?</p><form action="/calculate-shipping/{author_id}" method="POST"><label>Phone Number:</label><br><input type="text" name="phone" required style="width:100%; padding:10px; margin:10px 0;"><br><label>Region / City:</label><br><input type="text" name="region" required style="width:100%; padding:10px; margin:10px 0;"><br><label>Delivery Address:</label><br><textarea name="address" required style="width:100%; padding:10px; margin:10px 0;"></textarea><br><button type="submit" style="background:#2ecc71; color:white; padding:12px; border:none; width:100%; border-radius:5px;">Complete Order</button></form></div></div>' + FOOTER + '</body></html>'

@app.post("/calculate-shipping/{author_id}", response_class=HTMLResponse)
def calculate_shipping(request: Request, author_id: int, phone: str = Form(...), region: str = Form(...), address: str = Form(...)):  
    with Session(engine) as session:
        a = session.get(Author, author_id)
        book_price = a.paperback_price
        shipping_fee = 15000.0
        total_price = book_price + shipping_fee
        
        html = f'<html><body style="font-family:Arial; background:#f4f4f4;">{get_navbar(request)}<div style="padding:50px;"><div style="background:white; padding:40px; border-radius:8px; max-width:400px; margin:auto;"><h2 style="text-align:center; color:#2c3e50;">Order Summary</h2><img src="{a.cover_image}" style="width:100px; height:150px; object-fit:cover; display:block; margin:0 auto 20px;"><div style="display:flex; justify-content:space-between; margin-bottom:10px;"><span>Book Price:</span><strong>{book_price} TZS</strong></div><div style="display:flex; justify-content:space-between; margin-bottom:10px;"><span>Delivery Fee:</span><strong>{shipping_fee} TZS</strong></div><hr><div style="display:flex; justify-content:space-between; margin-bottom:20px; font-size:20px; color:#2ecc71;"><span>Total:</span><strong>{total_price} TZS</strong></div><form action="/confirm-paperback/{author_id}" method="POST"><input type="hidden" name="phone" value="{phone}"><input type="hidden" name="region" value="{region}"><input type="hidden" name="address" value="{address}"><button type="submit" style="background:#3498db; color:white; padding:15px; border:none; width:100%; border-radius:5px; font-size:16px; font-weight:bold; cursor:pointer;">Confirm & Pay {total_price} TZS</button></form></div></div>{FOOTER}</body></html>'
        return html
@app.post("/confirm-paperback/{author_id}", response_class=HTMLResponse)
def confirm_paperback(request: Request, author_id: int, phone: str = Form(...), region: str = Form(...), address: str = Form(...)):
    customer_email = request.cookies.get("customer_email")
    with Session(engine) as session:
        c = session.exec(select(Customer).where(Customer.email == customer_email)).first()
        a = session.get(Author, author_id)
        
        if not session.exec(select(Purchase).where(Purchase.customer_id == c.id, Purchase.author_id == a.id, Purchase.format_bought == "Paperback")).first():
            session.add(Purchase(
                customer_id=c.id, 
                author_id=a.id, 
                book_title=a.book_title, 
                format_bought="Paperback", 
                phone_number=phone, 
                region=region, 
                shipping_address=address,
                status="paid"
            ))
            session.commit()
            
    return f"<html><body style='font-family:Arial; background:#f4f4f4;'>{get_navbar(request)}<div style='text-align:center; padding:100px;'><h1 style='color:#2ecc71;'>Order Successful!</h1><p>Your paperback is being prepared for printing.</p><p>We will deliver it to: {address}, {region}.</p><a href='/' style='background:#3498db; color:white; padding:12px 25px; text-decoration:none; border-radius:5px;'>Continue Shopping</a></div>{FOOTER}</body></html>"

@app.post("/pay-product/{product_id}")
def process_payment_product(request: Request, product_id: int, phone: str = Form(...)):
    customer_email = request.cookies.get("customer_email")
    if not customer_email: 
        return RedirectResponse(url="/customer-login", status_code=303)
    ref_cookie = request.cookies.get("gophigo_ref")
    referrer_id = int(ref_cookie) if (ref_cookie and ref_cookie.isdigit() and int(ref_cookie) != c.id) else None
    commission = round(final_amount * 0.10, 2) if referrer_id else 0.0
        
    with Session(engine) as session:
        c = session.exec(select(Customer).where(Customer.email == customer_email)).first()
        p = session.get(Product, product_id)
        
        if not p or not c:
            return HTMLResponse(content="<h1>Error: Product or Customer not found.</h1>", status_code=400)

        purchase_ref = str(uuid.uuid4())
        
        purchase = Purchase(
            customer_id=c.id, 
            author_id=p.author_id, 
            book_title=p.title,
            pdf_file=p.file_url, 
            format_bought=p.category,
            reference=purchase_ref, 
            status="pending",
        )
        session.add(purchase)
        session.commit()

        api_key = os.environ.get("SNIPPE_API_KEY")
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        name_parts = c.fullname.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else "Customer"

        clean_phone = phone.strip()
        if clean_phone.startswith("0"):
            clean_phone = "255" + clean_phone[1:]

        payload = {
            "phone_number": clean_phone,
            "webhook_url": "https://www.gophigo.co.tz/snippe-webhook",
            "customer": {"firstname": first_name, "lastname": last_name, "email": c.email},
            "business_name": "Gophigo Store",
            "details": {"amount": int(p.price), "currency": "TZS", "description": f"Gophigo: {p.title}"},
            "metadata": {"purchase_reference": purchase_ref}
        }

        try:
            response = requests.post("https://api.snippe.sh/v1/payments", json=payload, headers=headers, timeout=15)
            
            if response.status_code in [200, 201]:
                data = response.json()
            snippe_ref = data.get("data", {}).get("reference")
            if snippe_ref:
                purchase.snippe_ref = snippe_ref
                session.add(purchase)
                session.commit()
                payment_url = data.get("data", {}).get("checkout_url") or data.get("data", {}).get("payment_url")
                
                if payment_url:
                    return RedirectResponse(url=payment_url, status_code=303)
                    
                return HTMLResponse(content=f'<html><body style="font-family:Arial; text-align:center; padding:50px;"><h1 style="color:#2ecc71;">Payment Prompt Sent!</h1><p>We have sent a payment request to <strong>{phone}</strong>.</p><p>Please check your phone and enter your mobile money PIN to complete the purchase.</p><p style="color:#7f8c8d;">Reference: {purchase_ref}</p><br><a href="/my-library" style="background:#3498db; color:white; padding:12px 25px; text-decoration:none; border-radius:5px;">I have paid - Go to My Library</a></body></html>', status_code=200)
            else:
                purchase.status = "failed"
                session.add(purchase)
                session.commit()
                return HTMLResponse(content=f"<h1>Snippe Error</h1><p>{response.text}</p>", status_code=400)
                
        except Exception as e:
            return HTMLResponse(content=f"<h1>Connection Error</h1><p>{str(e)}</p>", status_code=500)
            
@app.post("/review/{purchase_id}")
def process_review(request: Request, purchase_id: int, rating: int = Form(...), comment: str = Form(...)):
    customer_email = request.cookies.get("customer_email")
    with Session(engine) as session:
        p = session.get(Purchase, purchase_id); c = session.exec(select(Customer).where(Customer.email == customer_email)).first()
        session.add(Review(author_id=p.author_id, customer_id=c.id, rating=rating, comment=comment)); session.commit()
    return RedirectResponse(url="/my-library", status_code=303)

@app.get("/read/{purchase_id}", response_class=HTMLResponse)
def read_book(request: Request, purchase_id: int):
    with Session(engine) as session:
        p = session.get(Purchase, purchase_id)
        return f"<html><body style='margin:0; height:100vh; display:flex; flex-direction:column;'><div style='background:#2c3e50; color:white; padding:15px; text-align:center;'><h3>Gophigo Reader - {p.book_title}</h3></div><iframe src='https://docs.google.com/viewer?url={p.pdf_file}&embedded=true' style='flex:1; border:none; width:100%; height:100vh;'></iframe></body></html>"

@app.get("/author-portal", response_class=HTMLResponse)
def author_portal(request: Request):
    return '<html><head><link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;700&display=swap" rel="stylesheet"><style>body { font-family: Poppins; margin:0; } .hero { background: linear-gradient(135deg,#1a252f,#2c3e50); color: white; padding: 100px 20px; text-align: center; } .btn { padding: 15px 30px; border-radius: 5px; text-decoration: none; font-weight: bold; display: inline-block; margin: 10px; }</style></head><body>' + get_navbar(request) + '<div class="hero"><h1 style="font-size:48px;">Become a Gophigo Author</h1><p style="font-size:20px;">The global marketplace where authors keep 50% of their sales.</p><a href="/register" class="btn" style="background:#3498db; color:white;">✍️ Register</a><a href="/login" class="btn" style="background:#2ecc71; color:white;">Author Login</a></div>' + FOOTER + '</body></html>'

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    author_email = request.cookies.get("author_email")
    is_logged_in = False
    author_name = ""
    author_email_val = ""

    if author_email:
        with Session(engine) as session:
            author = session.exec(select(Author).where(Author.email == author_email)).first()
            if author:
                is_logged_in = True
                author_name = author.fullname
                author_email_val = author.email

    if not is_logged_in:
        login_fields = '''
            <input type="text" name="fullname" required style="width:100%; padding:10px; margin:8px 0; box-sizing:border-box;" placeholder="Full Legal Name (Matching NIDA) *">
            <input type="email" name="email" required style="width:100%; padding:10px; margin:8px 0; box-sizing:border-box;" placeholder="Email Address *">
            <input type="text" name="phone_number" required style="width:100%; padding:10px; margin:8px 0; box-sizing:border-box;" placeholder="Mobile Money / Phone Number (e.g. 0754123456) *">
            <input type="password" name="password" required style="width:100%; padding:10px; margin:8px 0; box-sizing:border-box;" placeholder="Create Password *">

            <div style="background:#f8f9fa; border:1px solid #dce1e7; padding:14px; border-radius:8px; margin:12px 0;">
                <h4 style="margin:0 0 8px 0; color:#2c3e50;">🪪 Creator Verification (KYC)</h4>
                <input type="text" name="nida_number" required maxlength="20" style="width:100%; padding:10px; margin:6px 0; box-sizing:border-box;" placeholder="NIDA Number (20 Digits) *">
                <label style="font-size:12px; font-weight:bold; display:block; margin-top:6px;">Upload NIDA ID / Copy (PDF or Photo) *:</label>
                <input type="file" name="nida_doc" accept=".pdf,image/*" required style="width:100%; padding:6px 0;">

                <input type="text" name="tin_number" style="width:100%; padding:10px; margin:10px 0 6px; box-sizing:border-box;" placeholder="TRA TIN Number (Optional)">
                <label style="font-size:12px; font-weight:bold; display:block; margin-top:6px; color:#555;">Upload TIN Certificate (Optional — Required Later for Payouts):</label>
                <input type="file" name="tin_doc" accept=".pdf,image/*" style="width:100%; padding:6px 0;">
            </div>
        '''
    else:
        login_fields = f'''
            <input type="hidden" name="fullname" value="{author_name}">
            <input type="hidden" name="email" value="{author_email_val}">
            <div style="background:#e8f8f5; padding:10px; border-radius:5px; margin-bottom:15px; color:#2c3e50;">
                <strong>Logged in as:</strong> {author_name} ({author_email_val})
            </div>
        '''

    return f'''<html><body style="font-family:Poppins, Arial, sans-serif; background:#f4f4f4; margin:0;">
        {get_navbar(request)}
        <div style="padding:40px 15px;">
            <div style="background:white; padding:30px; border-radius:10px; max-width:540px; margin:auto; box-shadow:0 4px 15px rgba(0,0,0,0.08);">
                <h2 style="text-align:center; color:#2c3e50; margin-top:0;">Creator & Author Registration</h2>
                <form action="/register" method="POST" enctype="multipart/form-data">
                    {login_fields}
                    
                    <input type="text" name="book_title" required style="width:100%; padding:10px; margin:10px 0; box-sizing:border-box;" placeholder="Title of Book, Song, Movie, or Event *">
                    
                    <select name="category" id="categorySelect" required style="width:100%; padding:10px; margin:10px 0; box-sizing:border-box;">
                        <option value="Book">📚 General Book</option>
                        <option value="Media">🎬 Movies, Music, Comedy & Podcasts</option>
                        <option value="Manual">🏫 University Manual / Lecture Notes</option>
                        <option value="Law">⚖️ Laws, Regulations & Manuals</option>
                        <option value="Newspaper">📰 Newspaper & Articles</option>
                        <option value="Ticket">🎟️ Event Ticket / Football Match</option>
                        <option value="Religious">🙏 Religious Book</option>
                    </select>

                    <div id="universityFields" style="display: none;">
                        <input type="text" name="institution" style="width:100%; padding:10px; margin:10px 0; box-sizing:border-box;" placeholder="University Name (e.g., UDSM, CBE)">
                        <input type="text" name="course_code" style="width:100%; padding:10px; margin:10px 0; box-sizing:border-box;" placeholder="Course Code (e.g., BUS 101)">
                    </div>

                    <div id="mediaFields" style="display: none; background:#1a252f; color:white; padding:15px; border-radius:8px; margin:10px 0;">
                        <h4 style="margin:0 0 10px 0; color:#f1c40f;">🎬 Premiere Studio Details</h4>
                        <select name="media_type" style="width:100%; padding:10px; margin-bottom:10px; border-radius:5px; box-sizing:border-box;">
                            <option value="Single Track">🎵 Single Audio Track</option>
                            <option value="Full Album / EP">💿 Full Album / EP</option>
                            <option value="Feature Movie">🎬 Feature Movie / Film</option>
                            <option value="Series / Episode">📺 Series / Episode</option>
                            <option value="Comedy / Podcast">🎙️ Stand-Up Comedy / Podcast</option>
                        </select>
                        <input type="text" name="cast_or_artist" style="width:100%; padding:10px; margin-bottom:10px; border-radius:5px; border:none; box-sizing:border-box;" placeholder="Featured Artists / Cast & Director">
                        <input type="text" name="duration" style="width:100%; padding:10px; margin-bottom:10px; border-radius:5px; border:none; box-sizing:border-box;" placeholder="Duration (e.g., 3:45 or 1h 50m)">
                        <label style="font-size:13px; font-weight:bold; color:#2ecc71; display:block; margin-top:5px;">Free 30s Audio Hook / 60s Video Trailer (Optional):</label>
                        <input type="file" name="trailer_file" accept=".mp3,.mp4,.wav,.m4a,.mov,audio/*,video/*" style="width:100%; padding:8px 0; color:white;">
                    </div>
                    
                    <input type="number" name="price" required style="width:100%; padding:10px; margin:10px 0; box-sizing:border-box;" placeholder="Standard Price (TZS) *">
                    
                    <label style="font-size:14px; font-weight:bold; display:block; margin-top:10px;">Upload Cover Image / Poster *:</label>
                    <input type="file" name="cover" accept="image/*" required style="width:100%; padding:10px 0;">
                    
                    <label id="fileLabel" style="font-size:14px; font-weight:bold; display:block; margin-top:10px;">Upload PDF / Document:</label>
                    <input type="file" id="fileInput" name="pdf_file" accept=".pdf,.doc,.docx" style="width:100%; padding:10px 0;">
                    
                    <div style="margin: 15px 0; display: flex; align-items: flex-start; gap: 10px;">
                        <input type="checkbox" name="agree_terms" value="yes" required style="margin-top: 5px; transform: scale(1.4);">
                        <label style="font-size: 13px; color: #555;">
                            I declare that I am the copyright owner of this work and I agree to the
                            <a href="/terms" target="_blank" style="color: #3498db;">Gophigo Terms & Conditions</a>.
                        </label>
                    </div>
                    
                    <button type="submit" style="background:#2ecc71; color:white; padding:14px; border:none; width:100%; border-radius:6px; font-size:16px; font-weight:bold; cursor:pointer;">Complete Registration & Submit</button>
                </form>
            </div>
        </div>
        {FOOTER}
        <script>
            document.getElementById('categorySelect').addEventListener('change', function() {{
                var uniFields = document.getElementById('universityFields');
                var mediaFields = document.getElementById('mediaFields');
                var fileInput = document.getElementById('fileInput');
                var fileLabel = document.getElementById('fileLabel');
                
                uniFields.style.display = (this.value === 'Manual') ? 'block' : 'none';
                mediaFields.style.display = (this.value === 'Media') ? 'block' : 'none';
                
                if (this.value === 'Media') {{
                    fileInput.accept = ".mp3,.mp4,.wav,.m4a,.mov,audio/*,video/*";
                    fileLabel.innerText = "Upload Full Master Audio/Video File:";
                }} else {{
                    fileInput.accept = ".pdf,.doc,.docx";
                    fileLabel.innerText = "Upload PDF / Document:";
                }}
            }});
        </script>
    </body></html>'''


@app.post("/register", response_class=HTMLResponse)
def process_registration(
    request: Request,
    fullname: str = Form(None),
    email: str = Form(None),
    phone_number: str = Form(None),
    password: str = Form(None),
    nida_number: str = Form(None),
    tin_number: str = Form(None),
    nida_doc: UploadFile = File(None),
    tin_doc: UploadFile = File(None),
    book_title: str = Form(...),
    category: str = Form(...),
    institution: str = Form(None),
    course_code: str = Form(None),
    media_type: str = Form(None),
    cast_or_artist: str = Form(None),
    duration: str = Form(None),
    price: float = Form(...),
    cover: UploadFile = File(...),
    pdf_file: UploadFile = File(None),
    trailer_file: UploadFile = File(None),
    agree_terms: str = Form(None)
):
    if not agree_terms:
        return HTMLResponse(content="<h1>Error</h1><p>You must agree to the Terms and Conditions.</p>", status_code=400)

    author_email = request.cookies.get("author_email")
    current_year = datetime.now().year

    # 1. Upload cover, master file, and optional trailer
    cover_url = cloudinary.uploader.upload(cover.file, folder="gophigo_covers", resource_type="image").get("secure_url")

    file_url = None
    if pdf_file and pdf_file.filename:
        if category == "Media":
            file_url = cloudinary.uploader.upload(pdf_file.file, folder="gophigo_media", resource_type="video").get("secure_url")
        else:
            file_url = cloudinary.uploader.upload(pdf_file.file, folder="gophigo_pdfs", resource_type="raw", access_mode="public").get("secure_url")

    trailer_url = None
    if trailer_file and trailer_file.filename:
        trailer_url = cloudinary.uploader.upload(trailer_file.file, folder="gophigo_trailers", resource_type="video").get("secure_url")

    with Session(engine) as session:
        total_products = len(session.exec(select(Product)).all())
        new_book_id = f"GOP-{current_year}-{total_products + 1:04d}"

        if author_email:
            author = session.exec(select(Author).where(Author.email == author_email)).first()
            if not author:
                return HTMLResponse(content="<h1>Error: Author session invalid. Please log in again.</h1>", status_code=400)
            reg_no_display = author.author_reg_no or f"GOP-AUTH-{current_year}-{author.id:04d}"
        else:
            if not phone_number or not nida_number or not (nida_doc and nida_doc.filename):
                return HTMLResponse(content="<h1>Error</h1><p>Phone number, NIDA number, and NIDA document are mandatory.</p>", status_code=400)

            existing = session.exec(select(Author).where(Author.email == email)).first()
            if existing:
                return HTMLResponse(content="<h1>Email already registered.</h1><a href='/login'>Login here</a>", status_code=400)

            nida_url = cloudinary.uploader.upload(nida_doc.file, folder="gophigo_kyc", resource_type="auto").get("secure_url")
            tin_url = cloudinary.uploader.upload(tin_doc.file, folder="gophigo_kyc", resource_type="auto").get("secure_url") if (tin_doc and tin_doc.filename) else None

            total_authors = len(session.exec(select(Author)).all())
            reg_no_display = f"GOP-AUTH-{current_year}-{total_authors + 1:04d}"

            author = Author(
                fullname=fullname,
                email=email,
                phone_number=phone_number.strip(),
                password=hashlib.sha256(password.encode()).hexdigest(),
                author_reg_no=reg_no_display,
                nida_number=nida_number.strip(),
                nida_doc_url=nida_url,
                tin_number=tin_number.strip() if tin_number else None,
                tin_doc_url=tin_url,
                kyc_status="Pending Verification",
                book_title=book_title,
                book_format=category,
                ebook_price=price,
                cover_image=cover_url,
                pdf_file=file_url,
                book_id=new_book_id,
                membership_status="Pending"
            )
            session.add(author)
            session.commit()
            session.refresh(author)
            author_email = email

        product_status = "Approved" if author.kyc_status == "Verified" else "Pending KYC"

        new_product = Product(
            author_id=author.id,
            title=book_title,
            category=category,
            institution=institution if institution else None,
            course_code=course_code if course_code else None,
            media_type=media_type if category == "Media" else None,
            cast_or_artist=cast_or_artist if category == "Media" else None,
            duration=duration if category == "Media" else None,
            trailer_url=trailer_url if category == "Media" else None,
            price=price,
            cover_image=cover_url,
            file_url=file_url,
            product_code=new_book_id,
            status=product_status
        )
        session.add(new_product)
        session.commit()

    success_html = '<html><body style="font-family:Arial; text-align:center; padding:60px 15px; background:#f4f4f4; margin:0;">' + get_navbar(request) + f'''
    <div style="text-align:center; padding:45px 30px; background:white; border-radius:10px; max-width:520px; margin:40px auto; box-shadow:0 4px 12px rgba(0,0,0,0.08);">
        <h1 style="color:#2ecc71; margin-top:0;">Registration Complete!</h1>
        <p style="margin:8px 0;">Official Author Registration Number:</p>
        <div style="background:#2c3e50; color:#f1c40f; font-size:22px; font-weight:bold; padding:10px 18px; border-radius:6px; display:inline-block; margin-bottom:12px;">{reg_no_display}</div>
        <p style="color:#e67e22; font-size:14px;"><strong>KYC Status:</strong> {author.kyc_status} (Your item <code>{new_book_id}</code> will go live on the storefront immediately once our compliance team verifies your NIDA details.)</p>
        <br>
        <a href="/author-dashboard" style="background:#3498db; color:white; padding:12px 25px; text-decoration:none; border-radius:5px; font-weight:bold;">Go to My Dashboard</a>
    </div>''' + FOOTER + '</body></html>'

    response = HTMLResponse(content=success_html)
    response.set_cookie(key="author_email", value=author_email, httponly=True)
    return response

@app.post("/register", response_class=HTMLResponse)
def process_registration(
    request: Request,
    fullname: str = Form(None),
    email: str = Form(None),
    password: str = Form(None),
    book_title: str = Form(...),
    category: str = Form(...),
    institution: str = Form(None),
    course_code: str = Form(None),
    media_type: str = Form(None),
    cast_or_artist: str = Form(None),
    duration: str = Form(None),
    price: float = Form(...),
    cover: UploadFile = File(...),
    pdf_file: UploadFile = File(None),
    trailer_file: UploadFile = File(None),
    agree_terms: str = Form(None)
):
    if not agree_terms:
        return HTMLResponse(content="<h1>Error</h1><p>You must agree to the Terms and Conditions.</p>", status_code=400)

    author_email = request.cookies.get("author_email")

    # 1. Upload cover, master file, and optional trailer to Cloudinary
    cover_url = cloudinary.uploader.upload(cover.file, folder="gophigo_covers", resource_type="image").get("secure_url")
    
    file_url = None
    if pdf_file and pdf_file.filename:
        if category == "Media":
            file_url = cloudinary.uploader.upload(pdf_file.file, folder="gophigo_media", resource_type="video").get("secure_url")
        else:
            file_url = cloudinary.uploader.upload(pdf_file.file, folder="gophigo_pdfs", resource_type="raw", access_mode="public").get("secure_url")

    trailer_url = None
    if trailer_file and trailer_file.filename:
        trailer_url = cloudinary.uploader.upload(trailer_file.file, folder="gophigo_trailers", resource_type="video").get("secure_url")

    # 2. Generate Predictable Item ID
    current_year = datetime.now().year
    with Session(engine) as session:
        total_products = len(session.exec(select(Product)).all())
    new_book_id = f"GOP-{current_year}-{total_products + 1:04d}"

    with Session(engine) as session:
        if author_email:
            author = session.exec(select(Author).where(Author.email == author_email)).first()
            if not author:
                return HTMLResponse(content="<h1>Error: Author session invalid. Please log in again.</h1>", status_code=400)
        else:
            author = Author(
                fullname=fullname,
                email=email,
                password=hashlib.sha256(password.encode()).hexdigest(),
                book_title=book_title,
                book_format=category,
                ebook_price=price,
                cover_image=cover_url,
                pdf_file=file_url,
                book_id=new_book_id,
                membership_status="Pending"
            )
            session.add(author)
            session.commit()
            session.refresh(author)
            author_email = email

        new_product = Product(
            author_id=author.id,
            title=book_title,
            category=category,
            institution=institution if institution else None,
            course_code=course_code if course_code else None,
            media_type=media_type if category == "Media" else None,
            cast_or_artist=cast_or_artist if category == "Media" else None,
            duration=duration if category == "Media" else None,
            trailer_url=trailer_url if category == "Media" else None,
            price=price,
            cover_image=cover_url,
            file_url=file_url,
            product_code=new_book_id,
            status="Approved"
        )
        session.add(new_product)
        session.commit()

    success_html = '<html><body style="font-family:Arial; text-align:center; padding:60px 15px; background:#f4f4f4; margin:0;">' + get_navbar(request) + f'<div style="text-align:center; padding:50px 30px; background:white; border-radius:10px; max-width:500px; margin:40px auto; box-shadow:0 4px 12px rgba(0,0,0,0.08);"><h1 style="color:#2ecc71;">Published Successfully!</h1><p>Your Item ID is: <strong style="font-size:24px; color:#2c3e50;">{new_book_id}</strong></p><p>Share this direct link with fans on WhatsApp, Instagram & TikTok:<br><code style="background:#eee; padding:6px 10px; display:inline-block; margin-top:8px;">www.gophigo.co.tz/item/{new_book_id}</code></p><br><a href="/author-dashboard" style="background:#3498db; color:white; padding:12px 25px; text-decoration:none; border-radius:5px; font-weight:bold;">Go to My Dashboard</a></div>' + FOOTER + '</body></html>'

    response = HTMLResponse(content=success_html)
    response.set_cookie(key="author_email", value=author_email, httponly=True)
    return response

@app.get("/manage-tracks/{product_id}", response_class=HTMLResponse)
def manage_tracks_page(request: Request, product_id: int):
    author_email = request.cookies.get("author_email")
    if not author_email:
        return RedirectResponse(url="/login", status_code=303)

    with Session(engine) as session:
        author = session.exec(select(Author).where(Author.email == author_email)).first()
        p = session.get(Product, product_id)
        if not p or not author or p.author_id != author.id:
            return HTMLResponse(content="<h1>Unauthorized</h1>", status_code=403)

        tracks = session.exec(
            select(ProductTrack).where(ProductTrack.product_id == p.id).order_by(ProductTrack.track_number)
        ).all()

        rows = ""
        for t in tracks:
            rows += f"<tr><td style='padding:8px;'>#{t.track_number}</td><td style='padding:8px;'>{t.track_title}</td><td style='padding:8px;'>{t.duration or '-'}</td></tr>"
        if not rows:
            rows = "<tr><td colspan='3' style='padding:12px; color:#7f8c8d;'>No extra tracks/episodes added yet.</td></tr>"

        return f"""
        <html><body style="font-family:Poppins, Arial, sans-serif; background:#f4f4f4; margin:0;">
            {get_navbar(request)}
            <div style="padding:40px 15px; max-width:600px; margin:auto;">
                <div style="background:white; padding:25px; border-radius:10px; box-shadow:0 4px 12px rgba(0,0,0,0.08);">
                    <h2 style="margin-top:0; color:#2c3e50;">💿 Manage Tracks / Episodes</h2>
                    <p style="color:#7f8c8d;"><strong>Release:</strong> {p.title}</p>

                    <form action="/manage-tracks/{p.id}" method="POST" enctype="multipart/form-data" style="margin:20px 0; background:#f8f9fa; padding:15px; border-radius:8px;">
                        <input type="number" name="track_number" value="{len(tracks) + 1}" required style="width:100%; padding:10px; margin-bottom:10px; box-sizing:border-box;" placeholder="Track / Episode Number">
                        <input type="text" name="track_title" required style="width:100%; padding:10px; margin-bottom:10px; box-sizing:border-box;" placeholder="Song Title or Episode Name">
                        <input type="text" name="duration" style="width:100%; padding:10px; margin-bottom:10px; box-sizing:border-box;" placeholder="Duration (e.g., 3:40 or 42:00)">
                        <label style="font-size:13px; font-weight:bold;">Upload Audio / Video File:</label>
                        <input type="file" name="track_file" accept=".mp3,.mp4,.wav,.m4a,.mov,audio/*,video/*" required style="width:100%; padding:8px 0;">
                        <button type="submit" style="background:#2ecc71; color:white; border:none; padding:12px; width:100%; border-radius:6px; font-weight:bold; cursor:pointer; margin-top:10px;">+ Add Track / Episode</button>
                    </form>

                    <table border="1" style="width:100%; border-collapse:collapse; text-align:left;">
                        <tr style="background:#2c3e50; color:white;"><th style="padding:8px;">#</th><th style="padding:8px;">Title</th><th style="padding:8px;">Duration</th></tr>
                        {rows}
                    </table>
                    <br>
                    <a href="/author-dashboard" style="color:#3498db; text-decoration:none; font-weight:bold;">← Back to Dashboard</a>
                </div>
            </div>
            {FOOTER}
        </body></html>
        """
        
@app.post("/manage-tracks/{product_id}")
def add_product_track(
    request: Request,
    product_id: int,
    track_number: int = Form(...),
    track_title: str = Form(...),
    duration: str = Form(None),
    track_file: UploadFile = File(...)
):
    author_email = request.cookies.get("author_email")
    if not author_email:
        return RedirectResponse(url="/login", status_code=303)

    with Session(engine) as session:
        author = session.exec(select(Author).where(Author.email == author_email)).first()
        p = session.get(Product, product_id)
        if not p or not author or p.author_id != author.id:
            return HTMLResponse(content="<h1>Unauthorized</h1>", status_code=403)

        uploaded_url = cloudinary.uploader.upload(track_file.file, folder="gophigo_media", resource_type="video").get("secure_url")
        session.add(ProductTrack(
            product_id=p.id,
            track_number=track_number,
            track_title=track_title,
            duration=duration,
            file_url=uploaded_url
        ))
        session.commit()

    return RedirectResponse(url=f"/manage-tracks/{product_id}", status_code=303)
    
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return '<html><body style="font-family:Arial; background:#f4f4f4;">' + get_navbar(request) + '<div style="padding:50px;"><div style="background:white; padding:30px; border-radius:8px; max-width:400px; margin:auto;"><h2 style="text-align:center;">Author Login</h2><form action="/login" method="POST"><input type="email" name="email" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Email"><input type="password" name="password" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Password"><button type="submit" style="background:#3498db; color:white; padding:12px; border:none; width:100%; border-radius:5px;">Login</button></form><div style="text-align:center; margin-top:15px;"><a href="/forgot-password">Forgot Password?</a></div></div></div>' + FOOTER + '</body></html>'

@app.post("/login")
def process_login(response: Response, email: str = Form(...), password: str = Form(...)):
    with Session(engine) as session:
        author = session.exec(select(Author).where(Author.email == email, Author.password == hashlib.sha256(password.encode()).hexdigest())).first()
        if author:
            redirect = RedirectResponse(url="/author-dashboard", status_code=303)
            redirect.set_cookie(key="author_email", value=author.email, httponly=True)
            return redirect
    return HTMLResponse(content=f"<h1>Login Failed. <a href='/login'>Try again</a></h1>{FOOTER}", status_code=401)

@app.get("/author-dashboard", response_class=HTMLResponse)
def author_dashboard(request: Request):
    author_email = request.cookies.get("author_email")
    if not author_email: 
        return RedirectResponse(url="/login", status_code=303)
    
    with Session(engine) as session:
        author = session.exec(select(Author).where(Author.email == author_email)).first()
        
        if author.membership_status == "Pending":
            pay_html = '<div style="background:#fff3cd; padding:20px; border-radius:8px; margin-bottom: 20px;"><h3>Membership Payment Required</h3><a href="/pay-membership" style="background:#2ecc71; color:white; padding:10px 20px; text-decoration:none; border-radius:5px; font-weight:bold;">Pay 20,000 TZS</a></div>'
        else:
            pay_html = '<div style="background:#d4edda; padding:20px; margin-bottom: 20px; border-radius:8px;"><h3>Account Status: Active</h3><h4 style="margin: 5px 0 0 0;">Book Status: ' + author.book_status + '</h4></div>'
            
        price_form = f'<div style="background: #f8f9fa; border: 1px solid #ddd; padding: 20px; border-radius: 8px; margin-top: 20px; text-align: left;"><h4 style="margin-top: 0; color: #2c3e50;">Manage Pricing</h4><form action="/update-price" method="POST" style="display: flex; gap: 10px; flex-wrap: wrap;"><div style="flex: 1;"><label style="font-size: 14px; font-weight: bold;">Ebook Price (TZS)</label><input type="number" name="ebook_price" value="{author.ebook_price}" required style="width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #ccc; border-radius: 5px;"></div><div style="flex: 1;"><label style="font-size: 14px; font-weight: bold;">Paperback Price (TZS)</label><input type="number" name="paperback_price" value="{author.paperback_price}" required style="width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #ccc; border-radius: 5px;"></div><div style="width: 100%; margin-top: 10px;"><button type="submit" style="background: #f39c12; color: white; padding: 10px 20px; border: none; border-radius: 5px; font-weight: bold; cursor: pointer;">Update Prices</button></div></form></div>'

        share_link_form = f"""
        <div style="background: #e8f8f5; border: 1px solid #2ecc71; padding: 15px; border-radius: 8px; margin-top: 15px; text-align: center;">
            <h4 style="margin: 0; color: #2c3e50;">Your Item Link</h4>
            <p style="word-break: break-all; color: #3498db; font-weight: bold; margin: 10px 0;">www.gophigo.co.tz/item/{author.book_id}</p>
            <button onclick="navigator.clipboard.writeText('www.gophigo.co.tz/item/{author.book_id}'); alert('Link copied to clipboard!');" style="background: #2ecc71; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">Copy Link</button>
        </div>
        """
        reg_no = author.author_reg_no or f"GOP-AUTH-2026-{author.id:04d}"
        kyc_badge_color = "#2ecc71" if author.kyc_status == "Verified" else "#e67e22"
        kyc_box = f"""
        <div style="background:#f8f9fa; border:1px solid #dce1e7; padding:15px; border-radius:8px; margin-bottom:18px; text-align:left;">
            <p style="margin:4px 0;"><strong>Author Reg No:</strong> <span style="background:#2c3e50; color:#f1c40f; padding:3px 10px; border-radius:4px; font-weight:bold;">{reg_no}</span></p>
            <p style="margin:4px 0;"><strong>Phone:</strong> {author.phone_number or 'Not provided'}</p>
            <p style="margin:4px 0;"><strong>NIDA:</strong> {author.nida_number or 'Pending'} | <strong>TIN:</strong> {author.tin_number or 'Not submitted (Optional)'}</p>
            <p style="margin:4px 0;"><strong>KYC Due Diligence Status:</strong> <span style="color:{kyc_badge_color}; font-weight:bold;">{author.kyc_status}</span></p>
        </div>
        """

        return f"""
        <html><body style="font-family:Arial; background:#f4f4f4;">
            {get_navbar(request)}
            <div style="padding:50px; text-align:center;">
                <h2 style="color: #2c3e50;">{author.fullname}'s Dashboard</h2>
                
                <div style="background:white; padding:30px; border-radius:8px; max-width:600px; margin:auto;">
                    <img src="{author.cover_image}" style="width:150px; height:200px; object-fit:cover; border-radius:4px; margin-bottom: 15px;">
                    <h3>{author.book_title}</h3>
                    <p style="color: #7f8c8d;">{author.book_format}</p>
                    
                    {pay_html}
                    {price_form}
                    {share_link_form}
                </div>
            </div>
            {FOOTER}
        </body></html>
        """
@app.get("/pay-membership")
def pay_membership(request: Request):
    author_email = request.cookies.get("author_email")
    with Session(engine) as session:
        author = session.exec(select(Author).where(Author.email == author_email)).first()
        if author: author.membership_status = "Active"; session.add(author); session.commit()
    return RedirectResponse(url="/author-dashboard", status_code=303)

@app.get("/logout")
def logout():
    res = RedirectResponse(url="/", status_code=303); res.delete_cookie("author_email"); return res

@app.get("/customer-gateway", response_class=HTMLResponse)
def customer_gateway(request: Request, next: str = "/"):
    return f'<html><body style="font-family:Arial; background:#f4f4f4;">{get_navbar(request)}<div style="padding:50px;"><div style="background:white; padding:40px; border-radius:8px; max-width:400px; margin:auto; text-align:center;"><h2>Before you buy...</h2><a href="/customer-login?next={next}" style="background:#3498db; color:white; padding:12px; text-decoration:none; border-radius:5px; display:block; margin-bottom:15px;">Login</a><a href="/customer-register?next={next}" style="background:#2ecc71; color:white; padding:12px; text-decoration:none; border-radius:5px; display:block;">Register</a></div></div>{FOOTER}</body></html>'

@app.get("/customer-register", response_class=HTMLResponse)
def customer_register_page(request: Request, next: str = "/"):
    return f'<html><body style="font-family:Arial; background:#f4f4f4;">{get_navbar(request)}<div style="padding:50px;"><div style="background:white; padding:30px; border-radius:8px; max-width:400px; margin:auto;"><h2 style="text-align:center;">Create Account</h2><form action="/customer-register?next={next}" method="POST"><label>Full Name:</label><br><input type="text" name="fullname" required style="width:100%; padding:10px; margin:10px 0;"><br><label>Email:</label><br><input type="email" name="email" required style="width:100%; padding:10px; margin:10px 0;"><br><label>Password:</label><br><input type="password" name="password" required style="width:100%; padding:10px; margin:10px 0;"><br><button type="submit" style="background:#2ecc71; color:white; padding:12px; border:none; width:100%; border-radius:5px;">Register</button></form></div></div>{FOOTER}</body></html>'

@app.post("/customer-register")
def process_customer_register(fullname: str = Form(...), email: str = Form(...), password: str = Form(...), next: str = Form("/")):
    with Session(engine) as session:
        session.add(Customer(fullname=fullname, email=email, password=hashlib.sha256(password.encode()).hexdigest())); session.commit()
    res = RedirectResponse(url=next, status_code=303); res.set_cookie(key="customer_email", value=email, httponly=True); return res

@app.get("/customer-logout")
def customer_logout():
    res = RedirectResponse(url="/", status_code=303); res.delete_cookie("customer_email"); return res

@app.get("/employee-login", response_class=HTMLResponse)
def employee_login_page(request: Request):
    return f'<html><body style="font-family:Arial; background:#f4f4f4;">{get_navbar(request)}<div style="padding:50px;"><div style="background:white; padding:30px; border-radius:8px; max-width:400px; margin:auto;"><h2 style="color:#f39c12; text-align:center;">Staff Login</h2><form action="/employee-login" method="POST"><input type="email" name="email" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Email"><input type="password" name="password" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Password"><button type="submit" style="background:#f39c12; color:white; padding:12px; border:none; width:100%; border-radius:5px;">Login</button></form><p style="text-align:center; margin-top:15px;"><a href="/forgot-password" style="color:#e74c3c;">Forgot Password?</a></p><p style="text-align:center;"><a href="/admin-login">Admin Login</a></p></div></div>{FOOTER}</body></html>'

@app.post("/employee-login")
def process_employee_login(response: Response, email: str = Form(...), password: str = Form(...)):
    with Session(engine) as session:
        e = session.exec(select(Employee).where(Employee.email == email, Employee.password == hashlib.sha256(password.encode()).hexdigest())).first()
        if e:
            url = "/employee-change-password" if e.must_change_password else "/employee-dashboard"
            res = RedirectResponse(url=url, status_code=303); res.set_cookie(key="employee_email", value=e.email, httponly=True); return res
    return HTMLResponse(content=f"<h1>Login Failed. <a href='/employee-login'>Try again</a></h1>{FOOTER}", status_code=401)

@app.get("/employee-change-password", response_class=HTMLResponse)
def employee_change_password_page(request: Request):
    return f'<html><body style="font-family:Arial; background:#f4f4f4;">{get_navbar(request)}<div style="padding:50px;"><div style="background:white; padding:30px; border-radius:8px; max-width:400px; margin:auto;"><h2 style="text-align:center; color:#e74c3c;">Change Password</h2><form action="/employee-change-password" method="POST"><input type="password" name="new_password" required style="width:100%; padding:10px; margin:10px 0;" placeholder="New Password"><button type="submit" style="background:#e74c3c; color:white; padding:12px; border:none; width:100%; border-radius:5px;">Update</button></form></div></div>{FOOTER}</body></html>'

@app.post("/employee-change-password")
def process_employee_change_password(request: Request, new_password: str = Form(...)):
    with Session(engine) as session:
        e = session.exec(select(Employee).where(Employee.email == request.cookies.get("employee_email"))).first()
        e.password = hashlib.sha256(new_password.encode()).hexdigest(); e.must_change_password = False; session.add(e); session.commit()
    return RedirectResponse(url="/employee-dashboard", status_code=303)

@app.get("/employee-dashboard", response_class=HTMLResponse)
def employee_dashboard(request: Request):
    employee_email = request.cookies.get("employee_email")
    if not employee_email: return RedirectResponse(url="/employee-login", status_code=303)
    with Session(engine) as session:
        e = session.exec(select(Employee).where(Employee.email == employee_email)).first()
        if e.must_change_password: return RedirectResponse(url="/employee-change-password", status_code=303)
        books = session.exec(select(Author).where(Author.book_status == ("Pending Review" if e.role == "Reviewer" else "Under Supervisor Review" if e.role == "Supervisor" else "Pending Final Approval"))).all()
        
        html = f'<html><body style="font-family:Arial; background:#f4f4f4;">{get_navbar(request)}<div style="padding:50px;"><div style="display:flex; justify-content:space-between;"><h1>{e.role} Dashboard</h1><a href="/employee-logout" style="background:#e74c3c; color:white; padding:10px 20px; text-decoration:none; border-radius:5px; height:fit-content;">Sign Out</a></div><p>Welcome, <strong>{e.fullname}</strong>.</p><table border="1" style="width:100%; background:white; border-collapse:collapse;"><tr style="background:#f39c12; color:white;"><th>ID</th><th>Cover</th><th>Book</th><th>Status</th><th>Read</th><th>Action</th></tr>'
        
        for b in books:
            read_btn = f"<a href='/employee-read/{b.id}' style='background:#9b59b6; color:white; padding:5px 10px; text-decoration:none; border-radius:3px;'>📖 Read Book</a>"
            if not b.is_read:
                action_btn = "<span style='color:gray; font-style:italic;'>Must Read First</span>"
            else:
                if e.role == "Reviewer": action_btn = f"<a href='/employee-forward/{b.id}/Under Supervisor Review' style='background:#3498db; color:white; padding:5px 10px; text-decoration:none; border-radius:3px;'>Send to Supervisor</a>"
                elif e.role == "Supervisor": action_btn = f"<a href='/employee-forward/{b.id}/Pending Final Approval' style='background:#3498db; color:white; padding:5px 10px; text-decoration:none; border-radius:3px;'>Send to Approver</a>"
                elif e.role == "Approver": action_btn = f"<a href='/employee-approve/{b.id}' style='background:#2ecc71; color:white; padding:5px 10px; text-decoration:none; border-radius:3px;'>Approve</a> <a href='/employee-request-delete/{b.id}' style='background:#e74c3c; color:white; padding:5px 10px; text-decoration:none; border-radius:3px;'>Request Delete</a>"
            html += f"<tr><td>{b.id}</td><td><img src='{b.cover_image}' style='width:50px;'></td><td>{b.book_title}</td><td>{b.book_status}</td><td>{read_btn}</td><td>{action_btn}</td></tr>"
        return html + f"</table></div>{FOOTER}</body></html>"

@app.get("/employee-read/{author_id}", response_class=HTMLResponse)
def employee_read_book(request: Request, author_id: int):
    with Session(engine) as session:
        a = session.get(Author, author_id)
        a.is_read = True; session.add(a); session.commit()
        return f"<html><body style='margin:0; height:100vh; display:flex; flex-direction:column;'><div style='background:#1a252f; color:white; padding:15px; text-align:center; display:flex; justify-content:space-between;'><h3 style='margin:0;'>Staff Review - {a.book_title}</h3><a href='/employee-dashboard' style='color:#f39c12; text-decoration:none; font-weight:bold;'>← Back</a></div><iframe src='https://docs.google.com/viewer?url={a.pdf_file}&embedded=true' style='flex:1; border:none; width:100%; height:100vh;'></iframe></body></html>"

@app.get("/employee-forward/{author_id}/{new_status}")
def employee_forward(author_id: int, new_status: str):
    with Session(engine) as session:
        a = session.get(Author, author_id); a.book_status = new_status; a.is_read = False; session.add(a); session.commit()
    return RedirectResponse(url="/employee-dashboard", status_code=303)

@app.get("/employee-approve/{author_id}")
def employee_approve(author_id: int):
    with Session(engine) as session:
        a = session.get(Author, author_id); a.book_status = "Approved"; session.add(a); session.commit()
    return RedirectResponse(url="/employee-dashboard", status_code=303)

@app.get("/employee-request-delete/{author_id}")
def employee_request_delete(author_id: int):
    with Session(engine) as session:
        a = session.get(Author, author_id); a.book_status = "Pending Deletion"; session.add(a); session.commit()
    return RedirectResponse(url="/employee-dashboard", status_code=303)

@app.get("/employee-logout")
def employee_logout():
    res = RedirectResponse(url="/", status_code=303); res.delete_cookie("employee_email"); return res

@app.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    return f'<html><body style="font-family:Arial; background:#f4f4f4;">{get_navbar(request)}<div style="padding:50px;"><div style="background:white; padding:30px; border-radius:8px; max-width:400px; margin:auto;"><h2 style="text-align:center;">Reset Password</h2><form action="/forgot-password" method="POST"><input type="email" name="email" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Email"><button type="submit" style="background:#e74c3c; color:white; padding:12px; border:none; width:100%; border-radius:5px;">Generate Reset Link</button></form></div></div>{FOOTER}</body></html>'

@app.post("/forgot-password", response_class=HTMLResponse)
def process_forgot_password(request: Request, email: str = Form(...)):
    token = secrets.token_hex(16); found = False; link = ""
    with Session(engine) as session:
        a = session.exec(select(Author).where(Author.email == email)).first()
        if a: a.reset_token = token; session.add(a); session.commit(); found = True; link = f"/reset-password?token={token}&type=author"
        e = session.exec(select(Employee).where(Employee.email == email)).first()
        if e: e.reset_token = token; session.add(e); session.commit(); found = True; link = f"/reset-password?token={token}&type=employee"
        cust = session.exec(select(Customer).where(Customer.email == email)).first()
        if cust: 
            cust.reset_token = token
            session.add(cust)
            session.commit()
            found = True
            link = f"/reset-password?token={token}&type=customer"
    if found: return f"<html><body style='text-align:center; padding:50px;'>{get_navbar(request)}<h2 style='color:green;'>Simulated Email Sent</h2><a href='{link}' style='background:#3498db; color:white; padding:12px; text-decoration:none; border-radius:5px;'>Click to Reset</a>{FOOTER}</body></html>"
    return HTMLResponse(content=f"<h1>Email not found. <a href='/forgot-password'>Try again</a></h1>{FOOTER}", status_code=404)

@app.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(request: Request, token: str, type: str = "author"):
    return f'<html><body style="font-family:Arial; background:#f4f4f4;">{get_navbar(request)}<div style="padding:50px;"><div style="background:white; padding:30px; border-radius:8px; max-width:400px; margin:auto;"><h2>New Password</h2><form action="/reset-password" method="POST"><input type="hidden" name="token" value="{token}"><input type="hidden" name="type" value="{type}"><input type="password" name="new_password" required style="width:100%; padding:10px; margin:10px 0;"><button type="submit" style="background:#2ecc71; color:white; padding:12px; border:none; width:100%; border-radius:5px;">Update</button></form></div></div>{FOOTER}</body></html>'

@app.post("/reset-password", response_class=HTMLResponse)
def process_reset_password(request: Request, token: str = Form(...), new_password: str = Form(...), type: str = Form("author")):
    pwd = hashlib.sha256(new_password.encode()).hexdigest(); success = False
    with Session(engine) as session:
        if type == "author":
            a = session.exec(select(Author).where(Author.reset_token == token)).first()
            if a: a.password = pwd; a.reset_token = None; session.add(a); session.commit(); success = True
        elif type == "employee":
            e = session.exec(select(Employee).where(Employee.reset_token == token)).first()
            if e: e.password = pwd; e.must_change_password = False; e.reset_token = None; session.add(e); session.commit(); success = True
            elif type == "customer":
                c = session.exec(select(Customer).where(Customer.reset_token == token)).first()
                if c: 
                   c.password = pwd
                   c.reset_token = None
                   session.add(c)
                   session.commit()
                   success = True
    if success: return f"<html><body style='text-align:center; padding:50px;'><h1 style='color:green;'>Password Updated!</h1><a href='/login'>Login</a></body></html>"
    return HTMLResponse(content=f"<h1>Invalid token. <a href='/forgot-password'>Try again</a></h1>{FOOTER}", status_code=400)

@app.get("/admin-login", response_class=HTMLResponse)
def admin_login_page(request: Request):
    return f'<html><body style="font-family:Arial; background:#f4f4f4;">{get_navbar(request)}<div style="padding:50px;"><div style="background:white; padding:30px; border-radius:8px; max-width:400px; margin:auto;"><h2 style="color:#e74c3c; text-align:center;">Admin Login</h2><form action="/admin-login" method="POST"><input type="text" name="username" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Username"><input type="password" name="password" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Password"><button type="submit" style="background:#e74c3c; color:white; padding:12px; border:none; width:100%; border-radius:5px;">Login</button></form></div></div>{FOOTER}</body></html>'

@app.post("/admin-login")
def admin_login(response: Response, username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "gophigo2026":
        res = RedirectResponse(url="/admin", status_code=303); res.set_cookie(key="admin_session", value="true", httponly=True); return res
    return HTMLResponse(content=f"<h1>Invalid Credentials. <a href='/admin-login'>Try again</a></h1>{FOOTER}", status_code=401)

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    try:
        if request.cookies.get("admin_session") != "true": 
            return RedirectResponse(url="/admin-login", status_code=303)
            
        with Session(engine) as session:
            products = session.exec(select(Product)).all()
            purchases = session.exec(select(Purchase).where(Purchase.status == "paid")).all()
            
            total_sales_count = len(purchases)
            gophigo_revenue = 0.0
            author_payouts = 0.0
            
            for p in purchases:
                author = session.get(Author, p.author_id)
                if author:
                    price = author.ebook_price if p.format_bought == "Ebook" else author.paperback_price
                    gophigo_revenue += price * 0.5
                    author_payouts += price * 0.5

            html = f'''<html><body style="font-family:Arial; background:#f4f4f4;">
            {get_navbar(request)}
            <div style="padding:50px; max-width: 1000px; margin: auto;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h1 style="color:#2c3e50;">Admin Dashboard</h1>
                    <a href="/admin-reports" style="background: #9b59b6; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">View Full Reports</a>
                </div>
                
                <div style="display: flex; gap: 20px; margin-bottom: 30px; margin-top: 20px;">
                    <div style="background: #3498db; color: white; padding: 20px; border-radius: 8px; flex: 1; text-align: center;">
                        <h4 style="margin: 0;">Total Books Sold</h4>
                        <h2 style="margin: 10px 0 0 0;">{total_sales_count}</h2>
                    </div>
                    <div style="background: #2c3e50; color: white; padding: 20px; border-radius: 8px; flex: 1; text-align: center;">
                        <h4 style="margin: 0;">Gophigo Revenue (50%)</h4>
                        <h2 style="margin: 10px 0 0 0;">{gophigo_revenue:,.2f} TZS</h2>
                    </div>
                    <div style="background: #2ecc71; color: white; padding: 20px; border-radius: 8px; flex: 1; text-align: center;">
                        <h4 style="margin: 0;">Author Payouts (50%)</h4>
                        <h2 style="margin: 10px 0 0 0;">{author_payouts:,.2f} TZS</h2>
                    </div>
                </div>

                <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 30px;">
                    <h3 style="margin-top: 0; color: #2c3e50;">Add New Employee</h3>
                    <form action="/admin-create-employee" method="POST" style="display: flex; gap: 10px; flex-wrap: wrap;">
                        <input type="text" name="fullname" placeholder="Full Name" required style="flex: 1; padding: 10px; border: 1px solid #ccc; border-radius: 5px;">
                        <input type="email" name="email" placeholder="Email Address" required style="flex: 1; padding: 10px; border: 1px solid #ccc; border-radius: 5px;">
                        <select name="role" required style="flex: 1; padding: 10px; border: 1px solid #ccc; border-radius: 5px;">
                            <option value="Reviewer">Reviewer</option>
                            <option value="Supervisor">Supervisor</option>
                            <option value="Approver">Approver</option>
                        </select>
                        <button type="submit" style="background: #3498db; color: white; padding: 10px 20px; border: none; border-radius: 5px; font-weight: bold; cursor: pointer;">Create Employee</button>
                    </form>
                </div>

                <h3>All Products</h3>
                <table border="1" style="width:100%; background:white; border-collapse:collapse; margin-bottom: 40px;">
                    <tr style="background:#34495e; color:white;">
                        <th>ID</th><th>Title</th><th>Category</th><th>Price</th><th>Status</th><th>Action</th>
                    </tr>
            '''
            
            for p in products:
                if p.status == "Flagged & Removed" or p.is_hidden:
                    btn = f"<a href='/admin-toggle-product/{p.id}?action=unhide' style='background:#3498db; color:white; padding:5px 10px; text-decoration:none; border-radius:3px;'>Unhide</a>"
                    status_display = "<span style='color:red;'>Hidden</span>"
                else:
                    btn = f"<a href='/admin-toggle-product/{p.id}?action=hide' style='background:#e74c3c; color:white; padding:5px 10px; text-decoration:none; border-radius:3px;'>Hide / Delete</a>"
                    status_display = "<span style='color:green;'>Active</span>"
                    
                html += f"<tr><td>{p.id}</td><td>{p.title}</td><td>{p.category}</td><td>{p.price} TZS</td><td>{status_display}</td><td>{btn}</td></tr>"
                
            html += f'''</table>
            </div>
            {FOOTER}
            </body></html>'''
            
            return html
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return HTMLResponse(content=f"<h1>Dashboard Debug Error</h1><p>{str(e)}</p><pre style='background:#eee; padding:20px;'>{error_details}</pre>", status_code=500)            
            
  
@app.get("/admin-logout")
def admin_logout():
    res = RedirectResponse(url="/admin-login", status_code=303); res.delete_cookie("admin_session"); return res

@app.get("/terms", response_class=HTMLResponse)
def terms_page(request: Request):
    return '<html><body style="font-family:Arial; background:#f4f4f4; margin:0;">' + get_navbar(request) + f'<div style="padding: 50px; max-width: 800px; margin: auto; background: white; border-radius: 8px; margin-top: 40px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);"><h1 style="color: #2c3e50; text-align: center;">Gophigo Author Terms & Conditions</h1><hr style="border: 1px solid #eee; margin: 20px 0;"><h3 style="color: #e74c3c;">1. Platform Role</h3><p>Gophigo store operates as a digital marketplace and distribution platform. Gophigo is not the publisher, creator, or owner of the books uploaded by authors.</p><h3 style="color: #e74c3c;">2. Author Responsibility</h3><p>By uploading a manuscript, the Author declares that they are the sole creator and copyright owner of the work, or have obtained all necessary legal rights and permissions to distribute the work.</p><h3 style="color: #e74c3c;">3. Prohibited Content</h3><p>Authors are strictly prohibited from uploading any material that is illegal, defamatory, infringing on copyright, plagiarized, or pornographic.</p><h3 style="color: #e74c3c;">4. Indemnification (Liability)</h3><p>The Author agrees to fully indemnify and hold harmless Gophigo store, its founders, and employees from any and all legal claims, damages, or expenses (including legal fees) arising from the Author\'s uploaded content. <strong>Gophigo will not be held responsible for any copyright disputes, legal actions, or damages resulting from the Author\'s actions.</strong> If a copyright claim is made against Gophigo due to an Author\'s book, Gophigo reserves the right to immediately remove the book and deduct any legal costs from the Author\'s pending royalties.</p><h3 style="color: #e74c3c;">5. Royalties and Fees</h3><p>Gophigo will retain a 50% commission on all net sales. The remaining 50% will be credited to the Author\'s dashboard. Gophigo reserves the right to adjust this fee structure with 30 days\' notice to the Author.</p><h3 style="color: #e74c3c;">6. Account Termination</h3><p>Gophigo reserves the right to suspend or permanently ban any Author and delete their books if they violate these terms, without refunding the annual membership fee.</p><h3 style="color: #e74c3c;">7. Governing Law</h3><p>These terms are governed by the laws of the United Republic of Tanzania.</p><br><p style="text-align: center; color: #7f8c8d; font-size: 14px;">Last updated: November 2026</p><div style="text-align: center; margin-top: 20px;"><a href="/register" style="background: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Back to Registration</a></div></div>' + FOOTER + '</body></html>'

@app.get("/admin-reports", response_class=HTMLResponse)
def admin_reports(request: Request, period: str = "all"):
    if request.cookies.get("admin_session") != "true": 
        return RedirectResponse(url="/admin-login", status_code=303)
        
    with Session(engine) as session:
        query = select(Purchase).where(Purchase.status == "paid")
        now = datetime.now(timezone.utc)
        
        if period == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            query = query.where(Purchase.created_at >= start_date)
        elif period == "week":
            start_date = now - timedelta(days=7)
            query = query.where(Purchase.created_at >= start_date)
        elif period == "month":
            start_date = now - timedelta(days=30)
            query = query.where(Purchase.created_at >= start_date)
        elif period == "year":
            start_date = now - timedelta(days=365)
            query = query.where(Purchase.created_at >= start_date)
            
        purchases = session.exec(query.order_by(Purchase.created_at.desc())).all()
        
        total_sales = len(purchases)
        total_revenue = 0.0
        
        for p in purchases:
            author = session.get(Author, p.author_id)
            if author:
                price = author.ebook_price if p.format_bought == "Ebook" else author.paperback_price
                total_revenue += price * 0.5
                
        html = f'''<html><body style="font-family:Arial; background:#f4f4f4;">
            {get_navbar(request)}
            <div style="padding:50px; max-width: 1000px; margin: auto;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h1 style="color:#2c3e50;">Sales Reports</h1>
                    <a href="/admin" style="background: #34495e; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Back to Dashboard</a>
                </div>

                <div style="margin-bottom: 20px; display: flex; gap: 10px;">
                    <a href="/admin-reports?period=today" style="background: {'#3498db' if period == 'today' else '#ccc'}; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px;">Today</a>
                    <a href="/admin-reports?period=week" style="background: {'#3498db' if period == 'week' else '#ccc'}; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px;">This Week</a>
                    <a href="/admin-reports?period=month" style="background: {'#3498db' if period == 'month' else '#ccc'}; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px;">This Month</a>
                    <a href="/admin-reports?period=year" style="background: {'#3498db' if period == 'year' else '#ccc'}; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px;">This Year</a>
                    <a href="/admin-reports?period=all" style="background: {'#3498db' if period == 'all' else '#ccc'}; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px;">All Time</a>
                </div>

                <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 20px;">
                    <h3 style="margin: 0; color: #2c3e50;">Summary</h3>
                    <p style="font-size: 18px;"><strong>Books Sold:</strong> {total_sales}</p>
                    <p style="font-size: 18px;"><strong>Gophigo Revenue (50%):</strong> {total_revenue:,.2f} TZS</p>
                </div>

                <table border="1" style="width:100%; background:white; border-collapse:collapse;">
                    <tr style="background:#34495e; color:white;">
                        <th>Date</th><th>Reference</th><th>Book</th><th>Format</th><th>Phone</th><th>Status</th>
                    </tr>
        '''
        
        for p in purchases:
            phone = p.phone_number if p.phone_number else "N/A"
            date_str = p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "Unknown"
            html += f"<tr><td>{date_str}</td><td>{p.reference[:8]}...</td><td>{p.book_title}</td><td>{p.format_bought}</td><td>{phone}</td><td style='color:green; font-weight:bold;'>{p.status.upper()}</td></tr>"
            
        html += f'''</table>
            </div>
            {FOOTER}
        </body></html>'''
        
        return html
@app.post("/update-price")
def update_price(request: Request, ebook_price: float = Form(...), paperback_price: float = Form(...)):
    author_email = request.cookies.get("author_email")
    if not author_email: 
        return RedirectResponse(url="/login", status_code=303)
        
    with Session(engine) as session:
        author = session.exec(select(Author).where(Author.email == author_email)).first()
        if author:
            author.ebook_price = ebook_price
            author.paperback_price = paperback_price
            session.add(author)
            session.commit()
            
    return RedirectResponse(url="/author-dashboard", status_code=303)

@app.get("/author-reports", response_class=HTMLResponse)
def author_reports(request: Request):
    author_email = request.cookies.get("author_email")
    if not author_email: 
        return RedirectResponse(url="/login", status_code=303)
        
    with Session(engine) as session:
        author = session.exec(select(Author).where(Author.email == author_email)).first()
        
        purchases = session.exec(select(Purchase).where(Purchase.author_id == author.id, Purchase.status == "paid").order_by(Purchase.created_at.desc())).all()
        
        total_sales = len(purchases)
        total_earnings = 0.0
        
        for p in purchases:
            if p.format_bought == "Ebook":
                total_earnings += author.ebook_price * 0.5
            else:
                total_earnings += author.paperback_price * 0.5
                
        html = f'''<html><body style="font-family:Arial; background:#f4f4f4;">
            {get_navbar(request)}
            <div style="padding:50px; max-width: 1000px; margin: auto;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h1 style="color:#2c3e50;">My Earnings Report</h1>
                    <a href="/author-dashboard" style="background: #34495e; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Back to Dashboard</a>
                </div>

                <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 20px;">
                    <h3 style="margin: 0; color: #2c3e50;">Summary</h3>
                    <p style="font-size: 18px;"><strong>Total Books Sold:</strong> {total_sales}</p>
                    <p style="font-size: 18px;"><strong>Total Royalties (50%):</strong> {total_earnings:,.2f} TZS</p>
                </div>

                <table border="1" style="width:100%; background:white; border-collapse:collapse;">
                    <tr style="background:#34495e; color:white;">
                        <th>Date</th><th>Book</th><th>Format</th><th>Your Royalty</th><th>Status</th>
                    </tr>
        '''
        
        for p in purchases:
            date_str = p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "Unknown"
            price = author.ebook_price if p.format_bought == "Ebook" else author.paperback_price
            royalty = price * 0.5
            
            html += f"<tr><td>{date_str}</td><td>{p.book_title}</td><td>{p.format_bought}</td><td style='color:#2ecc71; font-weight:bold;'>{royalty:,.2f} TZS</td><td style='color:green;'>{p.status.upper()}</td></tr>"
            
        html += f'''</table>
            </div>
            {FOOTER}
        </body></html>'''
        
        return html

@app.get("/admin-delete-book/{author_id}")
def admin_delete_book(request: Request, author_id: int, action: str):
    if request.cookies.get("admin_session") != "true": 
        return RedirectResponse(url="/admin-login", status_code=303)
        
    with Session(engine) as session:
        a = session.get(Author, author_id)
        if a:
            if action == "hide":
                a.is_hidden = True
            elif action == "unhide":
                a.is_hidden = False
            elif action == "delete":
                a.book_status = "Flagged & Removed"
                a.is_hidden = True
            session.add(a)
            session.commit()
            
            return HTMLResponse(content=f'<html><body style="font-family:Arial; text-align:center; padding:50px;"><h1 style="color:#2ecc71;">Payment Prompt Sent!</h1><p>We have sent a payment request to <strong>{phone}</strong>.</p><p>Please check your phone and enter your mobile money PIN to complete the purchase.</p><p style="color:#7f8c8d;">Reference: {purchase_ref}</p><br><p style="color:#e74c3c; font-weight:bold;">Redirecting to your library in 5 seconds...</p><meta http-equiv="refresh" content="5;url=/my-library" /><a href="/my-library" style="background:#3498db; color:white; padding:12px 25px; text-decoration:none; border-radius:5px;">Go to My Library Now</a></body></html>', status_code=200)
from fastapi.responses import JSONResponse

@app.get("/book/{book_id}")
def direct_book_link(request: Request, book_id: str):
    with Session(engine) as session:
        product = session.exec(select(Product).where(Product.product_code == book_id)).first()
        
        if not product:
            return HTMLResponse(content="<h1>Book not found</h1>", status_code=404)
            
        # Check if they are logged in
        customer_email = request.cookies.get("customer_email")
        if not customer_email:
            # Send to login, but tell it to come BACK to this specific checkout page
            return RedirectResponse(url=f"/customer-login?next=/checkout-product/{product.id}", status_code=303)
            
        # If logged in, go straight to checkout
        return RedirectResponse(url=f"/checkout-product/{product.id}", status_code=303)
        
@app.post("/upload-product")
def process_upload_product(request: Request, title: str = Form(...), category: str = Form(...), institution: str = Form(None), level_of_study: str = Form(None), year_of_study: str = Form(None), course_code: str = Form(None), religion: str = Form(None), sub_category: str = Form(None), language: str = Form(None), price: float = Form(...), cover: UploadFile = File(...), file: UploadFile = File(...)):
    author_email = request.cookies.get("author_email")
    if not author_email: return RedirectResponse(url="/login", status_code=303)
    
    with Session(engine) as session:
        author = session.exec(select(Author).where(Author.email == author_email)).first()
        if not author: return RedirectResponse(url="/login", status_code=303)

        cover_url = cloudinary.uploader.upload(cover.file, folder="gophigo_covers", resource_type="image").get("secure_url")
        file_url = cloudinary.uploader.upload(file.file, folder="gophigo_docs", resource_type="raw", access_mode="public").get("secure_url")

        current_year = datetime.now().year
        total_products = len(session.exec(select(Product)).all())
        product_code = f"GOP-{current_year}-{total_products + 1:04d}"

        new_product = Product(
            author_id=author.id,
            title=title,
            category=category,
            institution=institution if institution else None,
            level_of_study=level_of_study if level_of_study else None,
            year_of_study=year_of_study if year_of_study else None,
            course_code=course_code if course_code else None,
            religion=religion if religion else None,
            sub_category=sub_category if sub_category else None,
            language=language if language else None,
            price=price,
            cover_image=cover_url,
            file_url=file_url,
            product_code=product_code,
            status="Approved"
        )
        
        session.add(new_product)
        session.commit()
        
    return '<html><body style="font-family:Arial; text-align:center; padding:100px; background:#f4f4f4;">' + get_navbar(request) + f'<div style="text-align:center; padding:100px;"><h1 style="color:#2ecc71;">Registration Successful!</h1><p>Your Book ID is: <strong style="font-size:24px; color:#2c3e50;">{new_book_id}</strong></p><p>Your unique share link is: <br> <code>www.gophigo.co.tz/book/{new_book_id}</code></p><br><a href="/login" style="background:#3498db; color:white; padding:12px 25px; text-decoration:none; border-radius:5px;">Go to Login</a></div>' + FOOTER + '</body></html>'

@app.get("/run-migration-v2")
def run_migration_v2():
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE product ADD COLUMN religion VARCHAR;"))
            conn.commit()
    except Exception:
        pass
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE product ADD COLUMN sub_category VARCHAR;"))
            conn.commit()
    except Exception:
        pass
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE product ADD COLUMN year_of_study VARCHAR;"))
            conn.commit()
    except Exception:
        pass
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE product ADD COLUMN language VARCHAR;"))
            conn.commit()
    except Exception:
        pass
        
    return {"status": "success", "message": "Product table updated with religion, sub_category, year_of_study, and language!"}

@app.get("/customer-login", response_class=HTMLResponse)
def customer_login_page(request: Request, next: str = "/"):
    return '<html><body style="font-family:Arial; background:#f4f4f4;">' + get_navbar(request) + f'<div style="padding:50px;"><div style="background:white; padding:30px; border-radius:8px; max-width:400px; margin:auto;"><h2 style="text-align:center;">Customer Login</h2><form action="/customer-login?next={next}" method="POST"><input type="hidden" name="next" value="{next}"><input type="email" name="email" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Email"><input type="password" name="password" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Password"><button type="submit" style="background:#2ecc71; color:white; padding:12px; border:none; width:100%; border-radius:5px;">Login</button></form><div style="text-align:center; margin-top:15px;"><p style="margin-bottom: 5px;"><a href="/customer-register?next={next}">Register here</a></p><p style="margin-top: 5px;"><a href="/forgot-password" style="color: #e74c3c;">Forgot Password?</a></p></div></div></div>' + FOOTER + '</body></html>'
@app.post("/customer-login")
def process_customer_login(response: Response, email: str = Form(...), password: str = Form(...), next: str = Form("/")):
    with Session(engine) as session:
        c = session.exec(select(Customer).where(Customer.email == email, Customer.password == hashlib.sha256(password.encode()).hexdigest())).first()
        if c:
            res = RedirectResponse(url=next, status_code=303)
            res.set_cookie(key="customer_email", value=c.email, httponly=True)
            return res
    return HTMLResponse(content=f"<h1>Login Failed. <a href='/customer-login?next={next}'>Try again</a></h1>{FOOTER}", status_code=401)
@app.get("/admin-toggle-product/{product_id}")
def admin_toggle_product(request: Request, product_id: int, action: str):
    if request.cookies.get("admin_session") != "true": 
        return RedirectResponse(url="/admin-login", status_code=303)
        
    with Session(engine) as session:
        p = session.get(Product, product_id)
        if p:
            if action == "hide":
                p.is_hidden = True
            elif action == "unhide":
                p.is_hidden = False
            session.add(p)
            session.commit()
            
    return RedirectResponse(url="/admin", status_code=303)
@app.post("/register", response_class=HTMLResponse)
def process_registration(
    request: Request, 
    fullname: str = Form(None), 
    email: str = Form(None), 
    password: str = Form(None), 
    book_title: str = Form(...), 
    category: str = Form(...), 
    institution: str = Form(None), 
    course_code: str = Form(None), 
    price: float = Form(...), 
    cover: UploadFile = File(...), 
    pdf_file: UploadFile = File(None), 
    agree_terms: str = Form(None)
):
    if not agree_terms:
        return HTMLResponse(content="<h1>Error</h1><p>You must agree to the Terms and Conditions.</p>", status_code=400)
        
    author_email = request.cookies.get("author_email")
    
    # 1. Upload files to Cloudinary
    cover_url = cloudinary.uploader.upload(cover.file, folder="gophigo_covers", resource_type="image").get("secure_url")
    file_url = None
    if pdf_file and pdf_file.filename: 
        if category == "Media":
            file_url = cloudinary.uploader.upload(pdf_file.file, folder="gophigo_media", resource_type="video").get("secure_url")
        else:
            file_url = cloudinary.uploader.upload(pdf_file.file, folder="gophigo_pdfs", resource_type="raw", access_mode="public").get("secure_url")

    # 2. Generate the Predictable Book ID
    current_year = datetime.now().year
    with Session(engine) as session:
        total_products = len(session.exec(select(Product)).all())
    new_book_id = f"GOP-{current_year}-{total_products + 1:04d}"

    with Session(engine) as session:
        # 3. Check if the author is already logged in
        if author_email:
            author = session.exec(select(Author).where(Author.email == author_email)).first()
            if not author:
                return HTMLResponse(content="<h1>Error: Author session invalid. Please log in again.</h1>", status_code=400)
        else:
            # 4. If not logged in, create a NEW author
            author = Author(
                fullname=fullname, 
                email=email, 
                password=hashlib.sha256(password.encode()).hexdigest(), 
                book_title=book_title, 
                book_format=category, 
                ebook_price=price, 
                cover_image=cover_url, 
                pdf_file=file_url,
                book_id=new_book_id,
                membership_status="Pending"
            )
            session.add(author)
            session.commit()
            session.refresh(author)
            
            # Auto-login the new author
            author_email = email

        # 5. Create the Product (for both new and existing authors)
        new_product = Product(
            author_id=author.id,
            title=book_title,
            category=category,
            institution=institution,
            course_code=course_code,
            price=price,
            cover_image=cover_url,
            file_url=file_url,
            product_code=new_book_id,
            status="Approved"
        )
        session.add(new_product)
        session.commit()

    # 6. Show Success Page
    success_html = '<html><body style="font-family:Arial; text-align:center; padding:100px; background:#f4f4f4;">' + get_navbar(request) + f'<div style="text-align:center; padding:100px; background:white; border-radius:8px; max-width:500px; margin:auto;"><h1 style="color:#2ecc71;">Product Uploaded!</h1><p>Your Item ID is: <strong style="font-size:24px; color:#2c3e50;">{new_book_id}</strong></p><p>Your unique share link is: <br> <code>www.gophigo.co.tz/item/{new_book_id}</code></p><br><a href="/author-dashboard" style="background:#3498db; color:white; padding:12px 25px; text-decoration:none; border-radius:5px; font-weight:bold;">Go to My Dashboard</a></div>' + FOOTER + '</body></html>'
    
    response = HTMLResponse(content=success_html)
    response.set_cookie(key="author_email", value=author_email, httponly=True)
    return response
app.get("/my-library", response_class=HTMLResponse)
def my_library(request: Request):
    try:
        customer_email = request.cookies.get("customer_email")
        if not customer_email:
            return RedirectResponse(url="/customer-login?next=/my-library", status_code=303)

        with Session(engine) as session:
            c = session.exec(select(Customer).where(Customer.email == customer_email)).first()
            if not c:
                return RedirectResponse(url="/customer-login?next=/my-library", status_code=303)

            raw_purchases = session.exec(
                select(Purchase).where(Purchase.customer_id == c.id, Purchase.status == "paid")
            ).all()

            seen = set()
            purchases = []
            for item in raw_purchases:
                key = (item.book_title, item.format_bought)
                if item.format_bought == "Ticket" or key not in seen:
                    seen.add(key)
                    purchases.append(item)

            if not purchases:
                body = "<p style='text-align:center; color:#7f8c8d; padding:40px;'>You haven't purchased any items yet. <a href='/'>Browse the store</a></p>"
            else:
                body = '<div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(220px, 1fr)); gap:20px; padding:20px; max-width:1100px; margin:auto;">'
                for p in purchases:
                    product = session.exec(
                        select(Product).where(Product.title == p.book_title, Product.author_id == p.author_id)
                    ).first()
                    cover = product.cover_image if (product and product.cover_image) else "https://via.placeholder.com/180x250?text=Gophigo"

                    if product and product.category == "Ticket":
                        qr_data = f"EVENT:{product.product_code}|TICKET:{p.reference}"
                        qr = qrcode.QRCode(version=1, box_size=10, border=5)
                        qr.add_data(qr_data)
                        qr.make(fit=True)
                        img = qr.make_image(fill_color="black", back_color="white")

                        buffered = BytesIO()
                        img.save(buffered, format="PNG")
                        img_str = base64.b64encode(buffered.getvalue()).decode()

                        action = f"<img src='data:image/png;base64,{img_str}' style='width:100%; max-width:150px; margin-top:10px;'><p style='font-size:12px; color:#7f8c8d;'>Ticket ID: {p.reference[:8]}</p>"
                    elif product and product.category == "Media":
                        action = f"<a href='/play-media/{p.id}' style='background:#e74c3c; color:white; padding:10px; border-radius:5px; text-decoration:none; display:block; margin-bottom:5px; font-weight:bold;'>▶️ Play Media</a>"
                    elif p.format_bought == "Paperback":
                        action = f"<span style='background:#f39c12; color:white; padding:8px 12px; border-radius:5px; display:block; margin-bottom:5px; font-size:13px;'>📦 Paperback Shipping to {p.region or 'Address'}</span>"
                    else:
                        action = f"<a href='/read/{p.id}' style='background:#3498db; color:white; padding:10px; border-radius:5px; text-decoration:none; display:block; margin-bottom:5px; font-weight:bold;'>📖 Read / View</a>"

                    review_form = f"""
                    <form action="/review/{p.id}" method="POST" style="margin-top:10px; border-top:1px solid #eee; padding-top:10px;">
                        <select name="rating" style="width:100%; padding:5px; margin-bottom:5px;">
                            <option value="5">⭐⭐⭐⭐⭐ (5)</option>
                            <option value="4">⭐⭐⭐⭐ (4)</option>
                            <option value="3">⭐⭐⭐ (3)</option>
                            <option value="2">⭐⭐ (2)</option>
                            <option value="1">⭐ (1)</option>
                        </select>
                        <input type="text" name="comment" placeholder="Leave a review..." required style="width:100%; padding:6px; box-sizing:border-box; margin-bottom:5px;">
                        <button type="submit" style="background:#2ecc71; color:white; border:none; padding:6px 10px; border-radius:4px; width:100%; cursor:pointer;">Submit Review</button>
                    </form>
                    """

                    body += f"""
                    <div style="background:white; padding:15px; border-radius:8px; text-align:center; box-shadow:0 4px 10px rgba(0,0,0,0.08); display:flex; flex-direction:column; justify-content:space-between;">
                        <div>
                            <img src="{cover}" style="width:100%; height:220px; object-fit:cover; border-radius:4px; margin-bottom:10px;">
                            <h3 style="color:#2c3e50; margin:0 0 8px; font-size:16px;">{p.book_title}</h3>
                        </div>
                        <div>
                            {action}
                            {review_form}
                        </div>
                    </div>
                    """
                body += "</div>"

            return f'<html><body style="font-family:Arial; background:#f4f4f4; margin:0;">{get_navbar(request)}<h1 style="text-align:center; color:#2c3e50; padding:20px;">My Library</h1>{body}{FOOTER}</body></html>'

    except Exception as e:
        import traceback
@app.get("/item/{product_code}")
def direct_item_link(request: Request, product_code: str, ref: int = None):
    with Session(engine) as session:
        product = session.exec(select(Product).where(Product.product_code == product_code)).first()
        if not product:
            return HTMLResponse(content="<h1>Item not found</h1>", status_code=404)

        customer_email = request.cookies.get("customer_email")
        target = f"/checkout-product/{product.id}" if customer_email else f"/customer-login?next=/checkout-product/{product.id}"
        res = RedirectResponse(url=target, status_code=303)
        if ref:
            res.set_cookie(key="gophigo_ref", value=str(ref), max_age=86400 * 7)
        return res
        
@app.post("/snippe-webhook")
async def snippe_webhook(request: Request):
    body = await request.body()
    try:
        event = json.loads(body)
    except:
        return {"status": "error", "message": "invalid json"}

    # Get references from Snippe's payload
    metadata = event.get("data", {}).get("metadata", {}) or {}
    purchase_ref = metadata.get("purchase_reference")
    snippe_ref_from_payload = event.get("data", {}).get("reference")
    
    if purchase_ref or snippe_ref_from_payload:
        with Session(engine) as session:
            # Match by our UUID or Snippe's SN...
            purchase = session.exec(select(Purchase).where(
                (Purchase.reference == purchase_ref) | (Purchase.snippe_ref == snippe_ref_from_payload)
            )).first()
            
            if purchase and purchase.status != "paid":
                purchase.status = "paid"
                session.add(purchase)
                session.commit()
                
    return {"status": "success"}
@app.get("/scanner", response_class=HTMLResponse)
def scanner_page(request: Request):
    if not request.cookies.get("admin_session") and not request.cookies.get("employee_email"):
        return RedirectResponse(url="/employee-login", status_code=303)

    return """
    <html><head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://unpkg.com/html5-qrcode"></script>
    <style>
        body { font-family: Arial; text-align: center; background: #2c3e50; color: white; margin: 0; padding: 20px; }
        #reader { width: 100%; max-width: 400px; margin: auto; background: white; border-radius: 10px; padding: 10px; }
    </style>
    </head><body>
        <h1>📷 Gophigo Scanner</h1>
        <div id="reader"></div>
        <script>
            function onScanSuccess(decodedText, decodedResult) {
                // Stop scanning
                html5QrcodeScanner.clear();
                // Redirect the page to the verify URL directly!
                window.location.href = '/verify-ticket?qr_data=' + encodeURIComponent(decodedText);
            }
            let html5QrcodeScanner = new Html5QrcodeScanner("reader", { fps: 10, qrbox: 250 });
            html5QrcodeScanner.render(onScanSuccess);
        </script>
    </body></html>
    """
@app.get("/verify-ticket", response_class=HTMLResponse)
def verify_ticket(qr_data: str):
    try:
        parts = qr_data.split("|")
        event_code = parts[0].replace("EVENT:", "")
        ticket_ref = parts[1].replace("TICKET:", "")
    except:
        return "<h1 style='color:red;'>Invalid QR Code format.</h1><a href='/scanner'>Scan Again</a>"

    with Session(engine) as session:
        purchase = session.exec(select(Purchase).where(Purchase.reference == ticket_ref)).first()
        
        if not purchase:
            return "<h1 style='color:red; text-align:center; padding:50px;'>Fake Ticket! Not found.</h1><a href='/scanner' style='display:block; text-align:center;'>Scan Again</a>"
            
        if purchase.status != "paid":
            return "<h1 style='color:red; text-align:center; padding:50px;'>Unpaid Ticket!</h1><a href='/scanner' style='display:block; text-align:center;'>Scan Again</a>"
            
        if purchase.scanned:
            return "<h1 style='color:red; text-align:center; padding:50px;'>ALREADY SCANNED! This ticket has been used.</h1><a href='/scanner' style='display:block; text-align:center;'>Scan Again</a>"
            
        product = session.exec(select(Product).where(Product.title == purchase.book_title)).first()
        if not product or product.product_code != event_code:
            return "<h1 style='color:red; text-align:center; padding:50px;'>Wrong Event! This ticket is for a different match.</h1><a href='/scanner' style='display:block; text-align:center;'>Scan Again</a>"
            
        purchase.scanned = True
        session.add(purchase)
        session.commit()
        
        return f"<html><body style='background:#2ecc71; color:white; text-align:center; padding:100px; font-family:Arial;'><h1>ENTRY ALLOWED!</h1><h2>{purchase.book_title}</h2><p>Ticket ID: {purchase.reference[:8]}</p><a href='/scanner' style='background:white; color:#2ecc71; padding:15px 30px; text-decoration:none; border-radius:5px; font-weight:bold; font-size:20px;'>Scan Next Fan</a></body></html>"

@app.get("/play-media/{purchase_id}", response_class=HTMLResponse)
def play_media(request: Request, purchase_id: int):
    customer_email = request.cookies.get("customer_email")
    if not customer_email:
        return RedirectResponse(url="/customer-login", status_code=303)

    with Session(engine) as session:
        c = session.exec(select(Customer).where(Customer.email == customer_email)).first()
        p = session.get(Purchase, purchase_id)
        if not p or not c or p.customer_id != c.id or p.status != "paid":
            return HTMLResponse(content="<h1 style='text-align:center; padding:50px;'>Unauthorized or unpaid media access.</h1>", status_code=403)

        product = session.exec(select(Product).where(Product.title == p.book_title, Product.author_id == p.author_id)).first()
        cover = product.cover_image if (product and product.cover_image) else ""
        artist_info = product.cast_or_artist if (product and product.cast_or_artist) else "Gophigo Exclusive"

        media_url = p.pdf_file or ""
        # Optimize Cloudinary streaming for mobile data bundles
        if "res.cloudinary.com" in media_url and "/upload/" in media_url:
            media_url = media_url.replace("/upload/", "/upload/f_auto,q_auto/", 1)

        is_audio = any(ext in media_url.lower() for ext in [".mp3", ".wav", ".m4a", ".ogg"])
        watermark_text = f"{c.email} • ID:{(p.reference or '')[:8].upper()}"
        vip_badge = f"<span style='background:#f1c40f; color:#1a252f; padding:4px 12px; border-radius:20px; font-size:12px; font-weight:bold;'>🏆 {p.supporter_tier}</span>" if p.supporter_tier and p.supporter_tier != "Standard" else ""

        if is_audio:
            player_html = f"""
            <div style="max-width:420px; margin:20px auto; background:#111827; padding:25px; border-radius:14px; border:1px solid #374151;">
                <img src="{cover}" style="width:220px; height:220px; object-fit:cover; border-radius:10px; box-shadow:0 8px 25px rgba(0,0,0,0.6); margin-bottom:15px;">
                <h3 style="margin:5px 0; color:white;">{p.book_title}</h3>
                <p style="color:#9ca3af; font-size:13px; margin:0 0 15px;">{artist_info}</p>
                {vip_badge}
                <audio id="mediaPlayer" controls autoplay controlsList="nodownload" oncontextmenu="return false;" style="width:100%; margin-top:15px;">
                    <source src="{media_url}">
                </audio>
                <p style="font-size:11px; color:#6b7280; margin-top:12px;">Licensed stream: {watermark_text}</p>
            </div>
            """
        else:
            player_html = f"""
            <div id="cinemaStage" oncontextmenu="return false;" style="position:relative; max-width:900px; margin:20px auto; background:black; border-radius:12px; overflow:hidden; box-shadow:0 10px 30px rgba(0,0,0,0.7);">
                <video id="mediaPlayer" controls autoplay playsinline controlsList="nodownload noplaybackrate" disablePictureInPicture oncontextmenu="return false;" style="width:100%; max-height:75vh; display:block;">
                    <source src="{media_url}">
                </video>
                <div id="piracyWatermark" style="position:absolute; top:12%; left:8%; color:rgba(255,255,255,0.28); font-size:13px; font-weight:bold; pointer-events:none; user-select:none; text-shadow:1px 1px 2px black; transition:all 1.5s ease;">
                    {watermark_text}
                </div>
            </div>
            <div style="margin-top:10px;">
                {vip_badge}
                <button onclick="setSpeed(1)" style="background:#374151; color:white; border:none; padding:6px 12px; border-radius:5px; cursor:pointer; margin:0 3px;">1x</button>
                <button onclick="setSpeed(1.25)" style="background:#374151; color:white; border:none; padding:6px 12px; border-radius:5px; cursor:pointer; margin:0 3px;">1.25x</button>
                <button onclick="setSpeed(1.5)" style="background:#374151; color:white; border:none; padding:6px 12px; border-radius:5px; cursor:pointer; margin:0 3px;">1.5x</button>
            </div>
            <script>
                function setSpeed(rate) {{
                    document.getElementById('mediaPlayer').playbackRate = rate;
                }}
                setInterval(function() {{
                    var wm = document.getElementById('piracyWatermark');
                    if (wm) {{
                        wm.style.top = (10 + Math.floor(Math.random() * 70)) + '%';
                        wm.style.left = (5 + Math.floor(Math.random() * 65)) + '%';
                    }}
                }}, 6000);
            </script>
              """

        extra_tracks = []
        if product:
            extra_tracks = session.exec(
                select(ProductTrack).where(ProductTrack.product_id == product.id).order_by(ProductTrack.track_number)
            ).all()

        playlist_html = ""
        if extra_tracks:
            items = f"<button onclick=\"switchMedia('{media_url}', '{p.title}')\" style='display:block; width:100%; text-align:left; padding:10px; margin-bottom:6px; background:#1f2937; color:#f1c40f; border:1px solid #374151; border-radius:6px; cursor:pointer; font-weight:bold;'>1. {p.title} (Main)</button>"
            for idx, tr in enumerate(extra_tracks, start=2):
                tr_url = tr.file_url.replace("/upload/", "/upload/f_auto,q_auto/", 1) if "res.cloudinary.com" in tr.file_url else tr.file_url
                safe_tr = tr.track_title.replace("'", "\\'")
                dur_tag = f" ({tr.duration})" if tr.duration else ""
                items += f"<button onclick=\"switchMedia('{tr_url}', '{safe_tr}')\" style='display:block; width:100%; text-align:left; padding:10px; margin-bottom:6px; background:#111827; color:white; border:1px solid #374151; border-radius:6px; cursor:pointer;'>{idx}. {tr.track_title}{dur_tag}</button>"
            playlist_html = f"""
            <div style="max-width:600px; margin:20px auto; text-align:left; background:#0f172a; padding:15px; border-radius:10px; border:1px solid #1e293b;">
                <h4 style="margin:0 0 10px 0; color:#f1c40f;">💿 Full Tracklist / Episodes</h4>
                {items}
            </div>
            <script>
                function switchMedia(newUrl, title) {{
                    var player = document.getElementById('mediaPlayer');
                    if (player) {{
                        player.src = newUrl;
                        player.play();
                    }}
                }}
            </script>
            """

        return f"""
        <html><body style="font-family:Poppins, Arial, sans-serif; background:#0b0f19; color:white; margin:0;" oncontextmenu="return false;">
            {get_navbar(request)}
            <div style="padding:30px 15px; text-align:center;">
                <h2 style="color:#f1c40f; margin-bottom:5px;">🎬 Gophigo Premiere Vault</h2>
                <p style="color:#9ca3af; margin-top:0; font-size:14px;">{p.book_title} • {artist_info}</p>
                {player_html}
                <div style="margin-top:25px;">
                    <a href="/my-library" style="background:#3498db; color:white; padding:12px 25px; text-decoration:none; border-radius:6px; font-weight:bold;">← Back to My Library</a>
                </div>
            </div>
            {FOOTER}
        </body></html>
        """

@app.post("/admin-create-employee", response_class=HTMLResponse)
def admin_create_employee(request: Request, fullname: str = Form(...), email: str = Form(...), role: str = Form(...)):
    if request.cookies.get("admin_session") != "true":
        return RedirectResponse(url="/admin-login", status_code=303)

    temp_password = secrets.token_hex(4)
    with Session(engine) as session:
        existing = session.exec(select(Employee).where(Employee.email == email)).first()
        if existing:
            return HTMLResponse(content=f"<h1>Employee email already exists.</h1><a href='/admin'>Back</a>", status_code=400)
        emp = Employee(
            fullname=fullname,
            email=email,
            password=hashlib.sha256(temp_password.encode()).hexdigest(),
            role=role,
            must_change_password=True
        )
        session.add(emp)
        session.commit()

    return HTMLResponse(content=f"""
    <html><body style="font-family:Arial; text-align:center; padding:50px;">
        {get_navbar(request)}
        <div style="background:white; padding:30px; border-radius:8px; max-width:450px; margin:40px auto;">
            <h2 style="color:#2ecc71;">Employee Created</h2>
            <p><strong>Name:</strong> {fullname} ({role})</p>
            <p><strong>Email:</strong> {email}</p>
            <p><strong>Temporary Password:</strong> <code style="background:#eee; padding:4px 8px;">{temp_password}</code></p>
            <a href="/admin" style="display:inline-block; margin-top:15px; background:#3498db; color:white; padding:10px 20px; text-decoration:none; border-radius:5px;">Back to Admin</a>
        </div>
        {FOOTER}
    </body></html>
    """)
