from rest_framework.views import APIView  
from rest_framework.response import Response  
from rest_framework import status  
from PIL import Image
from google.cloud import vision
import openai
import os
import io

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

# ES_HOST = get_secret("ES_HOST")
# MODEL_SERVER_URL = get_secret("MODEL_SERVER_URL")
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

  
def chatGPT(ocr_result): # cahtGPT API
  openai.api_key = OPENAI_KEY
  try:
    completion = openai.ChatCompletion.create(
      model="gpt-3.5-turbo",
      messages=[
        {
          "role": "user",
          "content": str(ocr_result) + "Extract one product name from this list. Also tell me the index of that element. Respond in the following JSON format. {\"index\": number,\"product_name\":\"product name\"} . If extraction fails, respond with: {\"product_name\":\"fail\"}"
        }
      ],
    )
  except Exception as e:
    print('ChatGPT 예외가 발생했습니다.', e)

  decoded = completion.choices[0].message["content"]
  return decoded


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


class ImageSearchView(APIView):
    
  def post(self, request):
      
    # OCR 진행
    req_img = request.FILES['image']
    pil_image = Image.open(req_img)
    image_bytes = image_to_byte_array(pil_image)
    ocr_result = ocr(image_bytes)
    print("> 1차 ocr 결과: \n" + str(ocr_result)+'\n')

    # Parsing 진행
    split_result_list = ocr_result.split('\n')
    # pd_name_dic = get_pd_name(split_result_list) # 상품명 추출
    gpt_result = chatGPT(split_result_list)
    dic_result = json.loads(gpt_result)
    print("> ner 결과: " + str(dic_result))
    # return Response(gpt_result)

    if dic_result['product_name'] == 'fail':
      final_result_dic = {'success':False, 'error': '상품명 추출 실패'}
      return Response(final_result_dic)
    
    pd_price = get_pd_price(split_result_list, dic_result['index']) # 가격 추출
    if pd_price == 'fail':
      pd_price = 0
    
    final_result_dic = {'success':True, 'item': {'item_name':dic_result['product_name'], 'item_price':pd_price}, 'error': None}

    return Response(final_result_dic)