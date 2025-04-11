import requests
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.conf import settings

API_BASE_URL = 'http://127.0.0.1:8000/api'


def index(request):
    token = request.COOKIES.get('auth_token')
    headers = {'Authorization': f'Token {token}'} if token else {}
    search = request.GET.get('title', '').strip().lower()
    res = requests.get(f"{API_BASE_URL}/books", headers=headers)
    books = res.json() if res.ok else []
    if search:
        books = [b for b in books if search in b['title'].lower()]
    books.sort(key=lambda b: b.get('added_date', ''), reverse=True)
    latest_book = books[0] if books else None
    recent_books = books[1:4]
    return render(request, 'library/index.html', {
        'latest_book': latest_book,
        'recent_books': recent_books,
        'is_authenticated': bool(token),
        'token': token,
        'search_query': search,
    })

def books(request):
    token = request.COOKIES.get('auth_token')
    headers = {'Authorization': f'Token {token}'} if token else {}
    search = request.GET.get('title', '').strip().lower()
    res = requests.get(f"{API_BASE_URL}/books", headers=headers)
    books = res.json() if res.ok else []
    if search:
        books = [b for b in books if search in b['title'].lower()]
    return render(request, 'library/books.html', {
        'books': books,
        'is_authenticated': bool(token),
        'token': token,
        'search_query': search
    })

def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        response = requests.post(f"{API_BASE_URL}/auth/sessions", data={
            'username': username,
            'password': password,
        })
        if response.status_code == 200:
            token = response.json().get('token')
            if token:
                # Store token in cookies
                response = redirect('library:index')
                response.set_cookie('auth_token', token, httponly=True, secure=True)
                return response
            else:
                return render(request, 'library/login.html', {'error': 'Token missing'})
        return render(request, 'library/login.html', {'error': 'Invalid credentials'})
    return render(request, 'library/login.html')


def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        response = requests.post(f"{API_BASE_URL}/auth/users", data={
            'username': username,
            'email': email,
            'password': password,
        })
        if response.status_code == 201:
            return redirect('library:index')
        else:
            # Handle error
            return render(request, 'library/login.html', {'error': 'Registration failed'})


def logout(request):
    token = request.COOKIES.get('auth_token')
    if not token:
        return redirect('library:index')

    headers = {'Authorization': f'Token {token}'}
    response = requests.delete(f"http://127.0.0.1:8000/api/auth/logout", headers=headers)
    if response.status_code == 204:
        response = redirect('library:index')
        response.delete_cookie('auth_token')
        return response
    else:
        return redirect('library:index')


def book_detail(request, book_id):
    return render(request, 'frontend/book_detail.html', {'book': requests.get(f"{API_BASE_URL}/books/{book_id}/").json()} if requests.get(f"{API_BASE_URL}/books/{book_id}/").status_code == 200 else JsonResponse({'error': 'Failed to fetch book'}, status=500))

def create_book(request):
    return redirect('book_list') if requests.post(f"{API_BASE_URL}/books/", data={k: request.POST.get(k) for k in ['title', 'author', 'published_date', 'isbn']}).status_code == 201 else JsonResponse({'error': 'Failed to create book'}, status=400)

def update_book(request, book_id):
    return redirect('book_detail', book_id=book_id) if requests.put(f"{API_BASE_URL}/books/{book_id}/", data={k: request.POST.get(k) for k in ['title', 'author', 'published_date', 'isbn']}).status_code in [200, 204] else JsonResponse({'error': 'Failed to update book'}, status=400)

def delete_book(request, book_id):
    return redirect('book_list') if requests.delete(f"{API_BASE_URL}/books/{book_id}/").status_code == 204 else JsonResponse({'error': 'Failed to delete book'}, status=400)

def availablebook_list(request, book_id):
    return render(request, 'frontend/availablebook_list.html', {'available_books': requests.get(f"{API_BASE_URL}/books/{book_id}/availablebooks/").json()} if requests.get(f"{API_BASE_URL}/books/{book_id}/availablebooks/").status_code == 200 else JsonResponse({'error': 'Failed to fetch available books'}, status=500))

