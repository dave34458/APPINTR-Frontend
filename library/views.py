import requests
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.urls import reverse
from django.utils.timezone import now
from datetime import date

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
    res = requests.get(f"{API_BASE_URL}/users/me", headers=headers)
    is_staff = res.json().get('role') == 'staff' if res.ok else False
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
        'is_staff': is_staff
    })

def all_books(request):
    token = request.COOKIES.get('auth_token')
    headers = {'Authorization': f'Token {token}'} if token else {}
    res = requests.get(f"{API_BASE_URL}/users/me", headers=headers)
    is_staff = res.json().get('role') == 'staff' if res.ok else False
    q = {k: request.GET.get(k, '').lower() for k in ['title', 'genre', 'author', 'published_date']}
    res = requests.get(f"{API_BASE_URL}/books", headers=headers)
    books = res.json() if res.ok else []
    for key, val in q.items():
        if val:
            books = [b for b in books if val in b.get(key, '').lower()]
    for book in books:
        reviews_res = requests.get(f"{API_BASE_URL}/books/{book['id']}/reviews", headers=headers)
        if reviews_res.ok:
            reviews = reviews_res.json()
            if reviews:
                total_rating = sum(review['rating'] for review in reviews)
                book['average_rating'] = round(total_rating / len(reviews), 2)  # Round to 2 decimal places
            else:
                book['average_rating'] = 0
        else:
            book['average_rating'] = 0
        book['half_star_comparison'] = [star - 0.5 for star in range(1, 6)]  # For half-star logic
    range_of_stars = range(1, 6)
    return render(request, 'library/all-books.html', {
        'books': books,
        'is_authenticated': bool(token),
        'token': token,
        **{f'{k}_query': v for k, v in q.items()},
        'range_of_stars': range_of_stars,
        'is_staff': is_staff
    })

def book_detail(request, book_id):
    token=request.COOKIES.get('auth_token')
    headers={'Authorization':f'Token {token}'} if token else {}
    res=requests.get(f"{API_BASE_URL}/users/me", headers=headers)
    is_staff=res.json().get('role')=='staff' if res.ok else False
    if request.method in ['POST', 'PUT']:
        method=request.POST.get('_method')
        review_id=request.POST.get('review_id')
        book_id=request.POST.get('book_id')  # Get book_id from the form data
        rating=request.POST.get('rating')
        comment=request.POST.get('comment')
        if method == 'DELETE':
            r=requests.delete(f'{API_BASE_URL}/books/{book_id}/reviews/{review_id}', headers=headers)
            if r.status_code != 204:
                return JsonResponse({'error':'Failed to delete review'}, status=500)
        elif method == 'PUT':
            if review_id:
                review_payload = {'rating': rating, 'comment': comment} if rating and comment else {}
                r = requests.put(f'{API_BASE_URL}/books/{book_id}/reviews/{review_id}', json=review_payload, headers=headers)
                if r.status_code != 200:
                    return JsonResponse({'error': 'Failed to update review'}, status=500)
        else:
            if rating and comment:
                review_payload = {'book': book_id, 'user': request.user.id, 'rating': rating, 'comment': comment}
                review_response = requests.post(f'{API_BASE_URL}/books/{book_id}/reviews', json=review_payload, headers=headers)
                if review_response.status_code != 201:
                    return JsonResponse({'error':'Failed to submit review'}, status=500)
        return redirect('library:book_detail', book_id=book_id)
    book_response = requests.get(f"{API_BASE_URL}/books/{book_id}", headers=headers)
    if book_response.status_code != 200:
        return JsonResponse({'error':'Failed to fetch book'}, status=500)
    book = book_response.json()
    available_books_response = requests.get(f"{API_BASE_URL}/books/{book_id}/available-books", headers=headers)
    if available_books_response.status_code != 200:
        return JsonResponse({'error':'Failed to fetch available books'}, status=500)
    available_books = available_books_response.json()
    reviews_response = requests.get(f"{API_BASE_URL}/books/{book_id}/reviews", headers=headers)
    if reviews_response.status_code != 200:
        return JsonResponse({'error':'Failed to fetch reviews'}, status=500)
    reviews = reviews_response.json()
    overall_rating = round(sum(r['rating'] for r in reviews) / len(reviews), 2) if reviews else None
    context = {'book_id':book_id, 'book': book, 'available_books': available_books, 'reviews': reviews, 'overall_rating': overall_rating, 'is_authenticated': bool(token), 'is_staff': is_staff}
    return render(request, 'library/book-detail.html', context)

