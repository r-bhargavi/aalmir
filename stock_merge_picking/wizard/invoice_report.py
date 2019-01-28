# -*- coding: utf-8 -*-
from openerp.report import report_sxw
from openerp import api, models
from datetime import datetime, timedelta
import logging
_logger = logging.getLogger(__name__)

class product_report_parser(report_sxw.rml_parse):
    
    def __init__(self, cr, uid, name, context):
        super(product_report_parser, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_view': self._get_view,
            'get_total': self._get_total,
            'get_total_due': self._get_total_due,
            'get_sale':self._get_sale,
        })
        
    def _get_sale(self, object):
        sale_qry=False
        lines=[]
        if object.filter_by =='running_sale' and not object.partner_id:
            sale_qry="select id from sale_order where state='sale'"
            self.cr.execute(sale_qry)
        else: 
            if object.partner_id:
               all_partners_and_children = {}
               all_partner_ids = []
               for partner in object.partner_id:
                   all_partners_and_children[partner] =self.pool.get('res.partner').search(self.cr, self.uid,[('id', 'child_of', object.partner_id.id)])
                   all_partner_ids += all_partners_and_children[partner]
               sale_qry="select id from sale_order where  partner_id in {}".format (tuple(all_partner_ids))
               self.cr.execute(sale_qry)
        sale_ids=[i[0] for i in self.cr.fetchall()]
        pick_name=invoice_name=''
        if sale_ids:
           for line in self.pool.get('sale.order').browse(self.cr,self.uid,sale_ids):
               if line.picking_ids:
                  for picking in line.picking_ids:
                      pick_name +=str(picking.name)+','
               
               if line.invoice_ids:
                  for inv in line.invoice_ids:
                      invoice_name +=str(inv.number)+','
               vals = {
                  'date':line.date_order,
                  'name':line.name,
                  'customer':line.partner_id.name,
                  'lpo': line.sale_lpo_number,
                  'salesperson':line.user_id.name,
                  'opportunity':line.opportunity_id.name,
                  'amount_total':line.amount_total,
                  'currency':line.report_currency_id.name,
                  'state':line.state,
                  'convert_amount':line.converted_amount_total,
                  'invoice_val':line.invoice_val,
                  'delivery_ids':pick_name,
                  'invoice_no':invoice_name
                  
            }
               lines.append(vals)
               pick_name=invoice_name=''
           return lines

    def _get_view(self, object):
        lines=[]
        invoice_qry = '''SELECT id from account_invoice where type in ('out_invoice','out_refund') '''
        args_list=[]
        
        if object.partner_id:
           all_partners_and_children = {}
           all_partner_ids = []
           for partner in object.partner_id:
               all_partners_and_children[partner] =self.pool.get('res.partner').search(self.cr, self.uid,[('id', 'child_of', object.partner_id.id)])
               all_partner_ids += all_partners_and_children[partner]

        if object.date_from and object.date_to:
           dt = datetime.strptime(object.date_from,'%Y-%m-%d %H:%M:%S')
           n1=dt.date()
           dt1 = datetime.strptime(object.date_to,'%Y-%m-%d %H:%M:%S')
           n2=dt1.date()
        
        if object.filter_by =='submission' and object.lpo_id_inv:
           partner=tuple(all_partner_ids)
           status=object.invoice_status
           
           lpo_id=[]
           for lpo in object.lpo_id_inv:
               lpo_id.append(lpo.id)
           
           if lpo_id:
           	lpo_qry = '= {}'.format(lpo_id[0]) if len(lpo_id)==1 else ' in {}'.format(tuple(lpo_id))
           	invoice_qry += 'and id in (select cust_doc_rel from customer_invoice_rel where customer_upload_doc_id {})'.format(lpo_qry)
           if object.date_from and object.date_to:
              args_list =(partner, status, n1,n2)
              invoice_qry +=" and partner_id in %s and state='%s' AND date_invoice >= '%s' AND date_invoice <= '%s' order by date_invoice"% args_list 
           else:
              if object.invoice_status !='all':
                 args_list =(partner, status)
                 invoice_qry +=" and partner_id in %s and state= '%s' order by date_invoice"%args_list
              else:
                 invoice_qry +=" and partner_id  in {} and state !='cancel' order by date_invoice ".format(partner)
                 
        if object.filter_by in ('customer','submission') and not object.lpo_id_inv:
           if object.date_from and object.date_to:
              partner=tuple(all_partner_ids)
              if object.invoice_status !='all' and object.filter_by =='submission':
                 status=object.invoice_status
                 args_list =(partner,status,n1, n2)
                 invoice_qry +=" and state !='cancel' and partner_id in %s AND state='%s' AND date_invoice >= '%s' AND date_invoice <= '%s' order by date_invoice"%args_list
              else:
                 args_list =(partner,n1, n2)
                 invoice_qry +=" and state !='cancel' AND partner_id in %s AND date_invoice >= '%s' AND date_invoice <= '%s' order by date_invoice"%args_list

           else:
               if object.invoice_status !='all' and object.filter_by =='submission':
                  partner=tuple(all_partner_ids)
                  status=object.invoice_status
                  args_list =(partner,status)
                  invoice_qry +=" and partner_id in %s AND state='%s' order by date_invoice"%args_list  
               else:
                   invoice_qry +="and state !='cancel' and partner_id in {} order by date_invoice".format (tuple(all_partner_ids))
                   
        if object.filter_by =='all':
           if object.date_from and object.date_to:
              args_list =(n1, n2)
              invoice_qry +="state !='cancel' AND date_invoice >= '%s' AND date_invoice <= '%s' order by date_invoice"%args_list     
           else:
              invoice_qry +="select id from account_invoice where  state !='cancel' order by date_invoice"
        print "invoice quryy---------------------",invoice_qry
	_logger.info('Invoice-Report Query {}'.format(invoice_qry))
        self.cr.execute(invoice_qry)      
        invoice_ids=[i[0] for i in self.cr.fetchall()]
        if invoice_ids:
           amount_total=sum(line.amount_total for line in self.pool.get('account.invoice').browse(self.cr,self.uid,invoice_ids))
           lpo_number=''
           for inv in self.pool.get('account.invoice').browse(self.cr,self.uid,invoice_ids):
           	if inv.document_id:
                  	lpo_number = ','.join([ str(doc.lpo_number) for doc in inv.document_id ])
          	else:
          		lpo_number = inv.sale_id.sale_lpo_number
                  	
                vals = {
                  'date':inv.date_invoice,
                  'number':inv.number,
                  'customer':inv.partner_id.name,
                  'sale':inv.origin,
                  'lpo': lpo_number,
                  'salesperson':inv.user_id.name,
                  'due_date':inv.date_due,			#inv.date_due,
                  'total':inv.amount_total_signed,
                  'due':inv.residual_signed,			#inv.payment_date_inv,
                  'currency':inv.currency_id.name,
                  'state':inv.state,
                  'amount_total':amount_total
            }
                lines.append(vals)
                lpo_number=''
        return lines

    def _get_total(self, object):
        lines=self._get_view(object)
        total=0.0
        if lines:
           total=sum(line['total'] for line in lines)
        return total or 0.0

    def _get_total_due(self, object):
        lines=self._get_view(object)
        total=0.0
        if lines:
           total=sum(line['due'] for line in lines)
        return total or 0.0
    
class report_product_parser(models.AbstractModel):
    _name = 'report.stock_merge_picking.report_invoice_wise'
    _inherit = 'report.abstract_report'
    _template = 'stock_merge_picking.report_invoice_wise'
    _wrapped_report_class = product_report_parser

