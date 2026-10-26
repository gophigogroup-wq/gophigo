import cloudinary
import cloudinary.uploader
from fastapi import FastAPI, Form, Depends, HTTPException, status, Request, Response, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, Field, Session, create_engine, select
import hashlib
import secrets
import shutil
import os
import uuid
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")

)
app = FastAPI()

# --- 1. STATIC FILES SETUP ---
os.makedirs("static/covers", exist_ok=True)
os.makedirs("static/books", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

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

# --- 3. THE WEB PAGES ---

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
        <body style="font-family: Arial; text-align: center; background-color: #f4f4f4; padding: 50px;">
            <h1>Welcome to Gophigo Publishing Portal</h1>
            <p>The best place for Tanzanian authors to sell their books.</p>
            <a href="/store" style="background-color: #f39c12; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">📚 Visit Public Bookstore</a>
            <br><br>
            <a href="/register" style="background-color: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Register as an Author</a>
            <br><br>
            <a href="/login" style="color: #2c3e50;">Author Login</a> | <a href="/customer-login" style="color: #2ecc71;">Customer Login</a> | <a href="/admin-login" style="color: #e74c3c;">Admin Login</a>
        </body>
    </html>
    """

@app.get("/register", response_class=HTMLResponse)
def register_page():
    return """
    <html>
        <body style="font-family: Arial; padding: 50px; background-color: #f4f4f4;">
            <div style="background: white; padding: 30px; border-radius: 8px; max-width: 400px; margin: auto;">
                <h2>Author Registration</h2>
                <form action="/register" method="POST" enctype="multipart/form-data">
                    <label>Full Name:</label><br><input type="text" name="fullname" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                    <label>Email Address:</label><br><input type="email" name="email" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                    <label>Password:</label><br><input type="password" name="password" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                    <label>Book Title:</label><br><input type="text" name="book_title" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                    <label>Book Price (TZS):</label><br><input type="number" name="price" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                    <label>Book Cover Image:</label><br><input type="file" name="cover" accept="image/*" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                    <label>Manuscript (PDF):</label><br><input type="file" name="pdf_file" accept=".pdf" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                    <button type="submit" style="background-color: #2ecc71; color: white; padding: 10px; border: none; width: 100%; margin-top: 10px;">Submit</button>
                </form>
            </div>
        </body>
    </html>
    """

@app.post("/register", response_class=HTMLResponse)
def process_registration(fullname: str = Form(...), email: str = Form(...), password: str = Form(...), book_title: str = Form(...), price: float = Form(...), cover: UploadFile = File(...), pdf_file: UploadFile = File(...)):
      # 1. Upload Cover Image to Cloudinary
    cover_result = cloudinary.uploader.upload(cover.file, folder="gophigo_covers")
    cover_url = cover_result.get("secure_url")

    # 2. Upload PDF to Cloudinary (as raw file)
    pdf_result = cloudinary.uploader.upload(pdf_file.file, folder="gophigo_pdfs", resource_type="raw")
    pdf_url = pdf_result.get("secure_url")

    scrambled_password = hashlib.sha256(password.encode()).hexdigest()
    new_author = Author(fullname=fullname, email=email, password=scrambled_password, book_title=book_title, price=price, cover_image=cover_url, pdf_file=pdf_url)
    
    
    with Session(engine) as session:
        session.add(new_author)
        session.commit()
    
    return "<html><body style='text-align:center; padding:50px;'><h1 style='color:#2ecc71;'>Registration Successful!</h1><a href='/login'>Login here</a></body></html>"

# --- 4. THE PUBLIC BOOKSTORE ---
@app.get("/store", response_class=HTMLResponse)
def store():
    with Session(engine) as session:
        active_authors = session.exec(select(Author).where(Author.membership_status == "Active", Author.book_status == "Approved")).all()
        
        html = "<html><body style='font-family: Arial; padding: 50px; background-color: #f4f4f4;'>"
        html += "<h1 style='text-align: center;'>📚 Gophigo Bookstore</h1>"
        html += "<div style='display: flex; flex-wrap: wrap; gap: 20px; justify-content: center;'>"
        
        if not active_authors:
            html += "<p>No books available yet. Check back later!</p>"
            
        for author in active_authors:
            html += f"""
            <div style='background: white; border-radius: 8px; padding: 20px; width: 250px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); text-align: center;'>
                <img src="/{author.cover_image}" alt="Book Cover" style="width: 100%; height: 300px; object-fit: cover; border-radius: 4px; margin-bottom: 15px; border: 1px solid #ccc;">
                <h3 style='color: #2c3e50; margin: 0;'>{author.book_title}</h3>
                <p style='color: #7f8c8d; margin: 5px 0;'>By {author.fullname}</p>
                <h4 style='color: #2ecc71;'>{author.price} TZS</h4>
                <form action="/checkout/{author.id}" method="GET" style="margin: 0;">
                    <button type="submit" style="background-color: #3498db; color: white; padding: 10px; border: none; border-radius: 5px; width: 100%; cursor: pointer; font-size: 16px;">Buy Now</button>
                </form>
            </div>
            """
            
        html += "</div><br><br><div style='text-align: center;'><a href='/'>Back to Home</a></div></body></html>"
        return html

# --- 5. CUSTOMER LOGIN & PURCHASING ---
@app.get("/customer-register", response_class=HTMLResponse)
def customer_register_page():
    return """
    <html><body style="font-family: Arial; padding: 50px; background-color: #f4f4f4;">
        <div style="background: white; padding: 30px; border-radius: 8px; max-width: 400px; margin: auto;">
            <h2>Create Customer Account</h2>
            <form action="/customer-register" method="POST">
                <label>Full Name:</label><br><input type="text" name="fullname" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                <label>Email Address:</label><br><input type="email" name="email" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                <label>Password:</label><br><input type="password" name="password" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                <button type="submit" style="background-color: #2ecc71; color: white; padding: 10px; border: none; width: 100%; margin-top: 10px;">Register</button>
            </form>
        </div>
    </body></html>
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
    return """
    <html><body style="font-family: Arial; padding: 50px; background-color: #f4f4f4;">
        <div style="background: white; padding: 30px; border-radius: 8px; max-width: 400px; margin: auto;">
            <h2>Customer Login</h2>
            <form action="/customer-login" method="POST">
                <label>Email Address:</label><br><input type="email" name="email" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                <label>Password:</label><br><input type="password" name="password" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                <button type="submit" style="background-color: #2ecc71; color: white; padding: 10px; border: none; width: 100%; margin-top: 10px;">Login</button>
            </form>
            <p style="text-align: center; margin-top: 15px;"><a href="/customer-register">Need an account? Register here</a></p>
        </div>
    </body></html>
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
        return HTMLResponse(content="<h1>Login Failed. <a href='/customer-login'>Try again</a></h1>", status_code=401)

@app.get("/checkout/{author_id}", response_class=HTMLResponse)
def checkout(request: Request, author_id: int):
    customer_email = request.cookies.get("customer_email")
    if not customer_email:
        return RedirectResponse(url="/customer-login", status_code=303)
    
    with Session(engine) as session:
        author = session.get(Author, author_id)
        if not author:
            return HTMLResponse(content="<h1>Book Not Found!</h1>", status_code=404)
        return f"""
        <html><body style="font-family: Arial; text-align: center; padding: 50px; background-color: #f4f4f4;">
            <div style="background: white; padding: 30px; border-radius: 8px; max-width: 400px; margin: auto;">
                <h2>Checkout</h2>
                <img src="/static/covers/{author.cover_image}" style="width: 150px; height: 200px; object-fit: cover; border-radius: 4px;">
                <h3>{author.book_title}</h3>
                <h4 style="color: #2ecc71;">{author.price} TZS</h4>
                <a href="/pay/{author.id}" style="background-color: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: block; margin-top: 20px;">Pay with Mobile Money (Simulate)</a>
            </div>
        </body></html>
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
        
        html = "<html><body style='font-family: Arial; padding: 50px; background-color: #f4f4f4;'>"
        html += "<h1>📖 My Library</h1>"
        html += f"<p>Welcome, {customer.fullname}!</p>"
        
        if not purchases:
            html += "<p>You haven't bought any books yet. <a href='/store'>Visit the store</a></p>"
        else:
            html += "<ul>"
            for p in purchases:
                html += f"<li style='margin-bottom: 10px;'><strong>{p.book_title}</strong> - <a href='/read/{p.id}' style='background:#2ecc71; color:white; padding:5px 10px; text-decoration:none; border-radius:3px;'>Read Now</a></li>"
            html += "</ul>"
            
        html += "<br><a href='/customer-logout'>Logout</a> | <a href='/'>Back to Home</a></body></html>"
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
            return HTMLResponse(content="<h1>Access Denied</h1>", status_code=403)
            
        return f"""
        <html>
            <head><title>Reading: {purchase.book_title}</title></head>
            <body style="margin: 0; padding: 0; height: 100vh; display: flex; flex-direction: column;">
                <div style="background: #2c3e50; color: white; padding: 10px; text-align: center;">
                    <h3>Gophigo Secure Reader - {purchase.book_title}</h3>
                    <p style="font-size: 12px; color: #bdc3c7;">Licensed to: {customer_email}. Screenshots are traceable.</p>
                </div>
                <iframe src="/static/books/{purchase.pdf_file}#toolbar=0" style="flex: 1; border: none; width: 100%;"></iframe>
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
    return """
    <html><body style="font-family: Arial; padding: 50px; background-color: #f4f4f4;">
        <div style="background: white; padding: 30px; border-radius: 8px; max-width: 400px; margin: auto;">
            <h2>Author Login</h2>
            <form action="/login" method="POST">
                <label>Email Address:</label><br><input type="email" name="email" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                <label>Password:</label><br><input type="password" name="password" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                <button type="submit" style="background-color: #3498db; color: white; padding: 10px; border: none; width: 100%; margin-top: 10px;">Login</button>
            </form>
            <div style="text-align: center; margin-top: 15px;"><a href="/forgot-password">Forgot Password?</a></div>
        </div>
    </body></html>
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
    return HTMLResponse(content="<h1>Login Failed. <a href='/login'>Try again</a></h1>", status_code=401)

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
        total_earned = len(author_sales) * (author.price * 0.70)

        if author.membership_status == "Pending":
            payment_html = """
            <div style="background: #fff3cd; padding: 20px; border-radius: 8px; border: 1px solid #ffeeba; margin-top: 20px;">
                <h3 style="color: #856404;">Membership Payment Required</h3>
                <a href="/pay-membership" style="background-color: #2ecc71; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Pay 20,000 TZS Annually</a>
            </div>
            """
        else:
            payment_html = f"""
            <div style="background: #d4edda; padding: 20px; border-radius: 8px; margin-top: 20px;">
                <h3 style="color: #155724;">✅ Membership Active</h3>
                <h4 style="color: #155724;">Total Earnings (70%): {total_earned} TZS</h4>
            </div>
            <div style="background: #fff3cd; padding: 20px; border-radius: 8px; margin-top: 10px;">
                <h4 style="color: #856404;">Book Status: {author.book_status}</h4>
            </div>
            """

        return f"""
        <html><body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>Author Dashboard</h1>
            <h2>Welcome Back, {author.fullname}!</h2>
            <div style="background: #f9f9f9; padding: 20px; border-radius: 8px; max-width: 500px; margin: auto;">
                <img src="{author.cover_image}" style="width: 150px; height: 200px; object-fit: cover; border-radius: 4px;">
                <h3>Your Book: {author.book_title}</h3>
                <p><strong>Price:</strong> {author.price} TZS</p>
                {payment_html}
            </div>
            <br><br><a href="/logout" style="background-color: #e74c3c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Logout</a>
        </body></html>
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
    return """
    <html><body style="font-family: Arial; padding: 50px; background-color: #f4f4f4;">
        <div style="background: white; padding: 30px; border-radius: 8px; max-width: 400px; margin: auto;">
            <h2>Admin Login</h2>
            <form action="/admin-login" method="POST">
                <label>Username:</label><br><input type="text" name="username" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                <label>Password:</label><br><input type="password" name="password" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                <button type="submit" style="background-color: #e74c3c; color: white; padding: 10px; border: none; width: 100%; margin-top: 10px;">Admin Login</button>
            </form>
        </div>
    </body></html>
    """

@app.post("/admin-login")
def admin_login(response: Response, username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "gophigo2026":
        redirect = RedirectResponse(url="/admin", status_code=303)
        redirect.set_cookie(key="admin_session", value="true", httponly=True)
        return redirect
    return HTMLResponse(content="<h1>Invalid Admin Credentials. <a href='/admin-login'>Try again</a></h1>", status_code=401)

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    if request.cookies.get("admin_session") != "true":
        return RedirectResponse(url="/admin-login", status_code=303)

    with Session(engine) as session:
        authors = session.exec(select(Author)).all()
        purchases = session.exec(select(Purchase)).all()
        
        total_sales = len(purchases) * 20000
    
    html = "<html><body style='font-family: Arial; padding: 50px; background-color: #f4f4f4;'>"
    html += "<h1>Gophigo Admin Dashboard</h1>"
    html += f"<div style='background: #2c3e50; color: white; padding: 20px; border-radius: 8px;'><h3>Total Book Sales</h3><p style='font-size: 24px;'>{len(purchases)} copies sold</p></div>"
    
    html += "<br><table border='1' style='border-collapse: collapse; width: 100%; background: white;'><tr style='background-color: #34495e; color: white;'><th>ID</th><th>Cover</th><th>Name</th><th>Book</th><th>Status</th><th>Book Quality</th><th>Actions</th></tr>"
    
    for author in authors:
        status_color = "green" if author.membership_status == "Active" else "red"
        
        if author.membership_status == "Active" and author.book_status == "Pending Review":
            action_buttons = f"<a href='/approve/{author.id}' style='background-color: #2ecc71; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;'>Approve</a> <a href='/reject/{author.id}' style='background-color: #e74c3c; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;'>Reject</a>"
        else:
            action_buttons = ""
            
        book_color = "green" if author.book_status == "Approved" else ("red" if author.book_status == "Rejected" else "#f39c12")
        
        html += f"<tr><td>{author.id}</td><td><img src='{author.cover_image}' style='width: 50px; height: 60px; object-fit: cover;'></td><td>{author.fullname}</td><td>{author.book_title}</td><td style='color: {status_color}; font-weight: bold;'>{author.membership_status}</td><td style='color: {book_color}; font-weight: bold;'>{author.book_status}</td><td>{action_buttons}</td></tr>"
        
    html += "</table><br>"
    html += "<a href='/admin-logout' style='background-color: #e74c3c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;'>Admin Logout</a>"
    html += "</body></html>"
    
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
