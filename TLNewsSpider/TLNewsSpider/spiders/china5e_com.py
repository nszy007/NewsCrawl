# -*- coding: utf-8 -*-

import re
import math
import scrapy
from urllib.parse import urlsplit

from ..utils import date, over_page
from ..items import TlnewsspiderItem, TlnewsItemLoader
from ..package.rules.utils import urljoin
from ..package.rules import TitleRules, PublishDateRules, ContentRules, AuthorExtractor



class China5eComSpider(scrapy.Spider):
    name = 'china5e.com'
    allowed_domains = ['china5e.com']
    site_name = '中国能源网'
    title_rules = TitleRules()
    publish_date_rules = PublishDateRules()
    author_rules = AuthorExtractor()

    # 分析链接页面之间相似性 分组抓取
    start_urls = [
        ["行业舆情", "首页>数据分析", "https://www.china5e.com/news/exponential/"],
        ["宏观舆情", "首页>政策与经济>宏观经济", "https://www.china5e.com/energy-economy/macroeconomy/"],
        ["行业舆情", "首页>电力>综合", "https://www.china5e.com/power/general/"],
        ["行业舆情", "首页>油气>综合", "https://www.china5e.com/oil-gas/general/"],
        ["行业舆情", "首页>煤炭>综合", "https://www.china5e.com/coal/general/"],
        ["行业舆情", "首页>新能源>综合", "https://www.china5e.com/new-energy/general/"],
        ["行业舆情", "首页>节能低碳>综合", "https://www.china5e.com/energy-conservation/general/"],
        ["行业舆情", "首页>分布式能源>综合", "https://www.china5e.com/distributed-energy/general/"],
        ["行业舆情", "首页>碳中和产业>综合", "https://www.china5e.com/carbon-neutrality/general/"]
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
        if 'news/exponential/' in response.url:
            yield from self.parse_news(response)
            
        else:
            yield from self.parse_macro(response)

    # 下一页的翻页方式
    def parse_news(self, response):
        for url in response.xpath('//*[@class="lista maring10"]/li/a[2]'):
            yield response.follow(url, callback=self.parse_detail, meta=response.meta)

        # 翻页
        page=response.xpath('//a[text()="下一页"]/@href').get()
        response.meta['num'] += 1
        yield from over_page(page, response, page_num=response.meta['num'], callback=self.parse)
        
    def parse_macro(self, response):
        for url in response.css('li.singleline a'):
            yield response.follow(url, callback=self.parse_detail, meta=response.meta)

        # 翻页
        page=response.xpath('//a[text()="下一页"]/@href').get()
        response.meta['num'] += 1
        yield from over_page(page, response, page_num=response.meta['num'], callback=self.parse)

    def parse_detail(self, response):
        item = TlnewsItemLoader(item=TlnewsspiderItem(), selector=response, response=response)
        # 通用提取规则
        content_rules = ContentRules()  # 正文初始化 每次都需要初始化
        item.add_value('title', self.title_rules.extract(response.text))  # 标题/title
        item.add_value('publish_date', self.publish_date_rules.extractor(response.text))  # 发布日期/publish_date
        content=response.xpath('//*[@class="showcontent"]/div[1]//text()').getall()
        content_text=[x.strip() for x in content if x.strip() != '']
        item.add_value('content_text',content_text )  # 正文内容/text_content
        # 自定义规则
        item.add_xpath('article_source', '//*[@class="showtitinfo"]/text()[2]',re='(.*?) ')  # 来源/article_source
        item.add_xpath('article_source', '//*[@class="showtitinfo"]/a[1]/text()')  # 来源/article_source
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
