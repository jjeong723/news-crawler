from dotenv import load_dotenv
import os

import pandas as pd
import requests
import json
from tqdm import tqdm

import re
import datetime
import time

from googlenewsdecoder import gnewsdecoder
import feedparser


class NewsCrawer:
    def __init__(self):
        load_dotenv()
        self.google_key = os.getenv('GOOGLE_SEARCH_API_KEYSEARCH')
        self.naver_client = os.getenv('NAVER_CLIENT_ID')
        self.naver_secret = os.getenv('NAVER_CLIENT_SECRET')
        self.df = pd.DataFrame(columns=['Title','Link','Date', 'Description'])
    
    def save_df(self, file_name):
        self.df.to_json(file_name, orient='records', lines=True, force_ascii=False)
        
    def df_add(self, row):
        if self.df.empty:
            self.df = pd.DataFrame(row)
        else:
            self.df = pd.concat([self.df, row], ignore_index=True)

    def naver_search_news(self, query, period) -> pd.DataFrame:
        naver_client = self.naver_client
        naver_secret = self.naver_secret
        
        start=1      # 최대 Start 값은 1000
        display=100  # 최소 10 ~ 최대 100
        sort='date'  # 내림차순 / sim(정확도 기준) date(날짜순 기준)
        
        pbar = tqdm(total=1000, desc="Naver News Processing")
        while(True):
            time.sleep(1) # NAVER API 호출 제한 때문에 1초 대기
            url = "https://openapi.naver.com/v1/search/news.json?query="+ str(query) +\
            "&display=" + str(display)+ \
            "&start=" + str(start) + \
            "&sort=" + sort
            headers = {
                            "X-Naver-Client-Id": naver_client,
                            "X-Naver-Client-Secret": naver_secret
                    }
            
            try:            
                response = requests.get(url, headers=headers)
                rescode = response.status_code 

                if(rescode==200):
                    json_data = response.json()['items']
                    total_response = response.json()['total']
                    if(start > total_response):
                        break
                    else:
                        start += display
                    
                    remove_tag = re.compile('<.*?>')
                    # html문법의 태그들을 제거하는 컴파일러를 정규식을 패키지를 통해 생성
                    end_tf = False
                    for item in json_data:
                        title = re.sub(remove_tag, '', item['title'])
                        link = item['originallink']
                        description = re.sub(remove_tag, '', item['description'])
                        
                        # datetime 형식으로 변환
                        date = item['pubDate']
                        date = datetime.datetime.strptime(date, '%a, %d %b %Y %H:%M:%S %z').replace(tzinfo=None)
                        delta_date = datetime.datetime.now() - datetime.timedelta(days=period)
                        if date < delta_date:
                            end_tf = True
                            break
                        
                        row = pd.DataFrame([{'Title':title, 'Link':link, 'Date':date, 'Description':description}])
                        self.df_add(row)
                        #self.df.append(row, ignore_index=True)
                    
                    pbar.update(display)                    
                    if end_tf:
                        pbar.close()
                        return self.df
                else:
                    if(start >= 1001):   # Naver API 제한 조건 최대 1000개 이상 호출 시 종료
                        pbar.close()
                        return self.df
                    print("Naver API Error Code:" + str(rescode))
                    print(f"Error Message: {response.json()['errorMessage']}")
                    print(f"url: {url} total_response: {total_response}")
                    return self.df

            except Exception as e:
                print(f"Error Naver Search API: {str(e)}")
                return self.df

    def google_link_decode(self, link, interval_time=2) -> str:
        try:
                d_link = gnewsdecoder(link, interval=interval_time)
                if d_link.get("status"):
                        return d_link["decoded_url"]
                else:
                        print("Error:", d_link["message"])
        except Exception as e:
                print(f"Error occurred: {e}")        
                
    def google_search_news(self, query, period) -> pd.DataFrame:
        url = f'https://news.google.com/rss/search?q={query}' + \
            f'%20when%3A{period}d' + \
            '&hl=ko&gl=KR&ceid=KR:ko'
        
        try:
            response = feedparser.parse(url)
            
            for entry in tqdm(response.entries, desc="Google News Processing"):
                title = entry.title
                link = entry.link
                link = self.google_link_decode(link, interval_time=0.5)
                
                date = entry.published
                #date = datetime.datetime.strptime(date, '%a, %d %b %Y %H:%M:%S %z').replace(tzinfo=None)
                date_without_tz = date.replace(' GMT', '')
                date = datetime.datetime.strptime(date_without_tz, '%a, %d %b %Y %H:%M:%S')

                remove_tag = re.compile('<.*?>')
                description = entry.summary
                description = re.sub(remove_tag, '', description)
                
                row = pd.DataFrame([{'Title':title, 'Link':link, 'Date':date, 'Description':description}])
                self.df_add(row)
            
            return self.df
        except Exception as e:
            print(f"Error occurred: {e}")
            return self.df


        
                

def main():
    query = "인공지능"
    period = 1
    
    crawler = NewsCrawer()
    crawler.naver_search_news(query, period)
    crawler.google_search_news(query, period)
    
    # 파일 저장
    date = datetime.datetime.now().strftime("%Y%m%d")
    filename = f"{date}_news.json"
    crawler.save_df(filename)
    
    print(crawler.df)


if __name__ == "__main__":
    main()
