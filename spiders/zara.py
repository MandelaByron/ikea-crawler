import re
import json
import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor

from suppliercrawler.utils import _price

from suppliercrawler.items import SuppliercrawlerItem

class ZaraSpider(CrawlSpider):
    name = 'zara'
    allowed_domains = ['zara.com']

    start_urls = [
        'https://www.zara.com/tr/en'
    ]

    custom_settings = {
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': 90,
            'scrapy_proxies.RandomProxy': 300, # If you are using the RandomProxy middleware it doesnt work!
            'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
        }
    }

    rules = (
        Rule(LinkExtractor(
            allow=(
                r'-p\d{2,16}.html',
                r'-l\d{2,16}.html',
                r'-pL\d{2,16}.html',
                r'-mkt\d{2,16}.html',
            )
            ), 
            callback='parse', 
            follow=True
        ),
    )

    
    def parse(self, response):
        regex_exp = r'-p\d{2,16}.html'
        if re.search(regex_exp, response.url):
            name = response.css('h1.product-detail-info__header-name::text').get()
            raw_data = response.xpath('//script[contains(text(),"window.zara.viewPayload")]/text()').get()
            raw_data = raw_data.split('window.zara.viewPayload = ')[1][:-1]
            data = json.loads(raw_data)
            '''with open('zara_{}.json'.format(name.replace('/','')), 'w') as f:
                json.dump(data, f, indent=4)'''
            
            product = data['product']
            product_name = product['name']
            scrap_url = response.url
            brand = 'ZARA'
            category = '/'.join([x['text'] for x in product['seo']['breadCrumb'][:-1]])
            code = product['detail']['displayReference']
            group_code = code.replace("/", "-") + "-grp"
            list_price = _price(response.css('div.product-detail-info__price span.price-original__amount::text').get())
            if not list_price:
                list_price = _price(response.css('div.product-detail-info__price span.price-old__amount::text').get())
            price = _price(response.css('div.product-detail-info__price span.price-current__amount span.money-amount__main::text').get())
            if not list_price:
                list_price = price
            description = ' '.join(response.css('div.product-detail-description *::text').extract())

            colors = product['detail']['colors']
            product_images = []
            for color in colors:
                images = color['xmedia']
                for image in images:
                    if not 'contents/cm' in image['path']:
                        image_name = 'https://static.zara.net/photos//' + image['path'] + '/' + image['name'] + '.jpg?ts=' + image['timestamp']
                        product_images.append(image_name)
                
                sizes = color['sizes']
                old_price = ''
                for  size in sizes:
                    product_code = code + ',' + size['name'] + ',' + color['name']
                    price = size['price'] / 100
                    if size.get('oldPrice'):
                        old_price = size['oldPrice'] / 100

                    if 'in_stock' in size['availability']:
                        qty = 1
                    else:
                        qty = 0
                    
                    item = SuppliercrawlerItem()
                    item['scrap_url'] = scrap_url
                    item['category'] = category
                    item['brand'] = brand
                    item['group_code'] = group_code
                    item['name'] = product_name
                    item['product_code'] = product_code
                    item['price'] = price
                    if not old_price:
                        old_price = price
                    item['list_price'] = old_price
                    item['qty'] = qty
                    item['color'] = color['name']
                    item['size'] = size['name']
                    item['description'] = description
                    for i in range(len(product_images)):
                        if i+1 == 10:
                            break
                        item[f'image{i+1}'] = product_images[i].split(' ')[0]
                    yield item

                    '''yield {
                        'scrap_url': scrap_url,
                        'category': category,
                        'group_code': group_code,
                        'code': code,
                        'price': price,
                        'list_price': list_price,
                        'description': description,
                        'images': product_images,
                    }'''
            '''brand = 'Zara'
            group_code = ''
            name = response.css('h1.product-detail-info__header-name::text').get()
            list_price = _price(response.css('div.product-detail-info__price span.price-original__amount::text').get())
            if not list_price:
                list_price = _price(response.css('div.product-detail-info__price span.price-old__amount::text').get())
            price = _price(response.css('div.product-detail-info__price span.price-current__amount span.money-amount__main::text').get())
            colors = response.css('ul.product-detail-color-selector__colors li span::text').extract()
            self.logger.info(f'scrap_url: {scrap_url}')
            self.logger.info(f'colors: {colors}')
            self.logger.info(f'price: {price}')
            self.logger.info(f'list_price: {list_price}')'''

            '''
            item = SuppliercrawlerItem()
            item['scrap_url'] = response.url
            item['category'] = '/'.join(response.css('div.breadcrumb__list li a::text').extract())
            item['product_code'] = response.url.split('-')[-1].split('.')[0].replace('p', '')
            item['brand'] = 'Zara'
            item['price'] = response.css('span.price__amount-wrapper span.price-current__amount span.money-amount__main::text').get()
            item['list_price'] = response.css('span.price__amount-wrapper span.price-old__amount span.money-amount__main::text').get()
            item['name'] = response.css('h1.product-detail-info__header-name::text').get()
            item['color'] = '/'.join(response.css('div.product-detail-color-selector__color-area span.screen-reader-text::text').extract())
            item['short_description'] = ' '.join(response.css('div.product-detail-description *::text').extract())
            item['description'] = ' '.join(response.css('div.product-detail-extra-detail *::text').extract())
            item['size'] = '/'.join(response.css('ul.size-selector__size-list li span.product-size-info__main-label::text').extract())
            images = response.css('ul.product-detail-images__images li picture > source:nth-child(1)::attr(srcset)').extract()
            for i in range(len(images)):
                if i+1 > 11:
                    break
                item[f'image{i+1}'] = images[i].split(' ')[0]
            yield item
            '''
