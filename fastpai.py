from fastapi import FastAPI, Form, Depends, HTTPException, status, Request, Response, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, Field, Session, create_engine, select
import hashlib
import secrets
import os
import uuid
import cloudinary
import cloudinary.uploader

app = FastAPI()

# --- 1. CLOUDINARY SETUP ---
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

# --- 2. DATABASE SETUP ---
database_url = os.environ.get("DATABASE_URL")
if database_url:
    database_url = database_url.replace("postgres://", "postgresql://", 1)
    sqlite_url = database_url
else:
    sqlite_file_name = "gophigo.db"
    sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url)

class Author(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    fullname: str
    email: str
    password: str
    book_title: str
    price: float = Field(default=0.0)
    membership_status: str = "Pending" 
    book_status: str = Field(default="Pending Review") 
    reset_token: str | None = Field(default=None)
    cover_image: str | None = Field(default=None) 
    pdf_file: str | None = Field(default=None) 

class Customer(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    fullname: str
    email: str
    password: str

class Purchase(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    customer_id: int
    author_id: int
    book_title: str
    pdf_file: str

SQLModel.metadata.create_all(engine)

# --- 3. SHARED DESIGN (NAVBAR & FOOTER) ---
NAVBAR = """
<nav style="background-color: #2c3e50; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; font-family: Arial; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
    <div style="font-size: 24px; font-weight: bold;">
        <a href="/" style="color: white; text-decoration: none;">📚 Gophigo</a>
    </div>
    <div>
        <a href="/store" style="color: white; text-decoration: none; margin-left: 20px; font-size: 16px;">Bookstore</a>
        <a href="/login" style="color: white; text-decoration: none; margin-left: 20px; font-size: 16px;">Author Login</a>
        <a href="/customer-login" style="color: white; text-decoration: none; margin-left: 20px; font-size: 16px;">Customer Login</a>
        <a href="/admin-login" style="color: #e74c3c; text-decoration: none; margin-left: 20px; font-size: 16px; font-weight: bold;">Admin Login</a>
    </div>
</nav>
"""

FOOTER = """
<footer style="background-color: #2c3e50; color: white; text-align: center; padding: 20px; margin-top: 50px; font-family: Arial; font-size: 14px;">
    <p>&copy; 2026 Gophigo Publishing. All rights reserved.</p>
    <p>Empowering Authors Globally.</p>
</footer>
"""

# --- 4. THE WEB PAGES ---

@app.get("/", response_class=HTMLResponse)
def home():
    return f"""
    <html>
        <body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
            {NAVBAR}
            <div style="text-align: center; padding: 100px 20px; min-height: 60vh;">
                <h1 style="color: #2c3e50; font-size: 40px; margin-bottom: 10px;">Welcome to Gophigo Publishing Portal</h1>
                <p style="font-size: 20px; color: #555; margin-bottom: 40px;">The global marketplace for authors to sell their books.</p>
                <a href="/store" style="background-color: #f39c12; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-size: 18px; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">📚 Visit Public Bookstore</a>
                <br><br>
                <a href="/register" style="background-color: #3498db; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-size: 18px; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">Register as an Author</a>
            </div>
            {FOOTER}
        </body>
    </html>
    """

@app.get("/register", response_class=HTMLResponse)
def register_page():
    return f"""
    <html>
        <body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
            {NAVBAR}
            <div style="padding: 50px; min-height: 60vh;">
                <div style="background: white; padding: 30px; border-radius: 8px; max-width: 400px; margin: auto; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                    <h2 style="text-align: center; color: #2c3e50;">Author Registration</h2>
                    <form action="/register" method="POST" enctype="multipart/form-data">
                        <label>Full Name:</label><br><input type="text" name="fullname" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                        <label>Email Address:</label><br><input type="email" name="email" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                        <label>Password:</label><br><input type="password" name="password" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                        <label>Book Title:</label><br><input type="text" name="book_title" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                        <label>Book Price (TZS):</label><br><input type="number" name="price" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                        <label>Book Cover Image:</label><br><input type="file" name="cover" accept="image/*" required style="width: 100%; padding: 10px; margin: 10px 0;"><br>
                        <label>Manuscript (PDF):</label><br><input type="file" name="pdf_file" accept=".pdf" required style="width: 100%; padding: 10px; margin: 10px 0;"><br>
                        <button type="submit" style="background-color: #2ecc71; color: white; padding: 12px; border: none; width: 100%; margin-top: 15px; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;">Submit</button>
                    </form>
                </div>
            </div>
            {FOOTER}
        </body>
    </html>
    """

@app.post("/register", response_class=HTMLResponse)
def process_registration(fullname: str = Form(...), email: str = Form(...), password: str = Form(...), book_title: str = Form(...), price: float = Form(...), cover: UploadFile = File(...), pdf_file: UploadFile = File(...)):
    cover_result = cloudinary.uploader.upload(cover.file, folder="gophigo_covers", resource_type="image")
    cover_url = cover_result.get("secure_url")

    pdf_result = cloudinary.uploader.upload(pdf_file.file, folder="gophigo_pdfs", resource_type="raw", access_mode="public")
    pdf_url = pdf_result.get("secure_url")

    scrambled_password = hashlib.sha256(password.encode()).hexdigest()
    new_author = Author(fullname=fullname, email=email, password=scrambled_password, book_title=book_title, price=price, cover_image=cover_url, pdf_file=pdf_url)
    
    with Session(engine) as session:
        session.add(new_author)
        session.commit()
    
    return f"""
    <html>
        <body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
            {NAVBAR}
            <div style="text-align: center; padding: 100px 20px; min-height: 60vh;">
                <h1 style="color: #2ecc71;">Registration Successful!</h1>
                <p style="font-size: 18px;">Thank you, <strong>{fullname}</strong>. Your book is pending review.</p>
                <a href="/login" style="background-color: #3498db; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-size: 16px;">Go to Login</a>
            </div>
            {FOOTER}
        </body>
    </html>
    """

@app.get("/store", response_class=HTMLResponse)
def store():
    with Session(engine) as session:
        active_authors = session.exec(select(Author).where(Author.membership_status == "Active", Author.book_status == "Approved")).all()
        
        html = f"""
        <html>
            <body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
                {NAVBAR}
                <div style="padding: 50px; min-height: 60vh;">
                    <h1 style="text-align: center; color: #2c3e50; margin-bottom: 40px;">📚 Gophigo Bookstore</h1>
                    <div style='display: flex; flex-wrap: wrap; gap: 30px; justify-content: center;'>
        """
        
        if not active_authors:
            html += "<p style='text-align: center; font-size: 18px; color: #7f8c8d;'>No books available yet. Check back later!</p>"
            
        for author in active_authors:
            html += f"""
            <div style='background: white; border-radius: 8px; padding: 20px; width: 250px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center; transition: transform 0.2s;'>
                <img src="{author.cover_image}" alt="Book Cover" style="width: 100%; height: 300px; object-fit: cover; border-radius: 4px; margin-bottom: 15px; border: 1px solid #eee;">
                <h3 style='color: #2c3e50; margin: 0 0 5px 0; font-size: 20px;'>{author.book_title}</h3>
                <p style='color: #7f8c8d; margin: 0 0 15px 0; font-size: 14px;'>By {author.fullname}</p>
                <h4 style='color: #2ecc71; margin: 0 0 15px 0; font-size: 18px;'>{author.price} TZS</h4>
                <form action="/checkout/{author.id}" method="GET" style="margin: 0;">
                    <button type="submit" style="background-color: #3498db; color: white; padding: 12px; border: none; border-radius: 5px; width: 100%; cursor: pointer; font-size: 16px; font-weight: bold;">Buy Now</button>
                </form>
            </div>
            """
            
        html += f"""
                    </div>
                </div>
                {FOOTER}
            </body>
        </html>
        """
        return html

# --- 5. CUSTOMER LOGIN & PURCHASING ---
@app.get("/customer-register", response_class=HTMLResponse)
def customer_register_page():
    return f"""
    <html>
        <body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
            {NAVBAR}
            <div style="padding: 50px; min-height: 60vh;">
                <div style="background: white; padding: 30px; border-radius: 8px; max-width: 400px; margin: auto; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                    <h2 style="text-align: center; color: #2c3e50;">Create Customer Account</h2>
                    <form action="/customer-register" method="POST">
                        <label>Full Name:</label><br><input type="text" name="fullname" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                        <label>Email Address:</label><br><input type="email" name="email" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                        <label>Password:</label><br><input type="password" name="password" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                        <button type="submit" style="background-color: #2ecc71; color: white; padding: 12px; border: none; width: 100%; margin-top: 15px; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;">Register</button>
                    </form>
                </div>
            </div>
            {FOOTER}
        </body>
    </html>
    """

@app.post("/customer-register")
def process_customer_register(fullname: str = Form(...), email: str = Form(...), password: str = Form(...)):
    scrambled_password = hashlib.sha256(password.encode()).hexdigest()
    new_customer = Customer(fullname=fullname, email=email, password=scrambled_password)
    with Session(engine) as session:
        session.add(new_customer)
        session.commit()
    return RedirectResponse(url="/customer-login", status_code=303)

@app.get("/customer-login", response_class=HTMLResponse)
def customer_login_page():
    return f"""
    <html>
        <body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
            {NAVBAR}
            <div style="padding: 50px; min-height: 60vh;">
                <div style="background: white; padding: 30px; border-radius: 8px; max-width: 400px; margin: auto; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                    <h2 style="text-align: center; color: #2c3e50;">Customer Login</h2>
                    <form action="/customer-login" method="POST">
                        <label>Email Address:</label><br><input type="email" name="email" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                        <label>Password:</label><br><input type="password" name="password" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                        <button type="submit" style="background-color: #2ecc71; color: white; padding: 12px; border: none; width: 100%; margin-top: 15px; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;">Login</button>
                    </form>
                    <p style="text-align: center; margin-top: 15px;"><a href="/customer-register" style="color: #3498db; text-decoration: none;">Need an account? Register here</a></p>
                </div>
            </div>
            {FOOTER}
        </body>
    </html>
    """

@app.post("/customer-login")
def process_customer_login(response: Response, email: str = Form(...), password: str = Form(...)):
    scrambled_password = hashlib.sha256(password.encode()).hexdigest()
    with Session(engine) as session:
        customer = session.exec(select(Customer).where(Customer.email == email, Customer.password == scrambled_password)).first()
        if customer:
            redirect = RedirectResponse(url="/my-library", status_code=303)
            redirect.set_cookie(key="customer_email", value=customer.email, httponly=True)
            return redirect
        return HTMLResponse(content=f"<h1>Login Failed. <a href='/customer-login'>Try again</a></h1>{FOOTER}", status_code=401)

@app.get("/checkout/{author_id}", response_class=HTMLResponse)
def checkout(request: Request, author_id: int):
    customer_email = request.cookies.get("customer_email")
    if not customer_email:
        return RedirectResponse(url="/customer-login", status_code=303)
    
    with Session(engine) as session:
        author = session.get(Author, author_id)
        if not author:
            return HTMLResponse(content=f"<h1>Book Not Found!</h1>{FOOTER}", status_code=404)
        return f"""
        <html>
            <body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
                {NAVBAR}
                <div style="padding: 50px; min-height: 60vh;">
                    <div style="background: white; padding: 40px; border-radius: 8px; max-width: 400px; margin: auto; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center;">
                        <h2 style="color: #2c3e50;">Checkout</h2>
                        <img src="{author.cover_image}" style="width: 180px; height: 250px; object-fit: cover; border-radius: 4px; margin: 20px 0; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
                        <h3 style="margin: 0; color: #2c3e50;">{author.book_title}</h3>
                        <h4 style="color: #2ecc71; font-size: 24px; margin: 15px 0;">{author.price} TZS</h4>
                        <a href="/pay/{author.id}" style="background-color: #3498db; color: white; padding: 15px 20px; text-decoration: none; border-radius: 5px; display: block; margin-top: 20px; font-size: 16px; font-weight: bold;">Pay with Mobile Money</a>
                    </div>
                </div>
                {FOOTER}
            </body>
        </html>
        """

@app.get("/pay/{author_id}")
def process_payment(request: Request, author_id: int):
    customer_email = request.cookies.get("customer_email")
    if not customer_email:
        return RedirectResponse(url="/customer-login", status_code=303)
    
    with Session(engine) as session:
        customer = session.exec(select(Customer).where(Customer.email == customer_email)).first()
        author = session.get(Author, author_id)
        
        existing = session.exec(select(Purchase).where(Purchase.customer_id == customer.id, Purchase.author_id == author.id)).first()
        if not existing:
            new_purchase = Purchase(customer_id=customer.id, author_id=author.id, book_title=author.book_title, pdf_file=author.pdf_file)
            session.add(new_purchase)
            session.commit()
            
    return RedirectResponse(url="/my-library", status_code=303)

# --- 6. THE CUSTOMER LIBRARY & SECURE READER ---
@app.get("/my-library", response_class=HTMLResponse)
def my_library(request: Request):
    customer_email = request.cookies.get("customer_email")
    if not customer_email:
        return RedirectResponse(url="/customer-login", status_code=303)
    
    with Session(engine) as session:
        customer = session.exec(select(Customer).where(Customer.email == customer_email)).first()
        purchases = session.exec(select(Purchase).where(Purchase.customer_id == customer.id)).all()
        
        html = f"""
        <html>
            <body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
                {NAVBAR}
                <div style="padding: 50px; min-height: 60vh;">
                    <h1 style="text-align: center; color: #2c3e50;">📖 My Library</h1>
                    <p style="text-align: center; color: #7f8c8d; margin-bottom: 30px;">Welcome back, {customer.fullname}!</p>
        """
        
        if not purchases:
            html += "<p style='text-align: center; font-size: 18px;'>You haven't bought any books yet. <a href='/store' style='color: #3498db;'>Visit the store</a></p>"
        else:
            html += "<div style='max-width: 600px; margin: auto;'>"
            for p in purchases:
                html += f"<div style='background: white; padding: 20px; margin-bottom: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); display: flex; justify-content: space-between; align-items: center;'><strong style='color: #2c3e50;'>{p.book_title}</strong> <a href='/read/{p.id}' style='background:#2ecc71; color:white; padding:8px 15px; text-decoration:none; border-radius:4px; font-weight: bold;'>Read Now</a></div>"
            html += "</div>"
            
        html += f"""
                </div>
                {FOOTER}
            </body>
        </html>
        """
        return html

@app.get("/read/{purchase_id}", response_class=HTMLResponse)
def read_book(request: Request, purchase_id: int):
    customer_email = request.cookies.get("customer_email")
    if not customer_email:
        return RedirectResponse(url="/customer-login", status_code=303)
        
    with Session(engine) as session:
        purchase = session.get(Purchase, purchase_id)
        customer = session.exec(select(Customer).where(Customer.email == customer_email)).first()
        
        if purchase.customer_id != customer.id:
            return HTMLResponse(content=f"<h1>Access Denied</h1>{FOOTER}", status_code=403)
            
        return f"""
        <html>
            <head><title>Reading: {purchase.book_title}</title></head>
            <body style="margin: 0; padding: 0; height: 100vh; display: flex; flex-direction: column; background-color: #2c3e50;">
                <div style="background: #1a252f; color: white; padding: 15px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                    <h3 style="margin: 0; font-family: Arial;">Gophigo Secure Reader - {purchase.book_title}</h3>
                    <p style="font-size: 12px; color: #bdc3c7; margin: 5px 0 0 0;">Licensed to: {customer_email}. Screenshots are traceable.</p>
                </div>
                <iframe src="https://docs.google.com/viewer?url={purchase.pdf_file}&embedded=true" style="flex: 1; border: none; width: 100%; height: 100vh;"></iframe>
            </body>
        </html>
        """

@app.get("/customer-logout")
def customer_logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("customer_email")
    return response

# --- 7. AUTHOR LOGIN & DASHBOARD ---
@app.get("/login", response_class=HTMLResponse)
def login_page():
    return f"""
    <html>
        <body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
            {NAVBAR}
            <div style="padding: 50px; min-height: 60vh;">
                <div style="background: white; padding: 30px; border-radius: 8px; max-width: 400px; margin: auto; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                    <h2 style="text-align: center; color: #2c3e50;">Author Login</h2>
                    <form action="/login" method="POST">
                        <label>Email Address:</label><br><input type="email" name="email" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                        <label>Password:</label><br><input type="password" name="password" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                        <button type="submit" style="background-color: #3498db; color: white; padding: 12px; border: none; width: 100%; margin-top: 15px; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;">Login</button>
                    </form>
                    <div style="text-align: center; margin-top: 15px;"><a href="/forgot-password" style="color: #e74c3c; text-decoration: none;">Forgot Password?</a></div>
                </div>
            </div>
            {FOOTER}
        </body>
    </html>
    """

@app.post("/login")
def process_login(response: Response, email: str = Form(...), password: str = Form(...)):
    scrambled_password = hashlib.sha256(password.encode()).hexdigest()
    with Session(engine) as session:
        author = session.exec(select(Author).where(Author.email == email, Author.password == scrambled_password)).first()
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
        if not author:
            return RedirectResponse(url="/login", status_code=303)

        author_sales = session.exec(select(Purchase).where(Purchase.author_id == author.id)).all()
        total_earned = len(author_sales) * (author.price * 0.50)

        if author.membership_status == "Pending":
            payment_html = """
            <div style="background: #fff3cd; padding: 20px; border-radius: 8px; border: 1px solid #ffeeba; margin-top: 20px;">
                <h3 style="color: #856404;">Membership Payment Required</h3>
                <p>Activate your account to start selling.</p>
                <a href="/pay-membership" style="background-color: #2ecc71; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 10px; font-weight: bold;">Pay 20,000 TZS Annually</a>
            </div>
            """
        else:
            payment_html = f"""
            <div style="background: #d4edda; padding: 20px; border-radius: 8px; margin-top: 20px; border: 1px solid #c3e6cb;">
                <h3 style="color: #155724;">✅ Membership Active</h3>
                <h4 style="color: #155724; margin: 10px 0 0 0;">Total Earnings (50%): {total_earned} TZS</h4>
            </div>
            <div style="background: #fff3cd; padding: 20px; border-radius: 8px; margin-top: 10px; border: 1px solid #ffeeba;">
                <h4 style="color: #856404;">Book Status: {author.book_status}</h4>
            </div>
            """

        return f"""
        <html>
            <body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
                {NAVBAR}
                <div style="padding: 50px; text-align: center; min-height: 60vh;">
                    <h1 style="color: #2c3e50;">Author Dashboard</h1>
                    <h2 style="color: #555;">Welcome Back, {author.fullname}!</h2>
                    <div style="background: white; padding: 30px; border-radius: 8px; max-width: 500px; margin: auto; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                        <img src="{author.cover_image}" style="width: 150px; height: 200px; object-fit: cover; border-radius: 4px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
                        <h3 style="margin-top: 20px;">Your Book: {author.book_title}</h3>
                        <p style="font-size: 18px;"><strong>Price:</strong> {author.price} TZS</p>
                        {payment_html}
                    </div>
                    <br><br>
                    <a href="/logout" style="background-color: #e74c3c; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Logout</a>
                </div>
                {FOOTER}
            </body>
        </html>
        """

@app.get("/pay-membership")
def pay_membership(request: Request):
    author_email = request.cookies.get("author_email")
    if not author_email:
        return RedirectResponse(url="/login", status_code=303)
    with Session(engine) as session:
        author = session.exec(select(Author).where(Author.email == author_email)).first()
        if author:
            author.membership_status = "Active"
            session.add(author)
            session.commit()
    return RedirectResponse(url="/author-dashboard", status_code=303)

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("author_email")
    return response

# --- 8. ADMIN DASHBOARD & MODERATION ---
@app.get("/admin-login", response_class=HTMLResponse)
def admin_login_page():
    return f"""
    <html>
        <body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
            {NAVBAR}
            <div style="padding: 50px; min-height: 60vh;">
                <div style="background: white; padding: 30px; border-radius: 8px; max-width: 400px; margin: auto; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                    <h2 style="text-align: center; color: #e74c3c;">Admin Login</h2>
                    <form action="/admin-login" method="POST">
                        <label>Username:</label><br><input type="text" name="username" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                        <label>Password:</label><br><input type="password" name="password" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                        <button type="submit" style="background-color: #e74c3c; color: white; padding: 12px; border: none; width: 100%; margin-top: 15px; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;">Admin Login</button>
                    </form>
                </div>
            </div>
            {FOOTER}
        </body>
    </html>
    """

@app.post("/admin-login")
def admin_login(response: Response, username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "gophigo2026":
        redirect = RedirectResponse(url="/admin", status_code=303)
        redirect.set_cookie(key="admin_session", value="true", httponly=True)
        return redirect
    return HTMLResponse(content=f"<h1>Invalid Admin Credentials. <a href='/admin-login'>Try again</a></h1>{FOOTER}", status_code=401)

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    if request.cookies.get("admin_session") != "true":
        return RedirectResponse(url="/admin-login", status_code=303)

    with Session(engine) as session:
        authors = session.exec(select(Author)).all()
        purchases = session.exec(select(Purchase)).all()
        
        total_sales = sum(author.price for author in authors if author.id in [p.author_id for p in purchases])
        total_platform_revenue = total_sales * 0.50
        total_author_payouts = total_sales * 0.50
    
    html = f"""
    <html>
        <body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
            {NAVBAR}
            <div style="padding: 50px; min-height: 60vh;">
                <h1 style="color: #2c3e50;">Gophigo Admin Dashboard</h1>
                
                <div style='background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
                    <h3 style="margin-top: 0;">Total Sales: {total_sales} TZS</h3>
                    <p style='font-size: 18px; margin-bottom: 0;'>Gophigo Revenue (50%): <strong style="color: #2ecc71;">{total_platform_revenue} TZS</strong> | Author Payouts (50%): <strong style="color: #f39c12;">{total_author_payouts} TZS</strong></p>
                </div>
                
                <div style="overflow-x: auto;">
                    <table border='1' style='border-collapse: collapse; width: 100%; background: white; box-shadow: 0 4px 8px rgba(0,0,0,0.1);'>
                        <tr style='background-color: #34495e; color: white;'>
                            <th style="padding: 10px;">ID</th>
                            <th style="padding: 10px;">Cover</th>
                            <th style="padding: 10px;">Name</th>
                            <th style="padding: 10px;">Book</th>
                            <th style="padding: 10px;">Status</th>
                            <th style="padding: 10px;">Book Quality</th>
                            <th style="padding: 10px;">Actions</th>
                        </tr>
    """
    
    for author in authors:
        status_color = "green" if author.membership_status == "Active" else "red"
        
        if author.membership_status == "Active" and author.book_status == "Pending Review":
            action_buttons = f"<a href='/approve/{author.id}' style='background-color: #2ecc71; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; margin-right: 5px;'>Approve</a> <a href='/reject/{author.id}' style='background-color: #e74c3c; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;'>Reject</a>"
        else:
            action_buttons = ""
            
        book_color = "green" if author.book_status == "Approved" else ("red" if author.book_status == "Rejected" else "#f39c12")
        
        html += f"<tr><td style='padding: 10px; text-align: center;'>{author.id}</td><td style='padding: 10px; text-align: center;'><img src='{author.cover_image}' style='width: 50px; height: 60px; object-fit: cover; border-radius: 4px;'></td><td style='padding: 10px;'>{author.fullname}</td><td style='padding: 10px;'>{author.book_title}</td><td style='padding: 10px; color: {status_color}; font-weight: bold;'>{author.membership_status}</td><td style='padding: 10px; color: {book_color}; font-weight: bold;'>{author.book_status}</td><td style='padding: 10px;'>{action_buttons}</td></tr>"
        
    html += f"""
                    </table>
                </div>
                <br>
                <a href='/admin-logout' style='background-color: #e74c3c; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;'>Admin Logout</a>
            </div>
            {FOOTER}
        </body>
    </html>
    """
    
    return html
@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    if request.cookies.get("admin_session") != "true":
        return RedirectResponse(url="/admin-login", status_code=303)

    with Session(engine) as session:
        authors = session.exec(select(Author)).all()
        purchases = session.exec(select(Purchase)).all()
        
        total_sales = sum(author.price for author in authors if author.id in [p.author_id for p in purchases])
        total_platform_revenue = total_sales * 0.50
        total_author_payouts = total_sales * 0.50
    
    html = f"""
    <html>
        <body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
            {NAVBAR}
            <div style="padding: 50px; min-height: 60vh;">
                <h1 style="color: #2c3e50;">Gophigo Admin Dashboard</h1>
                
                <div style='background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
                    <h3 style="margin-top: 0;">Total Sales: {total_sales} TZS</h3>
                    <p style='font-size: 18px; margin-bottom: 0;'>Gophigo Revenue (50%): <strong style="color: #2ecc71;">{total_platform_revenue} TZS</strong> | Author Payouts (50%): <strong style="color: #f39c12;">{total_author_payouts} TZS</strong></p>
                </div>
                
                <div style="overflow-x: auto;">
                    <table border='1' style='border-collapse: collapse; width: 100%; background: white; box-shadow: 0 4px 8px rgba(0,0,0,0.1);'>
                        <tr style='background-color: #34495e; color: white;'>
                            <th style="padding: 10px;">ID</th>
                            <th style="padding: 10px;">Cover</th>
                            <th style="padding: 10px;">Name</th>
                            <th style="padding: 10px;">Book</th>
                            <th style="padding: 10px;">Status</th>
                            <th style="padding: 10px;">Book Quality</th>
                            <th style="padding: 10px;">Actions</th>
                        </tr>
    """
    
    for author in authors:
        status_color = "green" if author.membership_status == "Active" else "red"
        
        if author.membership_status == "Active" and author.book_status == "Pending Review":
            action_buttons = f"<a href='/approve/{author.id}' style='background-color: #2ecc71; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; margin-right: 5px;'>Approve</a> <a href='/reject/{author.id}' style='background-color: #e74c3c; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;'>Reject</a>"
        else:
            action_buttons = ""
            
        book_color = "green" if author.book_status == "Approved" else ("red" if author.book_status == "Rejected" else "#f39c12")
        
        html += f"<tr><td style='padding: 10px; text-align: center;'>{author.id}</td><td style='padding: 10px; text-align: center;'><img src='{author.cover_image}' style='width: 50px; height: 60px; object-fit: cover; border-radius: 4px;'></td><td style='padding: 10px;'>{author.fullname}</td><td style='padding: 10px;'>{author.book_title}</td><td style='padding: 10px; color: {status_color}; font-weight: bold;'>{author.membership_status}</td><td style='padding: 10px; color: {book_color}; font-weight: bold;'>{author.book_status}</td><td style='padding: 10px;'>{action_buttons}</td></tr>"
        
    html += f"""
                    </table>
                </div>
                <br>
                <a href='/admin-logout' style='background-color: #e74c3c; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;'>Admin Logout</a>
            </div>
            {FOOTER}
        </body>
    </html>
    """
    
    return html

@app.get("/approve/{author_id}")
def approve_book(author_id: int):
    with Session(engine) as session:
        author = session.get(Author, author_id)
        if author:
            author.book_status = "Approved"
            session.add(author)
            session.commit()
    return RedirectResponse(url="/admin", status_code=303)

@app.get("/reject/{author_id}")
def reject_book(author_id: int):
    with Session(engine) as session:
        author = session.get(Author, author_id)
        if author:
            author.book_status = "Rejected"
            session.add(author)
            session.commit()
    return RedirectResponse(url="/admin", status_code=303)

@app.get("/admin-logout")
def admin_logout():
    response = RedirectResponse(url="/admin-login", status_code=303)
    response.delete_cookie("admin_session")
    return response
