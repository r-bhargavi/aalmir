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
    'name': 'API Dashboard', 
    'version': '1.0',
    'category': 'sales',
    'sequence': 1010,
    'summary': 'API Dashboard customization',
    'description': '''
   Sales Quotation customization
''',
    'author': 'Aalmir Plastic Industries',
    'website': 'https://aalmirplastic.com/',

    'depends': ['sale', 'api_raw_material', 'purchase', 'purchase_requisition', 'stock','api_inventory'],
    'data': [
        'security/ir.model.access.csv',
	    'views/sale_support_dashboard.xml',
        'views/data.xml',
        'views/mrp_dashboard.xml',
        'views/purchase_dash.xml',
        'views/account_dashboard.xml',
        'views/account_data.xml',
        'views/stock_dash.xml',
    ],
    'demo': [],
    'test': [],
    'qweb' : [ "static/src/xml/*.xml"],  #CH_N105 add file to remove saveas button form binary file upload field
    'installable': True,
    'auto_install': False,
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
