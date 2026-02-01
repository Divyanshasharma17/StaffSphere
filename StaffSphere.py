import sqlite3
import hashlib
import re
from datetime import datetime,date

DB_NAME = "ems.db"
WORKING_DAYS = 22

# ---------------- DATABASE ---------------- #

def connect_db():
    return sqlite3.connect(DB_NAME)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_tables():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
                CREATE TABLE IF NOT EXISTS user
                (
                    user_id
                    INTEGER
                    PRIMARY
                    KEY
                    AUTOINCREMENT,
                    username
                    TEXT
                    UNIQUE,
                    password_hash
                    TEXT,
                    email
                    TEXT
                    UNIQUE,
                    role
                    TEXT
                )
                """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS employee (
        employee_id INTEGER PRIMARY KEY,
        user_id INTEGER,
        name TEXT,
        base_salary REAL,
        FOREIGN KEY(user_id) REFERENCES user(user_id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        attendance_date TEXT,
        status TEXT,
        FOREIGN KEY(employee_id) REFERENCES employee(employee_id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS leave_request (
        leave_id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        from_date TEXT,
        to_date TEXT,
        reason TEXT,
        status TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notification (
        notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER,
        receiver_id INTEGER,
        message TEXT,
        timestamp TEXT,
        status TEXT
    )
    """)

    conn.commit()
    conn.close()

# ---------------- DEFAULT DATA ---------------- #

def insert_default_data():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
    INSERT OR IGNORE INTO user (user_id, username, password_hash, email, role)
    VALUES (1, 'admin', ?, 'admin@gmail.com', 'admin')
    """, (hash_password("admin123"),))

    cur.execute("""
    INSERT OR IGNORE INTO user (user_id, username, password_hash, email, role)
    VALUES (2, 'Divyansha', ?, 'divya17@gmail.com', 'employee')
    """, (hash_password("divya@17"),))

    cur.execute("""
    INSERT OR IGNORE INTO employee
    VALUES (101, 2, 'Divya', 30000)
    """)

    conn.commit()
    conn.close()


# ---------------- LOGIN ---------------- #

def login():
    try:
        username = input("Username: ").strip()
        password = input("Password: ").strip()

        if not username or not password:
            raise ValueError("Username and password cannot be empty")

        password = hash_password(password)

        conn = connect_db()
        cur = conn.cursor()

        cur.execute("""
        SELECT user_id, role FROM user
        WHERE username=? AND password_hash=?
        """, (username, password))

        user = cur.fetchone()
        conn.close()

        if not user:
            raise ValueError("Invalid username or password")

        print("✅ Login Successful")
        return {"user_id": user[0], "role": user[1]}

    except Exception as e:
        print("❌", e)
        return None


# ---------------- MENUS ---------------- #

def admin_menu():
    print("\n--- ADMIN MENU ---")
    print("1. Mark Attendance")
    print("2. Calculate Salary")
    print("3. Leave Request Of Employee")
    print("4. Show All Employees")
    print("5. Register New Employee")
    print("0. Logout")



def employee_menu():
    print("\n--- EMPLOYEE MENU ---")
    print("1. View Salary")
    print("2. Apply Leave")
    print("3. View Notifications")
    print("0. Logout")

# ---------------- ATTENDANCE ---------------- #

def mark_attendance():
    try:
        emp_id = int(input("Employee ID: "))
        if emp_id <= 0:
            raise ValueError("Invalid Employee ID")
        status = input("Status (P/A): ").upper()

        if status not in ["P", "A"]:
            raise ValueError("Invalid Status")

        conn = connect_db()
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO attendance VALUES (NULL,?,?,?)
        """, (emp_id, date.today(), status))

        conn.commit()
        conn.close()
        print("✅ Attendance Marked")

    except Exception as e:
        print("❌", e)

# ---------------- SALARY ---------------- #

