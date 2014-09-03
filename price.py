#!/bin/env python
"""Prints the price of our car."""

import collections

#pylint: disable=superfluous-parens


def main():
    """Calculates the price of our car."""
    item_to_price = {
        'Radio Shack Dune Warrior': 99.99,
        'Raspberry Pi': 39.99,
        'Pi Tin clear': 7.95,
        'Raspberry Pi camera': 29.95,
        'Raspberry Pi camera case': 6.95,
        '6600 mAh USB battery pack': 29.95,
        'Android phone': 39.99,
        'pcDuino USB WiFi dongle': 14.95,
        'adhesive Velcro': 9.88,
        'Velcro straps x 2': 15.98,
        'USB drive': 4.87,
        '32 GiB microSDHC + adapter': 12.99,
        'jumper wires standard pack of 30': 4.95,
    }

    item_to_price = collections.OrderedDict(sorted(item_to_price.items()))

    price_to_item = sorted(
        ((price, item) for item, price in item_to_price.items()),
        reverse=True
    )

    assert(len(item_to_price) == len(price_to_item))

    max_length = max((len(item) for item in item_to_price.keys()))
    format_string = '{{item: <{len_}}}${{price}}'.format(len_=max_length + 3)

    print('    *** By item ***')
    for item, price in item_to_price.items():
        print(format_string.format(item=item, price=price))
    print('')

    print('    *** By price ***')
    for price, item in price_to_item:
        print(format_string.format(item=item, price=price))
    print('')

    print('Total: ${total}'.format(total=sum(item_to_price.values())))


if __name__ == '__main__':
    main()
