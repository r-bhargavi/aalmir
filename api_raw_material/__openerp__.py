# -*- coding: utf-8 -*-
# copyright reserved

{
    "name": "API Raw Material",
    "version": "8.0",
    "category": "Manufacturing",
    'sequence': 1015,
    'author': 'Aalmir Plastic Industries',
    'website': 'http://aalmrplastic.com',
    'description': '''
	   It is use for raw material request and acceptance and validation on raw materialquantity
	''',
    "depends": ['gt_order_mgnt'],
    "data": [
    	"security/ir.model.access.csv",
    	"data/data.xml",
    	"data/route_data.xml",
        "views/data_mail.xml",
        "views/mrp_view.xml",
        'views/stock_view.xml',
        'views/sequence_view.xml',
        #'views/purchase_view.xml',
        'views/product_view.xml',
        'views/raw_material.xml',
        #'wizard/reserve_wizard_view.xml',
        'wizard/raw_material_shift_wizard_view.xml',
        'wizard/history_wizard_view.xml',
        'wizard/extra_raw_material_view.xml',
        'views/sale_reception.xml',
        'wizard/change_currency.xml',
    ],
    "demo": [    ],
    "installable": True,
}
