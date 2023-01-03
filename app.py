# Imports: load the source packages with `pip install -r requirements.txt`
from flask import Flask, flash, render_template, url_for, request, redirect
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import current_user, login_user, logout_user, login_required, LoginManager, UserMixin
from datetime import datetime
import os

# Configurations: base directory, app, db & login manager
base_dir = os.path.dirname(os.path.realpath(__file__))

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///' + \
    os.path.join(base_dir, 'ze_blog.db')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = 'dcabc46275bceb98bf55e21c'

db = SQLAlchemy(app)
db.init_app(app)

login_manager = LoginManager(app)


# Database Table Classes

# User Model: creates a table of users using UserMixin,
# and links each user to their articles in the table,
# then returns the username as its representation
class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(80), nullable=False, unique=True)
    password_hash = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"User: <{self.username}>"


# Article Model: creates a table of articles,
# and links each article to its author in the table,
# then returns the title as its representation
class Article(db.Model):
    __tablename__ = "articles"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    content = db.Column(db.String, nullable=False)
    created_on = db.Column(db.DateTime, default=datetime.now())
    user_id = db.Column(db.Integer, db.ForeignKey(
        "users.id"), unique=False, nullable=False)
    author = db.Column(db.String, nullable=False)

    def __repr__(self):
        return f"Article: <{self.title}>"


# Message Model: creates a table of messages from visitors,
# then returns the message title as its representation
class Message(db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(80), nullable=False)
    title = db.Column(db.String(80), nullable=False)
    message = db.Column(db.String, nullable=False)
    priority = db.Column(db.String(20))

    def __repr__(self):
        return f"Message: <{self.title}>"


# Personal reminder for Ze Austin
"""
To clear the messages db table via the terminal:

    python3
    from app import db, Message
    Message.__table__.drop(db.engine)
    exit()
"""


# Initialize db tables on first run
@app.before_first_request
def create_tables():
    db.create_all()


# Assign current user to Login Manager
@login_manager.user_loader
def user_loader(id):
    return User.query.get(int(id))


# Routing

# Home: displays all articles using the index template
@app.route('/')
def index():
    articles = Article.query.all()
    context = {
        "articles": articles
    }
    return render_template('index.html', **context)


# About: introduces the blog using the about template
@app.route('/about')
def about():
    return render_template('about.html')


# Contact: enables feedback using the contact template,
# then redirects to homepage after sending a message
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        sender = request.form.get('name')
        email = request.form.get('email')
        title = request.form.get('title')
        message = request.form.get('message')
        priority = request.form.get('priority')

        new_message = Message(sender=sender, email=email,
                              title=title, message=message, priority=priority)
        db.session.add(new_message)
        db.session.commit()

        flash("Message sent. Thanks for reaching out!")
        return redirect(url_for('index'))

    return render_template('contact.html')


# Sign Up: registers a new user and hashes their password,
# but flashes errors and reloads the page if data exists,
# then redirects to login page if successfully registered
@app.route('/signup', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')

        username_exists = User.query.filter_by(username=username).first()
        if username_exists:
            flash("This username already exists.")
            return redirect(url_for('register'))

        email_exists = User.query.filter_by(email=email).first()
        if email_exists:
            flash("This email is already registered.")
            return redirect(url_for('register'))

        password_hash = generate_password_hash(password)

        new_user = User(username=username, first_name=first_name,
                        last_name=last_name, email=email, password_hash=password_hash)
        db.session.add(new_user)
        db.session.commit()

        flash("You are now signed up.")
        return redirect(url_for('login'))

    return render_template('signup.html')


# Log In: logs the user in by checking their hashed password,
# but flashes an error and reloads the page if data is invalid,
# then redirects to home page if successfully logged in
@app.route('/login', methods=['GET', 'POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password_hash, password):
        login_user(user)
        flash("You are now logged in.")
        return redirect(url_for('index'))
    if (user and check_password_hash(user.password_hash, password)) == False:
        flash("Please provide valid credentials.")
        return redirect(url_for('login'))

    return render_template('login.html')


# Log Out: Login Manager makes this simple and short :)
@app.route('/logout')
def logout():
    logout_user()
    flash("You have been logged out.")
    return redirect(url_for('index'))


# Article: loads the selected article from the homepage
@app.route('/article/<int:id>/')
def article(id):
    article = Article.query.get_or_404(id)

    context = {
        "article": article
    }

    return render_template('article.html', **context)


# Contribute: enables article creation by logged in users only,
# but flashes an error and reloads the page if article title exists,
# then reloads page if successfully posted, encouraging another post
@app.route('/contribute', methods=['GET', 'POST'])
@login_required
def contribute():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        user_id = current_user.id
        author = current_user.username

        title_exists = Article.query.filter_by(title=title).first()
        if title_exists:
            flash("This article already exists. Please choose a new title.")
            return redirect(url_for('contribute'))

        new_article = Article(title=title, content=content,
                              user_id=user_id, author=author)
        db.session.add(new_article)
        db.session.commit()

        flash("Thanks for sharing your thoughts.")
        return redirect(url_for('index'))

    return render_template('contribute.html')


# Edit: enables article updates by chosen article's author only,
# then redirects to the article if it's been successfully edited,
# but flashes an error and redirects home if user's unauthorised
@app.route('/edit/<int:id>/', methods=['GET', 'POST'])
@login_required
def edit(id):
    article_to_edit = Article.query.get_or_404(id)

    if current_user.username == article_to_edit.author:
        if request.method == 'POST':
            article_to_edit.title = request.form.get('title')
            article_to_edit.content = request.form.get('content')

            db.session.commit()

            flash("Your changes have been saved.")
            return redirect(url_for('article', id=article_to_edit.id))

        context = {
            'article': article_to_edit
        }

        return render_template('edit.html', **context)

    flash("You cannot edit another user's article.")
    return redirect(url_for('index'))


# Delete: enables article removal by chosen article's author only,
# then redirects home if the article is successfully deleted,
# but flashes an error and redirects home if user's unauthorised
@app.route('/delete/<int:id>/', methods=['GET'])
@login_required
def delete(id):
    article_to_delete = Article.query.get_or_404(id)

    if current_user.username == article_to_delete.author:
        db.session.delete(article_to_delete)
        db.session.commit()
        flash("That article is gone!")
        return redirect(url_for('index'))

    flash("You cannot delete another user's article.")
    return redirect(url_for('index'))
