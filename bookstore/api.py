# api.py
from flask import Blueprint, request, jsonify
from flask_restx import Api, Resource, fields, reqparse
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from bookstore import db
from bookstore.models import (
    User, Role, Book, Category, Author, Comment, Order,
    OrderDetails, ImportTicket, ImportDetails, PaymentMethod
)

# Tạo blueprint cho API
api_bp = Blueprint('api', __name__, url_prefix='/api')
authorizations = {
    'Bearer Auth': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization',
        'description': "Type in the *'Value'* input box below: **'Bearer &lt;JWT&gt;'**, where JWT is the token"
    },
}

api = Api(
    api_bp,
    version='1.0',
    title='Bookstore API',
    description='API for Bookstore Management System',
    doc='/docs',
    authorizations=authorizations,
    security='Bearer Auth'
)

# Định nghĩa các namespace
ns_auth = api.namespace('auth', description='Authentication operations')
ns_books = api.namespace('books', description='Book operations')
ns_users = api.namespace('users', description='User operations')
ns_categories = api.namespace('categories', description='Category operations')
ns_authors = api.namespace('authors', description='Author operations')
ns_orders = api.namespace('orders', description='Order operations')
ns_comments = api.namespace('comments', description='Comment operations')

# Models cho Swagger UI
login_model = api.model('Login', {
    'email': fields.String(required=True, description='User email'),
    'password': fields.String(required=True, description='User password'),
})

user_model = api.model('User', {
    'id': fields.Integer(readonly=True, description='User ID'),
    'email': fields.String(required=True, description='User email'),
    'username': fields.String(required=True, description='Username'),
    'first_name': fields.String(description='First name'),
    'last_name': fields.String(description='Last name'),
    'phone_number': fields.String(description='Phone number'),
    'address': fields.String(description='Address'),
    'image_file': fields.String(description='Profile image URL'),
})

category_model = api.model('Category', {
    'id': fields.Integer(readonly=True, description='Category ID'),
    'name': fields.String(required=True, description='Category name'),
})

author_model = api.model('Author', {
    'id': fields.Integer(readonly=True, description='Author ID'),
    'name': fields.String(required=True, description='Author name'),
})

book_model = api.model('Book', {
    'id': fields.Integer(readonly=True, description='Book ID'),
    'name': fields.String(required=True, description='Book name'),
    'unit_price': fields.Integer(required=True, description='Unit price'),
    'available_quantity': fields.Integer(required=True, description='Available quantity'),
    'image_src': fields.String(description='Book image URL'),
    'category_id': fields.Integer(required=True, description='Category ID'),
    'author_id': fields.Integer(required=True, description='Author ID'),
    'enable': fields.Boolean(description='Is book enabled'),
    'description': fields.String(description='Book description'),
})

comment_model = api.model('Comment', {
    'id': fields.Integer(readonly=True, description='Comment ID'),
    'content': fields.String(required=True, description='Comment content'),
    'created_date': fields.DateTime(readonly=True, description='Creation date'),
    'user_id': fields.Integer(required=True, description='User ID'),
    'book_id': fields.Integer(required=True, description='Book ID'),
})

order_detail_model = api.model('OrderDetail', {
    'id': fields.Integer(readonly=True, description='Order detail ID'),
    'unit_price': fields.Integer(required=True, description='Unit price'),
    'quantity': fields.Integer(required=True, description='Quantity'),
    'book_id': fields.Integer(required=True, description='Book ID'),
})

order_model = api.model('Order', {
    'id': fields.Integer(readonly=True, description='Order ID'),
    'initiated_date': fields.DateTime(description='Initiated date'),
    'cancel_date': fields.DateTime(required=True, description='Cancel date'),
    'total_payment': fields.Integer(required=True, description='Total payment'),
    'received_money': fields.Integer(description='Received money'),
    'paid_date': fields.DateTime(description='Paid date'),
    'delivered_date': fields.DateTime(description='Delivered date'),
    'payment_method_id': fields.Integer(required=True, description='Payment method ID'),
    'customer_id': fields.Integer(required=True, description='Customer ID'),
    'staff_id': fields.Integer(required=True, description='Staff ID'),
    'delivery_at': fields.String(description='Delivery address'),
    'order_details': fields.List(fields.Nested(order_detail_model), description='Order details')
})


# Auth endpoints
@ns_auth.route('/login')
class UserLogin(Resource):
    @ns_auth.doc('user_login')
    @ns_auth.expect(login_model)
    def post(self):
        """User login and get JWT token"""
        data = request.json
        user = User.query.filter_by(email=data.get('email')).first()

        # Trong thực tế, bạn cần kiểm tra mật khẩu với phương thức xác thực an toàn
        # Ví dụ: if user and verify_password(data.get('password'), user.password):
        if user:
            access_token = create_access_token(identity=user.id)
            return {
                'access_token': access_token,
                'user_id': user.id,
                'email': user.email
            }, 200
        return {'message': 'Invalid credentials'}, 401


