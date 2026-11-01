from fastapi import FastAPI, Form, Depends, HTTPException, status, Request, Response, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, Field, Session, create_engine, select, func
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
    reset_token: str | None = Field(default=None)
    cover_image: str | None = Field(default=None) 
    pdf_file: str | None = Field(default=None) 

class Customer(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    fullname: str
    email: str
    password: str
    reset_token: str | None = Field(default=None)

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
    reset_token: str | None = Field(default=None)

# NEW: Review Table
class Review(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    author_id: int
    customer_id: int
    rating: int
    comment: str

SQLModel.metadata.create_all(engine)

# Create default employees
with Session(engine) as session:
    if not session.exec(select(Employee)).first():
        session.add(Employee(fullname="Reviewer John", email="reviewer@gophigo.com", password=hashlib.sha256("pass123".encode()).hexdigest(), role="Reviewer"))
        session.add(Employee(fullname="Supervisor Mary", email="supervisor@gophigo.com", password=hashlib.sha256("pass123".encode()).hexdigest(), role="Supervisor"))
        session.add(Employee(fullname="Approver Boss", email="approver@gophigo.com", password=hashlib.sha256("pass123".encode()).hexdigest(), role="Approver"))
        session.commit()

# --- 3. DYNAMIC SHARED DESIGN ---
def get_navbar(request: Request):
    author_email = request.cookies.get("author_email")
    customer_email = request.cookies.get("customer_email")
    employee_email = request.cookies.get("employee_email")
    admin_session = request.cookies.get("admin_session")

    links = ''

    if author_email:
        links += f'<a href="/author-dashboard" style="color: #f39c12; text-decoration: none; margin-left: 20px; font-size: 16px; font-weight: bold;">Author Dashboard</a>'
        links += '<a href="/logout" style="color: #e74c3c; text-decoration: none; margin-left: 20px; font-size: 16px;">Logout</a>'
    elif customer_email:
        links += f'<a href="/my-library" style="color: #2ecc71; text-decoration: none; margin-left: 20px; font-size: 16px; font-weight: bold;">My Library</a>'
        links += '<a href="/customer-logout" style="color: #e74c3c; text-decoration: none; margin-left: 20px; font-size: 16px;">Logout</a>'
    elif employee_email:
        links += f'<a href="/employee-dashboard" style="color: #f39c12; text-decoration: none; margin-left: 20px; font-size: 16px; font-weight: bold;">Staff Dashboard</a>'
        links += '<a href="/employee-logout" style="color: #e74c3c; text-decoration: none; margin-left: 20px; font-size: 16px;">Logout</a>'
    elif admin_session:
        links += f'<a href="/admin" style="color: #e74c3c; text-decoration: none; margin-left: 20px; font-size: 16px; font-weight: bold;">Admin Dashboard</a>'
        links += '<a href="/admin-logout" style="color: #e74c3c; text-decoration: none; margin-left: 20px; font-size: 16px;">Logout</a>'
    else:
        links += '<a href="/author-portal" style="color: white; text-decoration: none; margin-left: 20px; font-size: 16px;">Author Portal</a>'
        links += '<a href="/customer-login" style="color: white; text-decoration: none; margin-left: 20px; font-size: 16px;">Customer Login</a>'
        links += '<a href="/employee-login" style="color: #f39c12; text-decoration: none; margin-left: 20px; font-size: 16px; font-weight: bold;">Staff Login</a>'

    return f"""
    <nav style="background-color: #2c3e50; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; font-family: 'Poppins', Arial, sans-serif; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <div style="font-size: 24px; font-weight: bold;">
            <a href="/" style="color: white; text-decoration: none;">📚 Gophigo Bookstore</a>
        </div>
        <div>{links}</div>
    </nav>
    """

FOOTER = """
<footer style="background-color: #2c3e50; color: white; text-align: center; padding: 20px; margin-top: 50px; font-family: Arial; font-size: 14px;">
    <p>&copy; 2026 Gophigo Publishing. All rights reserved.</p>
    <p>Empowering Authors Globally.</p>
</footer>
"""
# --- 4. THE STORE (WITH SEARCH, FORMATS, & REVIEWS) ---
@app.get("/", response_class=HTMLResponse)
def store(request: Request, search: str = None):
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
                    .book-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; padding: 20px; }}
                </style>
            </head>
            <body style="margin: 0; padding: 0; background-color: #f4f4f4;">
                {get_navbar(request)}
                <div style="padding: 50px; min-height: 60vh;">
                    <h1 style="text-align: center; color: #2c3e50; margin-bottom: 20px;">Gophigo Bookstore</h1>
                    
                    <form action="/" method="GET" style="max-width: 500px; margin: 0 auto 40px auto; display: flex; gap: 10px;">
                        <input type="text" name="search" placeholder="Search by book title or author..." value="{search if search else ''}" style="flex: 1; padding: 12px; border: 1px solid #ccc; border-radius: 5px; font-size: 16px;">
                        <button type="submit" style="background-color: #3498db; color: white; padding: 12px 25px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;">Search</button>
                    </form>

                    <div class="book-grid">
        """
        
        if not active_authors:
            html += "<p style='text-align: center; font-size: 18px; color: #7f8c8d; grid-column: 1/-1;'>No books found matching your search.</p>"
            
        for author in active_authors:
            reviews = session.exec(select(Review).where(Review.author_id == author.id)).all()
            avg_rating = sum([r.rating for r in reviews]) / len(reviews) if reviews else 0
            stars = "⭐" * int(round(avg_rating)) if reviews else "No reviews yet"

            format_badge = f"<span style='background: #e0e0e0; color: #333; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 600;'>{author.book_format}</span>"
            
            buy_buttons = ""
            if author.book_format in ["Ebook", "Both"]:
                buy_buttons += f"<a href='/checkout/{author.id}?format=Ebook' class='buy-btn' style='background-color: #3498db; color: white; padding: 10px; border-radius: 5px; text-decoration: none; display: block; margin-bottom: 5px; font-weight: bold;'>Buy Ebook ({author.ebook_price} TZS)</a>"
            if author.book_format in ["Paperback", "Both"]:
                buy_buttons += f"<a href='/checkout/{author.id}?format=Paperback' class='buy-btn' style='background-color: #f39c12; color: white; padding: 10px; border-radius: 5px; text-decoration: none; display: block; font-weight: bold;'>Buy Paperback ({author.paperback_price} TZS)</a>"

            html += f"""
            <div class="book-card" style='background: white; border-radius: 8px; padding: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center;'>
                <img src="{author.cover_image}" alt="Book Cover" style="width: 100%; height: 250px; object-fit: cover; border-radius: 4px; margin-bottom: 15px; border: 1px solid #eee;">
                <h3 style='color: #2c3e50; margin: 0 0 5px 0; font-size: 18px; font-weight: 600;'>{author.book_title}</h3>
                <p style='color: #7f8c8d; margin: 0 0 5px 0; font-size: 13px;'>By {author.fullname}</p>
                <p style='color: #f1c40f; margin: 0 0 10px 0; font-size: 14px;'>{stars} ({len(reviews)})</p>
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

