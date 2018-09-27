# -*- coding: utf-8 -*-

from openerp.osv import fields, orm
from openerp.tools.translate import _
import re

def isodd(x):
    return bool(x % 2)
    
def _get_ean_next_code(self, cr, uid, sale, context=None):
        if context is None:
            context = {}
        sequence_obj = self.pool.get('ir.sequence')
        ean = ''
        if sale.ean_sequence_id:
            ean = sequence_obj.next_by_id(cr, uid, sale.ean_sequence_id.id, context=context)
        
        else:
            ean = sequence_obj.next_by_code(cr, uid, 'sale.ean13.code', context=context)
        if len(ean) > 12:
            raise orm.except_orm(_("Configuration Error!"),
                                 _("There next sequence is upper than 12 characters. This can't work."
                                   "You will have to redefine the sequence or create a new one"))
        else:
            ean = (len(ean[0:6]) == 6 and ean[0:6] or ean[0:6].ljust(6, '0')) + ean[6:].rjust(6, '0')
        return ean
        
def _get_ean_key(self, code):
        print"CCCCCCCCCCCc",code
        sum = 0 
        for i in range(12):
            if isodd(i):
                sum += 3 * int(code[i])
            else:
                sum += int(code[i])
        key = (10 - sum % 10) % 10
        print"+KKKKKKKKKKKKKKKK", key
        return str(key)

def _generate_ean13_value(self, cr, uid, sale, context=None):
        ean13 = False
        if context is None:
            context = {}
        ean =_get_ean_next_code(self,cr, uid, sale, context=context)
        print"(((((((((((",ean
        ean1=ean[0:9]
        print"**********888888888",ean1, sale.name[2:]
        name=0 
        if len(sale.name)>5:
           val=re.sub("\D", "", sale.name)
           print"---------------",sale.name, val
           
           name=val#sale.name[10:] if sale.name else ean
        else:
           name=sale.name[2:] if sale.name else ean
        print"9999999999",name
        ean = ean1 + name if sale.name else ean
        print"fffffffffffffff",ean
        if not ean:
            return None
        key =_get_ean_key(self,ean)
        print"hhhhhhhhhhhhhhhhhhhhh",key, ean
        555
        ean13 =sale.name + key
        return ean13
        
def generate_ean13(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        generate_context = context.copy()
        sequence_id=0
        product_ids = self.browse(cr, uid, ids, context=context)
        seq_ean13_internal = product_ids.env.ref('api_barcode.seq_ean13_sequence_sale')
        for product in product_ids:
            if product.barcode:
                continue
            else:
               sequence_id = seq_ean13_internal.id
            generate_context.update({'sequence_id': sequence_id})
            print"---------------",sequence_id
            ean13 =_generate_ean13_value(self,cr, uid, product, context=generate_context)
            print"EEEEEEEEEEEEEEEEE",sequence_id, ean13
            if not ean13:
                continue
            self.write(cr, uid, [product.id], {
                'ean_sequence_id': sequence_id,
                'barcode': ean13,
            }, context=context)
        return True
        
class sale_order(orm.Model):
    _inherit = 'sale.order'

    def create(self, cr, uid, vals, context=None):
        if context is None: context = {}
        id = super(sale_order, self).create(cr, uid, vals, context=context)
        if not vals.get('barcode'):
            ean13 =generate_ean13(self,cr, uid, [id], context=context)
        return id

class Stockpicking(orm.Model):
    _inherit = 'stock.picking'

    def create(self, cr, uid, vals, context=None):
        if context is None: context = {}
        id = super(Stockpicking, self).create(cr, uid, vals, context=context)
        #if not vals.get('barcode'):
            #ean13 =generate_ean13(self,cr, uid, [id], context=context)
        return id
        
class MrpOrderBatchNumber(orm.Model):
   _inherit='mrp.order.batch.number'

   def create(self, cr, uid, vals, context=None):
        if context is None: context = {}
        id = super(MrpOrderBatchNumber, self).create(cr, uid, vals, context=context)
        if not vals.get('barcode'):
            ean13 =generate_ean13(self,cr, uid, [id], context=context)
        return id
        
class account_invoice(orm.Model):
    _inherit = 'account.invoice'
   
    '''def write(self, cr, uid, vals, context=None):
        print"ERRRRRrrrrrrrr"
        if context is None: context = {}
        id = super(account_invoice, self).write(cr, uid, vals, context=context)
        if not vals.get('barcode') and vals.get('name'):
            self.write(cr, uid, [id], {
                'barcode': generate_ean13(self,cr, uid, [id], context=context),
            }, context=context)
        return id'''

class MrpProduction(orm.Model):
   _inherit='mrp.production'

   def create(self, cr, uid, vals, context=None):
        if context is None: context = {}
        id = super(MrpProduction, self).create(cr, uid, vals, context=context)
        if not vals.get('barcode'):
            ean13 =generate_ean13(self,cr, uid, [id], context=context)
        return id
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

