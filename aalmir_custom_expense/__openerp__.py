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
    'name': 'Aalmir Expense Custom',
    'version': '1.0',
    'category': 'product',
    'sequence': 1005,
    'summary': 'Expense Aalmir Custom',
    'description': '''
  Expense Customization
''',
    'author': 'Aalmir Plastic Industries',
    'website': 'http://aalmirplastic.com/',
    'depends': ['hr_expense','api_account'],
    'data': [
        'security/expenses_grant_security.xml',
        'security/ir.model.access.csv',

        'views/approval_config_view.xml',
        'views/hr_expense_view.xml',
        'views/product_view.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
