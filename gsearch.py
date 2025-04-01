# google search results crawler
import importlib
import sys
import os
from urllib.parse import quote
from urllib.error import URLError
from urllib.request import Request
from urllib.request import urlopen
import socket
import time
import gzip
from io import BytesIO
import gzip
import re
import random
import types
from dotenv import load_dotenv, find_dotenv
from bs4 import BeautifulSoup
importlib.reload(sys)
# Load config from .env file
# TODO: Error handling
try:
    load_dotenv(find_dotenv(usecwd=True))
    base_url = os.environ.get('BASE_URL')
    results_per_page = int(os.environ.get('RESULTS_PER_PAGE'))
except:
    print("ERROR: Make sure you have .env file with proper config")
    sys.exit(1)
user_agents = list()
# results from the search engine，basically include url, title,content
class SearchResult:
    def __init__(self):
        self.url = ''
        self.title = ''
        self.content = ''
    def getURL(self):
        return self.url
    def setURL(self, url):
        self.url = url
    def getTitle(self):
        return self.title
    def setTitle(self, title):
        self.title = title
    def getContent(self):
        return self.content
    def setContent(self, content):
        self.content = content
    def printIt(self, prefix=''):
        print ('url\t->', self.url, '\n','title\t->', self.title, '\n','content\t->', self.content)
    def writeFile(self, filename):
        file = open(filename, 'a')
        try:
            file.write('url:' + self.url + '\n')
            file.write('title:' + self.title + '\n')
            file.write('content:' + self.content + '\n\n')
        except IOError as e:
            print ('file error:', e)
        finally:
            file.close()

class GoogleAPI:
    def __init__(self):
        timeout = 60
        socket.setdefaulttimeout(timeout)
    def randomSleep(self):
        sleeptime = random.randint(60, 120)
        time.sleep(sleeptime)
    def extractDomain(self, url):
        """Return string  extract the domain of a url"""
        domain = ''
        pattern = re.compile(r'http[s]?://([^/]+)/', re.U | re.M)
        url_match = pattern.search(url)
        if(url_match and url_match.lastindex > 0):
            domain = url_match.group(1)
        return domain

    def extractUrl(self, href):
        """ Return a string     extract a url from a link """
        url = ''
        pattern = re.compile(r'(http[s]?://[^&]+)&', re.U | re.M)
        url_match = pattern.search(href)
        if(url_match and url_match.lastindex > 0):
            url = url_match.group(1)
        return url

    def extractSearchResults(self, html):
        """Return a list of search results extracted from the downloaded HTML."""
        results = list()
        soup = BeautifulSoup(html, 'html.parser')
        # 查找包含搜索结果的容器
        div = soup.find('div', id='main')
        if div is None:
            div = soup.find('div', id='center_col')
        if div is None:
            div = soup.find('body')
        if div is not None:
            # 查找所有链接
            links = div.find_all('a')
            for link in links:
                if link is None:
                    continue
                # 提取 URL
                url = link.get('href', '')
                if not url or ".google" in url:  # 过滤掉无效或 Google 链接
                    continue
                url = self.extractUrl(url)
                if not url:
                    continue
                # 提取标题
                title = link.encode_contents().decode('utf-8', errors='ignore')  # 解码为字符串
                title = re.sub(r'<.+?>', '', title)  # 去除 HTML 标签
                # 提取内容
                content = ''
                span = link.find('span')  # 尝试查找 <span> 标签
                if span is not None:
                    content = span.encode_contents().decode('utf-8', errors='ignore')  # 解码为字符串
                    if '<' in content and '>' in content:  # 如果包含 HTML 标签
                        content = re.sub(r'<.+?>', '', content)  # 去除 HTML 标签
                else:
                    content = 'No content available'  # 默认值
                # 创建 SearchResult 对象并添加到结果列表
                result = SearchResult()
                result.setURL(url)
                result.setTitle(title)
                result.setContent(content)
                results.append(result)
        return results

    def search(self, query, lang='en', num=results_per_page):
        """Return a list of lists search web @param query -> query key words
        @param lang -> language of search results @param num -> number of search results to return"""
        search_results = list()
        query = quote(query)
        if(num % results_per_page == 0):
            pages = num / results_per_page
        else:
            pages = num / results_per_page + 1

        for p in range(0, int(pages)):
            start = p * results_per_page
            url = '%s/search?hl=%s&num=%d&start=%s&q=%s' % (
                base_url, lang, results_per_page, start, query)
            print("Request URL:", url)  # 打印 URL
            retry = 3
            while(retry > 0):
                try:
                    request = Request(url)
                    length = len(user_agents)
                    index = random.randint(0, length-1)
                    user_agent = user_agents[index]
                    request.add_header('User-agent', user_agent)
                    request.add_header('connection', 'keep-alive')
                    request.add_header('Accept-Encoding', 'gzip')
                    request.add_header('referer', base_url)
                    response =urlopen(request)
                    html = response.read()
                    if(response.headers.get('content-encoding', None) == 'gzip'):
                        html = gzip.GzipFile(fileobj=BytesIO(html)).read()
                    results = self.extractSearchResults(html)
                    search_results.extend(results)
                    break
                except URLError as e:
                    print ('url error:', e)
                    self.randomSleep()
                    retry = retry - 1
                    continue
                except Exception as e:
                    print ('error:', e)
                    retry = retry - 1
                    self.randomSleep()
                    continue
        return search_results

def load_user_agent():
    fp = open('./user_agents', 'r')
    line = fp.readline().strip('\n')
    while(line):
        user_agents.append(line)
        line = fp.readline().strip('\n')
    fp.close()

def crawler():
    # Load use agent string from file
    load_user_agent()
    # Create a GoogleAPI instance
    api = GoogleAPI()
    # set expect search results to be crawled
    expect_num = 10
    # if no parameters, read query keywords from file
    if(len(sys.argv) < 2):
        keywords = open('./keywords', 'r', encoding='utf-8')
        keyword = keywords.readline()
        while(keyword):
            results = api.search(keyword, num=expect_num)
            for r in results:
                r.printIt()
            keyword = keywords.readline()
        keywords.close()
    else:
        keyword = sys.argv[1]
        results = api.search(keyword, num=expect_num)
        for r in results:
            r.printIt()

if __name__ == '__main__':
    crawler()
