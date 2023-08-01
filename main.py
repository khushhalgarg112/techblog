from flask import Flask, render_template, redirect, url_for, flash, request, abort
from functools import wraps
import os
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor, CKEditorField
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms.validators import DataRequired, URL
from datetime import date
from sqlalchemy.orm import relationship
# from sqlalchemy.orm import relationship
from forms import CreatePostForm, CreateUserForm,LoginForm, CommentForm


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap5(app)

login= LoginManager()
login.init_app(app)

def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        #If id is not 1 then return abort with 403 error
        if current_user.id != 1:
            return abort(403)
        #Otherwise continue with the route function
        return f(*args, **kwargs)        
    return decorated_function


# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://post_jghk_user:h4eZ7f7y24hJ6xl60sAZzXDlUNUDw199@dpg-cj4fmr18g3nakvg4snmg-a.oregon-postgres.render.com/post_jghk"
db = SQLAlchemy()
db.init_app(app)

# TODO: Create a User table for all your registered users. 
class Credentials(UserMixin,db.Model):
    __tablename__ = "user_data"
    id = id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
        #This will act like a List of BlogPost objects attached to each User. 
    #The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")

    comments = relationship("Comment", back_populates="comment_author")

# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    #Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("user_data.id"))
    #Create reference to the User object, the "posts" refers to the posts protperty in the User class.
    author = relationship("Credentials", back_populates="posts")
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    #***************Parent Relationship*************#
    comments = relationship("Comment", back_populates="parent_post")

    

class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)


    # Child relationship

    author_id = db.Column(db.Integer,  db.ForeignKey("user_data.id"))

    comment_author = relationship("Credentials", back_populates="comments")

     #***************Child Relationship*************#
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")

    comment = db.Column(db.Text, unique=True, nullable=False) 

with app.app_context():
    db.create_all()


# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register', methods=['POST','GET'])
def register():
    form = CreateUserForm()
    if form.validate_on_submit():
        user  = db.session.query(Credentials).filter_by(email = request.form.get('email')).first()
        if user:
           flash('Email already exist, try to login')
           return redirect(url_for('login'))
        obj = Credentials(name= request.form.get('name'),email= request.form.get('email'),password= generate_password_hash(request.form.get('password'), method='pbkdf2:sha1', salt_length=8),)
        db.session.add(obj)
        db.session.commit()
        login_user(obj)
        return redirect(url_for('get_all_posts'))
    return render_template("register.html", form =form)

@login.user_loader
def load_user(user_id):
    return Credentials.query.get(user_id)

@app.route('/login', methods=['POST','GET'])
def login():
    form = LoginForm()
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user  = db.session.query(Credentials).filter_by(email = email).first()
        if user:
            if check_password_hash(user.password,password):
                login_user(user)
                return redirect(url_for('get_all_posts'))
            else:
                 flash('Invalid Password , Please try again')
                 return redirect(url_for('login'))
        else:
            flash('Email does not exist.')
            return redirect(url_for('login'))

    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


# Code from previous lessons below
@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts)

gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)

@app.route("/post/<int:post_id>", methods=['POST','GET'])
def show_post(post_id):
    form = CommentForm()
    requested_post = db.get_or_404(BlogPost, post_id)
    
    if form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(
                comment=form.body.data,
                comment_author=current_user,
                parent_post=requested_post
            )
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for("show_post", post_id=post_id))
       
        else:
            flash("You need to login to leave a comment")
            return redirect(url_for("login"))
    

    
    return render_template("post.html", post=requested_post, form=form, current_user=current_user, gravatar=gravatar)


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form,current_user=current_user)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True,current_user=current_user)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0')
