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

    # Filter books based on query parameters
    for key, val in q.items():
        if val:
            books = [b for b in books if val in b.get(key, '').lower()]

    # Add average rating for each book based on reviews
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

        # Precompute values for comparison in template
        book['half_star_comparison'] = [star - 0.5 for star in range(1, 6)]  # For half-star logic

    range_of_stars = range(1, 6)
    return render(request, 'library/books.html', {
        'books': books,
        'is_authenticated': bool(token),
        'token': token,
        **{f'{k}_query': v for k, v in q.items()},
        'range_of_stars': range_of_stars
    })



def book_detail(request, book_id):
    token=request.COOKIES.get('auth_token')
    headers={'Authorization':f'Token {token}'} if token else {}
    if request.method=='POST':
        rating=request.POST.get('rating')
        comment=request.POST.get('comment')
        if rating and comment:
            review_payload={'book':book_id,'user':request.user.id,'rating':rating,'comment':comment}
            review_response=requests.post(f'{API_BASE_URL}/books/{book_id}/reviews',json=review_payload,headers=headers)
            if review_response.status_code!=201:
                return JsonResponse({'error':'Failed to submit review'},status=500)
        return redirect('library:book_detail',book_id=book_id)
    book_response=requests.get(f"{API_BASE_URL}/books/{book_id}",headers=headers)
    if book_response.status_code!=200:
        return JsonResponse({'error':'Failed to fetch book'},status=500)
    book=book_response.json()
    available_books_response=requests.get(f"{API_BASE_URL}/books/{book_id}/availablebooks",headers=headers)
    if available_books_response.status_code!=200:
        return JsonResponse({'error':'Failed to fetch available books'},status=500)
    available_books=available_books_response.json()
    reviews_response=requests.get(f"{API_BASE_URL}/books/{book_id}/reviews",headers=headers)
    if reviews_response.status_code!=200:
        return JsonResponse({'error':'Failed to fetch reviews'},status=500)
    reviews=reviews_response.json()
    overall_rating=round(sum(r['rating'] for r in reviews)/len(reviews),2) if reviews else None
    context={'book':book,'available_books':available_books,'reviews':reviews,'overall_rating':overall_rating,'is_authenticated':bool(token)}
    return render(request,'library/book-detail.html',context)



@staff_required
def borrows(request):
    headers={'Authorization':f'Token {request.COOKIES.get("auth_token")}'}
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
            r=requests.delete(f'{API_BASE_URL}/books/{book_id}/availablebooks/{available_book_id}/borrows/{borrow_id}',headers=headers)
        elif method=='PUT':
            r=requests.put(f'{API_BASE_URL}/books/{book_id}/availablebooks/{available_book_id}/borrows/{borrow_id}',headers=headers,data=payload)
        else:
            from datetime import date
            payload['borrow_date']=str(date.today())
            r=requests.post(f'{API_BASE_URL}/books/{book_id}/availablebooks/{available_book_id}/borrows',headers=headers,data=payload)
        return redirect('library:borrows') if r.status_code in [200,201,204] else HttpResponse(r.text,status=r.status_code)
    data={ep:requests.get(f"{API_BASE_URL}/{ep}",headers=headers).json() for ep in ['borrows','availablebooks','users']}
    locations=sorted({ab.get('location') for ab in data['availablebooks'] if ab.get('location')})
    return render(request,'library/borrows.html',data|{'locations':locations})


def create_book(request):
    response = requests.post(f"{API_BASE_URL}/books/",
                             data={k: request.POST.get(k) for k in ['title', 'author', 'published_date', 'isbn']})
    return redirect('book_list') if response.status_code == 201 else JsonResponse({'error': 'Failed to create book'},status=400)

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