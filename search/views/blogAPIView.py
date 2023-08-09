from rest_framework.views import APIView  
from rest_framework.response import Response  
from rest_framework import status
import urllib
import openai
import os
import json
import requests
from bs4 import BeautifulSoup as bs
from selenium import webdriver

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
OPENAI_KEY = get_secret("OPENAI_KEY")

def chatGPT(text): # 본문 요약
  openai.api_key = OPENAI_KEY
  try:
    completion = openai.ChatCompletion.create(
      model="gpt-3.5-turbo",
      messages=[
        {
          "role": "user",
          "content": text + "이 블로그 리뷰를 요약해줘."
        }
      ],
    )
  except Exception as e:
    print('ChatGPT 예외가 발생했습니다.', e)
    return "fail"

  decoded = completion.choices[0].message["content"]
  return decoded

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
      error_message = "Naver blog API error occurred: " + str(e)
      final_result_dic = {'success':False, 'error': error_message}
      return Response(final_result_dic, status=200)

    response_dic = json.loads(response.read().decode('utf-8'))
    final_result_dic = {'success':True, 'blog': {'reviews':response_dic['items']}, 'error': None}

    return Response(final_result_dic, status=200)
  

class BlogSummaryView(APIView):
  def get(self, request):
    # request.data.get('link')
    link = request.data.get('link')

    options = webdriver.ChromeOptions()
    options.add_argument("headless")
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(options=options)
    driver.get(link)
    try:
      driver.switch_to.frame("mainFrame")
      html = driver.page_source
      soup = bs(html, "html.parser")
      elements = soup.select('div > div.se-main-container')
    except Exception as e:
      print("블로그 파싱 에러.", e)
      error_message = "블로그 파싱 에러 발생: " + str(e)
      final_result_dic = {'success':False, 'error': error_message}
      return Response(final_result_dic, status=200)

    blog_main_text = ""
    #반복문을 사용해서 각 태그의 텍스트값만 출력
    for tag in elements:
      blog_main_text += tag.get_text()
    blog_main_text = blog_main_text.replace("\n", " ")
    summarized_text = chatGPT(blog_main_text)

    if summarized_text == "fail":
      final_result_dic = {'success':False, 'error': "블로그 요약을 실패했습니다."}
      return Response(final_result_dic)

    final_result_dic = {'success':True, 'result': summarized_text, 'error': None}

    return Response(final_result_dic)