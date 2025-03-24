from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime
import sqlite3
import bcrypt

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DATABASE = 'finance_tracker.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            payment_method TEXT NOT NULL,
            recurring INTERGER,
            last_added DATE,
            salary_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS salaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    savings INTEGER NOT NULL,
    salary_type TEXT NOT NULL DEFAULT Secondary,
    FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()
init_db()
@app.route('/salaries')
def salaries():
    if 'username' in session:
        user_id = session['user_id']
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('SELECT * FROM salaries WHERE user_id = ?', (user_id,))
        salaries = c.fetchall()
        conn.close()

        return render_template('salaries.html', salaries=salaries)
    else:
        return redirect(url_for('login'))
    
@app.route('/add_salary', methods=['GET', 'POST'])
def add_salary():
    if 'username' not in session:
        flash('You must be logged in to add a salary.', 'error')
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    user_id = session['user_id']

    # Check if a primary salary already exists
    c.execute("SELECT COUNT(*) FROM salaries WHERE user_id = ? AND salary_type = 'Primary'", (user_id,))
    primary_count = c.fetchone()[0]
    conn.close()

    if request.method == 'POST':
        try:
            amount = request.form.get('amount')
            savings_rate = request.form.get('savings_rate')
            custom_savings_rate = request.form.get('custom_savings_rate')
            salary_type = request.form.get('salary_type').capitalize()

            if not amount or not savings_rate or not salary_type:
                flash('Please fill out all fields.', 'error')
                return redirect(url_for('add_salary'))

            amount = float(amount)

            if savings_rate == "custom":
                if not custom_savings_rate:
                    flash('Please enter a custom savings rate.', 'error')
                    return redirect(url_for('add_salary'))
                savings = int(custom_savings_rate)
            else:
                savings = int(savings_rate)

            if salary_type not in ["Primary", "Secondary"]:
                flash('Invalid salary type.', 'error')
                return redirect(url_for('add_salary'))

            # Prevent multiple primary salaries
            if primary_count > 0 and salary_type == "Primary":
                flash('You already have a primary salary. Only one primary salary is allowed.', 'error')
                return redirect(url_for('add_salary'))

            # Insert into database
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute("INSERT INTO salaries (user_id, amount, savings, salary_type) VALUES (?, ?, ?, ?)", 
                      (user_id, amount, savings, salary_type))
            conn.commit()
            conn.close()

            flash('Salary added successfully.', 'success')
            return redirect(url_for('salaries'))

        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('add_salary'))

    return render_template('add_salary.html', primary_exists=primary_count > 0)





@app.route('/edit_salary/<int:salary_id>', methods=['GET', 'POST'])
def edit_salary(salary_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    user_id = session['user_id']

    # Get the current salary details
    c.execute("SELECT * FROM salaries WHERE id = ?", (salary_id,))
    salary = c.fetchone()

    if not salary:
        conn.close()
        flash('Salary not found.', 'error')
        return redirect(url_for('salaries'))

    # Check if another primary salary exists
    c.execute("SELECT COUNT(*) FROM salaries WHERE user_id = ? AND salary_type = 'Primary' AND id != ?", 
              (user_id, salary_id))
    primary_count = c.fetchone()[0]
    conn.close()

    if request.method == 'POST':
        try:
            amount = request.form['amount']
            savings_rate = request.form['savings']  # This might be "custom"
            custom_savings_rate = request.form.get('custom_savings_rate')  

            # Convert savings correctly
            if savings_rate == "custom":
                if not custom_savings_rate:
                    flash('Please enter a custom savings rate.', 'error')
                    return redirect(url_for('edit_salary', salary_id=salary_id))
                savings = int(custom_savings_rate)
            else:
                savings = int(savings_rate)

            salary_type = request.form['salary_type'].capitalize()

            if salary_type not in ["Primary", "Secondary"]:
                flash('Invalid salary type.', 'error')
                return redirect(url_for('edit_salary', salary_id=salary_id))

            # Prevent making another salary primary
            if primary_count > 0 and salary_type == "Primary":
                flash('You already have a primary salary. Only one primary salary is allowed.', 'error')
                return redirect(url_for('edit_salary', salary_id=salary_id))

            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute("UPDATE salaries SET amount = ?, savings = ?, salary_type = ? WHERE id = ?", 
                      (amount, savings, salary_type, salary_id))
            conn.commit()
            conn.close()

            flash('Salary updated successfully!', 'success')
            return redirect(url_for('salaries'))

        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('edit_salary', salary_id=salary_id))

    return render_template('edit_salary.html', salary=salary, primary_exists=primary_count > 0)





