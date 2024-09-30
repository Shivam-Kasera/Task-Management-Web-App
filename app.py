from flask import Flask, render_template, redirect, url_for, request, flash, session
from models import db, Task, User
from environment import *
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail, Message

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = MAIL_SERVER
app.config['MAIL_PORT'] = MAIL_PORT
app.config['MAIL_USE_TLS'] = MAIL_USE_TLS
app.config['MAIL_USERNAME'] = MAIL_USERNAME
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = MAIL_DEFAULT_SENDER

db.init_app(app)

s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
mail = Mail(app=app)

@app.before_request
def create_tables():
    db.create_all()

@app.route('/')
def index():
    user_id = session.get('user_id')
    if user_id:
        tasks = Task.query.filter(Task.user_id == user_id).all()
        return render_template('index.html', tasks=tasks)
    return redirect('/login')

@app.route('/registration', methods=['GET', 'POST'])
def registration():
    user = session.get('user_id')
    if user:
        return redirect('/')
    if request.method == 'POST':
        username = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        existing_user = User.query.filter((User.email == email)).first()
        if existing_user:
            flash('Username or email already exists!', 'error')
            return redirect(url_for('registration'))
        new_user = User(username=username, email=email)
        new_user.set_password(password)  # Hash and set the password
        # Save the user to the database
        db.session.add(new_user)
        db.session.commit()
        # Log the user in by setting the session
        session['user_id'] = new_user.id
        session['username'] = new_user.username
        flash('Registration successful! You are now logged in.', 'success')
        return redirect(url_for('index'))
    return render_template('registration.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    user = session.get('user_id')
    if user:
        return redirect('/')
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password. Please try again.', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    user = session.get('user_id')
    if user:
        redirect('/')
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()  # Corrected query method
        if not user:
            flash("Invalid email id!", "error")
            return redirect('/login')
        token = s.dumps(user.id, salt='password-reset-salt')
        reset_url = url_for('reset_password', token=token, _external=True)
        msg = Message("Password Reset Request", recipients=[email])
        msg.body = f"Please click the link to reset your password: {reset_url}"
        with app.app_context():
            mail.send(msg)
        flash("A password reset link has been sent to your email!", "success")
        return redirect('/forgot_password')
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = session.get('user_id')
    if user:
        redirect('/')
    try:
        user_id = s.loads(token, salt='password-reset-salt', max_age=3600)
    except Exception as e:
        flash("The reset link is invalid or has expired.", "error")
        return redirect('/login')
    if request.method == 'POST':
        new_password = request.form.get('password')
        user = User.query.get(user_id)
        if user:
            user.set_password(new_password)
            db.session.commit()
            flash("Your password has been updated!", "success")
            return redirect('/login')
    return render_template('reset_password.html', token=token)


@app.route('/add_task', methods=['GET', 'POST'])
def add_task():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        if not title or not description:
            flash("All fields are required", 'error')
            return redirect(url_for('index'))
        new_task = Task(title=title, description=description, user_id=session['user_id'])
        db.session.add(new_task)
        db.session.commit()
        flash("Task added successfully!", 'success')
        return redirect(url_for('index'))
    return render_template('index')

@app.route('/edit_task', methods=['GET', 'POST'])
def edit_task():
    task_id = request.args.get('task_id')
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    task = Task.query.get(task_id)
    if not task:
        flash('Task not found!', 'error')
        return redirect('/')
    if task.user_id != user_id:
        flash('Unauthorize!', 'error')
        return redirect('/')
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        task.title = title
        task.description = description
        db.session.commit()
        flash('Task update successful!', 'success')
        return redirect('/')
    return render_template('edit_task.html', task=task)

@app.route('/complete_task')
def complete_task():
    task_id = request.args.get('task_id')
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    task = Task.query.get(task_id)
    if not task:
        flash('Task not found!', 'error')
        return redirect('/')
    if task.user_id != user_id:
        flash('Unauthorize!', 'error')
        return redirect('/')
    task.completed = True
    db.session.commit()
    flash('Task completed', 'success')
    return redirect('/')

@app.route('/delete_task')
def delete_task():
    task_id = request.args.get('task_id')
    task = Task.query.get(task_id)
    if not task:
        flash('Task not found!', 'error')
        return redirect('/')
    db.session.delete(task)
    db.session.commit()
    db.session.commit()
    flash('Task deleted', 'success')
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logout successful!', 'success')
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)