def profile(request):
    token = request.COOKIES.get('auth_token')
    headers = {'Authorization': f'Token {token}'} if token else {}
    # Get user info
    res = requests.get(f"{API_BASE_URL}/users/me", headers=headers)
    if not res.ok:
        return JsonResponse({'error': 'Failed to fetch user info'}, status=500)
    user = res.json()
    is_staff = user.get('role') == 'staff'
    # Get borrows and reviews
    borrows_res = requests.get(f"{API_BASE_URL}/borrows?user=me", headers=headers)
    borrows = borrows_res.json() if borrows_res.ok else []
    reviews_res = requests.get(f"{API_BASE_URL}/reviews?user=me", headers=headers)
    reviews = reviews_res.json() if reviews_res.ok else []
    return render(request, 'library/profile.html', {
        'user': user,
        'borrows': borrows,
        'reviews': reviews,
        'is_authenticated': bool(token),
        'is_staff': is_staff
    })


@staff_required
def borrows(request):
    headers={'Authorization':f'Token {request.COOKIES.get("auth_token")}'}
    res = requests.get(f"{API_BASE_URL}/users/me", headers=headers)
    is_staff = res.json().get('role') == 'staff' if res.ok else False
    if request.method=='POST':
        method=request.POST.get('_method')
        book_id=request.POST.get('book_id')
        available_book_id=request.POST.get('available_book_id')
        borrow_id=request.POST.get('borrow_id')
        payload = {
            'user': request.POST.get('user'),
            'available_book': request.POST.get('available_book'),
            'return_date': request.POST.get('return_date'),
            'borrow_date': request.POST.get('borrow_date'),
            'date_returned': request.POST.get('date_returned')
        }
        if method=='DELETE':
            r=requests.delete(f'{API_BASE_URL}/books/{book_id}/available-books/{available_book_id}/borrows/{borrow_id}',headers=headers)
        elif method=='PUT':
            r=requests.put(f'{API_BASE_URL}/books/{book_id}/available-books/{available_book_id}/borrows/{borrow_id}',headers=headers,data=payload)
        else:
            payload['borrow_date']=str(date.today())
            r=requests.post(f'{API_BASE_URL}/books/{book_id}/available-books/{available_book_id}/borrows',headers=headers,data=payload)
        return redirect('library:borrows') if r.status_code in [200,201,204] else HttpResponse(r.text,status=r.status_code)
    borrows = requests.get(f"{API_BASE_URL}/borrows", headers=headers).json()
    availablebooks = requests.get(f"{API_BASE_URL}/available-books", headers=headers).json()
    users = requests.get(f"{API_BASE_URL}/users", headers=headers).json()
    data = {'borrows': borrows, 'availablebooks': availablebooks, 'users': users}
    locations=sorted({ab.get('location') for ab in data['availablebooks'] if ab.get('location')})
    return render(request,'library/borrows.html',data|{'locations':locations,'is_authenticated': bool(request.COOKIES.get("auth_token")), 'is_staff': is_staff})

