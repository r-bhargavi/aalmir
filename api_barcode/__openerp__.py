# -*- coding: utf-8 -*-
# copyright reserved

{
    "name": "API Barcode",
    "version": "8.0",
    "category": "Application",
    'sequence': 1016,
    'author': 'Aalmir Plastic Industries',
    'website': 'http://aalmrplastic.com',
    'description': '''
	   It is use for Generate Barcode in sale, invoice , stock, manufaturing and Batch.
	''',
    "depends": ['base', 'sale','account','product','stock','api_inventory'],
    "data": ['data/ean_sequence.xml',
             'views/barcode_view.xml',
             'views/stock_barcode_view.xml',
       
    ],
    "demo": [    ],
    "installable": True,
}
