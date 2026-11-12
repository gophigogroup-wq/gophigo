return f"""<html><body stylefrom fastapi import FastAPI, Form, Depends, HTTPException, status, Request, Response, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, Field, Session, create_engine, select
import hashlib, secrets, os, uuid, cloudinary, cloudinary.uploader
import requests

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
# -----------------------------
class Author(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    fullname: str; email: str; password: str; book_title: str
    ebook_price: float = Field(default=0.0); paperback_price: float = Field(default=0.0)
    book_format: str = Field(default="Ebook"); membership_status: str = "Pending" 
    book_status: str = Field(default="Pending Review"); reset_token: str | None = Field(default=None)
    cover_image: str | None = Field(default=None); pdf_file: str | None = Field(default=None) 
    is_read: bool = Field(default=False)

class Customer(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    fullname: str; email: str; password: str; reset_token: str | None = Field(default=None)

class Purchase(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    customer_id: int
    author_id: int
    book_title: str
    pdf_file: str | None = Field(default=None)
    format_bought: str = Field(default="Ebook")
    phone_number: str | None = Field(default=None)
    region: str | None = Field(default=None)
    shipping_address: str | None = Field(default=None)
    reference: str | None = Field(default=None, index=True)   # NEW
    status: str = Field(default="pending")                    # NEW: pending / paid / failed
class Employee(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    fullname: str; email: str; password: str; role: str 
    must_change_password: bool = Field(default=True); reset_token: str | None = Field(default=None)

class Review(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    author_id: int; customer_id: int; rating: int; comment: str

SQLModel.metadata.create_all(engine)

with Session(engine) as session:
    if not session.exec(select(Employee)).first():
        session.add(Employee(fullname="Reviewer John", email="reviewer@gophigo.com", password=hashlib.sha256("pass123".encode()).hexdigest(), role="Reviewer"))
        session.add(Employee(fullname="Supervisor Mary", email="supervisor@gophigo.com", password=hashlib.sha256("pass123".encode()).hexdigest(), role="Supervisor"))
        session.add(Employee(fullname="Approver Boss", email="approver@gophigo.com", password=hashlib.sha256("pass123".encode()).hexdigest(), role="Approver"))
        session.commit()

def get_navbar(request: Request):
    a = request.cookies.get("author_email"); c = request.cookies.get("customer_email")
    e = request.cookies.get("employee_email"); ad = request.cookies.get("admin_session")
    links = ''
    if a:
        links += '<a href="/author-dashboard" style="color: #f39c12; text-decoration: none; margin-left: 20px; font-weight: bold;">Author Dashboard</a><a href="/logout" style="color: #e74c3c; text-decoration: none; margin-left: 20px;">Logout</a>'
    elif c:
        links += '<a href="/my-library" style="color: #2ecc71; text-decoration: none; margin-left: 20px; font-weight: bold;">My Library</a><a href="/customer-logout" style="color: #e74c3c; text-decoration: none; margin-left: 20px;">Logout</a>'
    elif e:
        links += '<a href="/employee-dashboard" style="color: #f39c12; text-decoration: none; margin-left: 20px; font-weight: bold;">Staff Dashboard</a><a href="/employee-logout" style="color: #e74c3c; text-decoration: none; margin-left: 20px;">Logout</a>'
    elif ad:
        links += '<a href="/admin" style="color: #e74c3c; text-decoration: none; margin-left: 20px; font-weight: bold;">Admin Dashboard</a><a href="/admin-logout" style="color: #e74c3c; text-decoration: none; margin-left: 20px;">Logout</a>'
    else:
        links += '<a href="/author-portal" style="color: white; text-decoration: none; margin-left: 20px;">Author Portal</a><a href="/customer-login" style="color: white; text-decoration: none; margin-left: 20px;">Customer Login</a><a href="/employee-login" style="color: #f39c12; text-decoration: none; margin-left: 20px; font-weight: bold;">Staff Login</a>'
    return f'<nav style="background-color: #2c3e50; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; font-family: Poppins, sans-serif;"><div style="font-size: 24px; font-weight: bold;"><a href="/" style="color: white; text-decoration: none;">📚 Gophigo Bookstore</a></div><div>{links}</div></nav>'

FOOTER = '<footer style="background-color: #2c3e50; color: white; text-align: center; padding: 20px; margin-top: 50px; font-family: Arial;"><p>&copy; 2026 Gophigo Publishing. All rights reserved.</p></footer>'

@app.get("/", response_class=HTMLResponse)
        html = [
            '<html><head>',
            '<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">',
            '<style>',
            '  body { font-family: Poppins, sans-serif; }',
            '  .book-card { transition: 0.3s; }',
            '  .book-card:hover { transform: translateY(-8px); box-shadow: 0 12px 24px rgba(0,0,0,0.15) !important; }',
            '  .book-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; }',
            '</style>',
            '</head><body style="margin:0; background-color:#f4f4f4;">',
            get_navbar(request),
            '<div style="padding:40px; min-height:60vh;">',
            '<h1 style="text-align:center; color:#2c3e50;">Gophigo Bookstore</h1>',
            '<form action="/" method="GET" style="max-width:500px; margin:0 auto 40px; display:flex; gap:10px;">',
            f'<input type="text" name="search" placeholder="Search..." value="{search or ""}" style="flex:1; padding:12px; border:1px solid #ccc; border-radius:5px;">',
            '<button type="submit" style="background:#3498db; color:white; padding:12px 25px; border:none; border-radius:5px; cursor:pointer;">Search</button>',
            '</form>',
            '<div class="book-grid">'
        ]
        html = "".join(html)
        if not active_authors: 
            html += "<p style='text-align:center; grid-column:1/-1;'>No books found.</p>"
        
        for a in active_authors:
            reviews = session.exec(select(Review).where(Review.author_id == a.id)).all()
            avg = sum(r.rating for r in reviews)/len(reviews) if reviews else 0
            stars = "*" * int(round(avg)) if reviews else "No reviews yet"
            btns = ""
            if a.book_format in ["Ebook","Both"]: btns += f"<a href='/checkout/{a.id}?format=Ebook' style='background:#3498db; color:white; padding:10px; border-radius:5px; text-decoration:none; display:block; margin-bottom:5px; font-weight:bold;'>Buy Ebook ({a.ebook_price} TZS)</a>"
            if a.book_format in ["Paperback","Both"]: btns += f"<a href='/checkout/{a.id}?format=Paperback' style='background:#f39c12; color:white; padding:10px; border-radius:5px; text-decoration:none; display:block; font-weight:bold;'>Buy Paperback ({a.paperback_price} TZS)</a>"
            
            html += f"<div class='book-card' style='background:white; border-radius:8px; padding:15px; text-align:center; box-shadow:0 4px 12px rgba(0,0,0,0.1);'><img src='{a.cover_image}' style='width:100%; height:250px; object-fit:cover; border-radius:4px; margin-bottom:10px;'><h3 style='color:#2c3e50; margin:0 0 5px; font-size:18px;'>{a.book_title}</h3><p style='color:#7f8c8d; margin:0 0 5px; font-size:13px;'>By {a.fullname}</p><p style='color:#f1c40f; margin:0 0 10px; font-size:14px;'>{stars} ({len(reviews)})</p><span style='background:#e0e0e0; padding:4px 10px; border-radius:20px; font-size:12px; font-weight:600;'>{a.book_format}</span><br><br>{btns}</div>"
            
        return html + f"</div></div>{FOOTER}</body></html>"
@app.get("/checkout/{author_id}", response_class=HTMLResponse)
def checkout(request: Request, author_id: int, format: str = "Ebook"):
    customer_email = request.cookies.get("customer_email")
    if not customer_email: 
        return RedirectResponse(url=f"/customer-gateway?next=/checkout/{author_id}?format={format}", status_code=303)
    
    with Session(engine) as session:
        a = session.get(Author, author_id)
        price = a.ebook_price if format == "Ebook" else a.paperback_price
        
        if format == "Ebook":
            pay_btn = f'''
            <form action="/pay/{a.id}?format={format}" method="POST">
                <div style="margin-bottom: 15px; text-align: left;">
                    <label style="font-weight: bold;">Enter Mobile Money Number:</label><br>
                    <input type="text" name="phone" placeholder="e.g. 0754123456" required style="width: 100%; padding: 12px; border: 1px solid #ccc; border-radius: 5px; margin-top: 5px; font-size: 16px;">
                </div>
                <button type="submit" style="background:#3498db; color:white; padding:15px; border:none; border-radius:5px; display:block; width:100%; font-size:16px; font-weight:bold; cursor:pointer;">Pay {price} TZS</button>
            </form>
            '''
        else:
            pay_btn = f'<a href="/shipping-address/{a.id}" style="background:#f39c12; color:white; padding:15px; text-decoration:none; border-radius:5px; display:block; margin-top:20px;">Enter Shipping Address</a>'
            
        return f"""
        <html><body style="font-family:Arial; background:#f4f4f4;">
            {get_navbar(request)}
            <div style="padding:50px;">
                <div style="background:white; padding:40px; border-radius:8px; max-width:400px; margin:auto; text-align:center;">
                    <h2>Checkout - {format}</h2>
                    <img src="{a.cover_image}" style="width:180px; height:250px; object-fit:cover; margin:20px 0;">
                    <h3>{a.book_title}</h3>
                    <h4 style="color:#2ecc71;">{price} TZS</h4>
                    {pay_btn}
                </div>
            </div>
            {FOOTER}
        </body></html>
        """
        
@app.get("/shipping-address/{author_id}", response_class=HTMLResponse)
def shipping_address_form(request: Request, author_id: int):
    return f"""<html><body style="font-family:Arial; background:#f4f4f4;">{get_navbar(request)}<div style="padding:50px;"><div style="background:white; padding:30px; border-radius:8px; max-width:400px; margin:auto;"><h2>Shipping Details</h2><p>Where should we deliver your paperback?</p><form action="/calculate-shipping/{author_id}" method="POST"><label>Phone Number:</label><br><input type="text" name="phone" required style="width:100%; padding:10px; margin:10px 0;"><br><label>Region / City:</label><br><input type="text" name="region" required style="width:100%; padding:10px; margin:10px 0;"><br><label>Delivery Address:</label><br><textarea name="address" required style="width:100%; padding:10px; margin:10px 0;"></textarea><br><button type="submit" style="background:#2ecc71; color:white; padding:12px; border:none; width:100%; border-radius:5px;">Complete Order</button></form></div></div>{FOOTER}</body></html>"""

@app.post("/calculate-shipping/{author_id}", response_class=HTMLResponse)
def calculate_shipping(request: Request, author_id: int, phone: str = Form(...), region: str = Form(...), address: str = Form(...)):  
    with Session(engine) as session:
        a = session.get(Author, author_id)
        book_price = a.paperback_price
        shipping_fee = 15000.0  # Flat rate for Tanzania
        total_price = book_price + shipping_fee
        
        return f"""
        <html><body style="font-family:Arial; background:#f4f4f4;">
            {get_navbar(request)}
            <div style="padding:50px;">
                <div style="background:white; padding:40px; border-radius:8px; max-width:400px; margin:auto;">
                    <h2 style="text-align:center; color:#2c3e50;">Order Summary</h2>
                    <img src="{a.cover_image}" style="width:100px; height:150px; object-fit:cover; display:block; margin:0 auto 20px;">
                    
                    <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                        <span>Book Price:</span>
                        <strong>{book_price} TZS</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                        <span>Delivery Fee:</span>
                        <strong>{shipping_fee} TZS</strong>
                    </div>
                    <hr>
                    <div style="display:flex; justify-content:space-between; margin-bottom:20px; font-size:20px; color:#2ecc71;">
                        <span>Total:</span>
                        <strong>{total_price} TZS</strong>
                    </div>

                    <form action="/confirm-paperback/{author_id}" method="POST">
                        <input type="hidden" name="phone" value="{phone}">
                        <input type="hidden" name="region" value="{region}">
                        <input type="hidden" name="address" value="{address}">
                        <button type="submit" style="background:#3498db; color:white; padding:15px; border:none; width:100%; border-radius:5px; font-size:16px; font-weight:bold; cursor:pointer;">Confirm & Pay {total_price} TZS</button>
                    </form>
                </div>
            </div>
            {FOOTER}
        </body></html>
        """

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
                shipping_address=address
            ))
            session.commit()
            
    return f"<html><body style='font-family:Arial; background:#f4f4f4;'>{get_navbar(request)}<div style='text-align:center; padding:100px;'><h1 style='color:#2ecc71;'>Order Successful!</h1><p>Your paperback is being prepared for printing.</p><p>We will deliver it to: {address}, {region}.</p><a href='/my-library' style='background:#3498db; color:white; padding:12px 25px; text-decoration:none; border-radius:5px;'>Go to My Library</a></div>{FOOTER}</body></html>"
import uuid

@app.post("/pay/{author_id}")
def process_payment(request: Request, author_id: int, phone: str = Form(...), format: str = "Ebook"):
    customer_email = request.cookies.get("customer_email")
    if not customer_email:
        return RedirectResponse(url="/customer-login", status_code=303)
    if format == "Paperback":
        return RedirectResponse(url=f"/shipping-address/{author_id}", status_code=303)

    with Session(engine) as session:
        c = session.exec(select(Customer).where(Customer.email == customer_email)).first()
        a = session.get(Author, author_id)

        purchase_ref = str(uuid.uuid4())
        purchase = Purchase(
            customer_id=c.id, author_id=a.id, book_title=a.book_title,
            pdf_file=a.pdf_file, format_bought="Ebook",
            reference=purchase_ref, status="pending",
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
            "details": {
                "amount": int(a.ebook_price),
                "currency": "TZS",
                "description": f"Ebook: {a.book_title}",
            },
            "metadata": {"purchase_reference": purchase_ref},
        }

        try:
            response = requests.post("https://api.snippe.sh/v1/payments", json=payload, headers=headers)
            if response.status_code in (200, 201):
                data = response.json()
                payment_url = (
                    data.get("data", {}).get("checkout_url")
                    or data.get("data", {}).get("payment_url")
                )
                if payment_url:
                    return RedirectResponse(url=payment_url, status_code=303)

                return HTMLResponse(content=f"""
                <html><body style="font-family:Arial; text-align:center; padding:50px;">
                    <h1 style="color:#2ecc71;">Payment Prompt Sent!</h1>
                    <p>We have sent a payment request to <strong>{phone}</strong>.</p>
                    <p>Please check your phone and enter your mobile money PIN to complete the purchase.</p>
                    <p style="color:#7f8c8d;">Reference: {purchase_ref}</p>
                    <br>
                    <a href="/my-library" style="background:#3498db; color:white; padding:12px 25px; text-decoration:none; border-radius:5px;">I have paid - Go to My Library</a>
                </body></html>
                """, status_code=200)

            purchase.status = "failed"
            session.add(purchase)
            session.commit()
            return HTMLResponse(content=f"<h1>Snippe Error</h1><p>{response.text}</p>", status_code=400)

        except Exception as e:
            purchase.status = "failed"
            session.add(purchase)
            session.commit()
            return HTMLResponse(content=f"<h1>Connection Error</h1><p>{str(e)}</p>", status_code=500)            

@app.get("/review/{purchase_id}", response_class=HTMLResponse)
def review_page(request: Request, purchase_id: int):
    with Session(engine) as session:
        p = session.get(Purchase, purchase_id)
        return f"""<html><body style="font-family:Arial; background:#f4f4f4;">{get_navbar(request)}<div style="padding:50px;"><div style="background:white; padding:30px; border-radius:8px; max-width:400px; margin:auto; text-align:center;"><h2>Review: {p.book_title}</h2><form action="/review/{purchase_id}" method="POST"><label>Rating (1-5):</label><br><input type="number" name="rating" min="1" max="5" required style="width:100%; padding:10px; margin:10px 0;"><br><label>Comment:</label><br><textarea name="comment" required style="width:100%; padding:10px; margin:10px 0;"></textarea><br><button type="submit" style="background:#2ecc71; color:white; padding:12px; width:100%; border:none; border-radius:5px; cursor:pointer;">Submit Review</button></form></div></div>{FOOTER}</body></html>"""

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
    return f"""<html><head><link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;700&display=swap" rel="stylesheet"><style>body{{font-family:Poppins; margin:0;}} .hero{{background:linear-gradient(135deg,#1a252f,#2c3e50); color:white; padding:100px 20px; text-align:center;}} .btn{{padding:15px 30px; border-radius:5px; text-decoration:none; font-weight:bold; display:inline-block; margin:10px;}}</style></head><body>{get_navbar(request)}<div class="hero"><h1 style="font-size:48px;">Become a Gophigo Author</h1><p style="font-size:20px;">The global marketplace where authors keep 50% of their sales.</p><a href="/register" class="btn" style="background:#3498db; color:white;">✍️ Register</a><a href="/login" class="btn" style="background:#2ecc71; color:white;">Author Login</a></div>{FOOTER}</body></html>"""

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return f"""
    <html><body style="font-family:Arial; background:#f4f4f4;">
        {get_navbar(request)}
        <div style="padding:50px;">
            <div style="background:white; padding:30px; border-radius:8px; max-width:500px; margin:auto;">
                <h2 style="text-align:center;">Author Registration</h2>
                <form action="/register" method="POST" enctype="multipart/form-data">
                    <input type="text" name="fullname" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Name">
                    <input type="email" name="email" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Email">
                    <input type="password" name="password" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Password">
                    <input type="text" name="book_title" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Book Title">
                    <select name="book_format" style="width:100%; padding:10px; margin:10px 0;">
                        <option value="Ebook">Ebook</option>
                        <option value="Paperback">Paperback</option>
                        <option value="Both">Both</option>
                    </select>
                    <input type="number" name="ebook_price" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Ebook Price">
                    <input type="number" name="paperback_price" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Paperback Price">
                    <input type="file" name="cover" accept="image/*" required style="width:100%; padding:10px; margin:10px 0;">
                    <input type="file" name="pdf_file" accept=".pdf" style="width:100%; padding:10px; margin:10px 0;">
                    <div style="margin: 15px 0; display: flex; align-items: flex-start; gap: 10px;">
                        <input type="checkbox" name="agree_terms" value="yes" required style="margin-top: 5px; transform: scale(1.5);">
                        <label style="font-size: 14px; color: #555;">
                            I declare that I am the copyright owner of this book and I agree to the
                            <a href="/terms" target="_blank" style="color: #3498db;">Gophigo Author Terms & Conditions</a>,
                            including the indemnification clause.
                        </label>
                    </div>
                    <button type="submit" style="background:#2ecc71; color:white; padding:12px; border:none; width:100%; border-radius:5px; font-size:16px; font-weight:bold; cursor:pointer;">Submit Registration</button>
                </form>
            </div>
        </div>
        {FOOTER}
    </body></html>
    """
    @app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return f"""<html><body style="font-family:Arial; background:#f4f4f4;">{get_navbar(request)}<div style="padding:50px;"><div style="background:white; padding:30px; border-radius:8px; max-width:400px; margin:auto;"><h2 style="text-align:center;">Author Login</h2><form action="/login" method="POST"><input type="email" name="email" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Email"><input type="password" name="password" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Password"><button type="submit" style="background:#3498db; color:white; padding:12px; border:none; width:100%; border-radius:5px;">Login</button></form><div style="text-align:center; margin-top:15px;"><a href="/forgot-password">Forgot Password?</a></div></div></div>{FOOTER}</body></html>"""

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
        sales = session.exec(select(Purchase).where(Purchase.author_id == author.id)).all()
        total = sum(
            author.ebook_price * 0.5 if s.format_bought == "Ebook"
            else author.paperback_price * 0.5
            for s in sales
        )

        if author.membership_status == "Pending":
            pay_html = """
            <div style="background:#fff3cd; padding:20px; border-radius:8px;">
                <h3>Membership Payment Required</h3>
                <a href="/pay-membership" style="background:#2ecc71; color:white; padding:10px 20px; text-decoration:none; border-radius:5px;">Pay 20,000 TZS</a>
            </div>
            """
        else:
            pay_html = f"""
            <div style="background:#d4edda; padding:20px; border-radius:8px;">
                <h3>Active</h3>
                <h4>Earnings: {total} TZS</h4>
            </div>
            <div style="background:#fff3cd; padding:20px; margin-top:10px;">
                <h4>Book: {author.book_status}</h4>
            </div>
            """

        return f"""
        <html><body style="font-family:Arial; background:#f4f4f4;">
            {get_navbar(request)}
            <div style="padding:50px; text-align:center;">
                <h2>Welcome, {author.fullname}!</h2>
                <div style="background:white; padding:30px; border-radius:8px; max-width:500px; margin:auto;">
                    <img src="{author.cover_image}" style="width:150px; height:200px; object-fit:cover; border-radius:4px;">
                    <h3>{author.book_title}</h3>
                    <p>{author.book_format} | {author.ebook_price} TZS</p>
                    {pay_html}
                </div>
            </div>
            {FOOTER}
        </body></html>
        """@app.get("/pay-membership")
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
    return f"""<html><body style="font-family:Arial; background:#f4f4f4;">{get_navbar(request)}<div style="padding:50px;"><div style="background:white; padding:40px; border-radius:8px; max-width:400px; margin:auto; text-align:center;"><h2>Before you buy...</h2><a href="/customer-login?next={next}" style="background:#3498db; color:white; padding:12px; text-decoration:none; border-radius:5px; display:block; margin-bottom:15px;">Login</a><a href="/customer-register?next={next}" style="background:#2ecc71; color:white; padding:12px; text-decoration:none; border-radius:5px; display:block;">Register</a></div></div>{FOOTER}</body></html>"""

