from rest_framework.views import APIView  
from rest_framework.response import Response  
from rest_framework import status
import urllib

class BlogView(APIView):
    
  def get(self, request):
    product_name = request.GET['search']
    print(product_name)

    query = urllib.parse.quote(product_name)
    display = "10"
    url = "https://openapi.naver.com/v1/search/blog?query=" + \
        query + "&display=" + display
    
    

    request = urllib.request.Request(url)
    request.add_header('X-Naver-Client-Id', client_id)
    request.add_header('X-Naver-Client-Secret', client_secret)
    response = urllib.request.urlopen(request)
    print(response.read().decode('utf-8'))
    return Response(status=200)