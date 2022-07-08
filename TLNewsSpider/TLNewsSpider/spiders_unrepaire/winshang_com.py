# -*- coding: utf-8 -*-

import re
import math
import scrapy
from urllib.parse import urlsplit

from ..utils import date, over_page
from ..items import TlnewsspiderItem, TlnewsItemLoader
from ..package.rules.utils import urljoin
from ..package.rules import TitleRules, PublishDateRules, ContentRules, AuthorExtractor



class WinshangComSpider(scrapy.Spider):
    name = 'winshang.com'
    allowed_domains = ['winshang.com']
    site_name = '赢商网'
    title_rules = TitleRules()
    publish_date_rules = PublishDateRules()
    author_rules = AuthorExtractor()

    # 分析链接页面之间相似性 分组抓取
    start_urls = [
        ["企业舆情", "首页>资讯>公司", "http://news.winshang.com/list-61.html"],
        ["企业舆情", "首页>资讯>项目", "http://news.winshang.com/list-11.html"],
        ["行业舆情", "首页>资讯>品牌", "http://news.winshang.com/list-12.html"],
        ["行业舆情", "首页>资讯>金融", "http://news.winshang.com/list-52.html"]
    ]

    def __init__(self, task_id='', *args, **kwargs):
        super().__init__(*args, **kwargs)  # <- important
        self.task_id = task_id

    def start_requests(self):
        for url_item in self.start_urls:
            classification, catlog, url = url_item
            #若不需要用到num来传递次数，则可删去
            meta = {'classification': classification,'num':0}
            yield scrapy.Request(url, callback=self.parse, meta=meta)

    def parse(self, response):
        #直接在parse里遍历页码的翻页
        if 'list-61.html' in  response.url:
           for i in range(1,51):
               url=f"https://news.winshang.com/list-61/page-{i}.html"
               yield from over_page(url,response,page_num=i,callback=self.parse_jijing)
               
        if 'list-11.html' in  response.url:
           for i in range(1,101):
               url=f"http://news.winshang.com/list-11/page-{i}.html"
               yield from over_page(url,response,page_num=i,callback=self.parse_jijing)
               
        if 'list-12.html' in  response.url:
           for i in range(1,121):
               url=f"https://news.winshang.com/list-12/page-{i}.html"
               yield from over_page(url,response,page_num=i,callback=self.parse_jijing)
               
        if 'list-52.html' in  response.url:
           for i in range(1,11):
               url=f"https://news.winshang.com/list-52/page-{i}.html"
               yield from over_page(url,response,page_num=i,callback=self.parse_jijing)

    # 下一页的翻页方式
    def parse_jijing(self, response):
        for url in response.css(".win-new-list1 h3 a"):
            yield response.follow(url, callback=self.parse_detail, meta=response.meta)

    def parse_detail(self, response):
        item = TlnewsItemLoader(item=TlnewsspiderItem(), selector=response, response=response)
        # 通用提取规则
        content_rules = ContentRules()  # 正文初始化 每次都需要初始化
        item.add_value('title', self.title_rules.extract(response.text))  # 标题/titlek
        item.add_value('publish_date', self.publish_date_rules.extractor(response.text))  # 发布日期/publish_date
        item.add_value('content_text', content_rules.extract(response.text))  # 正文内容/text_content
        # 自定义规则
        item.add_css('article_source', '.source .ly a:first-child::text')  # 来源/article_source
        item.add_value('author',self.author_rules.extractor(response.text))  # 作者/author
        # 默认保存一般无需更改
        item.add_value('spider_time', date())  # 抓取时间
        item.add_value('created_time', date())  # 更新时间
        item.add_value('source_url', response.url)  # 详情网址/detail_url
        item.add_value('site_name', self.site_name)  # 站点名称
        item.add_value('site_url', urlsplit(response.url).netloc)  # 站点host
        item.add_value('classification', response.meta['classification'])  # 所属分类
        # 网页源码  调试阶段注释方便查看日志
        item.add_value('html_text', response.text)  # 网页源码

        # 上面获取值可能为空, 追加匹配值
        # item.add_xpath('title', '//h1/text() || //p/h5/text()', re='[标题]{2}:(.*?)')  # 标题/title
        # item.add_css('publish_date', 'p:nth-last-child(-n+5)', re="[0-9]{0,4}年[0-9]{1,2}月[0-9]{1,2}日")  # 发布日期/publish_date
        return item.load_item()
