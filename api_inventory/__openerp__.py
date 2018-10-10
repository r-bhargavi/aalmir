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
    'name': 'API Inventory Location Management', 
    'version': '1.0',
    'category': 'inventory',
    'sequence': 1015,
    'summary': 'Stock Location management',
    'description': ''' Manage Inventory location product qty .
                      <li> add product in Row, Shelf and case</li>
                      <li> Do proper Setting Before using this module</li>
                      <li> Make At least 2 Step route for manufcturing,Bye,and Received Prodcuts</li>
                      <li> This all are should be internal transfer routes</li>''',
    'author': 'Aalmir Plastic Industries',
    'website': 'http://aalmrplastic.com',
    'depends': ['stock','product','quality_control','purchase'],
    'data': [
                'security/stock_security.xml',
                'security/stock_menu.xml',
                'security/record_rule.xml',
                'security/ir.model.access.csv',
                'data/series_data.xml',
                "data/stock_data.xml",
                'data/removal_strategy_data.xml',
                'data/barcode_print_paper_format.xml',
                'views/stock_warehouse_view.xml',
                'views/store_bin_location_view.xml',
                'views/product_location.xml',
                'views/stock_location.xml',
                'views/stock_picking_view.xml',
                'views/operation_view.xml',
                'wizard/location_wizard.xml',
                'wizard/import_product_qty_view.xml',
                #'wizard/stock_picking_return_view.xml',
                'views/store_batch_view.xml',
                'views/stock_picking_type_view.xml',
                'views/bin_picking_list_view.xml',
                'wizard/picking_confirmation_view.xml',
                'wizard/transfer_binTbin_confirmation_view.xml',
                'wizard/batch_produce_wizard_view.xml',
                'wizard/unpicking_operation_view.xml',
                #'report/picking_list_report.xml',
                'report/print_batch_number.xml',
                'report/print_batch_details.xml',
                'data/data_mail.xml',
                'data/print_selection.xml',],

    'demo': [],
    'test': [],
    'qweb': ['static/src/xml/*.xml',],
    'installable': True,
    'auto_install': False,
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

