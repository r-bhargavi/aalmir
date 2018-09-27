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
    'name': 'API Sale Pricelist',
    'version': '1.0',
    'category': 'sale',
    'sequence': 1002,
    'summary': 'Calculate sale pricelist',
    'description': '''    Customize sale module and film calculator and changes in pricelist ''',
    'author': 'Aalmir Plastic Industries',
    'website': 'https://aalmirplastic.com/',
    'depends': ['sale_stock', 'account', 'gt_next_activity_reminder','sale'],
    'data': [
        'security/user_security.xml',
        'security/ir.model.access.csv',
        'view/pricelist_base.xml',
        'view/pricelist_cal.xml',
        'view/pricelist_view.xml',
        'view/sale_pricelist.xml',
        'view/form_view_extention.xml',
        'view/data_mail.xml',
		'view/product_view.xml',
    ],
    'qweb': [
        #'view/sales_team_dashboard.xml',
    ],
    'demo': [
        # 'view/demo_data.xml'
    ],
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