@app.get("/customer-login", response_class=HTMLResponse)
def customer_login_page(request: Request, next: str = "/"):
    return f"""<html><body style="font-family:Arial; background:#f4f4f4;">{get_navbar(request)}<div style="padding:50px;"><div style="background:white; padding:30px; border-radius:8px; max-width:400px; margin:auto;"><h2>Customer Login</h2><form action="/customer-login?next={next}" method="POST"><input type="email" name="email" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Email"><input type="password" name="password" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Password"><button type="submit" style="background:#2ecc71; color:white; padding:12px; border:none; width:100%; border-radius:5px;">Login</button></form><p style="text-align:center; margin-top:15px;"><a href="/customer-register?next={next}">Register here</a></p><p style="text-align:center;"><a href="/forgot-password" style="color:#e74c3c;">Forgot Password?</a></p></div></div>{FOOTER}</body></html>"""

@app.post("/customer-login")
def process_customer_login(response: Response, email: str = Form(...), password: str = Form(...), next: str = Form("/")):
    with Session(engine) as session:
        c = session.exec(select(Customer).where(Customer.email == email, Customer.password == hashlib.sha256(password.encode()).hexdigest())).first()
        if c:
            res = RedirectResponse(url=next, status_code=303); res.set_cookie(key="customer_email", value=c.email, httponly=True); return res
    return HTMLResponse(content=f"<h1>Login Failed. <a href='/customer-login?next={next}'>Try again</a></h1>{FOOTER}", status_code=401)

