# search_app/views.py

from rest_framework.views import APIView  
from rest_framework.response import Response  
from rest_framework import status  
  
from elasticsearch import Elasticsearch  

# 시크릿 정보 관리
import os, json
from django.core.exceptions import ImproperlyConfigured
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
secret_file = os.path.join(BASE_DIR, 'secrets.json') # secrets.json 파일 위치를 명시

with open(secret_file) as f:
    secrets = json.loads(f.read())

def get_secret(setting, secrets=secrets):
    try:
        return secrets[setting]
    except KeyError:
        error_msg = "Set the {} environment variable".format(setting)
        raise ImproperlyConfigured(error_msg)

ES_HOST = get_secret("ES_HOST")

class SearchView(APIView):

    def get(self, request): # 키워드 입력시 검색
        es = Elasticsearch(hosts=[{'host': ES_HOST, 'port': 9200, 'scheme': "http"}])

        # 검색어
        search_word = request.query_params.get('search')

        if not search_word:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'message': 'search word param is missing'})

        docs = es.search(index='dictionary',query= {"multi_match": {"query": search_word, "fields": ["name"] }} )

        data_list = docs['hits']
        data = data_list['hits'][0]['_source']['name']

        return Response(data)