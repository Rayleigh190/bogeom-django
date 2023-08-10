from django.urls import path  
from search.views import parseAPIView
from search.views import blogAPIView
from search.views import firstItemAPIView

urlpatterns = [  
    path('parse', parseAPIView.ImageSearchView.as_view()),
    path('search/blog', blogAPIView.BlogView.as_view()),
    path('search/blog/chatgpt', blogAPIView.BlogSummaryView.as_view()),
    path('search/first', firstItemAPIView.FirstItem.as_view()),
    path('search/first/enuri', firstItemAPIView.EnuriFirstItem.as_view()),
    path('search/first/danawa', firstItemAPIView.DanawaFirstItem.as_view()),
    path('search/first/naver', firstItemAPIView.NaverFirstItem.as_view()),
]