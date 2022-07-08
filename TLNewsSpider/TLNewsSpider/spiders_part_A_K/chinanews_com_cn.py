# -*- coding: utf-8 -*-

import re
import math
import scrapy
import json
from urllib.parse import urlsplit

from ..utils import date, over_page, date2time
from ..items import TlnewsspiderItem, TlnewsItemLoader
from ..package.rules.utils import urljoin
from ..package.rules import TitleRules, PublishDateRules, ContentRules, AuthorExtractor



class ChinanewsComCnSpider(scrapy.Spider):
    name = 'chinanews.com.cn'
    allowed_domains = ['chinanews.com.cn']
    site_name = '中国新闻网'
    title_rules = TitleRules()
    publish_date_rules = PublishDateRules()
    author_rules = AuthorExtractor()

    # 分析链接页面之间相似性 分组抓取
    start_urls = [
        ["企业舆情", "首页>滚动", "https://www.chinanews.com.cn/scroll-news/news.html"]
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
        # 详情页
        #直接在parse里遍历页码的翻页,实时新闻不用做限制
        for i in range(1,11):
            url=f"https://www.chinanews.com.cn/scroll-news/news{i}.html"
            yield scrapy.Request(url,callback=self.parse_jijing,meta=response.meta)
            

    # 下一页的翻页方式
    def parse_jijing(self, response):
        for url in response.css(".dd_bt a"):
            yield response.follow(url, callback=self.parse_detail, meta=response.meta)

    def parse_detail(self, response):
        item = TlnewsItemLoader(item=TlnewsspiderItem(), selector=response, response=response)
        # 通用提取规则
        content_rules = ContentRules()  # 正文初始化 每次都需要初始化
        item.add_xpath('title', '//*[@class="left"]/h1/text()')  # 标题/title
        item.add_xpath('title', '//*[@class="content"]/h1/text()')  # 标题/title
        item.add_xpath('title', '//*[@class="title"]/text()')  # 标题/title
        pd=response.xpath('//*[@class="left"]/p/text()').get()
        pd_=re.findall('发布时间：(.*?) ',str(pd))
        pdr=''.join(pd_)
        publish_date=pdr.replace('年','-').replace('月','-').replace('日','')
        if pd != None:
            item.add_value('publish_date',publish_date)  # 发布日期/publish_date
        else:
            item.add_value('publish_date', self.publish_date_rules.extractor(response.text))  # 发布日期/publish_date
        item.add_xpath('content_text','//*[@class="left_zw"]/p[not(@align)]/text()')  # 正文内容/text_content
        item.add_xpath('content_text','//*[@class="content_desc"]/p/text()')  # 正文内容/text_content
        item.add_xpath('content_text','//*[@class="t3"]/text()')  # 正文内容/text_content
        # 自定义规则
        item.add_xpath('article_source', '//*[@class="source"]/text()')  # 来源/article_source
        item.add_xpath('article_source', '//*[@class="left"]/p/text()',re='来源：(.*)')  # 来源/article_source
        item.add_value('author',self.author_rules.extractor(response.text))  # 作者/author
        # 默认保存一般无需更改
        item.add_value('spider_time', date())  # 抓取时间
        item.add_value('created_time', date())  # 更新时间
        item.add_value('source_url', response.url)  # 详情网址/detail_url
        item.add_value('site_name', self.site_name)  # 站点名称
        item.add_value('site_url', urlsplit(response.url).netloc)  # 站点host
        item.add_value('classification', response.meta['classification'])  # 所属分类
        #网页源码  调试阶段注释方便查看日志
        item.add_value('html_text', response.text)  # 网页源码
        return item.load_item()
