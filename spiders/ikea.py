import xmltodict
from scrapy import Spider, Request
from suppliercrawler.items import SuppliercrawlerItem

class ZaraSpider(Spider):
    name = 'ikea'
    allowed_domains = ['ikea.com.tr']
    start_urls = ['https://cdn.ikea.com.tr/sitemap/sitemap.xml']

    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36',
        'ROBOTSTXT_OBEY': False,
    }

    api_url = 'https://frontendapi.ikea.com.tr/api/search/products?language=tr&Category={cat_code}&IncludeFilters=false&StoreCode=331&sortby=None&IsSellable=&page={page}&size={size}'

    def parse(self, response):
        text = response.body.decode('utf-8')
        sitemap_dict = xmltodict.parse(text)
        if sitemap_dict.get('sitemapindex'):
            for data in sitemap_dict['sitemapindex']['sitemap']:
                if data['loc'].endswith('.xml'):
                    yield Request(
                        url=data['loc'], 
                        callback=self.parse
                    )
                elif data['loc'].endswith('.axd'):
                    continue
        else:
            listing_urls = sitemap_dict['urlset']['url']
            for  url in listing_urls[:]:
                if 'kategori' in url['loc']:
                    yield Request(
                        url=url['loc'], 
                        callback=self.parse_listing
                    )
    
    def parse_listing(self, response):
        self.logger.info(response.url)
        size = 40
        cat_code = response.xpath('//input[@id="ctl00_ContentPlaceHolder1_search_categoryUrl"]/@value').get()
        url_api = self.api_url.format(
            cat_code=cat_code,
            page=1,
            size=size,
        )
        yield Request(
            url=url_api,
            callback=self.parse_api,
            meta={
                'cat_code': cat_code,
                'page': 1,
            }
        )
    
    def parse_api(self, response):
        page = response.meta['page']
        cat_code = response.meta['cat_code']
        data = response.json()
        total = data['total']
        self.logger.info(f'page: {page} - total: {total}')
        products = data['products']
        for product in products[:]:
            scrap_url = 'https://www.ikea.com.tr' + product['url']
            scrap_url = scrap_url.replace('/urun/','/en/product/')
            price = product['price']
            try:
                old_price=product['crossPrice']
            except:
                old_price=price
            yield Request(
                url=scrap_url,
                callback=self.parse_product,
                meta={
                    'price':price,
                    'old_price':old_price
                }
            )
        
        if products:
            page += 1
            url_api = self.api_url.format(
                cat_code=cat_code,
                page=page,
                size=40,
            )
            yield Request(
                url=url_api,
                callback=self.parse_api,
                meta={
                    'cat_code': cat_code,
                    'page': page,
                }
            )
        
        if products:
            page += 1
            url_api = self.api_url.format(
                cat_code=cat_code,
                page=page,
                size=40,
            )
            yield Request(
                url=url_api,
                callback=self.parse_api,
                meta={
                    'cat_code': cat_code,
                    'page': page,
                }
            )
    
    def parse_product(self, response):
        print(response.meta)
        item = SuppliercrawlerItem()
        item['scrap_url'] = response.url
        item['brand'] = 'IKEA'

        item['product_code'] = response.css('.product-code::text').get().strip()
        #item['group_code'] = ''
        categories = response.xpath('//a[contains(@class,"breadcrumb-item")]/span[@class="name"]/text()').extract()
        item['name'] = categories[-1].strip()
        item['category'] = '/'.join([x.strip() for x in categories[2:-1]])
        item['description'] = ' '.join([x.strip() for x in response.css("div.product-description *::text").extract()]).strip()
        images = response.css('span.pub-aspect-ratio-image img::attr(src)').extract()
        for i in range(len(images)):
            if i+1 == 10:
                break
            item[f'image{i+1}'] = images[i].split(' ')[0]

        old_price = response.meta.get('old_price')
        price = response.meta.get('price')

        # old_price = ''.join(response.xpath('//span[contains(@class,"cross-price")]//text()').extract())
        # if old_price:
        #     old_price = _price(old_price.strip().replace('.','').replace(',','.'))
        # else:
        #     old_price = ""

        categories = response.xpath('//a[contains(@class,"breadcrumb-item")]/span[@class="name"]/text()').extract()[:-1]
        item['category'] = '/'.join([x.strip() for x in categories[2:]])

        description = ""
        description_element_1 = response.xpath('//div[@id="measurements-modal"]/div[@class="global-modal-body"]//text()').extract()
        for element in description_element_1:
            # clean text
            element = element.strip().replace('\n',' ').replace('\r',' ').replace('\t',' ')
            if element:
                description += element + " "
        description_element_2 = response.xpath('//div[@id="product-information-modal"]/div[@class="global-modal-body"]//text()').extract()
        for element in description_element_2:
            # clean text
            element = element.strip().replace('\n',' ').replace('\r',' ').replace('\t',' ')
            if element:
                description += element + " "
        item['description'] = description.strip().split('Assembly & Documents')[0]

        # price = ''.join(response.xpath('//span[contains(@class,"product-price")]/span/span//text()').extract())
        # if price:
        #     price = _price(price.strip().replace('.','').replace(',','.'))
        # else:
        #     price = ""
        # if not old_price:
        #     old_price = price
        item['list_price'] = old_price
        item['price'] = price

        item['qty'] = 2

        critical = response.xpath("//span[contains(@class,'icon-critical-stock')]")
        if critical:
            item['qty'] = 1

        not_stock = response.xpath("//span[contains(@class,'icon icon-Nostock')]")
        if not_stock:
            item['qty'] = 0
        
        yield item
            
            
            
            