# -*- coding: utf-8 -*-

import re
import math
import scrapy
from urllib.parse import urlsplit

from ..utils import date, over_page
from ..items import TlnewsspiderItem, TlnewsItemLoader
from ..package.rules.utils import urljoin
from ..package.rules import TitleRules, PublishDateRules, ContentRules, AuthorExtractor



class CnalComSpider(scrapy.Spider):
    name = 'cnal.com'
    allowed_domains = ['cnal.com']
    site_name = '世铝网'
    title_rules = TitleRules()
    publish_date_rules = PublishDateRules()
    author_rules = AuthorExtractor()

    # 分析链接页面之间相似性 分组抓取
    start_urls = [
        ["企业舆情", "首页 > 企业 > 铝企风采", "https://news.cnal.com/enterprise/"],
        ["企业舆情", "首页 > 企业 > 铝企面对面", "https://news.cnal.com/interview/"],
        ["宏观舆情", "首页 > 企业 > 会展资讯", "https://news.cnal.com/exhibition/"],
        ["企业舆情", "首页>铝业资讯>铝行业", "https://news.cnal.com/industry/"]
    ]

    def __init__(self, task_id='', *args, **kwargs):
        super().__init__(*args, **kwargs)  # <- important
        self.task_id = task_id

    def start_requests(self):
        for url_item in self.start_urls:
            classification, catlog, url = url_item
            #若不需要用到num来传递次数，则可删去
            meta = {'classification': classification,'num':0,'url':url}
            yield scrapy.Request(url, callback=self.parse, meta=meta)

    def parse(self, response):
        for url in response.css(".cnal-tit2 a"):
            yield response.follow(url, callback=self.parse_detail, meta=response.meta)

        # 翻页
        page=response.xpath('//a[text()=">>"]/@href').get()
        next_url=f"{response.meta['url']}{page}"
        response.meta['num'] += 1
        yield from over_page(next_url, response, page_num=response.meta['num'], callback=self.parse)

    def parse_detail(self, response):
        item = TlnewsItemLoader(item=TlnewsspiderItem(), selector=response, response=response)
        # 通用提取规则
        content_rules = ContentRules()  # 正文初始化 每次都需要初始化
        item.add_value('title', self.title_rules.extract(response.text))  # 标题/title
        pd=response.xpath('//*[@class="text-center font16 margin-top-20"]/text()[1]').get()
        publish_date=pd.replace('\n                ','')
        item.add_value('publish_date',publish_date)  # 发布日期/publish_date
        item.add_xpath('content_text', '//*[@class="cnal-details-con"]/p//text()')  # 正文内容/text_content
        # 自定义规则
        item.add_xpath('article_source', '//*[@class="text-center font16 margin-top-20"]/a/text()')  # 来源/article_source
        item.add_xpath('article_source', '//*[@class="text-center font16 margin-top-20"]/text()[2]',re='来源：\n                (.*)')  # 来源/article_source
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
