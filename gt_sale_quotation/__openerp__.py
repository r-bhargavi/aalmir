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
    'name': 'API Sales Quotation Customization', 
    'version': '1.0',
    'category': 'sales',
    'sequence': 1006,
    'summary': 'Sales Quotation customization',
    'description': '''
           Sales Quotation customization
        ''',
    'author': 'Aalmir Plastic Industries',
    'website': 'https://aalmirplastic.com/',
    'depends': ['base','sale', 'sale_stock', 'account', 'sale_crm', 'gt_customer_products'],
    'data': [
        'wizard/lock_wizard.xml',
        'views/quotation_sequence.xml',
        'views/res_company_view.xml',
        'views/sale_view.xml',
        'views/layouts.xml',
        'views/report_quotation_aalmir.xml',
        'sale_report.xml',
        'security/ir.model.access.csv',
	    'views/crm_lead.xml',
	    'views/sale_template_inherite.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