@staff_required
def available_books(request):
    headers={'Authorization':f'Token {request.COOKIES.get("auth_token")}'}
    res = requests.get(f"{API_BASE_URL}/users/me", headers=headers)
    is_staff = res.json().get('role') == 'staff' if res.ok else False
    if request.method=='POST':
        method=request.POST.get('_method')
        book_id=request.POST.get('book_id')
        available_book_id=request.POST.get('available_book_id')
        payload = {
            'book': request.POST.get('book'),
            'location': request.POST.get('location')
        }
        if method=='DELETE':
            r=requests.delete(f'{API_BASE_URL}/books/{book_id}/available-books/{available_book_id}',headers=headers)
        elif method=='PUT':
            r=requests.put(f'{API_BASE_URL}/books/{book_id}/available-books/{available_book_id}',headers=headers,data=payload)
        else:
            r=requests.post(f'{API_BASE_URL}/books/{book_id}/available-books',headers=headers,data=payload)
        return redirect('library:available_books') if r.status_code in [200,201,204] else HttpResponse(r.text,status=r.status_code)
    books = requests.get(f"{API_BASE_URL}/books", headers=headers).json()
    available_books = requests.get(f"{API_BASE_URL}/available-books", headers=headers).json()
    data = {'available_books': available_books, 'books': books,'is_authenticated': bool(request.COOKIES.get("auth_token")),'is_staff': is_staff}
    return render(request,'library/available-books.html',data)

@staff_required
def books(request):
    headers={'Authorization':f'Token {request.COOKIES.get("auth_token")}'}
    res = requests.get(f"{API_BASE_URL}/users/me", headers=headers)
    is_staff = res.json().get('role') == 'staff' if res.ok else False
    if request.method=='POST':
        method=request.POST.get('_method')
        book_id=request.POST.get('book_id')
        payload = {
            'location': request.POST.get('location'),
            'title': request.POST.get('title'),
            'author': request.POST.get('author'),
            'published_date': request.POST.get('published_date'),
            'genre': request.POST.get('genre'),
            'isbn': request.POST.get('isbn'),
            'description': request.POST.get('description'),
            'language': request.POST.get('language'),
        }
        files = {'preview_image': request.FILES['preview_image']} if 'preview_image' in request.FILES else None
        if method=='DELETE':
            r=requests.delete(f'{API_BASE_URL}/books/{book_id}',headers=headers)
        elif method=='PUT':
            r=requests.put(f'{API_BASE_URL}/books/{book_id}',headers=headers,data=payload, files=files)
        else:
            r=requests.post(f'{API_BASE_URL}/books',headers=headers,data=payload, files=files)
        return redirect('library:books') if r.status_code in [200,201,204] else HttpResponse(r.text,status=r.status_code)
    books = requests.get(f"{API_BASE_URL}/books", headers=headers).json()
    data = {'books': books,'is_authenticated': bool(request.COOKIES.get("auth_token")), 'is_staff': is_staff}
    return render(request,'library/books.html',data)

@staff_required
def users(request):
    headers={'Authorization':f'Token {request.COOKIES.get("auth_token")}'}
    res = requests.get(f"{API_BASE_URL}/users/me", headers=headers)
    is_staff = res.json().get('role') == 'staff' if res.ok else False
    if request.method=='POST':
        method=request.POST.get('_method')
        user_id=request.POST.get('user_id')
        payload = {
            'username': request.POST.get('username'),
            'email': request.POST.get('email'),
            'role': request.POST.get('role'),
            'password': request.POST.get('password')
        }
        if method=='DELETE':
            r=requests.delete(f'{API_BASE_URL}/users/{user_id}',headers=headers)
        elif method=='PUT':
            r=requests.put(f'{API_BASE_URL}/users/{user_id}',headers=headers,data=payload)
        else:
            r=requests.post(f'{API_BASE_URL}/users',headers=headers,data=payload)
        return redirect('library:users') if r.status_code in [200,201,204] else HttpResponse(r.text,status=r.status_code)
    users = requests.get(f"{API_BASE_URL}/users", headers=headers).json()
    data = {'users': users,'is_authenticated': bool(request.COOKIES.get("auth_token")), 'is_staff': is_staff}
    return render(request,'library/users.html',data)

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