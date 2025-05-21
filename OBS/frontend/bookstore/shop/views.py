from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from rest_framework.request import Request
from .api import BookListCreateView, OrderListCreateView
import requests

API_BASE = 'http://localhost:5000/api'

def home(request):
    from .models import Book  # Import the Book model
    
    # Get books from API
    api_view = BookListCreateView()
    response = api_view.get(Request(request))
    if response.status_code == 200:
        api_books = response.data
        # Get Django books to merge image information
        django_books = {book.id: book for book in Book.objects.all()}
        
        # Merge API data with Django data
        books = []
        for api_book in api_books:
            book_data = dict(api_book)
            if api_book['id'] in django_books:
                django_book = django_books[api_book['id']]
                if django_book.image:
                    book_data['image'] = django_book.image
            books.append(book_data)
            
        return render(request, 'shop/home.html', {'books': books})
    
    messages.error(request, 'Failed to fetch books')
    print(f"Home API error: {response.status_code}, {response.data}")
    return render(request, 'shop/error.html', {'error': 'Failed to fetch books'})

def cart(request):
    cart = request.session.get('cart', {})
    print(f"Cart in cart view: {cart}")
    if not cart:
        return render(request, 'shop/cart.html', {'cart_items': [], 'total': 0})
    api_view = BookListCreateView()
    response = api_view.get(Request(request))
    if response.status_code != 200:
        messages.error(request, 'Failed to fetch book details')
        print(f"Cart API error: {response.status_code}, {response.data}")
        return render(request, 'shop/error.html', {'error': 'Failed to fetch book details'})
    books = {str(book['id']): book for book in response.data}
    cart_items = []
    total = 0
    for book_id, quantity in cart.items():
        if book_id in books:
            book = books[book_id]
            if not isinstance(quantity, int) or quantity < 1:
                print(f"Invalid quantity for book_id={book_id}: {quantity}, setting to 1")
                cart[book_id] = 1
                request.session['cart'] = cart
                request.session.modified = True
                quantity = 1
            subtotal = book['price'] * quantity
            total += subtotal
            cart_items.append({'book': book, 'quantity': quantity, 'subtotal': subtotal})
        else:
            print(f"Book ID {book_id} not found in API response")
    print(f"Cart total: ${total:.2f}")
    return render(request, 'shop/cart.html', {'cart_items': cart_items, 'total': total})

def add_to_cart(request):
    if request.method == 'POST':
        book_id = request.POST.get('book_id')
        if not book_id:
            print("No book_id provided in add_to_cart")
            return redirect('home')
        cart = request.session.get('cart', {})
        cart[book_id] = cart.get(book_id, 0) + 1
        request.session['cart'] = cart
        request.session.modified = True
        print(f"Cart after add: {cart}")
        return redirect('cart')
    return redirect('home')

def update_cart(request):
    if request.method == 'POST':
        book_id = request.POST.get('book_id')
        quantity = request.POST.get('quantity')
        redirect_to = request.META.get('HTTP_REFERER', 'cart')  # Get the previous page URL
        
        print(f"Update cart POST data: book_id={book_id}, quantity={quantity}")
        if not book_id:
            print("No book_id provided in update_cart")
            return redirect(redirect_to)
            
        try:
            quantity = int(quantity)
            if quantity < 1:
                raise ValueError("Quantity must be at least 1")
        except (ValueError, TypeError) as e:
            print(f"Invalid quantity: {quantity}, error: {e}, defaulting to 1")
            quantity = 1
            
        cart = request.session.get('cart', {})
        if quantity > 0:
            cart[book_id] = quantity
        else:
            cart.pop(book_id, None)
            
        request.session['cart'] = cart
        request.session.modified = True
        print(f"Cart after update: {cart}")
        
        # Redirect back to the page that made the request (either cart or checkout)
        if 'checkout' in redirect_to:
            return redirect('checkout')
        return redirect('cart')
        
    print(f"Invalid request method: {request.method}")
    return redirect('cart')

def remove_from_cart(request):
    if request.method == 'POST':
        book_ids = request.POST.getlist('selected_items')
        cart = request.session.get('cart', {})
        for book_id in book_ids:
            cart.pop(book_id, None)
        request.session['cart'] = cart
        request.session.modified = True
        print(f"Cart after remove: {cart}")
        return redirect('cart')
    return redirect('cart')

