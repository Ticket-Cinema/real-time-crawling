import selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from bs4 import BeautifulSoup

from datetime import datetime

import pymysql
from db_setting import db

import time

import subprocess

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

# 6월 26일까지 영화 담기
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
    
    # 6월 27일 이전인지 확인
    target_date = datetime(today.year, 6, 27).date()
    if date < target_date:
      box_elements = ol_element.find_elements(By.CLASS_NAME, 'box-image')
      
      for box_element in box_elements:
        href_list.append(box_element.find_element(By.TAG_NAME, 'a').get_attribute("href"))
    
  except ValueError:
    # 날짜 형식이 아닌 경우 건너 뜀
    continue

links = []

for href in href_list:
  driver.get(href)
  
  try:
    director_dt = driver.find_element(By.XPATH, "//dt[contains(., '감독')]")
    director_as = director_dt.find_elements(By.XPATH, "./following-sibling::dd[1]/a")
    
    for director_a in director_as:
      new_link = director_a.get_attribute("href")
      
      if new_link not in links:
        links.append(new_link)
    
    actor_dt = driver.find_element(By.XPATH, "//dt[contains(., '배우')]")
    actor_as = actor_dt.find_elements(By.XPATH, "./following-sibling::dd[1]/a")
    
    for actor_a in actor_as:
      new_link = actor_a.get_attribute("href")
      
      if new_link not in links:
        links.append(new_link)
  
  except NoSuchElementException:
      print("정보 없음")
  
  time.sleep(0.1)
  
  
conn = pymysql.connect(host=db['host'], port=db['port'], user=db['user'], password=db['password'], db=db['db'], charset=db['charset'])
curs = conn.cursor(pymysql.cursors.DictCursor)


names = []
births = []
nations = []

for link in links:
  driver.get(link)
  html = driver.page_source
  
  soup = BeautifulSoup(html, 'html.parser')
  
  # 이름
  name_tag = soup.find(class_='title').find('strong').get_text(strip=True)
  
  # 출생, 국적 한번에 가져오기
  tags = soup.find(class_='spec').find('dl')
  
  # 출생
  birth_tag_sibling = tags.find('dt', text= lambda text: text and '출생' in text)
  if birth_tag_sibling:
    birth_tag = birth_tag_sibling.find_next_sibling().get_text(strip=True)
  else :
    birth_tag = ""
  
  # 국적
  nation_tag_sibling = tags.find('dt', text= lambda text: text and '국적' in text)
  if nation_tag_sibling:
    nation_tag = nation_tag_sibling.find_next_sibling().get_text(strip=True)
  else :
    nation_tag = ""
  
  print("name : ", name_tag)
  print("birth : ", birth_tag)
  print("nation : ", nation_tag)
  print("================================")
  
    
  # 배우 중복 체크 !!(이름, 출생, 국적)
  select_actor_sql = f"SELECT person_id FROM person WHERE name = '{name_tag}' and birth = '{birth_tag}' and nation = '{nation_tag}'"
  curs.execute(select_actor_sql)
  result = curs.fetchone()
  if result is None or result['person_id'] is None:
    names.append(name_tag)
    births.append(birth_tag)
    nations.append(nation_tag)

for name, birth, nation in zip(names, births, nations):
  sql = "INSERT INTO person (name, birth, nation) VALUES (%s, %s, %s)"
  val = (name, birth, nation)
  curs.execute(sql, val)
  
conn.commit()
conn.close()

driver.close()

subprocess.run(["python", "director_crawling.py"])
