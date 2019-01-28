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
    'name': 'API Order management', 
    'version': '1.0',
    'category': 'sales',
    'sequence': 1008,
    'summary': 'Manage all sales related activity in ERP, trace manufacturing order and delivery order of sale.',
    'description': '''
   Order management Customization
''',
    'author': 'Aalmir Plastic Industries',
    'website': 'http://aalmrplastic.com',
    'depends': ['base','account','sale','hr_payroll','hr_payroll_account',
                'gt_sale_quotation','mrp_operations',
                'purchase_requisition','product','hr','stock'],
    'data': [
        'data/product_uom_data.xml',
        'data/product_attribute_data.xml',
        'static/src/xml/template.xml',
        'security/user_security.xml',
        'security/ir.model.access.csv',
        'security/record_rule.xml',
        'wizard/order_split_machine_change_view.xml',
        'wizard/reject_bill_reason.xml',
        'wizard/print_batches_data.xml',
        'wizard/order_confirm_wizard_view.xml',
        'wizard/request_payment_term_wizard_view.xml',
        'wizard/order_confirm_by_sales_support_wizard_view.xml',
        'views/data_mail.xml',
        'views/sale_support_view.xml', 
        'views/sale_view.xml',
        'views/partner_view.xml',
        'views/account_payment_term.xml',
        'views/payment_request_dashboard.xml',
        'views/crm_team_dashboard_view.xml',
        'views/product_view.xml',
        'views/account_invoice.xml',
        'views/stock_picking_view.xml',
        'views/aalmir_invoice_report.xml',
        'report_menu.xml',
        'views/aalmir_delivery_report.xml',
        'views/purchase_view.xml',
        'views/mrp_request.xml',
        'views/purchase_rfq_report.xml',
        'views/purchase_order_report.xml',
        'views/sale_support_history_date_view.xml',
        'views/contract_view.xml',
        'data/sale_menu_data.xml',
        'views/sale_reception.xml',
        'views/assets.xml',
        'views/users_view.xml',
        'views/manufacuring_report.xml',
        'views/requisition_report.xml',
        'views/crm_lead.xml',
        'views/squence_view.xml',
        'views/mrp_workcenter.xml',
        'views/mrp_workorder_report.xml',
        'views/print_batch_number.xml',
        'views/app_search_view.xml',
        'views/workorder_form.xml',
        'views/aalmir_vendor_invoice.xml',
        'wizard/purchase_request_view.xml',
        'wizard/sale_support_reserve_view_wizard.xml',
        'wizard/mail_compose_view.xml',
        'wizard/sale_order_lpo_view.xml',
        'views/payment_receipt_report.xml',
        'views/account_payment_receipt_report.xml',
        'report/print_batch_details.xml',
#        'report/print_batch_number.xml',

        
    ],
    'demo': [],
    'test': [],
    'qweb': ['static/src/xml/*.xml', 'static/src/xml/digital_sign.xml'],
    'installable': True,
    'auto_install': False,
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