# Book endpoints
@ns_books.route('/')
class BooksList(Resource):
    @ns_books.doc('list_books')
    @ns_books.marshal_list_with(book_model)
    def get(self):
        """List all books"""
        books = Book.query.all()
        return books

    @ns_books.doc('create_book')
    @ns_books.expect(book_model)
    @ns_books.marshal_with(book_model, code=201)
    @ns_books.response(400, 'Validation Error')
    @jwt_required()
    def post(self):
        """Create a new book"""
        data = request.json

        # Kiểm tra category và author có tồn tại không
        category = Category.query.get(data.get('category_id'))
        author = Author.query.get(data.get('author_id'))

        if not category or not author:
            api.abort(400, "Category or Author not found")

        book = Book(
            name=data.get('name'),
            unit_price=data.get('unit_price'),
            available_quantity=data.get('available_quantity'),
            image_src=data.get('image_src'),
            category_id=data.get('category_id'),
            author_id=data.get('author_id'),
            description=data.get('description'),
            enable=data.get('enable', False)
        )

        db.session.add(book)
        db.session.commit()
        return book, 201


@ns_books.route('/<int:id>')
@ns_books.response(404, 'Book not found')
class BookDetail(Resource):
    @ns_books.doc('get_book')
    @ns_books.marshal_with(book_model)
    def get(self, id):
        """Get a book by ID"""
        book = Book.query.get_or_404(id)
        return book

    @ns_books.doc('update_book')
    @ns_books.expect(book_model)
    @ns_books.marshal_with(book_model)
    @jwt_required()
    def put(self, id):
        """Update a book"""
        book = Book.query.get_or_404(id)
        data = request.json

        book.name = data.get('name', book.name)
        book.unit_price = data.get('unit_price', book.unit_price)
        book.available_quantity = data.get('available_quantity', book.available_quantity)
        book.image_src = data.get('image_src', book.image_src)
        book.category_id = data.get('category_id', book.category_id)
        book.author_id = data.get('author_id', book.author_id)
        book.description = data.get('description', book.description)
        book.enable = data.get('enable', book.enable)

        db.session.commit()
        return book

    @ns_books.doc('delete_book')
    @ns_books.response(204, 'Book deleted')
    @jwt_required()
    def delete(self, id):
        """Delete a book"""
        book = Book.query.get_or_404(id)
        db.session.delete(book)
        db.session.commit()
        return '', 204


# Category endpoints
@ns_categories.route('/')
class CategoriesList(Resource):
    @ns_categories.doc('list_categories')
    @ns_categories.marshal_list_with(category_model)
    def get(self):
        """List all categories"""
        categories = Category.query.all()
        return categories

    @ns_categories.doc('create_category')
    @ns_categories.expect(category_model)
    @ns_categories.marshal_with(category_model, code=201)
    @jwt_required()
    def post(self):
        """Create a new category"""
        data = request.json
        category = Category(name=data.get('name'))
        db.session.add(category)
        db.session.commit()
        return category, 201


@ns_categories.route('/<int:id>')
@ns_categories.response(404, 'Category not found')
class CategoryDetail(Resource):
    @ns_categories.doc('get_category')
    @ns_categories.marshal_with(category_model)
    def get(self, id):
        """Get a category by ID"""
        category = Category.query.get_or_404(id)
        return category

    @ns_categories.doc('update_category')
    @ns_categories.expect(category_model)
    @ns_categories.marshal_with(category_model)
    @jwt_required()
    def put(self, id):
        """Update a category"""
        category = Category.query.get_or_404(id)
        data = request.json
        category.name = data.get('name', category.name)
        db.session.commit()
        return category

    @ns_categories.doc('delete_category')
    @ns_categories.response(204, 'Category deleted')
    @jwt_required()
    def delete(self, id):
        """Delete a category"""
        category = Category.query.get_or_404(id)
        # Kiểm tra xem category có đang được sử dụng không
        if len(category.books) > 0:
            api.abort(400, "Cannot delete category that has books associated with it")
        db.session.delete(category)
        db.session.commit()
        return '', 204


# Author endpoints
@ns_authors.route('/')
class AuthorsList(Resource):
    @ns_authors.doc('list_authors')
    @ns_authors.marshal_list_with(author_model)
    def get(self):
        """List all authors"""
        authors = Author.query.all()
        return authors

    @ns_authors.doc('create_author')
    @ns_authors.expect(author_model)
    @ns_authors.marshal_with(author_model, code=201)
    @jwt_required()
    def post(self):
        """Create a new author"""
        data = request.json
        author = Author(name=data.get('name'))
        db.session.add(author)
        db.session.commit()
        return author, 201