def calculate_salary(emp_id, display=True):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("SELECT base_salary FROM employee WHERE employee_id=?", (emp_id,))
    emp = cur.fetchone()
    if not emp:
        return None

    cur.execute("""
    SELECT COUNT(*) FROM attendance
    WHERE employee_id=? AND status='P'
    """, (emp_id,))
    present_days = cur.fetchone()[0]

    conn.close()

    net_salary = (emp[0] / WORKING_DAYS) * present_days

    if display:
        print("\n--- SALARY SLIP ---")
        print("Employee ID :", emp_id)
        print("Base Salary:", emp[0])
        print("Present Days:", present_days)
        print("Net Salary :", round(net_salary, 2))

    return net_salary

# ---------------- LEAVE MANAGEMENT ---------------- #

def apply_leave(user_id):
    try:
        conn = connect_db()
        cur = conn.cursor()

        cur.execute("SELECT employee_id FROM employee WHERE user_id=?", (user_id,))
        emp_id = cur.fetchone()[0]

        f = input("From Date (YYYY-MM-DD): ")
        t = input("To Date (YYYY-MM-DD): ")

        validate_date(f)
        validate_date(t)

        if f > t:
            raise ValueError("From date cannot be after To date")

        r = input("Reason: ")

        cur.execute("""
        INSERT INTO leave_request VALUES (NULL,?,?,?,?, 'Pending')
        """, (emp_id, f, t, r))

        conn.commit()
        conn.close()
        print("✅ Leave Applied")

    except Exception as e:
        print("❌", e)

def approve_leave():
    try:
        conn = connect_db()
        cur = conn.cursor()

        # Show pending leaves WITH REASON
        cur.execute("""
        SELECT l.leave_id, l.employee_id, e.name,
               l.from_date, l.to_date, l.reason
        FROM leave_request l
        JOIN employee e ON l.employee_id = e.employee_id
        WHERE l.status='Pending'
        """)
        leaves = cur.fetchall()

        if not leaves:
            print("No pending leave requests")
            conn.close()
            return

        print("\n--- PENDING LEAVE REQUESTS ---")
        for l in leaves:
            print(
                f"\nLeave ID : {l[0]}"
                f"\nEmp ID   : {l[1]}"
                f"\nName     : {l[2]}"
                f"\nFrom     : {l[3]}"
                f"\nTo       : {l[4]}"
                f"\nReason   : {l[5]}"
                "\n----------------------------"
            )

        leave_id = int(input("\nEnter Leave ID: "))
        decision = input("Approve (A) / Reject (R): ").upper()

        if decision not in ["A", "R"]:
            raise ValueError("Invalid choice")

        # Get employee user_id
        cur.execute("""
        SELECT u.user_id
        FROM leave_request l
        JOIN employee e ON l.employee_id = e.employee_id
        JOIN user u ON e.user_id = u.user_id
        WHERE l.leave_id=?
        """, (leave_id,))
        result = cur.fetchone()

        if not result:
            raise ValueError("Invalid Leave ID")

        employee_user_id = result[0]

        if decision == "A":
            status = "Approved"
            message = "✅ Your leave request has been APPROVED."
        else:
            status = "Rejected"
            message = "❌ Your leave request has been REJECTED."

        # Update leave status
        cur.execute(
            "UPDATE leave_request SET status=? WHERE leave_id=?",
            (status, leave_id)
        )

        # Send notification
        cur.execute("""
        INSERT INTO notification (sender_id, receiver_id, message, timestamp, status)
        VALUES (?, ?, ?, DATE('now'), 'Unread')
        """, (1, employee_user_id, message))

        conn.commit()
        conn.close()

        print(f"✅ Leave {status} and notification sent")

    except Exception as e:
        print("❌", e)


# ---------------- NOTIFICATIONS ---------------- #



