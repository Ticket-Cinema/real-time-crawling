import selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from bs4 import BeautifulSoup

from datetime import datetime, timedelta

import pymysql
from db_setting import db

import schedule

import time


def upcoming():
  # 브라우저 꺼짐 방지 옵션
  chrome_options = Options()
  chrome_options.add_experimental_option("detach", True)

  # URL of the theater page
  CGV_URL = 'http://www.cgv.co.kr/movies/pre-movies.aspx'

  driver = webdriver.Chrome(options=chrome_options)
  driver.delete_all_cookies()

  driver.get(url=CGV_URL)

  # 페이지가 완전히 로딩되도록 기다림
  time.sleep(0.2)
  
  href_list = []

  # 현재 날짜로부터 7일뒤 상영작 가져오기
  today = datetime.now().date()

  elements = driver.find_element(By.CLASS_NAME, 'sect-movie-chart')
  h4_elements = elements.find_elements(By.TAG_NAME, 'h4')

  print("h4_elements : ", h4_elements)

  for h4_element in h4_elements:
    parent_text = h4_element.text
    
    print("h4 text : ", parent_text)
    
    try:
      # (을 기준으로 앞 부분 추출
      text = parent_text.split("(")[0].strip()
      date = datetime.strptime(text, "%Y.%m.%d").date()
      # 날짜 형식인 경우 해당 h4요소와 형제 태그인 ol 태그 저장
      ol_element = h4_element.find_element(By.XPATH, 'following-sibling::ol')
      
      # 7일 후 날짜인지 확인
      if date == today + timedelta(days=7):
        box_elements = ol_element.find_elements(By.CLASS_NAME, 'box-image')
        
        for box_element in box_elements:
          href_list.append(box_element.find_element(By.TAG_NAME, 'a').get_attribute("href"))
      
    except ValueError:
      # 날짜 형식이 아닌 경우 건너 뜀
      continue

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
  
  # Chrome 종료
  driver.close()


# 매일 정각에 실행
schedule.every().day.at("00:02").do(upcoming)

while True:
  schedule.run_pending()
  time.sleep(1)