@app.get("/customer-register", response_class=HTMLResponse)
def customer_register_page(request: Request, next: str = "/"):
    return f"""
    <html><body style="font-family:Arial; background:#f4f4f4;">
        {get_navbar(request)}
        <div style="padding:50px;">
            <div style="background:white; padding:30px; border-radius:8px; max-width:400px; margin:auto;">
                <h2 style="text-align:center;">Create Account</h2>
                <form action="/customer-register?next={next}" method="POST">
                    <label>Full Name:</label><br>
                    <input type="text" name="fullname" required style="width:100%; padding:10px; margin:10px 0;"><br>
                    <label>Email:</label><br>
                    <input type="email" name="email" required style="width:100%; padding:10px; margin:10px 0;"><br>
                    <label>Password:</label><br>
                    <input type="password" name="password" required style="width:100%; padding:10px; margin:10px 0;"><br>
                    <button type="submit" style="background:#2ecc71; color:white; padding:12px; border:none; width:100%; border-radius:5px;">Register</button>
                </form>
            </div>
        </div>
        {FOOTER}
    </body></html>
    """
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
    return f"""<html><body style="font-family:Arial; background:#f4f4f4;">{get_navbar(request)}<div style="padding:50px;"><div style="background:white; padding:30px; border-radius:8px; max-width:400px; margin:auto;"><h2 style="color:#f39c12; text-align:center;">Staff Login</h2><form action="/employee-login" method="POST"><input type="email" name="email" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Email"><input type="password" name="password" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Password"><button type="submit" style="background:#f39c12; color:white; padding:12px; border:none; width:100%; border-radius:5px;">Login</button></form><p style="text-align:center; margin-top:15px;"><a href="/forgot-password" style="color:#e74c3c;">Forgot Password?</a></p><p style="text-align:center;"><a href="/admin-login">Admin Login</a></p></div></div>{FOOTER}</body></html>"""

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
    return f"""<html><body style="font-family:Arial; background:#f4f4f4;">{get_navbar(request)}<div style="padding:50px;"><div style="background:white; padding:30px; border-radius:8px; max-width:400px; margin:auto;"><h2 style="text-align:center; color:#e74c3c;">Change Password</h2><form action="/employee-change-password" method="POST"><input type="password" name="new_password" required style="width:100%; padding:10px; margin:10px 0;" placeholder="New Password"><button type="submit" style="background:#e74c3c; color:white; padding:12px; border:none; width:100%; border-radius:5px;">Update</button></form></div></div>{FOOTER}</body></html>"""

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
        
        html = f"""<html><body style="font-family:Arial; background:#f4f4f4;">{get_navbar(request)}<div style="padding:50px;"><div style="display:flex; justify-content:space-between;"><h1>{e.role} Dashboard</h1><a href="/employee-logout" style="background:#e74c3c; color:white; padding:10px 20px; text-decoration:none; border-radius:5px; height:fit-content;">Sign Out</a></div><p>Welcome, <strong>{e.fullname}</strong>.</p><table border="1" style="width:100%; background:white; border-collapse:collapse;"><tr style="background:#f39c12; color:white;"><th>ID</th><th>Cover</th><th>Book</th><th>Status</th><th>Read</th><th>Action</th></tr>"""
        
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
        return f"""<html><body style="margin:0; height:100vh; display:flex; flex-direction:column;"><div style="background:#1a252f; color:white; padding:15px; text-align:center; display:flex; justify-content:space-between;"><h3 style="margin:0;">Staff Review - {a.book_title}</h3><a href="/employee-dashboard" style="color:#f39c12; text-decoration:none; font-weight:bold;">← Back</a></div><iframe src="https://docs.google.com/viewer?url={a.pdf_file}&embedded=true" style="flex:1; border:none; width:100%; height:100vh;"></iframe></body></html>"""

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
    return f"""<html><body style="font-family:Arial; background:#f4f4f4;">{get_navbar(request)}<div style="padding:50px;"><div style="background:white; padding:30px; border-radius:8px; max-width:400px; margin:auto;"><h2 style="text-align:center;">Reset Password</h2><form action="/forgot-password" method="POST"><input type="email" name="email" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Email"><button type="submit" style="background:#e74c3c; color:white; padding:12px; border:none; width:100%; border-radius:5px;">Generate Reset Link</button></form></div></div>{FOOTER}</body></html>"""

