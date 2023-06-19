import selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from bs4 import BeautifulSoup

import pymysql
from db_setting import db

# 페이지 로딩을 기다리는데 사용할 time 모듈 import
import time

# 브라우저 꺼짐 방지 옵션
chrome_options = Options()
chrome_options.add_experimental_option("detach", True)

# URL of the theater page
CGV_URL = 'http://www.cgv.co.kr/movies/?lt=1&ft=1'

driver = webdriver.Chrome(options=chrome_options)
driver.delete_all_cookies()

driver.get(url=CGV_URL)

# 페이지가 완전히 로딩되도록 1초동안 기다림
time.sleep(0.3)

# 더보기 버튼이 있는지 확인
btn_mores = driver.find_elements(By.CLASS_NAME, 'btn-more-fontbold')

if btn_mores:
  for btn in btn_mores:
    btn.click()
    time.sleep(0.3)

# 영화 클릭
box_elements = driver.find_elements(By.CLASS_NAME, 'box-image')
href_list = []

for element in box_elements:
  
  href_list.append(element.find_element(By.TAG_NAME, 'a').get_attribute('href'))
  
  

conn = pymysql.connect(host=db['host'], port=db['port'], user=db['user'], password=db['password'], db=db['db'], charset=db['charset'])
curs = conn.cursor(pymysql.cursors.DictCursor)

for href in href_list:
  driver.get(href)
  
  directors = []
  actors = []
  
  title = driver.find_element(By.CLASS_NAME, 'title').find_element(By.TAG_NAME, 'strong').text.strip()
  print("title : ", title);
  
  try:
    director_dt = driver.find_element(By.XPATH, "//dt[contains(., '감독')]")
    director_as = director_dt.find_elements(By.XPATH, "./following-sibling::dd[1]/a")
    
    for director_a in director_as:
      director_name = director_a.text.strip()
      
      if director_name not in directors:
        directors.append(director_name)
    
    actor_dt = driver.find_element(By.XPATH, "//dt[contains(., '배우')]")
    actor_as = actor_dt.find_elements(By.XPATH, "./following-sibling::dd[1]/a")
    
    for actor_a in actor_as:
      actor_name = actor_a.text.strip()
      
      if actor_name not in actors:
        actors.append(actor_name)
  
  except NoSuchElementException:
      print("정보 없음")
      
      
  sql = "INSERT INTO director (movie_id, person_id, type) VALUES (%s, %s, %s)"
  
  # movie_id 가져오기
  select_movie_id_sql = f"SELECT movie_id FROM movie WHERE korean_title = '{title}'"
  curs.execute(select_movie_id_sql)
  movie_id = curs.fetchone()['movie_id']
  
  # person_id 가져오기
  for name in directors:
    select_person_id_sql = f"SELECT person_id FROM person WHERE name = '{name}'"
    curs.execute(select_person_id_sql)
    person_id = curs.fetchone()['person_id']
    val = (movie_id, person_id, "감독")
    curs.execute(sql, val)
    
  conn.commit()
    
  for name in actors:
    select_person_id_sql = f"SELECT person_id FROM person WHERE name = '{name}'"
    curs.execute(select_person_id_sql)
    person_id = curs.fetchone()['person_id']
    val = (movie_id, person_id, "배우")
    curs.execute(sql, val)
    
  conn.commit()
  
  time.sleep(0.1)

conn.close()

driver.close()
