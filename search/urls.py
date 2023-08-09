from django.urls import path  
from search.views import parseAPIView
from search.views import blogAPIView

urlpatterns = [  
    path('parse', parseAPIView.ImageSearchView.as_view()),
    path('search/blog', blogAPIView.BlogView.as_view()),
]