@app.post("/forgot-password", response_class=HTMLResponse)
def process_forgot_password(request: Request, email: str = Form(...)):
    token = secrets.token_hex(16); found = False; link = ""
    with Session(engine) as session:
        a = session.exec(select(Author).where(Author.email == email)).first()
        if a: a.reset_token = token; session.add(a); session.commit(); found = True; link = f"/reset-password?token={token}&type=author"
        e = session.exec(select(Employee).where(Employee.email == email)).first()
        if e: e.reset_token = token; session.add(e); session.commit(); found = True; link = f"/reset-password?token={token}&type=employee"
    if found: return f"<html><body style='text-align:center; padding:50px;'>{get_navbar(request)}<h2 style='color:green;'>Simulated Email Sent</h2><a href='{link}' style='background:#3498db; color:white; padding:12px; text-decoration:none; border-radius:5px;'>Click to Reset</a>{FOOTER}</body></html>"
    return HTMLResponse(content=f"<h1>Email not found. <a href='/forgot-password'>Try again</a></h1>{FOOTER}", status_code=404)

@app.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(request: Request, token: str, type: str = "author"):
    return f"""<html><body style="font-family:Arial; background:#f4f4f4;">{get_navbar(request)}<div style="padding:50px;"><div style="background:white; padding:30px; border-radius:8px; max-width:400px; margin:auto;"><h2>New Password</h2><form action="/reset-password" method="POST"><input type="hidden" name="token" value="{token}"><input type="hidden" name="type" value="{type}"><input type="password" name="new_password" required style="width:100%; padding:10px; margin:10px 0;"><button type="submit" style="background:#2ecc71; color:white; padding:12px; border:none; width:100%; border-radius:5px;">Update</button></form></div></div>{FOOTER}</body></html>"""

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
    if success: return f"<html><body style='text-align:center; padding:50px;'><h1 style='color:green;'>Password Updated!</h1><a href='/login'>Login</a></body></html>"
    return HTMLResponse(content=f"<h1>Invalid token. <a href='/forgot-password'>Try again</a></h1>{FOOTER}", status_code=400)

