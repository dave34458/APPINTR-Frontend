from django.urls import path
from . import views
from .views import return_book

app_name = 'library'  # Add this line to define the app name

urlpatterns = [
    path('index', views.index, name='index'),
    path('books', views.books, name='books'),
    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),
    path('register', views.register, name='register'),
    path('books/<int:book_id>', views.book_detail, name='book_detail'),
    path('borrows', views.borrows, name='borrows'),
    path('return-book/<int:borrow_id>', return_book, name='return_book'),
]
