#!/bin/env python
"""Prints the price of our car."""

import collections

#pylint: disable=superfluous-parens


def main():
    """Calculates the price of our car."""
    item_to_price = {
        'Tamiya Grasshopper RC Car': 89.41,
        '7.2V Tenergy 3800mAh NiMH battery': 26.99,
        'Raspberry Pi A+': 21.96,
        '2200 mAh USB battery': 16.99,
        'Raspberry Pi camera': 29.95,
        'Rosewill WiFi adapter': 5.99,
        '8 GiB microSDHC': 8.99,
        'jumper wires standard pack of 30': 4.95,
        'Velcro straps': 7.99,
        'NavSpark SUP800F GPS Antenna Module + 7-DOF IMU': 50.00,
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
