# -*- coding: utf-8 -*-


{
    'name': 'Sale Sourced by Line',
    'summary': 'Multiple warehouse source locations for Sale order',
    'version': '9.0.1.0.0',
    'author': 'Aalmir Plastic Industries',
             
    'category': 'Warehouse',
    'sequence': 2001,
    'license': 'AGPL-3',
    'website': "http://www.aalmirplastic.com",
    'depends': ['sale_stock',
                'sale_procurement_group_by_line',
                ],
    'data': [
        'view/sale_view.xml'
    ],
    'auto_install': False,
    'installable': True,
}
