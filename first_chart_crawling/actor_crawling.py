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
  

names = []
births = []
nations = []

for link in links:
  driver.get(link)
  html = driver.page_source
  
  soup = BeautifulSoup(html, 'html.parser')
  
  # 이름
  name_tag = soup.find(class_='title').find('strong').get_text(strip=True)
  names.append(name_tag)
  
  # 출생, 국적 한번에 가져오기
  tags = soup.find(class_='spec').find('dl')
  
  # 출생
  birth_tag_sibling = tags.find('dt', text= lambda text: text and '출생' in text)
  if birth_tag_sibling:
    birth_tag = birth_tag_sibling.find_next_sibling().get_text(strip=True)
  else :
    birth_tag = ""
  births.append(birth_tag)
  
  # 국적
  nation_tag_sibling = tags.find('dt', text= lambda text: text and '국적' in text)
  if nation_tag_sibling:
    nation_tag = nation_tag_sibling.find_next_sibling().get_text(strip=True)
  else :
    nation_tag = ""
  nations.append(nation_tag)
  
  print("name : ", name_tag)
  print("birth : ", birth_tag)
  print("nation : ", nation_tag)
  print("================================")

conn = pymysql.connect(host=db['host'], port=db['port'], user=db['user'], password=db['password'], db=db['db'], charset=db['charset'])
curs = conn.cursor(pymysql.cursors.DictCursor)

for name, birth, nation in zip(names, births, nations):
  sql = "INSERT INTO person (name, birth, nation) VALUES (%s, %s, %s)"
  val = (name, birth, nation)
  curs.execute(sql, val)
  
conn.commit()
conn.close()
