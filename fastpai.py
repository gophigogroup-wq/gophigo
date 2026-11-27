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
    database_url = database_url.replace("postgres://", "postgresql://", 1)
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
class Employee(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    fullname: str; email: str; password: str; role: str 
    must_change_password: bool = Field(default=True); reset_token: str | None = Field(default=None)

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
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
        <style>
            body { font-family: Poppins, sans-serif; margin: 0; background-color: #f4f4f4; }
            .store-header { text-align: center; padding: 20px; background: white; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
            .search-bar { max-width: 500px; margin: 15px auto 0; display: flex; gap: 10px; padding: 0 15px; }
            .search-bar input { flex: 1; padding: 12px; border: 1px solid #ccc; border-radius: 5px; font-size: 16px; }
            .search-bar button { background: #3498db; color: white; padding: 12px 25px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }
            .category-tabs { display: flex; justify-content: center; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
            .cat-btn { padding: 10px 20px; border-radius: 30px; text-decoration: none; font-weight: bold; font-size: 14px; transition: 0.2s; }
            .cat-btn.active { background: #2c3e50; color: white; }
            .cat-btn.inactive { background: white; color: #7f8c8d; border: 1px solid #ddd; }
            .book-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 15px; padding: 15px; max-width: 1200px; margin: auto; }
            .book-card { background: white; border-radius: 8px; padding: 15px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.08); display: flex; flex-direction: column; justify-content: space-between; transition: transform 0.2s; }
            .book-card:hover { transform: translateY(-5px); }
            .book-card img { width: 100%; height: 220px; object-fit: cover; border-radius: 4px; margin-bottom: 10px; }
            .book-title { color: #2c3e50; margin: 0 0 5px; font-size: 16px; font-weight: 600; line-height: 1.2; }
            .book-author { color: #7f8c8d; margin: 0 0 10px; font-size: 13px; }
            .btn-buy { display: block; width: 100%; padding: 10px; border-radius: 5px; text-decoration: none; font-weight: bold; color: white; margin-top: 5px; font-size: 14px; box-sizing: border-box; }
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
            <a href="/?category=Manual" class="cat-btn {'active' if category == 'Manual' else 'inactive'}">🏫 University Manuals</a>
            <a href="/?category=Law" class="cat-btn {'active' if category == 'Law' else 'inactive'}">⚖️ Laws & Manuals</a>
            <a href="/?category=Ticket" class="cat-btn {'active' if category == 'Ticket' else 'inactive'}">🎟️ Tickets</a>
            <a href="/?category=Media" class="cat-btn {'active' if category == 'Media' else 'inactive'}">🎬 Movies & Music</a>
            <a href="/?category=Newspaper" class="cat-btn {'active' if category == 'Newspaper' else 'inactive'}">📰 News & Articles</a>
            <a href="/?category=Religious" class="cat-btn {'active' if category == 'Religious' else 'inactive'}">🙏 Religious</a>
        </div>

        <div class="book-grid">
        """
        
        if not products:
            html += "<p style='text-align:center; grid-column:1/-1; color:#7f8c8d;'>No products found in this category.</p>"
            
        for p in products:
            author = session.get(Author, p.author_id)
            author_name = author.fullname if author else "Gophigo"
            
            reviews = session.exec(select(Review).where(Review.author_id == p.author_id)).all()
            avg = sum(r.rating for r in reviews)/len(reviews) if reviews else 0
            stars = "⭐" * int(round(avg)) if reviews else "No reviews yet"
            
            price_display = f"{p.price:,.0f}"
            
            if p.category == "Manual":
                extra_info = f"{p.institution} | {p.course_code}"
            elif p.category == "Law":
                extra_info = "⚖️ Law & Manual"
            elif p.category == "Newspaper":
                extra_info = "📰 News & Article"
            elif p.category == "Ticket":
                extra_info = "🎟️ Event Ticket"
            elif p.category == "Media":
                extra_info = "🎬 Media / Video"
            else:
                extra_info = p.category

            html += f"""
            <div class="book-card">
                <div>
                    <img src="{p.cover_image}" alt="{p.title}">
                    <h3 class="book-title">{p.title}</h3>
                    <p class="book-author">By {author_name}</p>
                    <p style="color:#f1c40f; margin:0 0 10px; font-size:14px;">{stars}</p>
                </div>
                <div>
                    <span style="background:#e0e0e0; padding:4px 10px; border-radius:20px; font-size:12px; font-weight:600; display:inline-block; margin-bottom:10px;">{extra_info}</span>
                    <a href="/checkout-product/{p.id}" class="btn-buy" style="background:#3498db;">Buy ({price_display} TZS)</a>
                </div>
            </div>
            """
            
        return html + f"</div>{FOOTER}</body></html>"
@app.get("/checkout-product/{product_id}", response_class=HTMLResponse)
def checkout_product(request: Request, product_id: int):
    try:
        customer_email = request.cookies.get("customer_email")
        if not customer_email: 
            return RedirectResponse(url=f"/customer-login?next=/checkout-product/{product_id}", status_code=303)
        
        with Session(engine) as session:
            p = session.get(Product, product_id)
            if not p:
                return HTMLResponse(content="<h1 style='text-align:center; padding:50px;'>Product not found in database.</h1><a href='/' style='display:block; text-align:center;'>Go back to Store</a>", status_code=404)
                
            author = session.get(Author, p.author_id)
            cover = p.cover_image if p.cover_image else "https://via.placeholder.com/180x250?text=No+Cover"
            price = p.price if p.price else 0
            
            pay_btn = f"""
            <form action="/pay-product/{p.id}" method="POST">
                <div style="margin-bottom: 15px; text-align: left;">
                    <label style="font-weight: bold;">Enter Mobile Money Number:</label><br>
                    <input type="text" name="phone" placeholder="e.g. 0754123456" required style="width: 100%; padding: 12px; border: 1px solid #ccc; border-radius: 5px; margin-top: 5px; font-size: 16px;">
                </div>
                <button type="submit" style="background:#3498db; color:white; padding:15px; border:none; border-radius:5px; display:block; width:100%; font-size:16px; font-weight:bold; cursor:pointer;">Pay {price:,.0f} TZS</button>
            </form>
            """
            
            return f"""
            <html><body style="font-family:Arial; background:#f4f4f4;">
                {get_navbar(request)}
                <div style="padding:50px;">
                    <div style="background:white; padding:40px; border-radius:8px; max-width:400px; margin:auto; text-align:center;">
                        <h2>Checkout</h2>
                        <img src="{cover}" style="width:180px; height:250px; object-fit:cover; margin:20px 0; border-radius: 5px;">
                        <h3>{p.title}</h3>
                        <p style="color:#7f8c8d; font-size:14px;">{p.category}</p>
                        <h4 style="color:#2ecc71;">{price:,.0f} TZS</h4>
                        {pay_btn}
                    </div>
                </div>
                {FOOTER}
            </body></html>
            """
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return HTMLResponse(content=f"<h1>Checkout Debug Error</h1><p>{str(e)}</p><pre style='background:#eee; padding:20px;'>{error_details}</pre>", status_code=500)        
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
            format_bought="p.category",
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
            return HTMLResponse(content=f"<h1>Connection Error</h1><p>{str(e)}</p>", status_code=500)@app.post("/review/{purchase_id}")
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

    # Dynamic form based on login status
    login_fields = ""
    if not is_logged_in:
        login_fields = f'''
            <input type="text" name="fullname" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Full Name">
            <input type="email" name="email" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Email">
            <input type="password" name="password" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Password">
        '''
    else:
        login_fields = f'''
            <input type="hidden" name="fullname" value="{author_name}">
            <input type="hidden" name="email" value="{author_email_val}">
            <div style="background:#e8f8f5; padding:10px; border-radius:5px; margin-bottom:15px; color:#2c3e50;">
                <strong>Logged in as:</strong> {author_name} ({author_email_val})
            </div>
        '''

    return f'''<html><body style="font-family:Arial; background:#f4f4f4;">
        {get_navbar(request)}
        <div style="padding:50px;">
            <div style="background:white; padding:30px; border-radius:8px; max-width:500px; margin:auto;">
                <h2 style="text-align:center;">Upload New Product</h2>
                <form action="/register" method="POST" enctype="multipart/form-data">
                    {login_fields}
                    
                    <input type="text" name="book_title" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Title of Product">
                    
                    <select name="category" id="categorySelect" required style="width:100%; padding:10px; margin:10px 0;">
                        <option value="Book">General Book</option>
                        <option value="Manual">University Manual / Lecture Notes</option>
                        <option value="Law">Laws, Regulations & Manuals</option>
                        <option value="Newspaper">Newspaper & Articles</option>
                        <option value="Ticket">Event Ticket / Football Match</option>
                        <option value="Media">Audio / Video / Movie</option>
                        <option value="Religious">Religious Book</option>
                    </select>

                    <div id="universityFields" style="display: none;">
                        <input type="text" name="institution" style="width:100%; padding:10px; margin:10px 0;" placeholder="University Name (e.g., CBE)">
                        <input type="text" name="course_code" style="width:100%; padding:10px; margin:10px 0;" placeholder="Course Code (e.g., BUS 101)">
                    </div>
                    
                    <input type="number" name="price" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Price (TZS)">
                    
                    <label style="font-size:14px; font-weight:bold;">Upload Cover Image:</label>
                    <input type="file" name="cover" accept="image/*" required style="width:100%; padding:10px; margin:10px 0;">
                    
                    <label id="fileLabel" style="font-size:14px; font-weight:bold;">Upload PDF / Document:</label>
                    <input type="file" id="fileInput" name="pdf_file" accept=".pdf" style="width:100%; padding:10px; margin:10px 0;">
                    
                    <div style="margin: 15px 0; display: flex; align-items: flex-start; gap: 10px;">
                        <input type="checkbox" name="agree_terms" value="yes" required style="margin-top: 5px; transform: scale(1.5);">
                        <label style="font-size: 14px; color: #555;">
                            I declare that I am the copyright owner of this work and I agree to the
                            <a href="/terms" target="_blank" style="color: #3498db;">Gophigo Terms & Conditions</a>.
                        </label>
                    </div>
                    
                    <button type="submit" style="background:#2ecc71; color:white; padding:12px; border:none; width:100%; border-radius:5px; font-size:16px; font-weight:bold; cursor:pointer;">Submit Product</button>
                </form>
            </div>
        </div>
        {FOOTER}
        
                <script>
            document.getElementById('categorySelect').addEventListener('change', function() {{
                var uniFields = document.getElementById('universityFields');
                var fileInput = document.getElementById('fileInput');
                var fileLabel = document.getElementById('fileLabel');
                
                if (this.value === 'Manual') {{
                    uniFields.style.display = 'block';
                }} else {{
                    uniFields.style.display = 'none';
                }}
                
                if (this.value === 'Media') {{
                    // Explicitly list extensions so Android OS opens the File Manager
                    fileInput.accept = ".mp3, .mp4, .wav, .m4a, .mov, audio/*, video/*";
                    fileLabel.innerText = "Upload Audio/Video File:";
                }} else {{
                    fileInput.accept = ".pdf, .doc, .docx";
                    fileLabel.innerText = "Upload PDF / Document:";
                }}
            }});
        </script>    
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

            f'''<html><body style="font-family:Arial; background:#f4f4f4;">
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
                        <h2 style='margin: 10px 0 0 0;'>{gophigo_revenue:,.2f} TZS</h2>
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
            '''
            
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
@app.get("/my-library", response_class=HTMLResponse)
def my_library(request: Request):
    try:
        customer_email = request.cookies.get("customer_email")
        if not customer_email:
            return RedirectResponse(url="/customer-login?next=/my-library", status_code=303)

        with Session(engine) as session:
            c = session.exec(select(Customer).where(Customer.email == customer_email)).first()
            if not c:
                return RedirectResponse(url="/customer-login?next=/my-library", status_code=303)

            raw_purchases = session.exec(select(Purchase).where(Purchase.customer_id == c.id, Purchase.status == "paid")).all()
            
            seen = set()
            purchases = []
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
            else:
                action = f"<a href='/read/{p.id}' style='background:#3498db; color:white; padding:10px; border-radius:5px; text-decoration:none; display:block; margin-bottom:5px; font-weight:bold;'>📖 Read / View</a>"            
                body += "</div>"

            return f'<html><body style="font-family:Arial; background:#f4f4f4; margin:0;">{get_navbar(request)}<h1 style="text-align:center; color:#2c3e50; padding:20px;">My Library</h1>{body}{FOOTER}</body></html>'
            
    except Exception as e:
        import traceback
        return HTMLResponse(content=f"<h1>Library Debug Error</h1><pre>{traceback.format_exc()}</pre>", status_code=500)

@app.get("/item/{product_code}")
def direct_item_link(request: Request, product_code: str):
    with Session(engine) as session:
        product = session.exec(select(Product).where(Product.product_code == product_code)).first()
        if not product:
            return HTMLResponse(content="<h1>Item not found</h1>", status_code=404)
            
        customer_email = request.cookies.get("customer_email")
        if not customer_email:
            return RedirectResponse(url=f"/customer-login?next=/checkout-product/{product.id}", status_code=303)
            
        return RedirectResponse(url=f"/checkout-product/{product.id}", status_code=303)
        
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
        p = session.get(Purchase, purchase_id)
        if not p:
            return HTMLResponse(content="<h1>Media not found.</h1>", status_code=404)
            
        # Get the media URL from the product or the purchase record
        media_url = p.pdf_file if p.pdf_file else ""
        
        # This checks if it's an audio file or video file
        is_audio = ".mp3" in media_url or ".wav" in media_url or ".m4a" in media_url
        
        if is_audio:
            player_html = f"<audio controls style='width: 100%; max-width: 600px; margin-top: 20px;'><source src='{media_url}' type='audio/mpeg'>Your browser does not support the audio element.</audio>"
        else:
            player_html = f"<video controls style='width: 100%; max-width: 800px; border-radius: 8px; margin-top: 20px;'><source src='{media_url}' type='video/mp4'>Your browser does not support the video tag.</video>"

        return f"""
        <html><body style="font-family:Arial; background:#f4f4f4;">
            {get_navbar(request)}
            <div style="padding:50px; text-align:center;">
                <h2 style="color:#2c3e50;">🎬 Now Playing: {p.book_title}</h2>
                <div style="background:white; padding:30px; border-radius:8px; max-width:900px; margin:auto; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                    {player_html}
                    <br><br>
                    <a href="/my-library" style="background:#3498db; color:white; padding:12px 25px; text-decoration:none; border-radius:5px; font-weight:bold;">← Back to Library</a>
                </div>
            </div>
            {FOOTER}
        </body></html>
        """
