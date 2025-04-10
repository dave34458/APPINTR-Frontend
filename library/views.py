import requests
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.conf import settings

API_BASE_URL = 'http://127.0.0.1:8000/api'


def index(request):
    response = requests.get(f"{API_BASE_URL}/books")
    if response.status_code == 200: books = response.json()
    else: books = []
    return render(request, 'library/index.html', {'books': books})

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
