from rest_framework.views import APIView  
from rest_framework.response import Response  
from rest_framework import status  
from elasticsearch import Elasticsearch
from PIL import Image
from google.cloud import vision
import os
import io

# 시크릿 정보 관리
import json
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
OPENAI_KEY = get_secret("OPENAI_KEY")


def image_to_byte_array(image: Image) -> bytes: # Pillow 이미지를 bytes로 변환하는 함수
  # BytesIO is a file-like buffer stored in memory
  imgByteArr = io.BytesIO()
  # image.save expects a file-like as a argument
  image.save(imgByteArr, format=image.format)
  # Turn the BytesIO object back into a bytes object
  imgByteArr = imgByteArr.getvalue()
  return imgByteArr


def ocr(image): # google cloud vision ocr API
  os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(BASE_DIR)+'/google_service_secret_key.json'

  # Instantiates a client
  client = vision.ImageAnnotatorClient()

  image = vision.Image(content=image)

  # Performs label detection on the image file
  response = client.text_detection(image=image)
  labels = response.text_annotations
  if(len(labels)==0):
    ocr_result = "fail"
  else: 
    ocr_result = labels[0].description

  return ocr_result


def search_name(search_word):
  es = Elasticsearch(hosts=[{'host': ES_HOST, 'port': 9200, 'scheme': "http"}])

  if not search_word:
    return Response(status=status.HTTP_400_BAD_REQUEST, data={'message': 'search word param is missing'})

  docs = es.search(index='dictionary',query= {"multi_match": {"query": search_word, "fields": ["name"] }} )

  data_list = docs['hits']
  try:
    score_data = data_list['hits'][0]['_score']
    name_data = data_list['hits'][0]['_source']['name']
    item_id = data_list['hits'][0]['_source']['id']
    dic_data = {'id': item_id, 'name': name_data, 'score': score_data}
    return dic_data
  except:
    data = "fail"

  return data


def get_pd_name(split_result_list): # 상품명 추출
  search_result_list = []
  max_score = 0
  name_idx = -1
  for block in split_result_list:
    search_result = search_name(block)
    if not search_result == 'fail':
      search_result_list.append(search_result)
      if search_result['score'] > max_score:
        max_score = search_result['score']
        name_idx = split_result_list.index(block)

  # score를 기준으로 내림차순 정렬
  sorted_search_result_list = sorted(search_result_list, key=lambda x: x['score'], reverse=True)
  
  if max_score > 4:
    dic = {'item_id': sorted_search_result_list[0]['id'], 'item_name': sorted_search_result_list[0]['name'], 'index': name_idx}
    return dic
  else:
    return "fail"


def get_pd_price(split_result_list, name_idx): # 가격 추출
  for block in split_result_list[name_idx:]:
    # if any(temp.isdigit() for temp in block): # 1000원 이하 가격 추출
    if (',' in block or '.' in block) and (2 < len(block) < 16):  # 1000원 이상 가격 추출
      price = ""
      for letter in block:
        if letter.isdigit():
          price += letter
      try:
        price = int(price)
        return price
      except:
        continue
    else:
      continue
  return 'fail'


class SearchView(APIView):
    
  def post(self, request):
      
    # OCR 진행
    req_img = request.FILES['image']
    pil_image = Image.open(req_img)
    image_bytes = image_to_byte_array(pil_image)
    ocr_result = ocr(image_bytes)
    print("> 1차 ocr 결과: \n" + str(ocr_result)+'\n')

    # Parsing 진행
    split_result_list = ocr_result.split('\n')
    pd_name_dic = get_pd_name(split_result_list) # 상품명 추출

    if pd_name_dic == 'fail':
      return Response(501)
    pd_price = get_pd_price(split_result_list, pd_name_dic['index']) # 가격 추출
    if pd_price == 'fail':
      pd_price = 0
    
    final_result_dic = {'img_id':pd_name_dic['item_id'], 'item_name':pd_name_dic['item_name'], 'item_price':pd_price}

    return Response(final_result_dic)