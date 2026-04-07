import razorpay
from flask import Flask, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'secret'

db = SQLAlchemy(app)

# 🔥 ADD YOUR REAL RAZORPAY KEYS HERE
razorpay_client = razorpay.Client(auth=("YOUR_KEY_ID", "YOUR_SECRET"))

# ================= MODELS =================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20), default="user")

class Donation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    amount = db.Column(db.Integer)
    date = db.Column(db.DateTime, default=db.func.now())

# ================= ROUTES =================

# HOME
@app.route('/')
def home():
    return render_template('index.html')

# ABOUT
@app.route('/about')
def about():
    return render_template('about.html')

# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pwd = request.form['password']

        found = User.query.filter_by(username=user).first()

        if found and check_password_hash(found.password, pwd):
            session['user'] = user
            session['role'] = found.role
            return redirect('/dashboard')

        return "Invalid Login ❌"

    return render_template('login.html')

# SIGNUP
@app.route('/signup', methods=['POST'])
def signup():
    user = request.form['username']
    pwd = generate_password_hash(request.form['password'])

    db.session.add(User(username=user, password=pwd))
    db.session.commit()

    return redirect('/login')

# DASHBOARD
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')

    total = db.session.query(db.func.sum(Donation.amount)).scalar() or 0

    user_total = db.session.query(db.func.sum(Donation.amount))\
        .filter_by(username=session['user']).scalar() or 0

    donations = Donation.query.order_by(Donation.date.desc()).all()
    amounts = [d.amount for d in donations]

    return render_template(
        "dashboard.html",
        total=total,
        user_total=user_total,
        donations=donations,
        amounts=amounts,
        user=session['user'],
        role=session.get('role')
    )

# ADMIN PANEL
@app.route('/admin')
def admin():
    if session.get('role') != 'admin':
        return "Access Denied ❌"

    donations = Donation.query.order_by(Donation.date.desc()).all()
    users = User.query.all()

    total = db.session.query(db.func.sum(Donation.amount)).scalar() or 0

    # ✅ FIX: create amounts list here
    amounts = [d.amount for d in donations]

    return render_template(
        "admin.html",
        donations=donations,
        users=users,
        total=total,
        amounts=amounts   # 👈 PASS THIS
    )
# DELETE USER
@app.route('/delete_user/<int:id>')
def delete_user(id):
    if session.get('role') != 'admin':
        return "Access Denied"

    user = User.query.get(id)
    if user:
        db.session.delete(user)
        db.session.commit()

    return redirect('/admin')


# DELETE DONATION
@app.route('/delete_donation/<int:id>')
def delete_donation(id):
    if session.get('role') != 'admin':
        return "Access Denied"

    donation = Donation.query.get(id)
    if donation:
        db.session.delete(donation)
        db.session.commit()

    return redirect('/admin')

# 🔁 CHANGE ROLE (admin ↔ user)
@app.route('/toggle_role/<int:id>')
def toggle_role(id):
    if session.get('role') != 'admin':
        return "Access Denied"

    user = User.query.get(id)

    if user:
        user.role = "admin" if user.role == "user" else "user"
        db.session.commit()

    return redirect('/admin')

# DONATE PAGE
@app.route('/donatepage')
def donate():
    return render_template('donate.html')

# CREATE ORDER (RAZORPAY)
@app.route('/create_order', methods=['POST'])
def create_order():
    amount = int(request.form['amount']) * 100

    order = razorpay_client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1
    })

    return jsonify(order)

# VERIFY PAYMENT
@app.route('/verify_payment', methods=['POST'])
def verify_payment():
    data = request.json

    try:
        razorpay_client.utility.verify_payment_signature({
            'razorpay_order_id': data['order_id'],
            'razorpay_payment_id': data['payment_id'],
            'razorpay_signature': data['signature']
        })

        db.session.add(Donation(
            username=data['user'],
            amount=data['amount']
        ))
        db.session.commit()

        return {"status": "success"}

    except Exception as e:
        print("Payment Error:", e)
        return {"status": "failed"}

# LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ================= RUN =================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        # 🔥 CREATE ADMIN USER (ONLY ONCE)
        if not User.query.filter_by(username="admin").first():
            admin = User(
                username="admin",
                password=generate_password_hash("admin123"),
                role="admin"
            )
            db.session.add(admin)
            db.session.commit()

if __name__ == "__main__":
    app.run(debug=True)