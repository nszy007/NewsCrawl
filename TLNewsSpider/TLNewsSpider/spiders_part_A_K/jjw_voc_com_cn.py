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



class JjwVocComCnSpider(scrapy.Spider):
    name = 'jjw.voc.com.cn'
    allowed_domains = ['jjw.voc.com.cn']
    site_name = '华声在线'
    title_rules = TitleRules()
    publish_date_rules = PublishDateRules()
    author_rules = AuthorExtractor()

    # 分析链接页面之间相似性 分组抓取
    start_urls = [
        ["宏观舆情", "首页>经济>经济要闻", "http://jjw.voc.com.cn/list.php?cid-247.html"],
        ["行业舆情", "首页>经济>金融保险", "http://jjw.voc.com.cn/list.php?cid-224.html"]
    ]

    def __init__(self, task_id='', *args, **kwargs):
        super().__init__(*args, **kwargs)  # <- important
        self.task_id = task_id

    def start_requests(self):
        for url_item in self.start_urls:
            classification, catlog, url = url_item
            #若不需要用到num来传递次数，则可删去
            meta = {'classification': classification,'num':1,'url':url}
            yield scrapy.Request(url, callback=self.parse, meta=meta)

    def parse(self, response):
        # 详情页
        for data in response.xpath('//*[@class="jxlbg"]'):
            data_url=data.xpath('./a/@href').get()
            data_time=data.xpath('./p/text()').get()
            url=f"http://jjw.voc.com.cn/{data_url}"
            pagetime=date2time(date_str=data_time)
            yield from over_page(url,response,page_num=1,page_time=pagetime,callback=self.parse_detail)

        # 翻页
        response.meta['num'] += 1
        page=response.meta['url']
        next_url_=page.replace('.html','')
        next_url=f"{next_url_}-page-{response.meta['num']}.html"
        yield from over_page(next_url, response, page_time=pagetime, page_num=response.meta['num']-1, callback=self.parse)


    def parse_detail(self, response):
        item = TlnewsItemLoader(item=TlnewsspiderItem(), selector=response, response=response)
        # 通用提取规则
        content_rules = ContentRules()  # 正文初始化 每次都需要初始化
        item.add_value('title', self.title_rules.extract(response.text))  # 标题/title
        item.add_value('publish_date', self.publish_date_rules.extractor(response.text))  # 发布日期/publish_date
        item.add_value('content_text', content_rules.extract(response.text))  # 正文内容/text_content
        # 自定义规则
        item.add_xpath('article_source', '//*[@class="auto txtcenter"]/text()',re='来源:(.*)\xa0')  # 来源/article_source
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
        return item.load_item()