@app.route('/salaries/delete/<int:salary_id>', methods=['GET'])
def delete_salary(salary_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM salaries WHERE id = ?", (salary_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('salaries'))

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Allows fetching results as dictionaries
    return conn

@app.route('/expenses')
def expenses():
    if 'username' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '', type=str)
    date = request.args.get('date', '', type=str)

    limit = 5  # Show 5 expenses per page
    offset = (page - 1) * limit

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, amount, salary_type FROM salaries WHERE user_id = ?", (user_id,))
    salaries = cursor.fetchall() 

    # Fetch total expenses count for pagination
    query_count = "SELECT COUNT(*) FROM expenses WHERE user_id = ?"
    params_count = [user_id]

    query = "SELECT * FROM expenses WHERE user_id = ?"
    params = [user_id]

    if category:
        query += " AND category = ?"
        params.append(category)
        query_count += " AND category = ?"
        params_count.append(category)

    if date:
        query += " AND date = ?"
        params.append(date)
        query_count += " AND date = ?"
        params_count.append(date)

    query += " ORDER BY date DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query_count, params_count)
    total_expenses = cursor.fetchone()[0]
    total_pages = (total_expenses + limit - 1) // limit  # Calculate total pages

    cursor.execute(query, params)
    expenses = cursor.fetchall()
    conn.close()

    return render_template(
        'expenses.html',
        expenses=expenses,
        page=page,
        total_pages=total_pages,
        category=category,
        date=date,
        salaries=salaries
    )




from datetime import datetime
import sqlite3

from flask import Flask, request, redirect, url_for, session
import sqlite3
import datetime


