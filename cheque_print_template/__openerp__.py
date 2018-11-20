# -*- coding: utf-8 -*-
{
    'name': "Customizable Report Template",
    'version': '1.1',
    'summary': """Customize Your Reports Layout""",
    'description': """Customize Your Reports Layout""",
    'author': "Odoo",
    'maintainer': 'Odoo',
    'company': "Odoo",
    'website': "https://www.odoo.com",
    'depends': ['base', 'account', 'account_check_printing','api_account'],
    'images': [],
    'data': [
        'views/layout.xml',
        'views/report.xml',
        'views/cheque_template.xml',
        "views/account_payment.xml",
        "views/account_journal_view.xml"
    ],
    'license': 'AGPL-3',
    'appliction': False,
    'installable': True
}