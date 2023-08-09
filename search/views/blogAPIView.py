from rest_framework.views import APIView  
from rest_framework.response import Response  
from rest_framework import status
import urllib
import os
import json

# 시크릿 정보 관리
import json
from django.core.exceptions import ImproperlyConfigured
from pathlib import Path


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
secret_file = os.path.join(BASE_DIR, 'secrets.json') # secrets.json 파일 위치를 명시

with open(secret_file) as f:
  secrets = json.loads(f.read())

def get_secret(setting, secrets=secrets):
  try:
    return secrets[setting]
  except KeyError:
    error_msg = "Set the {} environment variable".format(setting)
    raise ImproperlyConfigured(error_msg)

NAVER_CLIENT_ID = get_secret("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = get_secret("NAVER_CLIENT_SECRET")

class BlogView(APIView):
    
  def get(self, request):
    product_name = request.GET['search']

    query = urllib.parse.quote(product_name)
    display = "10"
    url = "https://openapi.naver.com/v1/search/blog?query=" + \
        query + "&display=" + display
    
    client_id = NAVER_CLIENT_ID
    client_secret = NAVER_CLIENT_SECRET

    request = urllib.request.Request(url)
    request.add_header('X-Naver-Client-Id', client_id)
    request.add_header('X-Naver-Client-Secret', client_secret)

    try:
      response = urllib.request.urlopen(request)
    except Exception as e:
      print("네이버 블로그 API 오류 발생.", e)
      final_result_dic = {'success':False, 'error': "네이버 블로그 API 오류 발생." + e}
      return Response(final_result_dic, status=200)

    response_dic = json.loads(response.read().decode('utf-8'))
    final_result_dic = {'success':True, 'blog': {'reviews':response_dic['items']}, 'error': None}

    return Response(final_result_dic, status=200)