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
    ebook_price: float = Field(default=0.0)
    paperback_price: float = Field(default=0.0)
    book_format: str = Field(default="Ebook")
    membership_status: str = "Pending" 
    book_status: str = Field(default="Pending Review") 
    reset_token: str | None = Field(default=None) # For password reset
    cover_image: str | None = Field(default=None) 
    pdf_file: str | None = Field(default=None) 

class Customer(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    fullname: str
    email: str
    password: str
    reset_token: str | None = Field(default=None) # For password reset

class Purchase(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    customer_id: int
    author_id: int
    book_title: str
    pdf_file: str
    format_bought: str = Field(default="Ebook")
    shipping_address: str | None = Field(default=None)

class Employee(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    fullname: str
    email: str
    password: str
    role: str 
    must_change_password: bool = Field(default=True)
    reset_token: str | None = Field(default=None) # For password reset

SQLModel.metadata.create_all(engine)

# Create default employees
with Session(engine) as session:
    if not session.exec(select(Employee)).first():
        session.add(Employee(fullname="Reviewer John", email="reviewer@gophigo.com", password=hashlib.sha256("pass123".encode()).hexdigest(), role="Reviewer"))
        session.add(Employee(fullname="Supervisor Mary", email="supervisor@gophigo.com", password=hashlib.sha256("pass123".encode()).hexdigest(), role="Supervisor"))
        session.add(Employee(fullname="Approver Boss", email="approver@gophigo.com", password=hashlib.sha256("pass123".encode()).hexdigest(), role="Approver"))
        session.commit()

# --- 3. SHARED DESIGN ---
NAVBAR = """
<nav style="background-color: #2c3e50; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; font-family: 'Poppins', Arial, sans-serif; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
    <div style="font-size: 24px; font-weight: bold;">
        <a href="/" style="color: white; text-decoration: none;">📚 Gophigo</a>
    </div>
    <div>
        <a href="/author-portal" style="color: white; text-decoration: none; margin-left: 20px; font-size: 16px;">Author Portal</a>
        <a href="/customer-login" style="color: white; text-decoration: none; margin-left: 20px; font-size: 16px;">Customer Login</a>
        <a href="/employee-login" style="color: #f39c12; text-decoration: none; margin-left: 20px; font-size: 16px; font-weight: bold;">Staff Login</a>
    </div>
</nav>
"""

FOOTER = """
<footer style="background-color: #2c3e50; color: white; text-align: center; padding: 20px; margin-top: 50px; font-family: Arial; font-size: 14px;">
    <p>&copy; 2026 Gophigo Publishing. All rights reserved.</p>
    <p>Empowering Authors Globally.</p>
</footer>
"""

# --- 4. THE STORE (WITH SEARCH & FORMATS) ---
@app.get("/", response_class=HTMLResponse)
def store(search: str = None):
    with Session(engine) as session:
        query = select(Author).where(Author.membership_status == "Active", Author.book_status == "Approved")
        if search:
            query = query.where((Author.book_title.contains(search)) | (Author.fullname.contains(search)))
            
        active_authors = session.exec(query).all()
        
        html = f"""
        <html>
            <head>
                <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap" rel="stylesheet">
                <style>
                    body {{ font-family: 'Poppins', sans-serif; }}
                    .book-card {{ transition: transform 0.3s ease, box-shadow 0.3s ease; }}
                    .book-card:hover {{ transform: translateY(-8px); box-shadow: 0 12px 24px rgba(0,0,0,0.15) !important; }}
                    .buy-btn {{ transition: background-color 0.2s ease; }}
                    .buy-btn:hover {{ filter: brightness(1.1); }}
                </style>
            </head>
            <body style="margin: 0; padding: 0; background-color: #f4f4f4;">
                {NAVBAR}
                <div style="padding: 50px; min-height: 60vh;">
                    <h1 style="text-align: center; color: #2c3e50; margin-bottom: 20px;">📚 Gophigo Bookstore</h1>
                    
                    <form action="/" method="GET" style="max-width: 500px; margin: 0 auto 40px auto; display: flex; gap: 10px;">
                        <input type="text" name="search" placeholder="Search by book title or author..." value="{search if search else ''}" style="flex: 1; padding: 12px; border: 1px solid #ccc; border-radius: 5px; font-size: 16px;">
                        <button type="submit" style="background-color: #3498db; color: white; padding: 12px 25px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;">Search</button>
                    </form>

                    <div style='display: flex; flex-wrap: wrap; gap: 30px; justify-content: center;'>
        """
        
        if not active_authors:
            html += "<p style='text-align: center; font-size: 18px; color: #7f8c8d;'>No books found matching your search.</p>"
            
        for author in active_authors:
            format_badge = f"<span style='background: #e0e0e0; color: #333; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 600;'>{author.book_format}</span>"
            
            buy_buttons = ""
            if author.book_format in ["Ebook", "Both"]:
                buy_buttons += f"<a href='/checkout/{author.id}?format=Ebook' class='buy-btn' style='background-color: #3498db; color: white; padding: 10px; border-radius: 5px; text-decoration: none; display: block; margin-bottom: 5px; font-weight: bold;'>Buy Ebook ({author.ebook_price} TZS)</a>"
            if author.book_format in ["Paperback", "Both"]:
                buy_buttons += f"<a href='/checkout/{author.id}?format=Paperback' class='buy-btn' style='background-color: #f39c12; color: white; padding: 10px; border-radius: 5px; text-decoration: none; display: block; font-weight: bold;'>Buy Paperback ({author.paperback_price} TZS)</a>"

            html += f"""
            <div class="book-card" style='background: white; border-radius: 8px; padding: 20px; width: 280px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center;'>
                <img src="{author.cover_image}" alt="Book Cover" style="width: 100%; height: 300px; object-fit: cover; border-radius: 4px; margin-bottom: 15px; border: 1px solid #eee;">
                <h3 style='color: #2c3e50; margin: 0 0 5px 0; font-size: 20px; font-weight: 600;'>{author.book_title}</h3>
                <p style='color: #7f8c8d; margin: 0 0 10px 0; font-size: 14px;'>By {author.fullname}</p>
                {format_badge}
                <br><br>
                {buy_buttons}
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

# --- 5. AUTHOR REGISTRATION & LOGIN ---
@app.get("/author-portal", response_class=HTMLResponse)
def author_portal():
    return f"<html><body style='font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;'>{NAVBAR}<div style='text-align: center; padding: 100px 20px; min-height: 60vh;'><h1 style='color: #2c3e50; font-size: 36px;'>Author Portal</h1><p style='font-size: 18px; color: #555; margin-bottom: 40px;'>Publish your book and keep 50% of your sales.</p><a href='/register' style='background-color: #3498db; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-size: 18px; font-weight: bold; margin-right: 10px;'>Register as a New Author</a><a href='/login' style='background-color: #2ecc71; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-size: 18px; font-weight: bold; margin-left: 10px;'>Author Login</a></div>{FOOTER}</body></html>"

@app.get("/register", response_class=HTMLResponse)
def register_page():
    return f"""
    <html><body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
        {NAVBAR}
        <div style="padding: 50px; min-height: 60vh;">
            <div style="background: white; padding: 30px; border-radius: 8px; max-width: 500px; margin: auto; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                <h2 style="text-align: center; color: #2c3e50;">Author Registration</h2>
                <form action="/register" method="POST" enctype="multipart/form-data">
                    <label>Full Name:</label><br><input type="text" name="fullname" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                    <label>Email Address:</label><br><input type="email" name="email" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                    <label>Password:</label><br><input type="password" name="password" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                    <label>Book Title:</label><br><input type="text" name="book_title" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                    <label>Book Format:</label><br>
                    <select name="book_format" style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;">
                        <option value="Ebook">Ebook Only</option>
                        <option value="Paperback">Paperback Only</option>
                        <option value="Both">Both Ebook & Paperback</option>
                    </select><br>
                    <label>Ebook Price (TZS):</label><br><input type="number" step="0.01" name="ebook_price" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                    <label>Paperback Price (TZS):</label><br><input type="number" step="0.01" name="paperback_price" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                    <label>Book Cover Image:</label><br><input type="file" name="cover" accept="image/*" required style="width: 100%; padding: 10px; margin: 10px 0;"><br>
                    <label>Manuscript (PDF):</label><br><input type="file" name="pdf_file" accept=".pdf" style="width: 100%; padding: 10px; margin: 10px 0;"><br>
                    <button type="submit" style="background-color: #2ecc71; color: white; padding: 12px; border: none; width: 100%; margin-top: 15px; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;">Submit</button>
                </form>
            </div>
        </div>
        {FOOTER}
    </body></html>
    """

@app.post("/register", response_class=HTMLResponse)
def process_registration(fullname: str = Form(...), email: str = Form(...), password: str = Form(...), book_title: str = Form(...), book_format: str = Form(...), ebook_price: float = Form(...), paperback_price: float = Form(...), cover: UploadFile = File(...), pdf_file: UploadFile = File(None)):
    cover_result = cloudinary.uploader.upload(cover.file, folder="gophigo_covers", resource_type="image")
    cover_url = cover_result.get("secure_url")
    
    pdf_url = None
    if pdf_file and pdf_file.filename:
        pdf_result = cloudinary.uploader.upload(pdf_file.file, folder="gophigo_pdfs", resource_type="raw", access_mode="public")
        pdf_url = pdf_result.get("secure_url")

    scrambled_password = hashlib.sha256(password.encode()).hexdigest()
    new_author = Author(
        fullname=fullname, email=email, password=scrambled_password, 
        book_title=book_title, book_format=book_format, 
        ebook_price=ebook_price, paperback_price=paperback_price, 
        cover_image=cover_url, pdf_file=pdf_url
    )
    
    with Session(engine) as session:
        session.add(new_author)
        session.commit()
    
    return f"<html><body style='font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;'>{NAVBAR}<div style='text-align: center; padding: 100px 20px; min-height: 60vh;'><h1 style='color: #2ecc71;'>Registration Successful!</h1><p style='font-size: 18px;'>Thank you, <strong>{fullname}</strong>. Your book is pending review.</p><a href='/login' style='background-color: #3498db; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-size: 16px;'>Go to Login</a></div>{FOOTER}</body></html>"

@app.get("/login", response_class=HTMLResponse)
def login_page():
    return f"""
    <html><body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
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
        total_earned = 0
        for sale in author_sales:
            if sale.format_bought == "Ebook":
                total_earned += author.ebook_price * 0.50
            else:
                total_earned += author.paperback_price * 0.50

        if author.membership_status == "Pending":
            payment_html = """<div style="background: #fff3cd; padding: 20px; border-radius: 8px; border: 1px solid #ffeeba; margin-top: 20px;"><h3 style="color: #856404;">Membership Payment Required</h3><p>Activate your account to start selling.</p><a href="/pay-membership" style="background-color: #2ecc71; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 10px; font-weight: bold;">Pay 20,000 TZS Annually</a></div>"""
        else:
            payment_html = f"""<div style="background: #d4edda; padding: 20px; border-radius: 8px; margin-top: 20px; border: 1px solid #c3e6cb;"><h3 style="color: #155724;">✅ Membership Active</h3><h4 style="color: #155724; margin: 10px 0 0 0;">Total Earnings (50%): {total_earned} TZS</h4></div><div style="background: #fff3cd; padding: 20px; border-radius: 8px; margin-top: 10px; border: 1px solid #ffeeba;"><h4 style="color: #856404;">Book Status: {author.book_status}</h4></div>"""
        
        return f"<html><body style='font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;'>{NAVBAR}<div style='padding: 50px; text-align: center; min-height: 60vh;'><h1 style='color: #2c3e50;'>Author Dashboard</h1><h2 style='color: #555;'>Welcome Back, {author.fullname}!</h2><div style='background: white; padding: 30px; border-radius: 8px; max-width: 500px; margin: auto; box-shadow: 0 4px 12px rgba(0,0,0,0.1);'><img src='{author.cover_image}' style='width: 150px; height: 200px; object-fit: cover; border-radius: 4px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);'><h3 style='margin-top: 20px;'>Your Book: {author.book_title}</h3><p style='font-size: 18px;'><strong>Format:</strong> {author.book_format}</p><p style='font-size: 18px;'><strong>Ebook Price:</strong> {author.ebook_price} TZS</p><p style='font-size: 18px;'><strong>Paperback Price:</strong> {author.paperback_price} TZS</p>{payment_html}</div><br><br><a href='/logout' style='background-color: #e74c3c; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;'>Logout</a></div>{FOOTER}</body></html>"

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

# --- 6. UNIFIED FORGOT PASSWORD FLOW ---
@app.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page():
    return f"""
    <html><body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
        {NAVBAR}
        <div style="padding: 50px; min-height: 60vh;">
            <div style="background: white; padding: 30px; border-radius: 8px; max-width: 400px; margin: auto; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                <h2 style="text-align: center; color: #2c3e50;">Reset Password</h2>
                <p style="text-align: center; font-size: 14px; color: #7f8c8d;">Enter your email to receive a reset link.</p>
                <form action="/forgot-password" method="POST">
                    <label>Email Address:</label><br><input type="email" name="email" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                    <button type="submit" style="background-color: #e74c3c; color: white; padding: 12px; border: none; width: 100%; margin-top: 15px; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;">Generate Reset Link</button>
                </form>
            </div>
        </div>
        {FOOTER}
    </body></html>
    """

@app.post("/forgot-password", response_class=HTMLResponse)
def process_forgot_password(email: str = Form(...)):
    token = secrets.token_hex(16)
    found = False
    reset_link = ""

    with Session(engine) as session:
        # Check if Author
        author = session.exec(select(Author).where(Author.email == email)).first()
        if author:
            author.reset_token = token
            session.add(author)
            session.commit()
            found = True
            reset_link = f"/reset-password?token={token}&type=author" # Assuming local testing, but in production it would be the domain

        # Check if Employee
        employee = session.exec(select(Employee).where(Employee.email == email)).first()
        if employee:
            employee.reset_token = token
            session.add(employee)
            session.commit()
            found = True
            reset_link = f"/reset-password?token={token}&type=employee"

    if found:
        # In production, you would email this link. Since we don't have an email server, we display it.
        return f"""
        <html><body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
            {NAVBAR}
            <div style="text-align: center; padding: 100px 20px; min-height: 60vh;">
                <h2 style="color: #2ecc71;">Simulated Email Sent!</h2>
                <p>In a real app, a link would be emailed to <strong>{email}</strong>.</p>
                <p>Since this is a local test, click the link below to reset your password:</p>
                <a href="{reset_link}" style="background-color: #3498db; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-size: 16px; margin-top: 20px; display: inline-block;">Click Here to Reset Password</a>
            </div>
            {FOOTER}
        </body></html>
        """
    else:
        return HTMLResponse(content=f"<h1>Email not found. <a href='/forgot-password'>Try again</a></h1>{FOOTER}", status_code=404)

@app.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(token: str, type: str = "author"):
    return f"""
    <html><body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
        {NAVBAR}
        <div style="padding: 50px; min-height: 60vh;">
            <div style="background: white; padding: 30px; border-radius: 8px; max-width: 400px; margin: auto; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                <h2 style="text-align: center; color: #2c3e50;">Enter New Password</h2>
                <form action="/reset-password" method="POST">
                    <input type="hidden" name="token" value="{token}">
                    <input type="hidden" name="type" value="{type}">
                    <label>New Password:</label><br><input type="password" name="new_password" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                    <button type="submit" style="background-color: #2ecc71; color: white; padding: 12px; border: none; width: 100%; margin-top: 15px; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;">Update Password</button>
                </form>
            </div>
        </div>
        {FOOTER}
    </body></html>
    """

@app.post("/reset-password", response_class=HTMLResponse)
def process_reset_password(token: str = Form(...), new_password: str = Form(...), type: str = Form("author")):
    scrambled_password = hashlib.sha256(new_password.encode()).hexdigest()
    success = False

    with Session(engine) as session:
        if type == "author":
            author = session.exec(select(Author).where(Author.reset_token == token)).first()
            if author:
                author.password = scrambled_password
                author.reset_token = None 
                session.add(author)
                session.commit()
                success = True
        elif type == "employee":
            employee = session.exec(select(Employee).where(Employee.reset_token == token)).first()
            if employee:
                employee.password = scrambled_password
                employee.must_change_password = False # Since they just set a new one
                employee.reset_token = None
                session.add(employee)
                session.commit()
                success = True

    if success:
        return f"<html><body style='font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;'>{NAVBAR}<div style='text-align: center; padding: 100px 20px; min-height: 60vh;'><h1 style='color: #2ecc71;'>Password Updated!</h1><p>You can now log in with your new password.</p><a href='/login'>Go to Author Login</a> | <a href='/employee-login'>Go to Staff Login</a></div>{FOOTER}</body></html>"
    else:
        return HTMLResponse(content=f"<h1>Invalid or expired token. <a href='/forgot-password'>Try again</a></h1>{FOOTER}", status_code=400)


# --- 7. CUSTOMER FLOW (WITH NEXT URL) ---
@app.get("/customer-gateway", response_class=HTMLResponse)
def customer_gateway(next: str = "/"):
    return f"""
    <html><body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
        {NAVBAR}
        <div style="padding: 50px; min-height: 60vh;">
            <div style="background: white; padding: 40px; border-radius: 8px; max-width: 400px; margin: auto; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center;">
                <h2 style="color: #2c3e50;">Before you buy...</h2>
                <p style="color: #7f8c8d; margin-bottom: 30px;">Please log in or create an account to complete your purchase.</p>
                <a href="/customer-login?next={next}" style="background-color: #3498db; color: white; padding: 12px; text-decoration: none; border-radius: 5px; font-size: 16px; font-weight: bold; display: block; margin-bottom: 15px;">I already have an account (Login)</a>
                <a href="/customer-register?next={next}" style="background-color: #2ecc71; color: white; padding: 12px; text-decoration: none; border-radius: 5px; font-size: 16px; font-weight: bold; display: block;">I am a new customer (Register)</a>
            </div>
        </div>
        {FOOTER}
    </body></html>
    """

@app.get("/customer-login", response_class=HTMLResponse)
def customer_login_page(next: str = "/"):
    return f"""
    <html><body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
        {NAVBAR}
        <div style="padding: 50px; min-height: 60vh;">
            <div style="background: white; padding: 30px; border-radius: 8px; max-width: 400px; margin: auto; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                <h2 style="text-align: center; color: #2c3e50;">Customer Login</h2>
                <form action="/customer-login?next={next}" method="POST">
                    <label>Email Address:</label><br><input type="email" name="email" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                    <label>Password:</label><br><input type="password" name="password" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                    <button type="submit" style="background-color: #2ecc71; color: white; padding: 12px; border: none; width: 100%; margin-top: 15px; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;">Login</button>
                </form>
                <p style="text-align: center; margin-top: 15px;"><a href="/customer-register?next={next}" style="color: #3498db; text-decoration: none;">Need an account? Register here</a></p>
                <div style="text-align: center; margin-top: 15px;"><a href="/forgot-password" style="color: #e74c3c; text-decoration: none;">Forgot Password?</a></div>
            </div>
        </div>
        {FOOTER}
    </body></html>
    """

@app.post("/customer-login")
def process_customer_login(response: Response, email: str = Form(...), password: str = Form(...), next: str = Form("/")):
    scrambled_password = hashlib.sha256(password.encode()).hexdigest()
    with Session(engine) as session:
        customer = session.exec(select(Customer).where(Customer.email == email, Customer.password == scrambled_password)).first()
        if customer:
            redirect = RedirectResponse(url=next, status_code=303)
            redirect.set_cookie(key="customer_email", value=customer.email, httponly=True)
            return redirect
        return HTMLResponse(content=f"<h1>Login Failed. <a href='/customer-login?next={next}'>Try again</a></h1>{FOOTER}", status_code=401)

@app.get("/customer-register", response_class=HTMLResponse)
def customer_register_page(next: str = "/"):
    return f"""
    <html><body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
        {NAVBAR}
        <div style="padding: 50px; min-height: 60vh;">
            <div style="background: white; padding: 30px; border-radius: 8px; max-width: 400px; margin: auto; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                <h2 style="text-align: center; color: #2c3e50;">Create Customer Account</h2>
                <form action="/customer-register?next={next}" method="POST">
                    <label>Full Name:</label><br><input type="text" name="fullname" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                    <label>Email Address:</label><br><input type="email" name="email" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                    <label>Password:</label><br><input type="password" name="password" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                    <button type="submit" style="background-color: #2ecc71; color: white; padding: 12px; border: none; width: 100%; margin-top: 15px; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;">Register</button>
                </form>
            </div>
        </div>
        {FOOTER}
    </body></html>
    """

@app.post("/customer-register")
def process_customer_register(fullname: str = Form(...), email: str = Form(...), password: str = Form(...), next: str = Form("/")):
    scrambled_password = hashlib.sha256(password.encode()).hexdigest()
    new_customer = Customer(fullname=fullname, email=email, password=scrambled_password)
    with Session(engine) as session:
        session.add(new_customer)
        session.commit()
    redirect = RedirectResponse(url=next, status_code=303)
    redirect.set_cookie(key="customer_email", value=email, httponly=True)
    return redirect

# --- 8. CHECKOUT & PURCHASE ---
@app.get("/checkout/{author_id}", response_class=HTMLResponse)
def checkout(request: Request, author_id: int, format: str = "Ebook"):
    customer_email = request.cookies.get("customer_email")
    if not customer_email:
        next_url = f"/checkout/{author_id}?format={format}"
        return RedirectResponse(url=f"/customer-gateway?next={next_url}", status_code=303)
    with Session(engine) as session:
        author = session.get(Author, author_id)
        if not author:
            return HTMLResponse(content=f"<h1>Book Not Found!</h1>{FOOTER}", status_code=404)
            
        price = author.ebook_price if format == "Ebook" else author.paperback_price
        action_url = f"/pay/{author.id}?format={format}"
            
        return f"""
        <html><body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
            {NAVBAR}
            <div style="padding: 50px; min-height: 60vh;">
                <div style="background: white; padding: 40px; border-radius: 8px; max-width: 400px; margin: auto; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center;">
                    <h2 style="color: #2c3e50;">Checkout - {format}</h2>
                    <img src="{author.cover_image}" style="width: 180px; height: 250px; object-fit: cover; border-radius: 4px; margin: 20px 0; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
                    <h3 style="margin: 0; color: #2c3e50;">{author.book_title}</h3>
                    <h4 style="color: #2ecc71; font-size: 24px; margin: 15px 0;">{price} TZS</h4>
                    <a href="{action_url}" style="background-color: #3498db; color: white; padding: 15px 20px; text-decoration: none; border-radius: 5px; display: block; margin-top: 20px; font-size: 16px; font-weight: bold;">Pay with Mobile Money</a>
                </div>
            </div>
            {FOOTER}
        </body></html>
        """

@app.get("/pay/{author_id}")
def process_payment(request: Request, author_id: int, format: str = "Ebook"):
    customer_email = request.cookies.get("customer_email")
    if not customer_email:
        return RedirectResponse(url="/customer-login", status_code=303)
    with Session(engine) as session:
        customer = session.exec(select(Customer).where(Customer.email == customer_email)).first()
        author = session.get(Author, author_id)
        existing = session.exec(select(Purchase).where(Purchase.customer_id == customer.id, Purchase.author_id == author.id, Purchase.format_bought == format)).first()
        
        if not existing:
            new_purchase = Purchase(
                customer_id=customer.id, author_id=author.id, book_title=author.book_title, 
                pdf_file=author.pdf_file if format == "Ebook" else None,
                format_bought=format,
                shipping_address="Address to be collected on next step" if format == "Paperback" else None
            )
            session.add(new_purchase)
            session.commit()
    return RedirectResponse(url="/my-library", status_code=303)

@app.get("/my-library", response_class=HTMLResponse)
def my_library(request: Request):
    customer_email = request.cookies.get("customer_email")
    if not customer_email:
        return RedirectResponse(url="/customer-login", status_code=303)
    with Session(engine) as session:
        customer = session.exec(select(Customer).where(Customer.email == customer_email)).first()
        purchases = session.exec(select(Purchase).where(Purchase.customer_id == customer.id)).all()
        
        html = f"<html><body style='font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;'>{NAVBAR}<div style='padding: 50px; min-height: 60vh;'><h1 style='text-align: center; color: #2c3e50;'>📖 My Library</h1><p style='text-align: center; color: #7f8c8d; margin-bottom: 30px;'>Welcome back, {customer.fullname}!</p>"
        
        if not purchases:
            html += "<p style='text-align: center; font-size: 18px;'>You haven't bought any books yet. <a href='/' style='color: #3498db;'>Visit the store</a></p>"
        else:
            html += "<div style='max-width: 700px; margin: auto;'>"
            for p in purchases:
                if p.format_bought == "Ebook":
                    action_html = f"<a href='/read/{p.id}' style='background:#2ecc71; color:white; padding:8px 15px; text-decoration:none; border-radius:4px; font-weight: bold;'>Read Now</a>"
                else:
                    action_html = f"<span style='color: #f39c12; font-weight: bold;'>📦 Printing & Shipping</span>"
                
                html += f"<div style='background: white; padding: 20px; margin-bottom: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); display: flex; justify-content: space-between; align-items: center;'><div><strong style='color: #2c3e50;'>{p.book_title}</strong><br><small style='color: #7f8c8d;'>{p.format_bought}</small></div> {action_html}</div>"
            html += "</div>"
            
        html += f"</div>{FOOTER}</body></html>"
        return html

@app.get("/read/{purchase_id}", response_class=HTMLResponse)
def read_book(request: Request, purchase_id: int):
    customer_email = request.cookies.get("customer_email")
    if not customer_email:
        return RedirectResponse(url="/customer-login", status_code=303)
    with Session(engine) as session:
        purchase = session.get(Purchase, purchase_id)
        customer = session.exec(select(Customer).where(Customer.email == customer_email)).first()
        if purchase.customer_id != customer.id or purchase.format_bought != "Ebook":
            return HTMLResponse(content=f"<h1>Access Denied</h1>{FOOTER}", status_code=403)
        return f"<html><head><title>Reading: {purchase.book_title}</title></head><body style='margin: 0; padding: 0; height: 100vh; display: flex; flex-direction: column; background-color: #2c3e50;'><div style='background: #1a252f; color: white; padding: 15px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.2);'><h3 style='margin: 0; font-family: Arial;'>Gophigo Secure Reader - {purchase.book_title}</h3><p style='font-size: 12px; color: #bdc3c7; margin: 5px 0 0 0;'>Licensed to: {customer_email}. Screenshots are traceable.</p></div><iframe src='https://docs.google.com/viewer?url={purchase.pdf_file}&embedded=true' style='flex: 1; border: none; width: 100%; height: 100vh;'></iframe></body></html>"

@app.get("/customer-logout")
def customer_logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("customer_email")
    return response

# --- 9. EMPLOYEE FLOW ---
@app.get("/employee-login", response_class=HTMLResponse)
def employee_login_page():
    return f"""
    <html><body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
        {NAVBAR}
        <div style="padding: 50px; min-height: 60vh;">
            <div style="background: white; padding: 30px; border-radius: 8px; max-width: 400px; margin: auto; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                <h2 style="text-align: center; color: #f39c12;">Staff Login</h2>
                <form action="/employee-login" method="POST">
                    <label>Email Address:</label><br><input type="email" name="email" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                    <label>Password:</label><br><input type="password" name="password" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                    <button type="submit" style="background-color: #f39c12; color: white; padding: 12px; border: none; width: 100%; margin-top: 15px; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;">Login</button>
                </form>
                <div style="text-align: center; margin-top: 15px;"><a href="/forgot-password" style="color: #e74c3c; text-decoration: none;">Forgot Password?</a></div>
                <div style="text-align: center; margin-top: 20px; border-top: 1px solid #eee; padding-top: 15px;">
                    <a href="/admin-login" style="color: #e74c3c; text-decoration: none; font-size: 14px; font-weight: bold;">Admin Login</a>
                </div>
            </div>
        </div>
        {FOOTER}
    </body></html>
    """

@app.post("/employee-login")
def process_employee_login(response: Response, email: str = Form(...), password: str = Form(...)):
    scrambled_password = hashlib.sha256(password.encode()).hexdigest()
    with Session(engine) as session:
        employee = session.exec(select(Employee).where(Employee.email == email, Employee.password == scrambled_password)).first()
        if employee:
            if employee.must_change_password:
                redirect = RedirectResponse(url="/employee-change-password", status_code=303)
                redirect.set_cookie(key="employee_email", value=employee.email, httponly=True)
                return redirect
            else:
                redirect = RedirectResponse(url="/employee-dashboard", status_code=303)
                redirect.set_cookie(key="employee_email", value=employee.email, httponly=True)
                return redirect
    return HTMLResponse(content=f"<h1>Login Failed. <a href='/employee-login'>Try again</a></h1>{FOOTER}", status_code=401)

@app.get("/employee-change-password", response_class=HTMLResponse)
def employee_change_password_page(request: Request):
    employee_email = request.cookies.get("employee_email")
    if not employee_email:
        return RedirectResponse(url="/employee-login", status_code=303)
    return f"""
    <html><body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
        {NAVBAR}
        <div style="padding: 50px; min-height: 60vh;">
            <div style="background: white; padding: 30px; border-radius: 8px; max-width: 400px; margin: auto; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                <h2 style="text-align: center; color: #e74c3c;">Change Your Password</h2>
                <p style="text-align: center; font-size: 14px; color: #7f8c8d;">For security reasons, you must change your initial password before accessing your dashboard.</p>
                <form action="/employee-change-password" method="POST">
                    <label>New Password:</label><br><input type="password" name="new_password" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;"><br>
                    <button type="submit" style="background-color: #e74c3c; color: white; padding: 12px; border: none; width: 100%; margin-top: 15px; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;">Update Password</button>
                </form>
            </div>
        </div>
        {FOOTER}
    </body></html>
    """

@app.post("/employee-change-password")
def process_employee_change_password(request: Request, new_password: str = Form(...)):
    employee_email = request.cookies.get("employee_email")
    if not employee_email:
        return RedirectResponse(url="/employee-login", status_code=303)
    with Session(engine) as session:
        employee = session.exec(select(Employee).where(Employee.email == employee_email)).first()
        if employee:
            employee.password = hashlib.sha256(new_password.encode()).hexdigest()
            employee.must_change_password = False
            session.add(employee)
            session.commit()
    return RedirectResponse(url="/employee-dashboard", status_code=303)

@app.get("/employee-dashboard", response_class=HTMLResponse)
def employee_dashboard(request: Request):
    employee_email = request.cookies.get("employee_email")
    if not employee_email:
        return RedirectResponse(url="/employee-login", status_code=303)
    with Session(engine) as session:
        employee = session.exec(select(Employee).where(Employee.email == employee_email)).first()
        if not employee:
            return RedirectResponse(url="/employee-login", status_code=303)
        if employee.must_change_password:
            return RedirectResponse(url="/employee-change-password", status_code=303)
            
        books = []
        if employee.role == "Reviewer":
            books = session.exec(select(Author).where(Author.book_status == "Pending Review")).all()
        elif employee.role == "Supervisor":
            books = session.exec(select(Author).where(Author.book_status == "Under Supervisor Review")).all()
        elif employee.role == "Approver":
            books = session.exec(select(Author).where(Author.book_status == "Pending Final Approval")).all()
            
        html = f"""
        <html><body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
            {NAVBAR}
            <div style="padding: 50px; min-height: 60vh;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h1 style="color: #2c3e50; margin: 0;">{employee.role} Dashboard</h1>
                        <p style="margin-top: 5px;">Welcome, <strong>{employee.fullname}</strong>.</p>
                    </div>
                    <a href="/employee-logout" style="background-color: #e74c3c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Sign Out</a>
                </div>
                <p>You have <strong>{len(books)}</strong> books waiting for your action.</p>
                <div style="overflow-x: auto; margin-top: 20px;">
                    <table border='1' style='border-collapse: collapse; width: 100%; background: white; box-shadow: 0 4px 8px rgba(0,0,0,0.1);'>
                        <tr style='background-color: #f39c12; color: white;'>
                            <th style="padding: 10px;">ID</th><th style="padding: 10px;">Cover</th><th style="padding: 10px;">Name</th><th style="padding: 10px;">Book</th><th style="padding: 10px;">Format</th><th style="padding: 10px;">Status</th><th style="padding: 10px;">Action</th>
                        </tr>
        """
        for book in books:
            action_btn = ""
            if employee.role == "Reviewer":
                action_btn = f"<a href='/employee-forward/{book.id}/Under Supervisor Review' style='background-color: #3498db; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;'>Send to Supervisor</a>"
            elif employee.role == "Supervisor":
                action_btn = f"<a href='/employee-forward/{book.id}/Pending Final Approval' style='background-color: #3498db; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;'>Send to Approver</a>"
            elif employee.role == "Approver":
                action_btn = f"<a href='/employee-approve/{book.id}' style='background-color: #2ecc71; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; margin-right: 5px;'>Approve & Publish</a> <a href='/employee-request-delete/{book.id}' style='background-color: #e74c3c; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;'>Request Deletion</a>"
            html += f"<tr><td style='padding: 10px; text-align: center;'>{book.id}</td><td style='padding: 10px; text-align: center;'><img src='{book.cover_image}' style='width: 50px; height: 60px; object-fit: cover;'></td><td style='padding: 10px;'>{book.fullname}</td><td style='padding: 10px;'>{book.book_title}</td><td style='padding: 10px;'>{book.book_format}</td><td style='padding: 10px; color: #f39c12; font-weight: bold;'>{book.book_status}</td><td style='padding: 10px;'>{action_btn}</td></tr>"
        html += f"</table></div></div>{FOOTER}</body></html>"
        return html

@app.get("/employee-forward/{author_id}/{new_status}")
def employee_forward(author_id: int, new_status: str):
    with Session(engine) as session:
        author = session.get(Author, author_id)
        if author:
            author.book_status = new_status
            session.add(author)
            session.commit()
    return RedirectResponse(url="/employee-dashboard", status_code=303)

@app.get("/employee-approve/{author_id}")
def employee_approve(author_id: int):
    with Session(engine) as session:
        author = session.get(Author, author_id)
        if author:
            author.book_status = "Approved"
            session.add(author)
            session.commit()
    return RedirectResponse(url="/employee-dashboard", status_code=303)

@app.get("/employee-request-delete/{author_id}")
def employee_request_delete(author_id: int):
    with Session(engine) as session:
        author = session.get(Author, author_id)
        if author:
            author.book_status = "Pending Deletion"
            session.add(author)
            session.commit()
    return RedirectResponse(url="/employee-dashboard", status_code=303)

@app.get("/employee-logout")
def employee_logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("employee_email")
    return response

# --- 10. ADMIN DASHBOARD & MODERATION ---
@app.get("/admin-login", response_class=HTMLResponse)
def admin_login_page():
    return f"<html><body style='font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;'>{NAVBAR}<div style='padding: 50px; min-height: 60vh;'><div style='background: white; padding: 30px; border-radius: 8px; max-width: 400px; margin: auto; box-shadow: 0 4px 8px rgba(0,0,0,0.1);'><h2 style='text-align: center; color: #e74c3c;'>Admin Login</h2><form action='/admin-login' method='POST'><label>Username:</label><br><input type='text' name='username' required style='width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;'><br><label>Password:</label><br><input type='password' name='password' required style='width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px;'><br><button type='submit' style='background-color: #e74c3c; color: white; padding: 12px; border: none; width: 100%; margin-top: 15px; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;'>Admin Login</button></form></div></div>{FOOTER}</body></html>"

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
        
        total_platform_revenue = 0
        total_author_payouts = 0
        for p in purchases:
            author = session.get(Author, p.author_id)
            if author:
                price = author.ebook_price if p.format_bought == "Ebook" else author.paperback_price
                total_platform_revenue += price * 0.50
                total_author_payouts += price * 0.50
        
    html = f"""
    <html><body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
        {NAVBAR}
        <div style="padding: 50px; min-height: 60vh;">
            <h1 style="color: #2c3e50;">Gophigo Admin Dashboard</h1>
            <div style='background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
                <h3 style="margin-top: 0;">Total Sales: {len(purchases)} copies</h3>
                <p style='font-size: 18px; margin-bottom: 0;'>Gophigo Revenue (50%): <strong style="color: #2ecc71;">{total_platform_revenue} TZS</strong> | Author Payouts (50%): <strong style="color: #f39c12;">{total_author_payouts} TZS</strong></p>
            </div>
            <div style="overflow-x: auto;">
                <table border='1' style='border-collapse: collapse; width: 100%; background: white; box-shadow: 0 4px 8px rgba(0,0,0,0.1);'>
                    <tr style='background-color: #34495e; color: white;'>
                        <th style="padding: 10px;">ID</th><th style="padding: 10px;">Cover</th><th style="padding: 10px;">Name</th><th style="padding: 10px;">Book</th><th style="padding: 10px;">Format</th><th style="padding: 10px;">Status</th><th style="padding: 10px;">Actions</th>
                    </tr>
    """
    for author in authors:
        status_color = "green" if author.membership_status == "Active" else "red"
        book_color = "green" if author.book_status == "Approved" else ("red" if author.book_status == "Rejected" else "#f39c12")
        action_btn = f"<a href='/admin-confirm-delete/{author.id}' style='background-color: #e74c3c; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;'>Confirm Delete</a>" if author.book_status == "Pending Deletion" else ""
        html += f"<tr><td style='padding: 10px; text-align: center;'>{author.id}</td><td style='padding: 10px; text-align: center;'><img src='{author.cover_image}' style='width: 50px; height: 60px; object-fit: cover; border-radius: 4px;'></td><td style='padding: 10px;'>{author.fullname}</td><td style='padding: 10px;'>{author.book_title}</td><td style='padding: 10px;'>{author.book_format}</td><td style='padding: 10px; color: {book_color}; font-weight: bold;'>{author.book_status}</td><td style='padding: 10px;'>{action_btn}</td></tr>"
    html += f"</table></div><br><a href='/admin-logout' style='background-color: #e74c3c; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;'>Admin Logout</a></div>{FOOTER}</body></html>"
    return html

@app.get("/admin-confirm-delete/{author_id}")
def admin_confirm_delete(author_id: int):
    with Session(engine) as session:
        author = session.get(Author, author_id)
        if author:
            session.delete(author)
            session.commit()
    return RedirectResponse(url="/admin", status_code=303)

@app.get("/admin-logout")
def admin_logout():
    response = RedirectResponse(url="/admin-login", status_code=303)
    response.delete_cookie("admin_session")
    return response
