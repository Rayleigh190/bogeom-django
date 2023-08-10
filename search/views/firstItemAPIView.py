from rest_framework.views import APIView  
from rest_framework.response import Response  
from rest_framework import status
from bs4 import BeautifulSoup as bs
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import urllib.parse
import requests, os

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

CLOUDETYPE_API = get_secret("CLOUDETYPE_API")


class FirstItem(APIView):
  def get(self, request):
    item_name = request.GET['search']
    # item_name = request.data.get('item_name')  
    encoded_item_name = urllib.parse.quote(item_name)

    enuri_link = "https://m.enuri.com/m/search.jsp?keyword="+encoded_item_name
    danawa_link = "https://search.danawa.com/mobile/dsearch.php?keyword="+encoded_item_name
    naver_link = "https://msearch.shopping.naver.com/search/all?frm=NVSHMDL&origQuery="+ encoded_item_name +"&pagingIndex=1&pagingSize=40&productSet=model&query="+ encoded_item_name +"&sort=rel&viewType=lst"

    options = webdriver.ChromeOptions()
    options.add_argument("headless")
    options.add_argument("--disable-gpu")
    options.add_argument("lang=ko_KR")
    options.add_argument("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    # linux 환경에서 필요한 option
    options.add_argument("no-sandbox")
    options.add_argument("disable-dev-shm-usage")
    options.add_argument("lang=ko")
    driver = webdriver.Chrome(options=options)


    driver.get(enuri_link)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "listarea")))
    try:
      html = driver.page_source
      soup = bs(html, "html.parser")
      elements = soup.find('div', 'lp__prod_list').select('a')
      enuri_first_item_link = "https://m.enuri.com/"+elements[0]['href']
      print(enuri_first_item_link)
    except Exception as e:
      print("에누리 첫 번째 아이템 파싱 에러.", e)
      error_message = "에누리 첫 번째 아이템 파싱 에러 발생: " + str(e)
      final_result_dic = {'success':False, 'error': error_message}
      return Response(final_result_dic, status=200)


    driver.get(danawa_link)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "productListArea_list")))
    try:
      html = driver.page_source
      soup = bs(html, "html.parser")
      elements = soup.find('div', 'goods-list__wrap').select('a')
      dnawa_first_item_link = elements[0]['href']
      print(dnawa_first_item_link)
    except Exception as e:
      print("다나와 첫 번째 아이템 파싱 에러.", e)
      error_message = "다나와 첫 번째 아이템 파싱 에러 발생: " + str(e)
      final_result_dic = {'success':False, 'error': error_message}
      return Response(final_result_dic, status=200)


    try:
      naver_link_get_api = CLOUDETYPE_API+item_name
      response = requests.get(naver_link_get_api).json()
      naver_first_item_link = response['response']['naver']
      print(naver_first_item_link)
    except Exception as e:
      print("네이버 첫 번째 아이템 파싱 에러.", e)
      error_message = "네이버 첫 번째 아이템 파싱 에러 발생: " + str(e)
      final_result_dic = {'success':False, 'error': error_message}
      return Response(final_result_dic, status=200)
    

    final_result_dic = {'success':True, 'response': {'enuri':enuri_first_item_link, 'danawa':dnawa_first_item_link,'naver':naver_first_item_link}, 'error': None}

    driver.quit()

    return Response(final_result_dic)
  

class EnuriFirstItem(APIView):
  def get(self, request):
    item_name = request.GET['search']
    encoded_item_name = urllib.parse.quote(item_name)

    enuri_link = "https://m.enuri.com/m/search.jsp?keyword="+encoded_item_name

    options = webdriver.ChromeOptions()
    options.add_argument("headless")
    options.add_argument("--disable-gpu")
    options.add_argument("lang=ko_KR")
    options.add_argument("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    # linux 환경에서 필요한 option
    options.add_argument("no-sandbox")
    options.add_argument("disable-dev-shm-usage")
    options.add_argument("lang=ko")
    driver = webdriver.Chrome(options=options)


    driver.get(enuri_link)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "listarea")))
    try:
      html = driver.page_source
      soup = bs(html, "html.parser")
      elements = soup.find('div', 'lp__prod_list').select('a')
      enuri_first_item_link = "https://m.enuri.com/"+elements[0]['href']
      print(enuri_first_item_link)
    except Exception as e:
      print("에누리 첫 번째 아이템 파싱 에러.", e)
      error_message = "에누리 첫 번째 아이템 파싱 에러 발생: " + str(e)
      final_result_dic = {'success':False, 'error': error_message}
      return Response(final_result_dic, status=200)

    final_result_dic = {'success':True, 'response': {'enuri':enuri_first_item_link}, 'error': None}

    driver.quit()

    return Response(final_result_dic)
  

class DanawaFirstItem(APIView):
  def get(self, request):
    item_name = request.GET['search']
    encoded_item_name = urllib.parse.quote(item_name)

    danawa_link = "https://search.danawa.com/mobile/dsearch.php?keyword="+encoded_item_name

    options = webdriver.ChromeOptions()
    options.add_argument("headless")
    options.add_argument("--disable-gpu")
    options.add_argument("lang=ko_KR")
    options.add_argument("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    # linux 환경에서 필요한 option
    options.add_argument("no-sandbox")
    options.add_argument("disable-dev-shm-usage")
    options.add_argument("lang=ko")
    driver = webdriver.Chrome(options=options)


    driver.get(danawa_link)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "productListArea_list")))
    try:
      html = driver.page_source
      soup = bs(html, "html.parser")
      elements = soup.find('div', 'goods-list__wrap').select('a')
      dnawa_first_item_link = elements[0]['href']
      print(dnawa_first_item_link)
    except Exception as e:
      print("다나와 첫 번째 아이템 파싱 에러.", e)
      error_message = "다나와 첫 번째 아이템 파싱 에러 발생: " + str(e)
      final_result_dic = {'success':False, 'error': error_message}
      return Response(final_result_dic, status=200)

    
    final_result_dic = {'success':True, 'response': {'danawa':dnawa_first_item_link}, 'error': None}

    driver.quit()

    return Response(final_result_dic)
  

class NaverFirstItem(APIView):
  def get(self, request):
    item_name = request.GET['search']
    encoded_item_name = urllib.parse.quote(item_name)

    naver_link = "https://msearch.shopping.naver.com/search/all?frm=NVSHMDL&origQuery="+ encoded_item_name +"&pagingIndex=1&pagingSize=40&productSet=model&query="+ encoded_item_name +"&sort=rel&viewType=lst"

    try:
      naver_link_get_api = CLOUDETYPE_API+item_name
      response = requests.get(naver_link_get_api).json()
      naver_first_item_link = response['response']['naver']
      print(naver_first_item_link)
    except Exception as e:
      print("네이버 첫 번째 아이템 파싱 에러.", e)
      error_message = "네이버 첫 번째 아이템 파싱 에러 발생: " + str(e)
      final_result_dic = {'success':False, 'error': error_message}
      return Response(final_result_dic, status=200)
    

    final_result_dic = {'success':True, 'response': {'naver':naver_first_item_link}, 'error': None}

    return Response(final_result_dic)