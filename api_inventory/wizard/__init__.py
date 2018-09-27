# -*- encoding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory

import location_wizard
import import_product_qty
import stock_return_picking

import picking_confirmation		# Confirm Pick of master Batches from BIN-Location(for dispacth qty)
import backorder_comfirmation_wizard	
import transfer_binTbin_confirmation	# Transfer from BIn 2  Bin master batches
import batch_produce_wizard		# Produce bacthes in production(till Manufacturing LIVE)
import unpicking_operation		# To unpick picked master batches


