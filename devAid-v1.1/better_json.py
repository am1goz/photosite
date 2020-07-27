# encoding: utf-8
# (c) 2012-2014 Alexander Saltanov <asd@mokote.com>

import datetime
import uuid
import json
import decimal


DECIMAL_PLACES = 2
DECIMAL_PRECISION = decimal.Decimal(10) ** -DECIMAL_PLACES


def encode_decimal(val):
    if not val.is_finite():
        raise ValueError('Infinite decimals are not supported in BetterJSONEncoder.')
    decimal_places = 2
    if val < decimal.Decimal('0.001'):
        decimal_places = 4
    elif val < decimal.Decimal('0.01'):
        decimal_places = 3
    val = val.quantize(decimal.Decimal(10) ** -decimal_places)
    if val == val.to_integral_value():
        return int(val)
    else:
        return float(val.normalize())


class BetterJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return obj.hex
        elif isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, (set, frozenset)):
            return list(obj)
        elif isinstance(obj, decimal.Decimal):
            return encode_decimal(obj)

        return super(BetterJSONEncoder, self).default(obj)


def better_json_encode(value, pretty_print=False, ensure_ascii=True,
                       sort_keys=False):
    indent = None
    separators = (',', ':')

    if pretty_print:
        indent = 4
        sort_keys = True
        separators = (', ', ': ')

    return json.dumps(value, separators=separators, cls=BetterJSONEncoder, indent=indent,
                      sort_keys=sort_keys, ensure_ascii=ensure_ascii)
