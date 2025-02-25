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
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS salaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    savings INTEGER NOT NULL,
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

    if request.method == 'POST':
        try:
            amount = request.form.get('amount')  # Use .get() to avoid KeyError
            savings = request.form.get('savings')

            if not amount or not savings:
                flash('Please fill out all fields.', 'error')
                return redirect(url_for('add_salary'))

            user_id = session['user_id']
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute("INSERT INTO salaries (user_id, amount, savings) VALUES (?, ?, ?)", 
                      (user_id, amount, savings))
            conn.commit()
            conn.close()

            flash('Salary added successfully.', 'success')
            return redirect(url_for('salaries'))
        
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('add_salary'))

    return render_template('add_salary.html')


@app.route('/edit_salary/<int:salary_id>', methods=['GET', 'POST'])
def edit_salary(salary_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    if request.method == 'POST':
        amount = request.form['amount']
        savings = request.form['savings']

        c.execute("UPDATE salaries SET amount = ?, savings = ? WHERE id = ?", 
                  (amount, savings, salary_id))
        conn.commit()
        conn.close()

        flash('Salary updated successfully!', 'success')
        return redirect(url_for('salaries'))

    # Fetch salary details
    c.execute("SELECT * FROM salaries WHERE id = ?", (salary_id,))
    salary = c.fetchone()
    conn.close()

    # Debug
    print("Debug: Salary Data =", salary)

    return render_template('edit_salary.html', salary=salary)




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
        date=date
    )




@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    if 'username' in session:
        user_id = session['user_id']  
        date = request.form['date']
        category = request.form['category']
        amount = request.form['amount']
        payment_method = request.form['payment_method']
        description = request.form['notes']

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("INSERT INTO expenses (user_id, date, category, amount, payment_method, description) VALUES (?, ?, ?, ?, ?, ?)",
                  (user_id, date, category, amount, payment_method, description))
        conn.commit()
        conn.close()

        return redirect(url_for('expenses'))
    else:
        return redirect(url_for('login'))
    
@app.route('/delete_transaction/<int:transaction_id>', methods=['POST'])
def delete_transaction(transaction_id):
    if 'username' in session:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("DELETE FROM expenses WHERE id = ?", (transaction_id,))
        conn.commit()
        conn.close()
        flash('Transaction deleted successfully.', 'success')
    else:
        flash('You must be logged in to delete a transaction.', 'error')
    return redirect(url_for('expenses'))

from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import sqlite3
from datetime import datetime


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

    # Define date filters for Expense Breakdown (Pie Chart)
    month_filter = "strftime('%Y-%m', date) = ?"

    # Define date filters for Expense by Category
    if time_range == 'weekly':
        date_filter = "strftime('%Y-%W', date) = strftime('%Y-%W', 'now')"  # Current week
    elif time_range == 'quarterly':
        date_filter = "date >= date('now', '-3 months')"  # Last 3 months
    elif time_range == 'yearly':
        date_filter = "strftime('%Y', date) = strftime('%Y', 'now')"  # Current year
    elif time_range == 'older':  # Fix for "Older than a Year"
        date_filter = "date < date('now', '-1 year')"
    else:
        date_filter = "strftime('%Y-%m', date) = ?"  # Use selected_month

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

    # Fetch total expenses based on category and time range (Expense by Category)
    if selected_category:
        if time_range == 'older':
            c.execute(f"""
            SELECT COALESCE(SUM(amount), 0) FROM expenses 
            WHERE user_id = ? AND category = ? AND date < date('now', '-1 year')
            """, (user_id, selected_category))
        else:
            c.execute(f"""
            SELECT COALESCE(SUM(amount), 0) FROM expenses 
            WHERE user_id = ? AND category = ? AND {date_filter}
            """, (user_id, selected_category, selected_month) if time_range == 'monthly' else (user_id, selected_category))
    else:
        if time_range == 'older':
            c.execute(f"""
            SELECT COALESCE(SUM(amount), 0) FROM expenses 
            WHERE user_id = ? AND date < date('now', '-1 year')
            """, (user_id,))
        else:
            c.execute(f"""
            SELECT COALESCE(SUM(amount), 0) FROM expenses 
            WHERE user_id = ? AND {date_filter}
            """, (user_id, selected_month) if time_range == 'monthly' else (user_id,))


    total_expenses_by_category = c.fetchone()[0] or 0  # Ensure it's not None

    conn.close()

    return render_template(
        'analysis.html',
        expense_breakdown=expense_breakdown,
        expense_by_category_total=total_expenses_by_category,
        categories=categories,
        selected_category=selected_category,
        selected_month=selected_month,
        time_range=time_range,
        months=months
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
                               remaining_salary=remaining_salary,
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
        password = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt())

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
