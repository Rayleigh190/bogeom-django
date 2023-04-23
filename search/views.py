from rest_framework.views import APIView  
from rest_framework.response import Response  
from rest_framework import status  
from elasticsearch import Elasticsearch  
import requests
from PIL import Image
import cv2
import numpy as np
import base64
from google.cloud import vision
import openai
import os
import io
import math

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

def two_point_distance(x1,y1,x2,y2): # 두 좌표 사이의 거리를 구하는 함수
  a = x2 - x1    # 선 a의 길이
  b = y2 - y1    # 선 b의 길이
  c = math.sqrt((a * a) + (b * b))
  return c

def image_to_byte_array(image: Image) -> bytes: # Pillow 이미지를 bytes로 변환하는 함수
  # BytesIO is a file-like buffer stored in memory
  imgByteArr = io.BytesIO()
  # image.save expects a file-like as a argument
  image.save(imgByteArr, format=image.format)
  # Turn the BytesIO object back into a bytes object
  imgByteArr = imgByteArr.getvalue()
  return imgByteArr

def img_detec(req_img): # 모델 서버에 가격표 감지 요청 함수
  img_file = {'image': req_img.read()}
  response = requests.post(MODEL_SERVER_URL, files=img_file)
  
  # 받아온 좌표로 가격표 부분만 자름
  data = json.loads(response.text)
  if(len(data)>1):
    print("> waring: 가격표 복수 감지 > 중심 가격표 추출\n")
    pil_image = Image.open(req_img)
    img_center_x = pil_image.size[0]/2
    img_center_y = pil_image.size[1]/2
    dis_arry=[] # 이미지 중심 좌표와 바인딩 중심 좌표들과의 직선거리 저장
    for d in data:
      xmin = int(d.get('xmin'))
      ymin = int(d.get('ymin'))
      xmax = int(d.get('xmax'))
      ymax = int(d.get('ymax'))
      bind_center_x = (xmax-xmin)/2
      bind_center_y = (ymax-ymin)/2
      dis_arry.append(two_point_distance(img_center_x,img_center_y,bind_center_x,bind_center_y))
    ## 정리필요
    center_bind_idx = dis_arry.index(min(dis_arry)) # 이미지 중심 좌표와 가장 가까운 바인딩 Index
    # print("center bind: " + str(data[center_bind_idx])+'\n')
    xmin = int(data[center_bind_idx].get('xmin'))
    ymin = int(data[center_bind_idx].get('ymin'))
    xmax = int(data[center_bind_idx].get('xmax'))
    ymax = int(data[center_bind_idx].get('ymax'))

    # open image using PIL
    pil_image = Image.open(req_img)

    # use numpy to convert the pil_image into a numpy array
    numpy_image = np.array(pil_image)
    # convert to a openCV2 image
    img = cv2.cvtColor(numpy_image, cv2.COLOR_BGR2RGB)
    cropped = img[ymin:ymax, xmin:xmax]

    # numpy 이미지를 bytes로 변환
    succ, enc_image = cv2.imencode('.jpg', cropped)
    image_bytes = enc_image.tobytes()
    # result = base64.b64encode(image_bytes)
  elif(len(data)>0):
    xmin = int(data[0].get('xmin'))
    ymin = int(data[0].get('ymin'))
    xmax = int(data[0].get('xmax'))
    ymax = int(data[0].get('ymax'))

    # open image using PIL
    pil_image = Image.open(req_img)

    # use numpy to convert the pil_image into a numpy array
    numpy_image = np.array(pil_image)
    # convert to a openCV2 image
    img = cv2.cvtColor(numpy_image, cv2.COLOR_BGR2RGB)
    cropped = img[ymin:ymax, xmin:xmax]

    # numpy 이미지를 bytes로 변환
    succ, enc_image = cv2.imencode('.jpg', cropped)
    image_bytes = enc_image.tobytes()
    # result = base64.b64encode(image_bytes)
  else:
    print("> waring: 가격표 감지 실패 > 원본 이미지로 진행"+'\n')
    return "fail"
  
  return image_bytes

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

def chatGPT(ocr_result): # cahtGPT API
  openai.api_key = OPENAI_KEY
  completion = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
      {
        "role": "user",
        "content": "Extract one product name only from '" + ocr_result +"'. If you can't extract it, just print 'fail'."
        # ocr_result+"에서 상품명만 1개 정확하게 추출. 추출 못하겠으면 'fail'만 출력."
        # Extract one product name only from ~. If you can't extract it, just print "fail".
      }
    ],
  )
  decoded = completion.choices[0].message["content"]
  return decoded

def search_name(search_word):
  es = Elasticsearch(hosts=[{'host': ES_HOST, 'port': 9200, 'scheme': "http"}])

  if not search_word:
    return Response(status=status.HTTP_400_BAD_REQUEST, data={'message': 'search word param is missing'})

  docs = es.search(index='dictionary',query= {"multi_match": {"query": search_word, "fields": ["name"] }} )

  data_list = docs['hits']
  try:
    data = data_list['hits'][0]['_source']['name']
  except:
    data = "fail"

  return data


class SearchView(APIView):
    
  def post(self, request):
      
    # model 서버에 가격표 감지 요청하여 좌표 받아옴
    req_img = request.FILES['image']
    image_bytes = img_detec(req_img)

    if(image_bytes=="fail"):
      pil_image = Image.open(req_img)
      image_bytes = image_to_byte_array(pil_image)

    # OCR 진행
    ocr_result = ocr(image_bytes)
    print("> 1차 ocr 결과: \n" + str(ocr_result)+'\n')
    if(ocr_result=="fail"): # 가격표 감지가 이상하게 되어 ocr 진행이 어려울 때
      print("> waring: 1차 ocr 실패 > 원본 이미지로 재시도"+'\n')
      pil_image = Image.open(req_img)
      image_bytes = image_to_byte_array(pil_image)
      ocr_result = ocr(image_bytes)
      print("> 2차 ocr 결과: \n" + str(ocr_result)+'\n')
      # return Response(501) # "err: ocr 실패"
    
    # NER 진행
    gpt_result = chatGPT(ocr_result)
    print("> 1차 gpt 결과: \n" + str(gpt_result)+'\n')
    if(gpt_result.find('fail')!=-1):
      print("> waring: 1차 gpt 실패"+'\n')
      pil_image = Image.open(req_img)
      ocr_result = ocr(image_to_byte_array(pil_image))
      print("> 3차 ocr 결과:\n" + str(ocr_result)+'\n')
      gpt_result = chatGPT(ocr_result)
      print("> 2차 gpt 결과:\n " + str(gpt_result)+'\n')
      if(gpt_result.find('fail')!=-1):
        return Response(501)

    # Search 진행
    search_result = search_name(gpt_result)
    if(search_result.find('fail')!=-1):
      print("> 상품명 검색 결과: DB에 없는 상품" + '\n')
      return Response(502)
    else:
      print("> 상품명 검색 결과: \n" + str(search_result)+'\n')

    return Response(search_result)