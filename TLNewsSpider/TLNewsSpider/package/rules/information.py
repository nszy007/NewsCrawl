'''
    信息类别
'''

import re
from parsel import Selector


class InformationCategoryRules:

    def extract(self, text):
        sel = Selector(text=text)
        words = '信息类别'
        re_xpath_var = '.*?'.join(re.split('', words))
        td_sel = sel.xpath('//td//*[re:test(text(), $re_xpath_var)]/..', re_xpath_var=re_xpath_var)
        result = td_sel.xpath('./following-sibling::td/text()').get()
        return result


if __name__ == '__main__':
    pass
