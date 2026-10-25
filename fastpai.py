from fastapi import FastAPI, Form, Depends, HTTPException, status, Request, Response, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, Field, Session, create_engine, select
import hashlib
import secrets
import shutil
import os
import uuid

app = FastAPI()

# --- 1. STATIC FILES SETUP (For Images) ---
os.makedirs("static/covers", exist_ok=True)
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

class Sale(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    author_id: int
    book_title: str
    sale_amount: float
    platform_cut: float
    author_cut: float

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
            <a href="/login" style="color: #2c3e50;">Author Login</a> | <a href="/admin-login" style="color: #e74c3c;">Admin Login</a>
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
                    <label>Full Name:</label><br>
                    <input type="text" name="fullname" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                    <label>Email Address:</label><br>
                    <input type="email" name="email" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                    <label>Password:</label><br>
                    <input type="password" name="password" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                    <label>Book Title:</label><br>
                    <input type="text" name="book_title" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                    <label>Book Price (TZS):</label><br>
                    <input type="number" name="price" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                    <label>Book Cover Image:</label><br>
                    <input type="file" name="cover" accept="image/*" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                    <button type="submit" style="background-color: #2ecc71; color: white; padding: 10px; border: none; width: 100%; margin-top: 10px;">Submit</button>
                </form>
            </div>
        </body>
    </html>
    """

@app.post("/register", response_class=HTMLResponse)
def process_registration(
    fullname: str = Form(...), 
    email: str = Form(...), 
    password: str = Form(...), 
    book_title: str = Form(...), 
    price: float = Form(...),
    cover: UploadFile = File(...)
):
    file_extension = cover.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = f"static/covers/{unique_filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(cover.file, buffer)

    scrambled_password = hashlib.sha256(password.encode()).hexdigest()
    new_author = Author(
        fullname=fullname, 
        email=email, 
        password=scrambled_password, 
        book_title=book_title, 
        price=price,
        cover_image=unique_filename
    )
    
    with Session(engine) as session:
        session.add(new_author)
        session.commit()
    
    return f"""
    <html>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1 style="color: #2ecc71;">Registration Successful!</h1>
            <p>Thank you, <strong>{fullname}</strong>.</p>
            <a href="/login">Go to Login Page</a>
        </body>
    </html>
    """

@app.get("/store", response_class=HTMLResponse)
def store():
    with Session(engine) as session:
        active_authors = session.exec(select(Author).where(
            Author.membership_status == "Active", 
            Author.book_status == "Approved"
        )).all()
        
        html = "<html><body style='font-family: Arial; padding: 50px; background-color: #f4f4f4;'>"
        html += "<h1 style='text-align: center;'>📚 Gophigo Bookstore</h1>"
        html += "<div style='display: flex; flex-wrap: wrap; gap: 20px; justify-content: center;'>"
        
        if not active_authors:
            html += "<p>No books available yet. Check back later!</p>"
            
        for author in active_authors:
            html += f"""
            <div style='background: white; border-radius: 8px; padding: 20px; width: 250px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); text-align: center;'>
                <img src="/static/covers/{author.cover_image}" alt="Book Cover" style="width: 100%; height: 300px; object-fit: cover; border-radius: 4px; margin-bottom: 15px; border: 1px solid #ccc; background-color: #e0e0e0;">
                <h3 style='color: #2c3e50; margin: 0;'>{author.book_title}</h3>
                <p style='color: #7f8c8d; margin: 5px 0;'>By {author.fullname}</p>
                <h4 style='color: #2ecc71;'>{author.price} TZS</h4>
                <button style='background-color: #3498db; color: white; padding: 10px; border: none; border-radius: 5px; width: 100%; cursor: pointer;'>Buy Now</button>
            </div>
            """
            
        html += "</div><br><br><div style='text-align: center;'><a href='/'>Back to Home</a></div></body></html>"
        return html

@app.get("/login", response_class=HTMLResponse)
def login_page():
    return """
    <html>
        <body style="font-family: Arial; padding: 50px; background-color: #f4f4f4;">
            <div style="background: white; padding: 30px; border-radius: 8px; max-width: 400px; margin: auto;">
                <h2>Author Login</h2>
                <form action="/login" method="POST">
                    <label>Email Address:</label><br>
                    <input type="email" name="email" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                    <label>Password:</label><br>
                    <input type="password" name="password" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                    <button type="submit" style="background-color: #3498db; color: white; padding: 10px; border: none; width: 100%; margin-top: 10px;">Login</button>
                </form>
                <div style="text-align: center; margin-top: 15px;">
                    <a href="/forgot-password" style="color: #e74c3c; font-size: 14px;">Forgot Password?</a>
                </div>
            </div>
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
        else:
            return HTMLResponse(content="<h1>Login Failed. <a href='/login'>Try again</a></h1>", status_code=401)

@app.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page():
    return """
    <html>
        <body style="font-family: Arial; padding: 50px; background-color: #f4f4f4;">
            <div style="background: white; padding: 30px; border-radius: 8px; max-width: 400px; margin: auto;">
                <h2>Reset Password</h2>
                <form action="/forgot-password" method="POST">
                    <label>Email Address:</label><br>
                    <input type="email" name="email" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                    <button type="submit" style="background-color: #e74c3c; color: white; padding: 10px; border: none; width: 100%; margin-top: 10px;">Generate Reset Link</button>
                </form>
            </div>
        </body>
    </html>
    """

@app.post("/forgot-password", response_class=HTMLResponse)
def process_forgot_password(email: str = Form(...)):
    with Session(engine) as session:
        author = session.exec(select(Author).where(Author.email == email)).first()
        if author:
            token = secrets.token_hex(16)
            author.reset_token = token
            session.add(author)
            session.commit()
            reset_link = f"http://127.0.0.1:8001/reset-password?token={token}"
            return f"""
            <html>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h2 style="color: #2ecc71;">Simulated Email Sent!</h2>
                    <p>In a real application, an email would be sent to <strong>{email}</strong>.</p>
                    <a href="{reset_link}" style="background-color: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Click Here to Reset Password</a>
                </body>
            </html>
            """
        else:
            return HTMLResponse(content="<h1>Email not found. <a href='/forgot-password'>Try again</a></h1>", status_code=404)

@app.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(token: str):
    return f"""
    <html>
        <body style="font-family: Arial; padding: 50px; background-color: #f4f4f4;">
            <div style="background: white; padding: 30px; border-radius: 8px; max-width: 400px; margin: auto;">
                <h2>Enter New Password</h2>
                <form action="/reset-password" method="POST">
                    <input type="hidden" name="token" value="{token}">
                    <label>New Password:</label><br>
                    <input type="password" name="new_password" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                    <button type="submit" style="background-color: #2ecc71; color: white; padding: 10px; border: none; width: 100%; margin-top: 10px;">Update Password</button>
                </form>
            </div>
        </body>
    </html>
    """

@app.post("/reset-password", response_class=HTMLResponse)
def process_reset_password(token: str = Form(...), new_password: str = Form(...)):
    with Session(engine) as session:
        author = session.exec(select(Author).where(Author.reset_token == token)).first()
        if author:
            author.password = hashlib.sha256(new_password.encode()).hexdigest()
            author.reset_token = None 
            session.add(author)
            session.commit()
            return """
            <html>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1 style="color: #2ecc71;">Password Updated!</h1>
                    <a href="/login">Go to Login</a>
                </body>
            </html>
            """
        else:
            return HTMLResponse(content="<h1>Invalid token. <a href='/forgot-password'>Try again</a></h1>", status_code=400)

@app.get("/author-dashboard", response_class=HTMLResponse)
def author_dashboard(request: Request):
    author_email = request.cookies.get("author_email")
    if not author_email:
        return RedirectResponse(url="/login", status_code=303)
    
    with Session(engine) as session:
        author = session.exec(select(Author).where(Author.email == author_email)).first()
        if not author:
            return RedirectResponse(url="/login", status_code=303)

        author_sales = session.exec(select(Sale).where(Sale.author_id == author.id)).all()
        total_earned = sum(sale.author_cut for sale in author_sales)

        if author.membership_status == "Pending":
            payment_html = """
            <div style="background: #fff3cd; padding: 20px; border-radius: 8px; border: 1px solid #ffeeba; margin-top: 20px;">
                <h3 style="color: #856404;">Membership Payment Required</h3>
                <a href="/pay-membership" style="background-color: #2ecc71; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Pay 20,000 TZS Annually</a>
            </div>
            """
        else:
            review_color = "green" if author.book_status == "Approved" else ("red" if author.book_status == "Rejected" else "#856404")
            review_bg = "#d4edda" if author.book_status == "Approved" else ("#f8d7da" if author.book_status == "Rejected" else "#fff3cd")
            
            payment_html = f"""
            <div style="background: #d4edda; padding: 20px; border-radius: 8px; margin-top: 20px;">
                <h3 style="color: #155724;">✅ Membership Active</h3>
                <h4 style="color: #155724;">Total Earnings: {total_earned} TZS</h4>
            </div>
            <div style="background: {review_bg}; padding: 20px; border-radius: 8px; margin-top: 10px;">
                <h4 style="color: {review_color};">Book Status: {author.book_status}</h4>
            </div>
            """

        return f"""
        <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: #2c3e50;">Author Dashboard</h1>
                <h2>Welcome Back, {author.fullname}!</h2>
                <div style="background: #f9f9f9; padding: 20px; border-radius: 8px; max-width: 500px; margin: auto;">
                    <img src="/static/covers/{author.cover_image}" style="width: 150px; height: 200px; object-fit: cover; border-radius: 4px; margin-bottom: 15px;">
                    <h3>Your Book: {author.book_title}</h3>
                    <p><strong>Price:</strong> {author.price} TZS</p>
                    {payment_html}
                </div>
                <br><br>
                <a href="/logout" style="background-color: #e74c3c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Logout</a>
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

@app.get("/admin-login", response_class=HTMLResponse)
def admin_login_page():
    return """
    <html>
        <body style="font-family: Arial; padding: 50px; background-color: #f4f4f4;">
            <div style="background: white; padding: 30px; border-radius: 8px; max-width: 400px; margin: auto;">
                <h2>Admin Login</h2>
                <form action="/admin-login" method="POST">
                    <label>Username:</label><br>
                    <input type="text" name="username" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                    <label>Password:</label><br>
                    <input type="password" name="password" required style="width: 100%; padding: 8px; margin: 10px 0;"><br>
                    <button type="submit" style="background-color: #e74c3c; color: white; padding: 10px; border: none; width: 100%; margin-top: 10px;">Admin Login</button>
                </form>
            </div>
        </body>
    </html>
    """

@app.post("/admin-login")
def admin_login(response: Response, username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "gophigo2026":
        redirect = RedirectResponse(url="/admin", status_code=303)
        redirect.set_cookie(key="admin_session", value="true", httponly=True)
        return redirect
    else:
        return HTMLResponse(content="<h1>Invalid Admin Credentials. <a href='/admin-login'>Try again</a></h1>", status_code=401)

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    if request.cookies.get("admin_session") != "true":
        return RedirectResponse(url="/admin-login", status_code=303)

    with Session(engine) as session:
        authors = session.exec(select(Author)).all()
        sales = session.exec(select(Sale)).all()
        
        total_sales = sum(sale.sale_amount for sale in sales)
        total_platform_revenue = sum(sale.platform_cut for sale in sales)
        total_author_payouts = sum(sale.author_cut for sale in sales)
    
    html = "<html><body style='font-family: Arial; padding: 50px; background-color: #f4f4f4;'>"
    html += "<h1>Gophigo Admin Dashboard</h1>"
    
    html += f"""
    <div style='background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; display: flex; justify-content: space-around;'>
        <div><h3>Total Book Sales</h3><p style='font-size: 24px;'>{total_sales} TZS</p></div>
        <div><h3>Gophigo Revenue (30%)</h3><p style='color: #2ecc71; font-size: 24px;'>{total_platform_revenue} TZS</p></div>
        <div><h3>Author Payouts (70%)</h3><p style='color: #f39c12; font-size: 24px;'>{total_author_payouts} TZS</p></div>
    </div>
    """
    
    html += "<table border='1' style='border-collapse: collapse; width: 100%; background: white;'><tr style='background-color: #34495e; color: white;'><th>Cover</th><th>Name</th><th>Book</th><th>Status</th><th>Book Quality</th><th>Actions</th></tr>"
    
    for author in authors:
        status_color = "green" if author.membership_status == "Active" else "red"
        
        if author.membership_status == "Active" and author.book_status == "Approved":
            sale_btn = f"<a href='/simulate-sale/{author.id}' style='background-color: #3498db; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; margin-right: 5px;'>Simulate Sale</a>"
        else:
            sale_btn = ""

        if author.membership_status == "Active" and author.book_status == "Pending Review":
            approve_btn = f"<a href='/approve/{author.id}' style='background-color: #2ecc71; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; margin-right: 5px;'>Approve</a>"
            reject_btn = f"<a href='/reject/{author.id}' style='background-color: #e74c3c; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;'>Reject</a>"
            action_buttons = approve_btn + reject_btn
        else:
            action_buttons = sale_btn
            
        book_color = "green" if author.book_status == "Approved" else ("red" if author.book_status == "Rejected" else "#f39c12")
        
        html += f"<tr><td><img src='/static/covers/{author.cover_image}' style='width: 50px; height: 60px; object-fit: cover; border-radius: 4px;'></td><td>{author.fullname}</td><td>{author.book_title}</td><td style='color: {status_color}; font-weight: bold;'>{author.membership_status}</td><td style='color: {book_color}; font-weight: bold;'>{author.book_status}</td><td>{action_buttons}</td></tr>"
        
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

@app.get("/simulate-sale/{author_id}")
def simulate_sale(author_id: int):
    with Session(engine) as session:
        author = session.get(Author, author_id)
        if author and author.membership_status == "Active" and author.book_status == "Approved":
            sale_amount = author.price
            platform_cut = sale_amount * 0.30
            author_cut = sale_amount * 0.70
            
            new_sale = Sale(
                author_id=author.id,
                book_title=author.book_title,
                sale_amount=sale_amount,
                platform_cut=platform_cut,
                author_cut=author_cut
            )
            session.add(new_sale)
            session.commit()
            
    return RedirectResponse(url="/admin", status_code=303)

@app.get("/admin-logout")
def admin_logout():
    response = RedirectResponse(url="/admin-login", status_code=303)
    response.delete_cookie("admin_session")
    return response