@login_required
def checkout(request):
    cart = request.session.get('cart', {})
    print(f"Cart in checkout: {cart}")
    if not cart:
        messages.error(request, 'Cart is empty')
        return redirect('cart')
        
    api_view = BookListCreateView()
    response = api_view.get(Request(request))
    if response.status_code != 200:
        messages.error(request, 'Failed to fetch book details')
        print(f"Checkout API error: {response.status_code}, {response.data}")
        return render(request, 'shop/error.html', {'error': 'Failed to fetch book details'})
        
    books = {str(book['id']): book for book in response.data}
    cart_items = []
    total = 0
    
    # Validate stock and convert quantities first
    invalid_items = []
    updated_cart = {}
    for book_id, quantity in cart.items():
        if book_id not in books:
            invalid_items.append(book_id)
            continue
            
        book = books[book_id]
        try:
            quantity = int(quantity)
            if quantity < 1:
                quantity = 1
                
            # Check stock availability
            if quantity > book['stock']:
                messages.error(request, f'Only {book["stock"]} copies of "{book["title"]}" are available.')
                return redirect('cart')
                
            updated_cart[book_id] = quantity
                
        except (ValueError, TypeError):
            quantity = 1
            updated_cart[book_id] = quantity
    
    # Remove invalid items and update cart
    cart = updated_cart
    request.session['cart'] = cart
    request.session.modified = True
    
    # Calculate totals and prepare display items
    for book_id, quantity in cart.items():
        book = books[book_id]
        subtotal = float(book['price']) * quantity
        total += subtotal
        cart_items.append({
            'book': book,
            'quantity': quantity,
            'subtotal': subtotal
        })
        print(f"Checkout item: book_id={book_id}, quantity={quantity}, subtotal=${subtotal:.2f}")
            
    print(f"Checkout total: ${total:.2f}")
    
    if request.method == 'POST':
        # Prepare order items with the current cart quantities
        items = []
        for book_id, quantity in cart.items():
            if book_id in books:
                book = books[book_id]
                if quantity > book['stock']:
                    messages.error(request, f'Only {book["stock"]} copies of "{book["title"]}" are available.')
                    return redirect('checkout')
                    
                items.append({
                    'book_id': int(book_id),
                    'quantity': int(quantity),
                    'price': float(book['price'])
                })
        
        if not items:
            messages.error(request, 'No valid items in cart')
            return redirect('cart')
            
        order_data = {
            'user_id': request.user.id,
            'items': items
        }
        print(f"Order data: {order_data}")
        
        try:
            response = requests.post(f'{API_BASE}/orders', json=order_data)
            print(f"Order API response: {response.status_code}, {response.json()}")
            
            if response.status_code == 201:
                # Clear the cart
                request.session['cart'] = {}
                request.session.modified = True
                
                # Refresh the books data to get updated stock numbers
                refresh_response = api_view.get(Request(request))
                if refresh_response.status_code == 200:
                    print("Successfully refreshed book data after order")
                else:
                    print("Failed to refresh book data after order")
                    
                messages.success(request, 'Order placed successfully')
                return redirect('orders')
            
            error_msg = response.json().get('error', 'Unknown error')
            messages.error(request, f'Failed to place order: {error_msg}')
            return render(request, 'shop/error.html', {'error': f'Failed to place order: {error_msg}'})
            
        except requests.RequestException as e:
            print(f"Order API error: {e}")
            messages.error(request, 'Failed to place order')
            return render(request, 'shop/error.html', {'error': f'Failed to place order: {str(e)}'})
    
    return render(request, 'shop/checkout.html', {'cart_items': cart_items, 'total': total})

@login_required
def orders(request):
    api_view = OrderListCreateView()
    # Create a new request with query parameters properly set
    drf_request = Request(request)
    drf_request._request.GET = {'user_id': str(request.user.id)}
    response = api_view.get(drf_request)
    print(f"Orders API response: {response.status_code}, {response.data}")
    if response.status_code == 200:
        orders = response.data
        return render(request, 'shop/orders.html', {'orders': orders})
    messages.error(request, 'Failed to fetch orders')
    return render(request, 'shop/error.html', {'error': 'Failed to fetch orders'})

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
        else:
            User.objects.create_user(username=username, password=password)
            messages.success(request, 'Registration successful')
            return redirect('login')
    return render(request, 'shop/register.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            print(f"User {username} logged in, redirecting to home")
            return redirect('home')
        messages.error(request, 'Invalid credentials')
        print(f"Login failed for {username}")
    return render(request, 'shop/login.html')

def logout_view(request):
    logout(request)
    return redirect('home')