def create_availablebook(request, book_id):
    return redirect('availablebook_list', book_id=book_id) if requests.post(f"{API_BASE_URL}/books/{book_id}/availablebooks/", data={k: request.POST.get(k) for k in ['location', 'is_available']}).status_code == 201 else JsonResponse({'error': 'Failed to create available book'}, status=400)

def update_availablebook(request, book_id, available_book_id):
    return redirect('availablebook_list', book_id=book_id) if requests.put(f"{API_BASE_URL}/books/{book_id}/availablebooks/{available_book_id}/", data={k: request.POST.get(k) for k in ['location', 'is_available']}).status_code in [200, 204] else JsonResponse({'error': 'Failed to update available book'}, status=400)

def delete_availablebook(request, book_id, available_book_id):
    return redirect('availablebook_list', book_id=book_id) if requests.delete(f"{API_BASE_URL}/books/{book_id}/availablebooks/{available_book_id}/").status_code == 204 else JsonResponse({'error': 'Failed to delete available book'}, status=400)

def borrow_list(request, book_id, available_book_id):
    return render(request, 'frontend/borrow_list.html', {'borrows': requests.get(f"{API_BASE_URL}/books/{book_id}/availablebooks/{available_book_id}/borrows/").json()} if requests.get(f"{API_BASE_URL}/books/{book_id}/availablebooks/{available_book_id}/borrows/").status_code == 200 else JsonResponse({'error': 'Failed to fetch borrows'}, status=500))

def create_borrow(request, book_id, available_book_id):
    return redirect('borrow_list', book_id=book_id, available_book_id=available_book_id) if requests.post(f"{API_BASE_URL}/books/{book_id}/availablebooks/{available_book_id}/borrows/", data={k: request.POST.get(k) for k in ['user_id', 'borrow_date']}).status_code == 201 else JsonResponse({'error': 'Failed to create borrow'}, status=400)

def update_borrow(request, book_id, available_book_id, borrow_id):
    return redirect('borrow_list', book_id=book_id, available_book_id=available_book_id) if requests.put(f"{API_BASE_URL}/books/{book_id}/availablebooks/{available_book_id}/borrows/{borrow_id}/", data={k: request.POST.get(k) for k in ['user_id', 'return_date']}).status_code in [200, 204] else JsonResponse({'error': 'Failed to update borrow'}, status=400)

def delete_borrow(request, book_id, available_book_id, borrow_id):
    return redirect('borrow_list', book_id=book_id, available_book_id=available_book_id) if requests.delete(f"{API_BASE_URL}/books/{book_id}/availablebooks/{available_book_id}/borrows/{borrow_id}/").status_code == 204 else JsonResponse({'error': 'Failed to delete borrow'}, status=400)

def review_list(request, book_id):
    return render(request, 'frontend/review_list.html', {'reviews': requests.get(f"{API_BASE_URL}/books/{book_id}/reviews/").json()} if requests.get(f"{API_BASE_URL}/books/{book_id}/reviews/").status_code == 200 else JsonResponse({'error': 'Failed to fetch reviews'}, status=500))

def create_review(request, book_id):
    return redirect('review_list', book_id=book_id) if requests.post(f"{API_BASE_URL}/books/{book_id}/reviews/", data={k: request.POST.get(k) for k in ['user_id', 'rating', 'comment']}).status_code == 201 else JsonResponse({'error': 'Failed to create review'}, status=400)

def update_review(request, book_id, review_id):
    return redirect('review_list', book_id=book_id) if requests.put(f"{API_BASE_URL}/books/{book_id}/reviews/{review_id}/", data={k: request.POST.get(k) for k in ['rating', 'comment']}).status_code in [200, 204] else JsonResponse({'error': 'Failed to update review'}, status=400)

def delete_review(request, book_id, review_id):
    return redirect('review_list', book_id=book_id) if requests.delete(f"{API_BASE_URL}/books/{book_id}/reviews/{review_id}/").status_code == 204 else JsonResponse({'error': 'Failed to delete review'}, status=400)
