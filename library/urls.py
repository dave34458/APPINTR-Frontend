from django.urls import path
from . import views

app_name = 'library'  # Add this line to define the app name

urlpatterns = [
    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),
    path('register', views.register, name='register'),
    path('index', views.index, name='index'),
    path('all-books', views.all_books, name='all_books'),
    path('profile', views.profile, name='profile'),

    path('books/<int:book_id>', views.book_detail, name='book_detail'),
    path('books', views.books, name='books'),
    path('available-books', views.available_books, name='available_books'),
    path('borrows', views.borrows, name='borrows'),
    path('users', views.users, name='users'),

]
