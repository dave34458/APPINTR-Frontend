from django.urls import path
from . import views

app_name = 'library'  # Add this line to define the app name

urlpatterns = [
    path('books/', views.book_list, name='book_list'),
    path('books/<int:book_id>/', views.book_detail, name='book_detail'),
]
