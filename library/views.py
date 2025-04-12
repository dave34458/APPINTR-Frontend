import requests
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.urls import reverse
from django.utils.timezone import now

API_BASE_URL = 'http://127.0.0.1:8000/api'

def staff_required(function):
    def wrap(request, *args, **kwargs):
        token = request.COOKIES.get('auth_token')
        if not token or requests.get(f'{API_BASE_URL}/users/me', headers={'Authorization': f'Token {token}'}).json().get('role') != 'staff':
            return JsonResponse({'error': 'Forbidden'}, status=403)
        return function(request, *args, **kwargs)
    return wrap
def index(request):
    token = request.COOKIES.get('auth_token')
    headers = {'Authorization': f'Token {token}'} if token else {}
    search = request.GET.get('title', '').strip().lower()
    res = requests.get(f"{API_BASE_URL}/books", headers=headers)
    books = res.json() if res.ok else []
    if search:
        books = [b for b in books if search in b['title'].lower()]
    books.sort(key=lambda b: b.get('id', 0), reverse=True)
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
    q = {k: request.GET.get(k, '').lower() for k in ['title', 'genre', 'author', 'published_date']}
    res = requests.get(f"{API_BASE_URL}/books", headers=headers)
    books = res.json() if res.ok else []
    for key, val in q.items():
        if val:
            books = [b for b in books if val in b.get(key, '').lower()]
    return render(request, 'library/books.html', {
        'books': books,
        'is_authenticated': bool(token),
        'token': token,
        **{f'{k}_query': v for k, v in q.items()}
    })


def book_detail(request, book_id):
    book_response = requests.get(f"{API_BASE_URL}/books/{book_id}")
    if book_response.status_code != 200:
        return JsonResponse({'error': 'Failed to fetch book'}, status=500)
    book = book_response.json()
    available_books_response = requests.get(f"{API_BASE_URL}/books/{book_id}/availablebooks")
    if available_books_response.status_code != 200:
        return JsonResponse({'error': 'Failed to fetch available books'}, status=500)
    available_books = available_books_response.json()
    context = {
        'book': book,
        'available_books': available_books
    }
    return render(request, 'library/book-detail.html', context)


@staff_required
def borrows(request, borrow_id=None):
    headers = {'Authorization': f'Token {request.COOKIES.get("auth_token")}'}
    data = {endpoint: requests.get(f"{API_BASE_URL}/{endpoint}", headers=headers).json() for endpoint in ['borrows', 'availablebooks', 'users', 'books']}
    for borrow in data['borrows']:
        available_book = next((ab for ab in data['availablebooks'] if ab['id'] == borrow['available_book']), None)
        if available_book:
            borrow['location'] = available_book.get('location', '')
            book = next((b for b in data['books'] if b['id'] == available_book['book']), None)
            if book: borrow.update({f'book_{key}': book.get(key, '') for key in ['title', 'author', 'published_date', 'genre', 'isbn', 'language']})
        user = next((u for u in data['users'] if u['id'] == borrow['user']), None)
        if user: borrow.update({f'user_{key}': user.get(key, '') for key in ['username', 'full_name', 'email']})
    for available_book in data['availablebooks']:
        book = next((b for b in data['books'] if b['id'] == available_book['book']), None)
        if book: available_book.update({f'book_{key}': book.get(key, '') for key in ['title', 'author', 'published_date', 'genre', 'isbn', 'language']})
    if request.method == 'POST' and request.POST.get('_method') == 'DELETE':
        try:
            response = requests.delete(f'{API_BASE_URL}/borrows/{borrow_id}', headers=headers)
            if response.status_code == 204:
                return redirect('library:borrows')
            else:
                return HttpResponse(f"Error deleting borrow record: {response.text}", status=response.status_code)
        except requests.RequestException as e:
            return HttpResponse(f"An error occurred: {str(e)}", status=500)
    elif request.method == 'POST':
        user_id, available_book_id, return_date = request.POST.get('user'), request.POST.get('available_book'), request.POST.get('return_date')
        if user_id and available_book_id and return_date:
            borrow_response = requests.post(f"{API_BASE_URL}/borrows", headers=headers, data={'user': user_id, 'available_book': available_book_id, 'return_date': return_date})
            if borrow_response.status_code == 201: return redirect('library:borrows')
            else: return HttpResponse(f"An error occurred", status=500)
    return render(request, 'library/borrows.html', {'borrows': data['borrows'], 'availablebooks': data['availablebooks'], 'users': data['users']})

@staff_required
def return_book(request, borrow_id):
    if request.method == 'POST':
        headers = {'Authorization': f'Token {request.COOKIES.get("auth_token")}'}
        book_data = {
            "user": request.POST.get('user'), "available_book": request.POST.get('available_book'),
            "borrow_date": request.POST.get('borrow_date'), "return_date": request.POST.get('return_date'),
            "date_returned": now().date().isoformat()
        }
        response = requests.put(f"{API_BASE_URL}/borrows/{borrow_id}", json=book_data, headers=headers)
        if response.status_code == 200:
            return redirect(reverse('library:borrows'))
        return JsonResponse({"status": "error", "message": "Failed to update the book return"}, status=400)
    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)

def create_book(request):
    response = requests.post(f"{API_BASE_URL}/books/",
                             data={k: request.POST.get(k) for k in ['title', 'author', 'published_date', 'isbn']})
    return redirect('book_list') if response.status_code == 201 else JsonResponse({'error': 'Failed to create book'},
                                                                                  status=400)


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

def review_list(request, book_id):
    return render(request, 'frontend/review_list.html', {'reviews': requests.get(f"{API_BASE_URL}/books/{book_id}/reviews/").json()} if requests.get(f"{API_BASE_URL}/books/{book_id}/reviews/").status_code == 200 else JsonResponse({'error': 'Failed to fetch reviews'}, status=500))

def create_review(request, book_id):
    return redirect('review_list', book_id=book_id) if requests.post(f"{API_BASE_URL}/books/{book_id}/reviews/", data={k: request.POST.get(k) for k in ['user_id', 'rating', 'comment']}).status_code == 201 else JsonResponse({'error': 'Failed to create review'}, status=400)

def update_review(request, book_id, review_id):
    return redirect('review_list', book_id=book_id) if requests.put(f"{API_BASE_URL}/books/{book_id}/reviews/{review_id}/", data={k: request.POST.get(k) for k in ['rating', 'comment']}).status_code in [200, 204] else JsonResponse({'error': 'Failed to update review'}, status=400)

def delete_review(request, book_id, review_id):
    return redirect('review_list', book_id=book_id) if requests.delete(f"{API_BASE_URL}/books/{book_id}/reviews/{review_id}/").status_code == 204 else JsonResponse({'error': 'Failed to delete review'}, status=400)

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
        username, email, password = request.POST['username'], request.POST['email'], request.POST['password']
        r = requests.post(f"{API_BASE_URL}/auth/users", data={'username': username, 'email': email, 'password': password})
        if r.status_code == 201: return login(request)
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