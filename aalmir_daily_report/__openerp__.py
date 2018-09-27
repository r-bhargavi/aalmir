# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'API SalesPerson Daily Reports',
    'version': '1.0',
    'category': 'CRM Management',
    'sequence': 1007,
    'author': 'Aalmir Plastic Industries',
    'summary': 'Manage prelead information using coldcalling',
    'description': """
    """,
    'website': 'http://www.aalmir.com/',
    'depends': ['base','sale_crm','crm','gt_aalmir_coldcalling'],
    'data': [
	    'security/ir.model.access.csv',
            'wizard/crm_report_view.xml',
           
     ],
    'qweb': [
       
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
