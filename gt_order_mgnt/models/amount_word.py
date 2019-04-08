from openerp import netsvc
from openerp.osv import fields, osv
from openerp.tools.amount_to_text_en import amount_to_text
import re

def _amount_total_text(self, cursor, user, ids, name, arg, context=None):
    res = {}
    for order in self.browse(cursor, user, ids, context=context):
        a = ''
        b = ''
        if order.currency_id.name == 'AED':
            a = 'Dirham'
            b = 'Fils'
        if order.currency_id.name == 'OMR':
            a = 'Rial'
            b = 'Baisa'
        if order.currency_id.name == 'USD':
            a = 'Dollar'
            b = 'cent'
        res[order.id] =re.sub('[\,]', '', amount_to_text(order.amount_total, 'en', a).replace('Cents', b).replace('Cent', b))


    return res
    
def _amount_total_text_inv(self, cursor, user, ids, name, arg, context=None):
    res = {}
    for order in self.browse(cursor, user, ids, context=context):
        a = ''
        b = ''
        if order.company_id.currency_id.name == 'AED':
            a = 'Dirham'
            b = 'Fils'
        if order.currency_id.name == 'OMR':
            a = 'Rial'
            b = 'Baisa'
        if order.currency_id.name == 'USD':
            a = 'Dollar'
            b = 'cent'
        amount= order.residual if order.residual else order.amount_total
        res[order.id] = re.sub('[\$,]', '', amount_to_text(amount , 'en', a).replace('Cents', b).replace('Cent', b))
             
    return res
    
class sale_order(osv.osv):
    _inherit = "sale.order"
    _columns = {
        'amount_total_text': fields.function(_amount_total_text, string='Amount Total (Text)', type='char'),
    }
sale_order()



class Purchase_order(osv.osv):
    _inherit = "purchase.order"
    _columns = {
        'amount_total_text': fields.function(_amount_total_text, string='Amount Total (Text)', type='char'),
    }
Purchase_order()


class Account_Invoice(osv.osv):
    _inherit = "account.invoice"
    _columns = {
        'amount_total_text': fields.function(_amount_total_text_inv, string='Amount Total (Text)', type='char'),
    }
Account_Invoice()