@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    if 'username' in session:
        user_id = session['user_id']
        date = request.form['date']
        category = request.form['category']
        amount = float(request.form['amount'])
        payment_method = request.form['payment_method']
        description = request.form.get('notes', '')
        recurring = request.form.get('recurring', 'No')
        salary_id = request.form.get('salary_id')  # Get selected salary

        # Convert "Yes" to 1 and "No" to 0
        recurring = 1 if recurring == 'Yes' else 0

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        # Fetch valid salary options for the user
        c.execute("SELECT id FROM salaries WHERE user_id = ?", (user_id,))
        valid_salary_ids = [str(s[0]) for s in c.fetchall()]

        # Ensure the selected salary_id is valid
        if salary_id not in valid_salary_ids:
            salary_id = None  # Default to None if an invalid ID is received

        # Insert the new expense
        c.execute("""
            INSERT INTO expenses (user_id, date, category, amount, payment_method, description, recurring, last_added, salary_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, date, category, amount, payment_method, description, recurring, date if recurring else None, salary_id))
        
        conn.commit()
        conn.close()

        # If recurring, ensure past months are accounted for
        if recurring:
            add_recurring_expenses()

        return redirect(url_for('expenses'))
    else:
        return redirect(url_for('login'))



from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import sqlite3


def add_recurring_expenses():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # Fetch recurring expenses from the database
    c.execute("""
        SELECT id, user_id, category, amount, payment_method, description, date, last_added 
        FROM expenses 
        WHERE recurring = 1
    """)
    recurring_expenses = c.fetchall()

    today = date.today()
    current_month_start = today.replace(day=1)  # First day of this month

    for expense in recurring_expenses:
        expense_id, user_id, category, amount, payment_method, description, original_date, last_added = expense

        # Convert `original_date` to a `date` object
        original_date = date.fromisoformat(original_date)
        expense_day = original_date.day  # The day the recurring expense should be added

        # Determine the last recorded month
        if last_added is None:
            last_added = original_date  # Start from the original expense date
        else:
            last_added = date.fromisoformat(last_added)

        # Generate missing months from last_added to previous month
        missing_months = []
        next_month = last_added.replace(day=1) + relativedelta(months=1)  # Move to the next month

        while next_month < current_month_start:
            missing_months.append(next_month)
            next_month = next_month + relativedelta(months=1)

        # Insert missing expenses
        for month in missing_months:
            try:
                new_expense_date = month.replace(day=expense_day)
            except ValueError:  # Handle cases like Feb 30 → Feb 28
                last_day_of_month = (month + relativedelta(months=1, days=-1)).day
                new_expense_date = month.replace(day=last_day_of_month)

            # Prevent duplicate entries
            c.execute("""
                SELECT id FROM expenses 
                WHERE user_id = ? AND category = ? AND date = ? AND recurring = 1
            """, (user_id, category, new_expense_date.strftime("%Y-%m-%d")))

            if not c.fetchone():  # If no existing expense, insert
                c.execute("""
                    INSERT INTO expenses (user_id, date, category, amount, payment_method, description, recurring, last_added)
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                """, (user_id, new_expense_date.strftime("%Y-%m-%d"), category, amount, payment_method, description, new_expense_date.strftime("%Y-%m-%d")))

        #  **NEW FIX: Ensure the current month is added**
        try:
            current_month_expense_date = current_month_start.replace(day=expense_day)
        except ValueError:  # Handle cases like Feb 30 → Feb 28
            last_day_of_month = (current_month_start + relativedelta(months=1, days=-1)).day
            current_month_expense_date = current_month_start.replace(day=last_day_of_month)

        # Check if the current month's expense already exists
        c.execute("""
            SELECT id FROM expenses 
            WHERE user_id = ? AND category = ? AND date = ? AND recurring = 1
        """, (user_id, category, current_month_expense_date.strftime("%Y-%m-%d")))

        if not c.fetchone():  # If no existing expense, insert
            c.execute("""
                INSERT INTO expenses (user_id, date, category, amount, payment_method, description, recurring, last_added)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """, (user_id, current_month_expense_date.strftime("%Y-%m-%d"), category, amount, payment_method, description, current_month_expense_date.strftime("%Y-%m-%d")))

        # Update `last_added` to the latest recorded month
        c.execute("""
            UPDATE expenses 
            SET last_added = ?
            WHERE id = ?
        """, (current_month_start.strftime("%Y-%m-%d"), expense_id))

    conn.commit()
    conn.close()

    
@app.route('/delete_transaction/<int:transaction_id>', methods=['POST', 'GET'])
def delete_transaction(transaction_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE id = ?", (transaction_id,))
    conn.commit()
    conn.close()
    flash("Transaction deleted successfully!", "success")
    return redirect(url_for('expenses'))

import pytesseract
import re
from PIL import Image
from flask import Flask, request, jsonify

# Set the Tesseract OCR path (if not set in PATH)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Patterns to identify the total amount in different formats
total_patterns = [
    r"(Total|Grand Total|Amount Payable|Balance Due|Total Due|Net Payable|Amount Due)[^\d]*([\d,]+\.?\d{0,2})",
    r"(Final Amount|Total Bill|Total Payment|Subtotal)[^\d]*([\d,]+\.?\d{0,2})",
    r"(Net Total|Final Payable|Gross Total)[^\d]*([\d,]+\.?\d{0,2})"
]

# Pattern for extracting date (formats like 12-03-2024, 03/12/2024, etc.)
date_patterns = [
    r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",  # Matches 12-03-2024, 03/12/24
    r"(\d{4}[-/]\d{2}[-/]\d{2})",        # Matches 2024-03-12
    r"(\d{1,2}\s*[A-Za-z]+\s*\d{4})",    # Matches 12 March 2024, 3rd Jan 2023
]

def extract_text_from_image(image_path):
    """Extract text from the given image using Tesseract OCR."""
    img = Image.open(image_path)
    return pytesseract.image_to_string(img, lang='eng')

def extract_total_amount(text):
    """Extract total amount from the text using regex."""
    for pattern in total_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(2).replace(",", "")  # Remove commas from amounts
    return None

def extract_date(text):
    """Extracts date from the start or end of the extracted text."""
    lines = text.split("\n")  # Split text into lines

    # Search in the first 5 and last 5 lines (common date locations)
    relevant_lines = lines[:5] + lines[-5:]
    for line in relevant_lines:
        for pattern in date_patterns:
            match = re.search(pattern, line)
            if match:
                return match.group(1)  # Return the first found date
    return None

@app.route("/upload_receipt", methods=["POST"])
def upload_receipt():
    """API endpoint to process the uploaded receipt image."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files["file"]
    image_path = "temp_receipt.jpg"  # Temporary save path
    file.save(image_path)

    # Extract text from image
    extracted_text = extract_text_from_image(image_path)
    
    # Extract amount and date
    total_amount = extract_total_amount(extracted_text)
    receipt_date = extract_date(extracted_text)

    return jsonify({
        "amount": total_amount if total_amount else "Not found",
        "date": receipt_date if receipt_date else "Not found"
    })


from datetime import datetime
from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3

@app.route('/analysis', methods=['GET'], endpoint='analysis')
def analysis():
    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('login'))  # Redirect if user is not logged in

    print(f"User ID from session in analysis page: {user_id}")  # Debugging

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # Get selected filters
    selected_category = request.args.get('category', None)
    selected_month = request.args.get('month', datetime.now().strftime('%Y-%m'))  # Default: Current month
    time_range = request.args.get('time_range', 'monthly')  # Default: Monthly
    selected_savings_month = request.args.get('savings_month', selected_month)  # Default: Current month
    selected_salary = request.args.get('salary_filter', 'all')  # Default: All Salaries

    # Define date filters
    month_filter = "strftime('%Y-%m', date) = ?"

    # Fetch available categories
    c.execute("SELECT DISTINCT category FROM expenses WHERE user_id = ?", (user_id,))
    categories = [row[0] for row in c.fetchall()]

    # Fetch available months
    c.execute("SELECT DISTINCT strftime('%Y-%m', date) FROM expenses WHERE user_id = ?", (user_id,))
    months = {row[0]: datetime.strptime(row[0], '%Y-%m').strftime('%B %Y') for row in c.fetchall() if row[0]}

    # Fetch total expenses for the selected month (Pie Chart)
    c.execute(f"""
        SELECT category, COALESCE(SUM(amount), 0) 
        FROM expenses 
        WHERE user_id = ? AND {month_filter}
        GROUP BY category
    """, (user_id, selected_month))

    expense_breakdown_result = c.fetchall()
    expense_breakdown = {row[0]: row[1] for row in expense_breakdown_result}

    # Fetch total expenses based on category and time range
    c.execute(f"""
        SELECT COALESCE(SUM(amount), 0) FROM expenses 
        WHERE user_id = ? AND {month_filter}
    """, (user_id, selected_savings_month))

    total_expenses = c.fetchone()[0] or 0

    # Fetch available salaries
    c.execute("SELECT DISTINCT amount FROM salaries WHERE user_id = ?", (user_id,))
    salary_list = [row[0] for row in c.fetchall()]

    # Fetch total salary based on selection
    if selected_salary == "all":
        c.execute(f"""
            SELECT COALESCE(SUM(amount), 0) FROM salaries WHERE user_id = ?
        """, (user_id,))
    else:
        c.execute(f"""
            SELECT COALESCE(SUM(amount), 0) FROM salaries WHERE user_id = ? AND amount = ?
        """, (user_id, selected_salary))

    total_salary = c.fetchone()[0] or 0

    # Fetch user's savings percentage
    c.execute("SELECT savings FROM salaries WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    savings_percentage = row[0] if row else 0  # Use 0 if row is None


    # Calculate required savings
    required_savings = (total_salary * int(savings_percentage)) / 100

    # Calculate remaining salary after expenses
    remaining_salary = total_salary - total_expenses

    # Calculate savings status as a percentage
    savings_status = ((remaining_salary - required_savings) / required_savings) * 100 if required_savings > 0 else 0

    conn.close()


    return render_template(
        'analysis.html',
        expense_breakdown=expense_breakdown,
        expense_by_category_total=int(total_expenses),
        categories=categories,
        selected_category=selected_category,
        selected_month=selected_month,
        time_range=time_range,
        months=months,
        total_salary=total_salary,
        required_savings=required_savings,
        remaining_salary=remaining_salary,
        savings_status=savings_status,
        salaries=salary_list,
        selected_salary=selected_salary,
        selected_savings_month=selected_savings_month,
        
    )


# New API route to fetch expenses dynamically based on selected month
@app.route('/get_expense_data')
def get_expense_data():
    user_id = session.get('user_id')
    selected_month = request.args.get('month')

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute("""
        SELECT category, COALESCE(SUM(amount), 0) 
        FROM expenses 
        WHERE user_id = ? AND strftime('%Y-%m', date) = ?
        GROUP BY category
    """, (user_id, selected_month))

    expense_data = dict(c.fetchall())
    conn.close()

    return jsonify(expense_data)




@app.route('/')
def index():
    if 'username' in session:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('login'))

        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # Fetch all expenses
        c.execute("SELECT * FROM expenses WHERE user_id = ?", (user_id,))
        expenses = c.fetchall()
        expenses = [dict(exp) for exp in expenses]

        # Compute remaining salary
        c.execute("SELECT COALESCE(SUM(amount), 0) FROM salaries WHERE user_id = ?", (user_id,))
        monthly_salary = c.fetchone()[0]

        c.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM expenses 
            WHERE user_id = ? AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now')
        """, (user_id,))
        monthly_expenses = c.fetchone()[0]
        remaining_salary = monthly_salary - monthly_expenses

        # Fetch highest expense category
        c.execute("""
            SELECT category, SUM(amount) as total_spent 
            FROM expenses 
            WHERE user_id = ? AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now')
            GROUP BY category
            ORDER BY total_spent DESC
            LIMIT 1
        """, (user_id,))
        highest_expense_category = c.fetchone()
        highest_category = highest_expense_category['category'] if highest_expense_category else "N/A"
        highest_category_amount = highest_expense_category['total_spent'] if highest_expense_category else 0

        # Fetch the most recent expense
        c.execute("""
            SELECT category, amount, date FROM expenses 
            WHERE user_id = ? 
            ORDER BY date DESC 
            LIMIT 1
        """, (user_id,))
        recent_expense = c.fetchone()
        recent_category = recent_expense['category'] if recent_expense else "No expenses yet"
        recent_amount = recent_expense['amount'] if recent_expense else 0
        recent_date = recent_expense['date'] if recent_expense else "-"

        conn.close()

        return render_template('index.html', 
                               username=session['username'],
                               remaining_salary=int(remaining_salary),
                               highest_category=highest_category,
                               highest_category_amount=highest_category_amount,
                               recent_category=recent_category,
                               recent_amount=recent_amount,
                               recent_date=recent_date)
    return redirect(url_for('login'))

from flask import request, jsonify

@app.route('/expense_category_data')
def expense_category_data():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 403

    start_date = request.args.get('start_date', '2000-01-01')  # Default to earliest date
    end_date = request.args.get('end_date', '2100-12-31')  # Default to farthest date

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT category, SUM(amount) as total_spent
        FROM expenses 
        WHERE user_id = ? AND date BETWEEN ? AND ?
        GROUP BY category
        ORDER BY total_spent DESC
    """, (user_id, start_date, end_date))

    expenses = c.fetchall()
    conn.close()

    labels = [row["category"] for row in expenses]
    amounts = [row["total_spent"] for row in expenses]

    return jsonify({"labels": labels, "amounts": amounts})



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT id, username, password FROM users WHERE username = ? AND password = ?", (username, password))
        user = c.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]  # Store user_id in session
            session['username'] = user[1]  # Store username in session
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password. Please try again.', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", 
                  (username, email, password))
        conn.commit()
        conn.close()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for('login'))
    
    return render_template('register.html')



