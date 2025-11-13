from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from models import db, User, Category, Post, Comment, Product, Order, Cart
from datetime import datetime
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'agrifarma-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///agrifarma.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize sample data
def init_sample_data():
    if Category.query.count() == 0:
        # Forum Categories
        crops = Category(name='Crops', description='Discussions about various crops', type='forum')
        db.session.add(crops)
        
        wheat = Category(name='Wheat', description='Wheat cultivation', type='forum', parent=crops)
        rice = Category(name='Rice', description='Rice farming', type='forum', parent=crops)
        cotton = Category(name='Cotton', description='Cotton farming', type='forum', parent=crops)
        
        db.session.add_all([wheat, rice, cotton])
        db.session.add_all([
            Category(name='Livestock', description='Animal husbandry', type='forum'),
            Category(name='Irrigation', description='Water management', type='forum'),
            Category(name='Soil Health', description='Soil management', type='forum'),
            Category(name='Pest Control', description='Pest management', type='forum')
        ])
        
        # Knowledge Base Categories
        db.session.add_all([
            Category(name='Success Stories', description='Farmer success stories', type='blog'),
            Category(name='Techniques', description='Farming techniques', type='blog'),
            Category(name='Weather Tips', description='Weather advice', type='blog'),
            Category(name='Market Insights', description='Market trends', type='blog')
        ])
        
        # Marketplace Categories
        db.session.add_all([
            Category(name='Grains', description='Various grains', type='product'),
            Category(name='Vegetables', description='Fresh vegetables', type='product'),
            Category(name='Fruits', description='Seasonal fruits', type='product'),
            Category(name='Livestock Products', description='Animal products', type='product')
        ])
        
        # Create admin user
        admin = User(
            name='Admin User',
            email='admin@agrifarma.com',
            profession='Administrator',
            expertise_level='expert',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        
        db.session.commit()


# ---------------------- ADMIN STATIC PAGES (UI) ----------------------
@app.route('/admin/dashboard')
def admin_dashboard_page():  # renamed to avoid conflict
    return render_template('admin_dashboard.html')

@app.route('/admin/farmers')
def farmers():
    return render_template('farmers.html')

@app.route('/admin/products')
def products():
    return render_template('products.html')

@app.route('/admin/requests')
def requests_view():
    return render_template('requests.html')

@app.route('/admin/reports')
def reports():
    return render_template('reports.html')


# ---------------------- MAIN WEBSITE ROUTES ----------------------
@app.route('/')
def index():
    latest_posts = Post.query.filter_by(is_approved=True).order_by(Post.created_at.desc()).limit(3).all()
    featured_products = Product.query.filter_by(is_approved=True).order_by(Product.created_at.desc()).limit(4).all()
    
    total_users = User.query.count()
    total_consultants = User.query.filter_by(is_consultant=True, is_consultant_approved=True).count()
    total_posts = Post.query.count()
    total_products = Product.query.filter_by(is_approved=True).count()
    
    return render_template('index.html', 
                         latest_posts=latest_posts, 
                         featured_products=featured_products,
                         total_users=total_users,
                         total_consultants=total_consultants,
                         total_posts=total_posts,
                         total_products=total_products)

@app.route('/dashboard')
@login_required
def dashboard():
    user_posts = Post.query.filter_by(user_id=current_user.id).count()
    user_products = Product.query.filter_by(user_id=current_user.id).count()
    user_orders = Order.query.filter_by(user_id=current_user.id).count()
    
    user_recent_posts = Post.query.filter_by(user_id=current_user.id).order_by(Post.created_at.desc()).limit(3).all()
    user_products_list = Product.query.filter_by(user_id=current_user.id).order_by(Product.created_at.desc()).limit(3).all()
    
    return render_template('dashboard.html', 
                         user_posts=user_posts, 
                         user_products=user_products, 
                         user_orders=user_orders,
                         user_recent_posts=user_recent_posts,
                         user_products_list=user_products_list)

# ---------------------- AUTHENTICATION ----------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        profession = request.form['profession']
        expertise = request.form['expertise']
        role = request.form['role']
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'error')
            return redirect(url_for('register'))
        
        user = User(
            name=name,
            email=email,
            profession=profession,
            expertise_level=expertise,
            role=role
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password!', 'error')
    
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# ---------------------- FORUM ROUTES ----------------------
@app.route('/forum')
def forum():
    categories = Category.query.filter_by(type='forum', parent_id=None).all()
    latest_posts = Post.query.filter_by(post_type='forum', is_approved=True).order_by(Post.created_at.desc()).limit(5).all()
    return render_template('forum/forum.html', categories=categories, latest_posts=latest_posts)

@app.route('/forum/category/<int:category_id>')
def forum_category(category_id):
    category = Category.query.get_or_404(category_id)
    posts = Post.query.filter_by(category=category.name, post_type='forum', is_approved=True).order_by(Post.created_at.desc()).all()
    return render_template('forum/category.html', category=category, posts=posts)

@app.route('/forum/post/<int:post_id>')
def forum_post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('forum/post.html', post=post)

@app.route('/forum/new', methods=['GET', 'POST'])
@login_required
def new_forum_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category = request.form['category']
        
        post = Post(
            title=title,
            content=content,
            category=category,
            post_type='forum',
            user_id=current_user.id
        )
        
        db.session.add(post)
        db.session.commit()
        flash('Post created successfully!', 'success')
        return redirect(url_for('forum_post', post_id=post.id))
    
    categories = Category.query.filter_by(type='forum').all()
    return render_template('forum/new_post.html', categories=categories)

@app.route('/forum/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    content = request.form['content']
    
    comment = Comment(
        content=content,
        user_id=current_user.id,
        post_id=post_id
    )
    
    db.session.add(comment)
    db.session.commit()
    flash('Comment added!', 'success')
    return redirect(url_for('forum_post', post_id=post_id))

# ---------------------- KNOWLEDGE BASE ----------------------
@app.route('/knowledge')
def knowledge_base():
    categories = Category.query.filter_by(type='blog').all()
    trending_posts = Post.query.filter_by(post_type='blog', is_approved=True).order_by(Post.likes.desc()).limit(5).all()
    return render_template('knowledge/base.html', categories=categories, trending_posts=trending_posts)

@app.route('/knowledge/post/<int:post_id>')
def knowledge_post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('knowledge/post.html', post=post)

@app.route('/knowledge/new', methods=['GET', 'POST'])
@login_required
def new_knowledge_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category = request.form['category']
        
        post = Post(
            title=title,
            content=content,
            category=category,
            post_type='blog',
            user_id=current_user.id
        )
        
        db.session.add(post)
        db.session.commit()
        flash('Article published successfully!', 'success')
        return redirect(url_for('knowledge_post', post_id=post.id))
    
    categories = Category.query.filter_by(type='blog').all()
    return render_template('knowledge/new_post.html', categories=categories)

# ---------------------- CONSULTANCY ----------------------
@app.route('/consultants')
def consultants():
    consultants = User.query.filter_by(is_consultant=True, is_consultant_approved=True).all()
    return render_template('consultancy/consultants.html', consultants=consultants)

@app.route('/consultant/<int:consultant_id>')
def consultant_profile(consultant_id):
    consultant = User.query.get_or_404(consultant_id)
    return render_template('consultancy/consultant_profile.html', consultant=consultant)

@app.route('/become-consultant', methods=['GET', 'POST'])
@login_required
def become_consultant():
    if request.method == 'POST':
        category = request.form['category']
        expertise = request.form['expertise']
        contact = request.form['contact']
        
        current_user.is_consultant = True
        current_user.consultant_category = category
        current_user.consultant_expertise = expertise
        current_user.consultant_contact = contact
        
        db.session.commit()
        flash('Consultant application submitted for approval!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('consultancy/register_consultant.html')

# ---------------------- MARKETPLACE ----------------------

@app.route('/cart')
def simple_cart():
    return render_template('marketplace/cart.html')


@app.route('/orders')
def simple_orders():
    return render_template('marketplace/orders.html')

@app.route('/marketplace')
def marketplace():
    products = Product.query.filter_by(is_approved=True).all()
    categories = Category.query.filter_by(type='product').all()
    return render_template('marketplace/marketplace.html', products=products, categories=categories)
    

@app.route('/marketplace/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('marketplace/product.html', product=product)

@app.route('/marketplace/new', methods=['GET', 'POST'])
@login_required
def new_product():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        category = request.form['category']
        quantity = int(request.form['quantity'])
        unit = request.form['unit']
        
        product = Product(
            name=name,
            description=description,
            price=price,
            category=category,
            quantity=quantity,
            unit=unit,
            user_id=current_user.id,
            is_approved=(current_user.role == 'admin')
        )
        
        db.session.add(product)
        db.session.commit()
        flash('Product listed successfully!', 'success')
        return redirect(url_for('marketplace'))
    
    categories = Category.query.filter_by(type='product').all()
    return render_template('marketplace/new_product.html', categories=categories)

@app.route('/marketplace/cart')
@login_required
def cart():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('marketplace/cart.html', cart_items=cart_items, total=total)

@app.route('/marketplace/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get('quantity', 1))
    
    cart_item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = Cart(user_id=current_user.id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)
    
    db.session.commit()
    flash('Product added to cart!', 'success')
    return redirect(url_for('cart'))

@app.route('/marketplace/cart/remove/<int:cart_id>')
@login_required
def remove_from_cart(cart_id):
    cart_item = Cart.query.get_or_404(cart_id)
    db.session.delete(cart_item)
    db.session.commit()
    flash('Product removed from cart!', 'success')
    return redirect(url_for('cart'))

@app.route('/marketplace/checkout', methods=['POST'])
@login_required
def checkout():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    
    if not cart_items:
        flash('Your cart is empty!', 'error')
        return redirect(url_for('cart'))
    
    for item in cart_items:
        order = Order(
            user_id=current_user.id,
            product_id=item.product_id,
            quantity=item.quantity,
            total_price=item.product.price * item.quantity,
            shipping_address=request.form['address']
        )
        db.session.add(order)
        db.session.delete(item)
    
    db.session.commit()
    flash('Order placed successfully!', 'success')
    return redirect(url_for('orders'))

@app.route('/marketplace/orders')
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('marketplace/orders.html', orders=user_orders)

# ---------------------- ADMIN PANEL ----------------------
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied!', 'error')
        return redirect(url_for('dashboard'))
    
    stats = {
        'total_users': User.query.count(),
        'total_products': Product.query.count(),
        'total_orders': Order.query.count(),
        'pending_consultants': User.query.filter_by(is_consultant=True, is_consultant_approved=False).count()
    }
    
    return render_template('admin/dashboard.html', stats=stats)

@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        flash('Access denied!', 'error')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/products')
@login_required
def admin_products():
    if current_user.role != 'admin':
        flash('Access denied!', 'error')
        return redirect(url_for('dashboard'))
    
    products = Product.query.all()
    return render_template('admin/products.html', products=products)

@app.route('/admin/approve-product/<int:product_id>')
@login_required
def approve_product(product_id):
    if current_user.role != 'admin':
        flash('Access denied!', 'error')
        return redirect(url_for('dashboard'))
    
    product = Product.query.get_or_404(product_id)
    product.is_approved = True
    db.session.commit()
    flash('Product approved!', 'success')
    return redirect(url_for('admin_products'))

@app.route('/admin/reports')
@login_required
def admin_reports():
    if current_user.role != 'admin':
        flash('Access denied!', 'error')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    products = Product.query.all()
    
    total_users = len(users)
    new_users_today = len([u for u in users if u.join_date.date() == datetime.today().date()])
    total_products = len(products)
    
    if products:
        avg_price = sum(p.price for p in products) / len(products)
        categories = {}
        for p in products:
            categories[p.category] = categories.get(p.category, 0) + 1
        top_category = max(categories, key=categories.get) if categories else 'N/A'
    else:
        avg_price = 0
        top_category = 'N/A'
    
    report_data = {
        'total_users': total_users,
        'new_users_today': new_users_today,
        'total_products': total_products,
        'avg_product_price': round(avg_price, 2),
        'top_category': top_category
    }
    
    return render_template('admin/reports.html', report_data=report_data)

# ---------------------- SEARCH ----------------------
@app.route('/search')
def search():
    query = request.args.get('q', '')
    if query:
        posts = Post.query.filter(
            (Post.title.contains(query)) | (Post.content.contains(query))
        ).filter_by(is_approved=True).all()
        
        products = Product.query.filter(
            (Product.name.contains(query)) | (Product.description.contains(query))
        ).filter_by(is_approved=True).all()
    else:
        posts = []
        products = []
    
    return render_template('search_results.html', posts=posts, products=products, query=query)


# ---------------------- MAIN RUN ----------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_sample_data()
    app.run(debug=True)
