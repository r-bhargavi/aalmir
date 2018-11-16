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
#    along with this program.
#
##############################################################################
{
    'name': 'API Accounting & Finance Management', 
    'version': '1.0',
    'category': 'accounting',
    'sequence': 1020,
    'summary': 'Manage payment and cheque reconcilation management',
    'description': ''' Customize Payments
                       <li>Bank Reconcilation </li>''',
    'author': 'Aalmir Plastic Industries',
    'website': 'http://aalmrplastic.com',
    'depends': ['account','product','gt_order_mgnt'],
    'data': [
                'security/ir.model.access.csv',
                'views/account_invoice_view.xml',
                'views/bank_view.xml',
                'views/account_payment.xml',
                'views/bank_reconcilation_view.xml',
#                'views/fund_transfer_wizard_view.xml',
                'views/ledgerwise_report.xml',
                'views/journal_voucher_view.xml',
                'views/squence_view.xml',
                'wizard/report_ledgerwise_detailed.xml',
                'wizard/report_ledgerwise_summary.xml',
                'wizard/account_register_payment_view.xml',
                ],
    'demo': [],
    'test': [],
    'qweb': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

