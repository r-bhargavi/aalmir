# -*- encoding: utf-8 -*-

{
    'name' : 'API Stock Merge Picking',
    'version' : '9.0',
    'author': 'Aalmir Plastic Industries',
    'website' : 'www.aalmirplastic.com',
    'depends' : ['api_raw_material'],
    'category' : 'Warehouse',
    'sequence': 1009,
    'description': """
This module allows used for .......
     1. Merge stock picking (for all sale order or sinlge order).
     2. Merge invoice in draft state (for all sale order or sinlge order).
     3. Sale summary report of all delivery orders and invoices.
     4. Send mail button shown in proforma invoice.
     5. Cancel sale order . 
     6. Cancel delivery order in draft or available state if delivery order state is done then send mail to inventory user 
     and also update origin field with cancelled information.
     7. Cancel invoice in draft state or proforma state if invoice state is done or open then send mail to Account user and also 
     update origin fields with cancelled information.
    """,
    'init_xml' : [],
    'demo_xml' : [],
    'data' : [
              'security/ir.model.access.csv',
		'security/api_security.xml',
              'data/report_paperformat.xml',
              'view/stock_view.xml',
              'wizard/merge_picking_view.xml', 
               'wizard/invoice_merge_view.xml',
               'view/report_menu.xml',
               'view/summary_report.xml',
		'view/stock_data.xml',
	      'view/mrp_view.xml',
	      'view/API_menu_setting.xml',
	      'view/sale_instruction_view.xml',
              'view/account_payment_print.xml',
              'view/receipt_print_template.xml',
	      'view/res_partner_view.xml',
              'view/sale_view.xml',
           
              'view/approve_sequence.xml',
              'view/approve_report.xml',
              'wizard/product_report_view.xml',
              'view/product_report_sale.xml',
              'view/invoice_wise_report.xml',
              
	      ],
    'active': False,
    'installable': True
}