@ns_authors.route('/<int:id>')
@ns_authors.response(404, 'Author not found')
class AuthorDetail(Resource):
    @ns_authors.doc('get_author')
    @ns_authors.marshal_with(author_model)
    def get(self, id):
        """Get an author by ID"""
        author = Author.query.get_or_404(id)
        return author

    @ns_authors.doc('update_author')
    @ns_authors.expect(author_model)
    @ns_authors.marshal_with(author_model)
    @jwt_required()
    def put(self, id):
        """Update an author"""
        author = Author.query.get_or_404(id)
        data = request.json
        author.name = data.get('name', author.name)
        db.session.commit()
        return author

    @ns_authors.doc('delete_author')
    @ns_authors.response(204, 'Author deleted')
    @jwt_required()
    def delete(self, id):
        """Delete an author"""
        author = Author.query.get_or_404(id)
        # Kiểm tra xem author có đang được sử dụng không
        if len(author.books) > 0:
            api.abort(400, "Cannot delete author that has books associated with it")
        db.session.delete(author)
        db.session.commit()
        return '', 204


# User endpoints
@ns_users.route('/')
class UsersList(Resource):
    @ns_users.doc('list_users')
    @ns_users.marshal_list_with(user_model)
    @jwt_required()
    def get(self):
        """List all users"""
        users = User.query.all()
        return users


@ns_users.route('/<int:id>')
@ns_users.response(404, 'User not found')
class UserDetail(Resource):
    @ns_users.doc('get_user')
    @ns_users.marshal_with(user_model)
    @jwt_required()
    def get(self, id):
        """Get a user by ID"""
        user = User.query.get_or_404(id)
        return user

    @ns_users.doc('update_user')
    @ns_users.expect(user_model)
    @ns_users.marshal_with(user_model)
    @jwt_required()
    def put(self, id):
        """Update a user"""
        current_user_id = get_jwt_identity()
        if int(current_user_id) != id:
            return {'message': 'Permission denied'}, 403

        user = User.query.get_or_404(id)
        data = request.json

        user.username = data.get('username', user.username)
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.phone_number = data.get('phone_number', user.phone_number)
        user.address = data.get('address', user.address)
        user.image_file = data.get('image_file', user.image_file)

        db.session.commit()
        return user


# Order endpoints
@ns_orders.route('/')
class OrdersList(Resource):
    @ns_orders.doc('list_orders')
    @ns_orders.marshal_list_with(order_model)
    @jwt_required()
    def get(self):
        """List all orders"""
        # Đối với admin, hiển thị tất cả đơn hàng
        # Đối với user thường, chỉ hiển thị đơn hàng của họ
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        # Kiểm tra nếu user có role admin
        is_admin = any(role.name == 'admin' for role in user.roles)

        if is_admin:
            orders = Order.query.all()
        else:
            orders = Order.query.filter_by(customer_id=current_user_id).all()

        return orders

    @ns_orders.doc('create_order')
    @ns_orders.expect(order_model)
    @ns_orders.marshal_with(order_model, code=201)
    @jwt_required()
    def post(self):
        """Create a new order"""
        data = request.json
        current_user_id = get_jwt_identity()

        # Tạo order
        order = Order(
            initiated_date=data.get('initiated_date'),
            cancel_date=data.get('cancel_date'),
            total_payment=data.get('total_payment'),
            payment_method_id=data.get('payment_method_id'),
            customer_id=current_user_id,
            staff_id=data.get('staff_id'),  # Trong thực tế, staff_id có thể được gán tự động
            delivery_at=data.get('delivery_at')
        )

        db.session.add(order)
        db.session.commit()

        # Thêm order details
        if 'order_details' in data:
            for detail in data['order_details']:
                order_detail = OrderDetails(
                    unit_price=detail.get('unit_price'),
                    quantity=detail.get('quantity'),
                    order_id=order.id,
                    book_id=detail.get('book_id')
                )
                db.session.add(order_detail)

                # Cập nhật số lượng sách
                book = Book.query.get(detail.get('book_id'))
                if book:
                    book.available_quantity -= detail.get('quantity')

        db.session.commit()
        return order, 201


@ns_orders.route('/<int:id>')
@ns_orders.response(404, 'Order not found')
class OrderDetail(Resource):
    @ns_orders.doc('get_order')
    @ns_orders.marshal_with(order_model)
    @jwt_required()
    def get(self, id):
        """Get an order by ID"""
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        order = Order.query.get_or_404(id)

        # Kiểm tra quyền truy cập
        is_admin = any(role.name == 'admin' for role in user.roles)
        if not is_admin and order.customer_id != current_user_id:
            return {'message': 'Permission denied'}, 403

        return order


# Comment endpoints
@ns_comments.route('/')
class CommentsList(Resource):
    @ns_comments.doc('create_comment')
    @ns_comments.expect(comment_model)
    @ns_comments.marshal_with(comment_model, code=201)
    @jwt_required()
    def post(self):
        """Create a new comment"""
        data = request.json
        current_user_id = get_jwt_identity()

        comment = Comment(
            content=data.get('content'),
            user_id=current_user_id,
            book_id=data.get('book_id')
        )

        db.session.add(comment)
        db.session.commit()
        return comment, 201


@ns_comments.route('/book/<int:book_id>')
class BookComments(Resource):
    @ns_comments.doc('get_book_comments')
    @ns_comments.marshal_list_with(comment_model)
    def get(self, book_id):
        """Get all comments for a book"""
        comments = Comment.query.filter_by(book_id=book_id).all()
        return comments