@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))



from datetime import datetime
from flask import jsonify, session
import sqlite3

# Daily Spending Data Route
@app.route('/daily_spending_data')
def daily_spending_data():
    user_id = session.get('user_id')
    if user_id:
        try:
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()

            # Get current month and year
            current_year = datetime.now().strftime('%Y')
            current_month = datetime.now().strftime('%m')

            # Fetch daily expenses for the current month
            c.execute('''
                SELECT strftime('%d', date) AS day, SUM(amount) 
                FROM expenses 
                WHERE user_id = ? 
                AND strftime('%Y', date) = ? 
                AND strftime('%m', date) = ? 
                GROUP BY day
                ORDER BY day
            ''', (user_id, current_year, current_month))
            
            daily_expenses = c.fetchall()
            conn.close()

            # Prepare data for the chart
            labels = [row[0] for row in daily_expenses]
            amounts = [int(row[1]) for row in daily_expenses]  # Ensure amounts are integers

            return jsonify({'labels': labels, 'amounts': amounts})
        except Exception as e:
            print("Error fetching daily spending data:", e)
            return jsonify({'labels': [], 'amounts': []})
    else:
        return jsonify({'labels': [], 'amounts': []})

# Monthly Spending Data Route
@app.route('/monthly_spending_data')
def monthly_spending_data():
    if 'user_id' in session:
        user_id = session['user_id']
        
        try:
            # Fetch monthly spending data from the database
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute('''
                SELECT strftime('%Y-%m', date) AS month, SUM(amount) 
                FROM expenses 
                WHERE user_id = ? 
                GROUP BY month 
                ORDER BY month
            ''', (user_id,))
            data = c.fetchall()
            conn.close()

            # Format data for Chart.js
            labels = [datetime.strptime(row[0], '%Y-%m').strftime('%b %Y') for row in data]
            amounts = [int(row[1]) for row in data]  # Ensure amounts are integers

            return jsonify({'labels': labels, 'amounts': amounts})
        except Exception as e:
            print("Error:", e)  # You can log the error for debugging
            return jsonify({'labels': [], 'amounts': []})   
    

if __name__ == '__main__':
    app.run(debug=True)
