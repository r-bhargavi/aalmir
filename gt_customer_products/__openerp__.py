 # -*- coding: utf-8 -*-
##############################################################################
#
#
#    Copyright (C) 2013-Today(www.aalmirplastic.com).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'API Cutomer Products Customization',
    'version': '1.0',
    'category': 'sales',
    'sequence': 1005,
    'summary': 'Customer Product Customization',
    'description': '''
  Customer Products Customization
''',
    'author': 'Aalmir Plastic Industries',
    'website': 'http://aalmirplastic.com/',
    'depends': ['mrp', 'gt_sale_pricelist', 'crm'],
    'data': [
        'data/product_type_data.xml',
        'security/ir.model.access.csv',
        'wizard/import_pricelist_view.xml',
        'wizard/import_generic_pricelist_view.xml',
        'views/films_product_number_sequence.xml',
        'views/injection_product_number_sequence.xml',
        'views/partner_view.xml',
        'views/product_view.xml',
        'data/data.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
