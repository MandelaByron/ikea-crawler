from price_parser import Price


def _price(raw_price):
    if isinstance(raw_price, str):
        price_obj = Price.fromstring(raw_price)
        return price_obj.amount_float
    # not valid
    return None