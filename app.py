import os
import secrets
import sqlite3
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", BASE_DIR / "inventory.db"))


def init_db():
    """Create a fresh local database with demo data when one does not exist."""
    if DATABASE_PATH.exists():
        return

    conn = sqlite3.connect(DATABASE_PATH)
    with open(BASE_DIR / "schema.sql", encoding="utf-8") as schema_file:
        conn.executescript(schema_file.read())

    demo_users = [
        ("admin", "admin123", "admin"),
        ("manager", "manager123", "manager"),
        ("regUser", "user123", "regUser"),
    ]
    conn.executemany(
        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
        [(username, generate_password_hash(password), role) for username, password, role in demo_users],
    )
    conn.commit()
    conn.close()


init_db()

# Function to establish a database connection
def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Decorator to require login for routes
def login_required(f):
    @wraps(f)
    def wrapped_function(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped_function

# Decorator to require specific roles for routes
def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def wrapped_function(*args, **kwargs):
            if "role" not in session:
                return redirect(url_for("login"))
            if session["role"] not in allowed_roles:
                return "Access Denied", 403
            return f(*args, **kwargs)
        return wrapped_function
    return decorator

# Home route, accessible to all logged-in users
@app.route("/")
@login_required
@role_required("admin", "manager", "regUser")
def home():
    return render_template("home.html")

# Inventory route for viewing and adding items
@app.route("/inventory", methods=["GET", "POST"])
@login_required
@role_required("admin", "manager", "regUser")
def inventory():
    conn = get_db_connection()

    if request.method == "POST":
        name = request.form["name"]
        sku = request.form["sku"]
        quantity = request.form["quantity"]

        conn.execute(
            "INSERT INTO items (name, sku, quantity) VALUES (?, ?, ?)",
            (name, sku, quantity)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("inventory"))

    items = conn.execute("SELECT * FROM items").fetchall()
    conn.close()
    return render_template("inventory.html", items=items)

# Billing route for processing sales
@app.route("/billing", methods=["GET", "POST"])
@login_required
@role_required("admin", "manager", "regUser")
def billing():
    conn = get_db_connection()

    if request.method == "POST":
        item_id = request.form["item"]
        quantity = int(request.form["quantity"])
        customer = request.form["customer"]

        item = conn.execute(
            "SELECT * FROM items WHERE id = ?",
            (item_id,)
        ).fetchone()

        if item and item["quantity"] >= quantity:
            total_charge = quantity * 20.0  # temp price

            # update inventory
            conn.execute(
                "UPDATE items SET quantity = quantity - ? WHERE id = ?",
                (quantity, item_id)
            )
            conn.execute(
    """
    INSERT INTO stock_logs (item_id, change_type, amount)
    VALUES (?, ?, ?)
    """,
    (item_id, "SALE", -quantity)
)

            # insert transaction
            conn.execute("""
                INSERT INTO transactions (item_id, item_name, quantity, total_charge, customer)
                VALUES (?, ?, ?, ?, ?)
            """, (item_id, item["name"], quantity, total_charge, customer))

            conn.commit()

    items = conn.execute("SELECT * FROM items").fetchall()

    transactions = conn.execute("""
        SELECT * FROM transactions ORDER BY created_at DESC
    """).fetchall()

    conn.close()

    return render_template(
        "billing.html",
        items=items,
        transactions=transactions
    )

# Reports route for viewing sales and logs
@app.route("/reports")
@login_required
@role_required("admin", "manager",)
def reports():
    conn = get_db_connection()

    total_sales = conn.execute(
        "SELECT SUM(total_charge) FROM transactions"
    ).fetchone()[0]

    total_items_sold = conn.execute(
        "SELECT SUM(quantity) FROM transactions"
    ).fetchone()[0]

    logs = conn.execute(
        "SELECT * FROM stock_logs ORDER BY timestamp DESC"
    ).fetchall()

    low_stock = conn.execute(
    "SELECT * FROM items WHERE quantity <= 5"
    ).fetchall()

    access_logs = conn.execute(
    "SELECT * FROM access_logs ORDER BY timestamp DESC"
    ).fetchall()
    

    conn.close()

    return render_template(
        "reports.html",
        total_sales=total_sales or 0,
        total_items_sold=total_items_sold or 0,
        logs=logs,
        low_stock=low_stock,
        access_logs=access_logs
    )

# Route to increase stock by 1
@app.route("/stock_in", methods=["POST"])
@login_required
def stock_in():
    id = request.form["id"]
    conn = get_db_connection()
    conn.execute("UPDATE items SET quantity = quantity + 1 WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("inventory"))

# Route to decrease stock by 1 if available
@app.route("/stock_out", methods=["POST"])
@login_required
def stock_out():
    id = request.form["id"]
    conn = get_db_connection()

    item = conn.execute("SELECT quantity FROM items WHERE id = ?", (id,)).fetchone()

    if item["quantity"] > 0:
        conn.execute("UPDATE items SET quantity = quantity - 1 WHERE id = ?", (id,))
        conn.commit()

    conn.close()
    return redirect(url_for("inventory"))

# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    conn = get_db_connection()

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):
            session["username"] = user["username"]
            session["role"] = user["role"]
            conn = get_db_connection()
            conn.execute("INSERT INTO access_logs (username, action) VALUES (?, ?)", (user["username"], "Logged In"))
            conn.commit()
            conn.close()
            
            return redirect(url_for("home"))
        else:
            conn = get_db_connection()
            conn.execute("INSERT INTO access_logs (username, action) VALUES (?, ?)", (username, "Failed Login Attempt"))
            conn.commit()
            conn.close()
            return render_template("login.html", error="Invalid credentials")

    conn.close()
    return render_template("login.html")

# Logout route
@app.route("/logout")
def logout():
    if "username" in session:
        conn = get_db_connection()
        conn.execute("INSERT INTO access_logs (username, action) VALUES (?, ?)", (session["username"], "Logged Out"))
        conn.commit()
        conn.close()
    session.clear()
    return redirect(url_for("login"))

# User management route for admins
@app.route("/user_management", methods=["GET", "POST"])
@login_required
@role_required("admin")
def user_management():
    conn = get_db_connection()

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]

        existing_user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if existing_user:
            users = conn.execute("SELECT * FROM users ORDER BY id ASC").fetchall()
            conn.close()
            return render_template(
                "user_management.html",
                error="Username already exists.",
                users=users
            )

        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, generate_password_hash(password), role)
        )
        conn.commit()

        users = conn.execute("SELECT * FROM users ORDER BY id ASC").fetchall()
        conn.close()
        return render_template(
            "user_management.html",
            success="User added successfully.",
            users=users
        )

    users = conn.execute("SELECT * FROM users ORDER BY id ASC").fetchall()
    conn.close()
    return render_template("user_management.html", users=users)

# Route to delete a user
@app.route("/delete_user", methods=["POST"])
@login_required
@role_required("admin")
def delete_user():
    user_id = request.form["user_id"]

    conn = get_db_connection()

    user_to_delete = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    if user_to_delete:
        if user_to_delete["username"] == session["username"]:
            users = conn.execute("SELECT * FROM users ORDER BY id ASC").fetchall()
            conn.close()
            return render_template(
                "user_management.html",
                error="You cannot delete the account you are currently logged into.",
                users=users
            )

        conn.execute(
            "DELETE FROM users WHERE id = ?",
            (user_id,)
        )
        conn.commit()

    conn.close()
    return redirect(url_for("user_management"))

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")




