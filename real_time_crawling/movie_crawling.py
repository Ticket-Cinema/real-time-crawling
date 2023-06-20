import selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from bs4 import BeautifulSoup

from datetime import datetime, timedelta

import pymysql
from db_setting import db

import schedule

import time

import subprocess


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
    
  
  korean_titles = []
  english_titles = []
  open_dates = []
  genres = []
  plots = []
  nations = []
  age_limits = []
  running_times = []
  poster_store_file_names = []

  for href in href_list:
    driver.get(href)
    html = driver.page_source
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # 제목, 감독으로 중복체크!!
    
    # 이미지 가져오기
    img_class = soup.find(class_='thumb-image')
    src = img_class.find('img')['src']
    poster_store_file_names.append(src)
    
    # 제목 가져오기
    title_class = soup.find(class_='title')
    korean_title_text = title_class.find('strong').get_text(strip=True)
    english_title_text = title_class.find('p').get_text(strip=True)
    korean_titles.append(korean_title_text)
    english_titles.append(english_title_text)
    
    print("korean_title : ", korean_title_text)
    print("english_title : ", english_title_text)
    print("-----------------------------------------")
    
    # 개봉일 가져오기
    spec_class = soup.find(class_='spec')
    open_date_sibiling = spec_class.find('dt', text=lambda text: text and '개봉' in text)
    open_date_text = open_date_sibiling.find_next_sibling().get_text(strip=True)
    open_dates.append(open_date_text)
    
    print("open_date : ", open_date_text)
    print("-----------------------------------------")
    
    # 장르 가져오기
    genre_class_text = spec_class.find('dt', text= lambda text: text and '장르' in text).get_text(strip=True)
    genre_text = genre_class_text.replace("장르 :", "").replace("&nbsp;", "").strip()
    genres.append(genre_text)
    
    print("genre : " , genre_text)
    print("-----------------------------------------")
    
    # 나이 제한, 러닝타임, 국가 한번에 가져오기
    text_sibiling = spec_class.find('dt', text= lambda text: text and '기본 정보' in text)
    text = text_sibiling.find_next_sibling().get_text(strip=True).replace("&nbsp;", "").strip()
    infos = [info.strip() for info in text.split(',')]
    
    # 국가
    nation_text = infos[2]
    nations.append(nation_text)
    # 러닝타임
    running_time_text = infos[1].replace("분", "")
    running_times.append(running_time_text)
    # 나이 제한
    age_limit_text = infos[0]
    age_limits.append(age_limit_text)
    
    print("nation : ", nation_text)
    print("running_time : " , running_time_text)
    print("age_limit : ", age_limit_text)
    print("-----------------------------------------")
    
    # 내용(줄거리) 가져오기
    content_text = soup.find(class_='sect-story-movie').get_text()
    plot_text = content_text.replace("<br>", "").strip()
    plots.append(plot_text)
    
    print("plot : ", plot_text)
    
    time.sleep(0.5)
    
  conn = pymysql.connect(host=db['host'], port=db['port'], user=db['user'], password=db['password'], db=db['db'], charset=db['charset'])
  curs = conn.cursor(pymysql.cursors.DictCursor)

  for korean_title, english_title, open_date, genre, plot, nation, running_time, poster_store_file_name, age_limit in zip(korean_titles, english_titles, open_dates, genres, plots, nations, running_times, poster_store_file_names, age_limits):
    sql = "INSERT INTO movie (korean_title, english_title, open_date, genre, plot, nation, running_time, poster_store_file_name, age_limit) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
    val = (korean_title, english_title, open_date, genre, plot, nation, running_time, poster_store_file_name, age_limit)
    curs.execute(sql, val)
    
  conn.commit()
  conn.close()

  # Chrome 종료
  driver.close()
  
  # actor_crawling.py 실행
  subprocess.run(["python", "actor_crawling.py"])

# 매일 정각에 실행
schedule.every().day.at("00:00").do(upcoming)

while True:
  schedule.run_pending()
  time.sleep(1)