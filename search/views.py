from rest_framework.views import APIView  
from rest_framework.response import Response  
from rest_framework import status  
from elasticsearch import Elasticsearch  
import requests
from PIL import Image
import cv2
import numpy as np
import base64

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
MODEL_SERVER_URL = get_secret("MODEL_SERVER_URL")

class SearchView(APIView):
    
    def post(self, request):
        
        # model 서버에 가격표 감지 요청하여 좌표 받아옴
        img_file = {'image': request.FILES['image'].read()}
        response = requests.post(MODEL_SERVER_URL, files=img_file)

        # 받아온 좌표로 가격표 부분만 자름
        data = json.loads(response.text)
        if(len(data)>0):
          xmin = int(data[0].get('xmin'))
          ymin = int(data[0].get('ymin'))
          xmax = int(data[0].get('xmax'))
          ymax = int(data[0].get('ymax'))

          # open image using PIL
          pil_image = Image.open(request.FILES['image'].file)
          print("hay")
          # use numpy to convert the pil_image into a numpy array
          numpy_image = np.array(pil_image)
          # convert to a openCV2 image
          img = cv2.cvtColor(numpy_image, cv2.COLOR_BGR2RGB)
          cropped = img[ymin:ymax, xmin:xmax]

          # numpy 이미지를 bytes로 변환
          succ, enc_image = cv2.imencode('.jpg', cropped)
          image_bytes = enc_image.tobytes()
          result = base64.b64encode(image_bytes)
        else:
          print(data)

        return Response(result)

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