# --- 5. AUTHOR PORTAL & REGISTRATION ---
@app.get("/author-portal", response_class=HTMLResponse)
def author_portal(request: Request):
    return f"""
    <html>
        <head>
            <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap" rel="stylesheet">
            <style>
                body {{ font-family: 'Poppins', sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; }}
                .hero {{ background: linear-gradient(135deg, #1a252f 0%, #2c3e50 100%); color: white; padding: 100px 20px; text-align: center; }}
                .hero h1 {{ font-size: 48px; margin-bottom: 20px; }}
                .hero p {{ font-size: 20px; color: #bdc3c7; margin-bottom: 40px; }}
                .features {{ display: flex; justify-content: center; gap: 30px; padding: 50px 20px; flex-wrap: wrap; }}
                .feature-card {{ background: white; padding: 30px; border-radius: 8px; width: 300px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
                .feature-card h3 {{ color: #3498db; }}
                .btn {{ padding: 15px 30px; border-radius: 5px; text-decoration: none; font-size: 18px; font-weight: bold; display: inline-block; margin: 10px; }}
            </style>
        </head>
        <body>
            {get_navbar(request)}
            <div class="hero">
                <h1>Become a Gophigo Author</h1>
                <p>The global marketplace where authors keep 50% of their sales.</p>
                <a href="/register" class="btn" style="background-color: #3498db; color: white;">✍️ Register as a New Author</a>
                <a href="/login" class="btn" style="background-color: #2ecc71; color: white;">Author Login</a>
            </div>
            <div class="features">
                <div class="feature-card">
                    <h3>💰 50% Royalties</h3>
                    <p>We believe in fair pay. Authors keep half of every sale.</p>
                </div>
                <div class="feature-card">
                    <h3>🔒 Secure DRM</h3>
                    <p>Your manuscripts are protected. No unauthorized downloads.</p>
                </div>
                <div class="feature-card">
                    <h3>🌍 Global Reach</h3>
                    <p>Sell your ebooks and paperbacks to readers everywhere.</p>
                </div>
            </div>
            {FOOTER}
        </body>
    </html>
    """

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return f"""
    <html><body style="font-family: Arial; margin: 0; padding: 0; background-color: #f4f4f4;">
        {get_navbar(request)}
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