@app.get("/admin-login", response_class=HTMLResponse)
def admin_login_page(request: Request):
    return f"""<html><body style="font-family:Arial; background:#f4f4f4;">{get_navbar(request)}<div style="padding:50px;"><div style="background:white; padding:30px; border-radius:8px; max-width:400px; margin:auto;"><h2 style="color:#e74c3c; text-align:center;">Admin Login</h2><form action="/admin-login" method="POST"><input type="text" name="username" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Username"><input type="password" name="password" required style="width:100%; padding:10px; margin:10px 0;" placeholder="Password"><button type="submit" style="background:#e74c3c; color:white; padding:12px; border:none; width:100%; border-radius:5px;">Login</button></form></div></div>{FOOTER}</body></html>"""

@app.post("/admin-login")
def admin_login(response: Response, username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "gophigo2026":
        res = RedirectResponse(url="/admin", status_code=303); res.set_cookie(key="admin_session", value="true", httponly=True); return res
    return HTMLResponse(content=f"<h1>Invalid Credentials. <a href='/admin-login'>Try again</a></h1>{FOOTER}", status_code=401)

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    if request.cookies.get("admin_session") != "true": return RedirectResponse(url="/admin-login", status_code=303)
    with Session(engine) as session:
        authors = session.exec(select(Author)).all(); purchases = session.exec(select(Purchase)).all()
        rev = sum((session.get(Author, p.author_id).ebook_price if p.format_bought == "Ebook" else session.get(Author, p.author_id).paperback_price) * 0.5 for p in purchases)
        
        html = f"""<html><body style="font-family:Arial; background:#f4f4f4;">{get_navbar(request)}<div style="padding:50px;"><h1>Admin Dashboard</h1><div style="background:#2c3e50; color:white; padding:20px; border-radius:8px;"><h3>Sales: {len(purchases)} | Revenue (50%): {rev} TZS</h3></div><table border="1" style="width:100%; background:white; margin-top:20px;"><tr style="background:#34495e; color:white;"><th>ID</th><th>Name</th><th>Book</th><th>Format</th><th>Status</th><th>Action</th></tr>"""
        
        for a in authors:
            btn = f"<a href='/admin-confirm-delete/{a.id}' style='background:#e74c3c; color:white; padding:5px 10px; text-decoration:none; border-radius:3px;'>Confirm Delete</a>" if a.book_status == "Pending Deletion" else ""
            html += f"<tr><td>{a.id}</td><td>{a.fullname}</td><td>{a.book_title}</td><td>{a.book_format}</td><td>{a.book_status}</td><td>{btn}</td></tr>"
            
        html += f"</table><h3 style='margin-top:40px;'>📦 Paperback Shipping Orders</h3><table border='1' style='width:100%; background:white;'><tr style='background:#f39c12; color:white;'><th>Book</th><th>Phone</th><th>Region</th><th>Address</th></tr>"
        for p in purchases:
            if p.format_bought == "Paperback":
                html += f"<tr><td>{p.book_title}</td><td>{p.phone_number}</td><td>{p.region}</td><td>{p.shipping_address}</td></tr>"
                
        return html + f"</table></div>{FOOTER}</body></html>"

@app.get("/admin-confirm-delete/{author_id}")
def admin_confirm_delete(author_id: int):
    with Session(engine) as session:
        a = session.get(Author, author_id); session.delete(a); session.commit()
    return RedirectResponse(url="/admin", status_code=303)

@app.get("/admin-logout")
def admin_logout():
    res = RedirectResponse(url="/admin-login", status_code=303); res.delete_cookie("admin_session"); return res
@app.get("/terms", response_class=HTMLResponse)
def terms_page(request: Request):
    return f"""
    <html><body style="font-family:Arial; background:#f4f4f4; margin:0;">
        {get_navbar(request)}
        <div style="padding: 50px; max-width: 800px; margin: auto; background: white; border-radius: 8px; margin-top: 40px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
            <h1 style="color: #2c3e50; text-align: center;">Gophigo Author Terms & Conditions</h1>
            <hr style="border: 1px solid #eee; margin: 20px 0;">
            
            <h3 style="color: #e74c3c;">1. Platform Role</h3>
            <p>Gophigo Publishing operates as a digital marketplace and distribution platform. Gophigo is not the publisher, creator, or owner of the books uploaded by authors.</p>
            
            <h3 style="color: #e74c3c;">2. Author Responsibility</h3>
            <p>By uploading a manuscript, the Author declares that they are the sole creator and copyright owner of the work, or have obtained all necessary legal rights and permissions to distribute the work.</p>
            
            <h3 style="color: #e74c3c;">3. Prohibited Content</h3>
            <p>Authors are strictly prohibited from uploading any material that is illegal, defamatory, infringing on copyright, plagiarized, or pornographic.</p>
            
            <h3 style="color: #e74c3c;">4. Indemnification (Liability)</h3>
            <p>The Author agrees to fully indemnify and hold harmless Gophigo Publishing, its founders, and employees from any and all legal claims, damages, or expenses (including legal fees) arising from the Author's uploaded content. <strong>Gophigo will not be held responsible for any copyright disputes, legal actions, or damages resulting from the Author's actions.</strong> If a copyright claim is made against Gophigo due to an Author's book, Gophigo reserves the right to immediately remove the book and deduct any legal costs from the Author's pending royalties.</p>
            
            <h3 style="color: #e74c3c;">5. Royalties and Fees</h3>
            <p>Gophigo will retain a 50% commission on all net sales. The remaining 50% will be credited to the Author's dashboard. Gophigo reserves the right to adjust this fee structure with 30 days' notice to the Author.</p>
            
            <h3 style="color: #e74c3c;">6. Account Termination</h3>
            <p>Gophigo reserves the right to suspend or permanently ban any Author and delete their books if they violate these terms, without refunding the annual membership fee.</p>
            
            <h3 style="color: #e74c3c;">7. Governing Law</h3>
            <p>These terms are governed by the laws of the United Republic of Tanzania.</p>
            
            <br>
            <p style="text-align: center; color: #7f8c8d; font-size: 14px;">Last updated: November 2026</p>
            <div style="text-align: center; margin-top: 20px;">
                <a href="/register" style="background: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Back to Registration</a>
            </div>
        </div>
        {FOOTER}
    </body></html>
    """
@app.post("/register", response_class=HTMLResponse)
def process_registration(
    request: Request,
    fullname: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    book_title: str = Form(...),
    book_format: str = Form(...),
    ebook_price: float = Form(...),
    paperback_price: float = Form(...),
    agree_terms: str = Form(None),          # NEW
    cover: UploadFile = File(...),
    pdf_file: UploadFile = File(None),
):
    # 1. Terms check FIRST — before any Cloudinary upload
    if not agree_terms:
        return HTMLResponse(
            content="<h1>Error</h1><p>You must agree to the Terms and Conditions to register.</p>",
            status_code=400,
        )

    cover_url = cloudinary.uploader.upload(
        cover.file, folder="gophigo_covers", resource_type="image"
    ).get("secure_url")

    pdf_url = None
    if pdf_file and pdf_file.filename:
        pdf_url = cloudinary.uploader.upload(
            pdf_file.file, folder="gophigo_pdfs",
            resource_type="raw", access_mode="public"
        ).get("secure_url")

    new_author = Author(
        fullname=fullname, email=email,
        password=hashlib.sha256(password.encode()).hexdigest(),
        book_title=book_title, book_format=book_format,
        ebook_price=ebook_price, paperback_price=paperback_price,
        cover_image=cover_url, pdf_file=pdf_url,
    )
    with Session(engine) as session:
        session.add(new_author)
        session.commit()

    return f"""
    <html><body style="font-family:Arial; background:#f4f4f4;">
        {get_navbar(request)}
        <div style="text-align:center; padding:100px;">
            <h1 style="color:#2ecc71;">Registration Successful!</h1>
            <a href="/login">Go to Login</a>
        </div>
        {FOOTER}
    </body></html>
    """
@app.get("/my-library", response_class=HTMLResponse)
def my_library(request: Request):
    customer_email = request.cookies.get("customer_email")
    if not customer_email:
        return RedirectResponse(url="/customer-login?next=/my-library", status_code=303)

    with Session(engine) as session:
        c = session.exec(select(Customer).where(Customer.email == customer_email)).first()
        if not c:
            return RedirectResponse(url="/customer-login?next=/my-library", status_code=303)

        # Show only PAID purchases — pending/failed must not unlock the book
        purchases = session.exec(
            select(Purchase).where(
                Purchase.customer_id == c.id,
                Purchase.status == "paid",
            )
        ).all()

        if not purchases:
            body = """
            <div style="text-align:center; padding:60px;">
                <h2>Your library is empty</h2>
                <p>Books you buy will appear here once payment is confirmed.</p>
                <a href="/" style="background:#3498db; color:white; padding:12px 25px; text-decoration:none; border-radius:5px;">Browse the Store</a>
            </div>
            """
        else:
            body = '<div style="display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:20px; padding:40px;">'
            for p in purchases:
                author = session.get(Author, p.author_id)
                cover = author.cover_image if author else ""
                if p.format_bought == "Ebook":
                    action = (
                        f"<a href='/read/{p.id}' style='background:#3498db; color:white; "
                        f"padding:10px; border-radius:5px; text-decoration:none; "
                        f"display:block; margin-bottom:5px; font-weight:bold;'>📖 Read</a>"
                    )
                else:
                    action = "<span style='display:block; padding:10px; color:#7f8c8d;'>📦 Shipping</span>"
                body += f"""
                <div style="background:white; border-radius:8px; padding:15px; text-align:center; box-shadow:0 4px 12px rgba(0,0,0,0.1);">
                    <img src="{cover}" style="width:100%; height:220px; object-fit:cover; border-radius:4px; margin-bottom:10px;">
                    <h3 style="margin:0 0 5px; font-size:16px;">{p.book_title}</h3>
                    <p style="color:#7f8c8d; font-size:13px; margin:0 0 10px;">{p.format_bought}</p>
                    {action}
                    <a href="/review/{p.id}" style="color:#f39c12; text-decoration:none; font-size:13px;">Leave a review</a>
                </div>
                """
            body += "</div>"

        return f"""
        <html><body style="font-family:Arial; background:#f4f4f4; margin:0;">
            {get_navbar(request)}
            <h1 style="text-align:center; color:#2c3e50; padding:20px;">My Library</h1>
            {body}
            {FOOTER}
        </body></html>
        """  