def view_notifications(user_id):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT notification_id, message, timestamp
    FROM notification
    WHERE receiver_id=?
    """, (user_id,))

    notes = cur.fetchall()

    if not notes:
        print("No notifications")
        conn.close()
        return

    print("\n--- NOTIFICATIONS ---")
    for n in notes:
        print("📩", n[1], "|", n[2])

    # Mark as read
    cur.execute("""
    UPDATE notification SET status='Read'
    WHERE receiver_id=?
    """, (user_id,))

    conn.commit()
    conn.close()

# ---------------- Show all Employees ---------------- #

def show_all_employees():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT e.employee_id, e.name, u.username, e.base_salary
    FROM employee e
    JOIN user u ON e.user_id = u.user_id
    """)

    employees = cur.fetchall()
    conn.close()

    print("\n--- EMPLOYEE LIST ---")
    for e in employees:
        print(f"ID:{e[0]} | Name:{e[1]} | Username:{e[2]} | Salary:{e[3]}")

def register_employee():
    try:
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        email = input("Email: ").strip()
        name = input("Employee Name: ").strip()
        salary = float(input("Base Salary: "))

        validate_username(username)
        validate_password(password)
        validate_email(email)
        validate_salary(salary)

        conn = connect_db()
        cur = conn.cursor()

        # Check duplicate username or email
        cur.execute("SELECT * FROM user WHERE username=? OR email=?", (username, email))
        if cur.fetchone():
            raise ValueError("Username or Email already exists")

        # Insert user
        cur.execute("""
        INSERT INTO user (username, password_hash, email, role)
        VALUES (?, ?, ?, 'employee')
        """, (username, hash_password(password), email))

        user_id = cur.lastrowid
        emp_id = user_id + 100

        cur.execute("""
        INSERT INTO employee VALUES (?, ?, ?, ?)
        """, (emp_id, user_id, name, salary))

        conn.commit()
        conn.close()

        print("✅ Employee Registered Successfully")
        print("Employee ID:", emp_id)

    except Exception as e:
        print("❌", e)


#------------Employeee Panel------------#
def show_my_details(user_id):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT e.employee_id, e.name, u.username, e.base_salary
    FROM employee e
    JOIN user u ON e.user_id = u.user_id
    WHERE u.user_id=?
    """, (user_id,))

    emp = cur.fetchone()
    conn.close()

    if emp:
        print("\n--- MY DETAILS ---")
        print("Employee ID :", emp[0])
        print("Name        :", emp[1])
        print("Username    :", emp[2])
        print("Base Salary :", emp[3])
    else:
        print("❌ Employee record not found")
def get_employee_id(user_id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT employee_id FROM employee WHERE user_id=?", (user_id,))
    emp_id = cur.fetchone()[0]
    conn.close()
    return emp_id


def validate_username(username):
    if not re.match(r'^[A-Za-z0-9_]{4,15}$', username):
        raise ValueError("Username must be 4–15 characters (letters, numbers, _)")

def validate_password(password):
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters long")

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValueError("Invalid email format")

def validate_salary(salary):
    if salary <= 0:
        raise ValueError("Salary must be positive")

def validate_date(date_text):
    try:
        datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Date must be in YYYY-MM-DD format")

# ---------------- MAIN ---------------- #

def main():
    create_tables()
    insert_default_data()

    user = login()
    if not user:
        return

    # ---------- ADMIN PANEL ----------
    if user["role"] == "admin":
        while True:
            admin_menu()
            ch = input("Choice: ").strip()

            if ch == "1":
                mark_attendance()

            elif ch == "2":
                calculate_salary(int(input("Employee ID: ")))

            elif ch == "3":
                approve_leave()

            elif ch == "4":
                show_all_employees()

            elif ch == "5":
                register_employee()

            elif ch == "0":
                print("👋 Admin logged out")
                break

            else:
                print("❌ Invalid choice")

    # ---------- EMPLOYEE PANEL ----------
    elif user["role"] == "employee":
        show_my_details(user["user_id"])

        while True:
            employee_menu()
            ch = input("Choice: ").strip()

            if ch == "1":
                calculate_salary(get_employee_id(user["user_id"]))

            elif ch == "2":
                apply_leave(user["user_id"])

            elif ch == "3":
                view_notifications(user["user_id"])

            elif ch == "0":
                print("👋 Employee logged out")
                break

            else:
                print("❌ Invalid choice")



if __name__ == "__main__":
    main()
