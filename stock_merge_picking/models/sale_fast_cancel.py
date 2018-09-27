
from openerp import models, api,_
from openerp.exceptions import UserError
from openerp import tools
from datetime import datetime, date, timedelta
from openerp.tools.translate import _

class sale(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_draft(self):
	for rec in self:
		custom_id=self.env['n.custom.product'].search([('n_sale_order_id','=',self.id),
								('n_add_rec','=',True)])
		if custom_id:
			custom_id.n_add_rec=False
		for line in rec.order_line:
			line.lock = False  
		return super(sale, self).action_draft()

    @api.one
    def action_cancel(self):
        mail_mail = self.env['mail.mail']
        mail_ids = []
        email_from=self.user_id.login
        footer = _("Kind regards.\n") 
        footer +=self.company_id.name
        subject=self.name 
        mail_body=self.name +"  This sale order is cancelled "
	body1=''
	flag=False
        if self.state == 'awaiting':
           if self.payment_id:
              if self.payment_id.state =='posted':
                 raise UserError ('Once Payment Done can not cancel Sale order.Please Contact to Admin.')
              else:
                 self.payment_id.unlink()
           else:
              self.write({'state': 'cancel'})


	#add code to reverse quantity in avilable qty
        for order in self.order_line:
		rec_id=self.env['n.manufacturing.request'].search([('n_sale_order_line','=',order.id),('n_state','not in',('draft','done','cancel'))])
                if rec_id:
			for rec in rec_id:
				if rec.n_mo_number:
					raise UserError(("Please First cancel the Manufacture order no:- "+str(search_id.n_mo_number.name)))
				if rec.n_po_number:
					raise UserError(("Please First cancel the Purchase order no:- "+str(search_id.n_po_number.name))) 

		vals={'product_id':order.product_id.id,'res_qty':order.product_uom_qty,
                     'n_status':'cancel','res_date':date.today(),'sale_line':order.id}
		self.env['reserve.history'].create(vals)
		search_id=self.env['n.manufacturing.request'].search([('n_sale_order_line','=',order.id),('n_state','=','draft')])
                if search_id:
			search_id.n_state='cancel'
		status_id=self.env['sale.order.line.status'].search([('n_string','=','cancel')],limit=1) ## add status
		if status_id:
			order.write({'n_status_rel':[(6,0,[status_id.id])],'reserved_qty':0.0,'n_extra_qty':0.0})

        for record in self.picking_ids:
            state=value = dict(self.env['stock.picking'].fields_get(allfields=['state'])['state']['selection'])[record.state]
            body1 +='<li>Delivery Order {} {} >> Cancelled </li>'.format(record.name,state)
            if  record.state in ('draft','confirmed', 'assigned'):
		record.message_post('Sale Order is Cancelled')
		record.action_cancel()
            elif  record.state in ('transit','done', 'delivered'):
                '''mail_val=mail_mail.create({'email_to':record.owner_id.email,
                                      'email_from':email_from,
                                       'subject': subject,
                                       'auto_delete':False,
                                       'body_html': '<pre><span class="inner-pre" style="font-size: 15px">%s<br>%s<br></pre>' %( mail_body,footer)
                                       }) 
                mail_ids.append(mail_val)
                mail_mail.send(mail_ids)'''
		if record.state in ('transit','done'):
			record.action_cancel()
		elif record.state =='delivered':
			raise UserError('There is Delivery Order {} is delivered'.format(record.name))

	    record.message_post('Sale Order is Cancelled')
            record.write({'origin':self.name  +" This sale order cancelled"})

        for invoice in self.invoice_ids:
            state=value = dict(self.env['account.invoice'].fields_get(allfields=['state'])['state']['selection'])[invoice.state]
            if invoice.state in ('draft', 'proforma', 'proforma2'):
            	if invoice.number:
               		body1 +='<li>Draft Invoice Cancelled </li>'
		else:
			body1 +='<li>Invoice {} state Changed {} >> Cancelled </li>'.format(str(invoice.number),state)

		invoice.action_cancel()
	    elif invoice.state =='open':
		if invoice.amount_total !=invoice.residual_new1:
			mail_body += 'Please Refund Invoice {}'.format(invoice.number)
			mail_val=mail_mail.create({'email_to': invoice.user_id.login,
                                      'email_from':email_from,
                                       'subject': subject,
                                       'auto_delete':False,
                                       'body_html': '<pre><span class="inner-pre" style="font-size: 15px">%s<br>%s<br></pre>' %( mail_body,footer)
                                       })
			mail_ids.append(mail_val)
		       	mail_mail.send(mail_ids)
        	       	body1 +='<li>Invoice {} is partially paid has to be refund</li>'.format(str(invoice.number))
	               	invoice.write({'origin':self.name  +" This sale order cancelled"})
		else:
		        body1 +='<li>Invoice {} state Changed {} >> Cancelled </li>'.format(str(invoice.number),state)
		        invoice.action_cancel()

            elif invoice.state in ('paid'):
	       mail_body += 'Please Refund Invoice {} \n'.format(invoice.number)
               mail_val=mail_mail.create({'email_to': invoice.user_id.login,
                              'email_from':email_from,
                              'subject': subject,
                              'auto_delete':False,
                      	'body_html': '<pre><span class="inner-pre" style="font-size: 15px">%s<br>%s<br></pre>' %( mail_body,footer)
                                       }) 

               mail_ids.append(mail_val)
               mail_mail.send(mail_ids)
	       body1 +='<li>Invoice {} is Fully paid has to be refund </li>'.format(str(invoice.number))
               invoice.write({'origin':self.name  +" This sale order cancelled"})
	    invoice.message_post('Sale Order is Cancelled Please Cancel This Invoice')
	self.message_post(body1)
        return super(sale, self).action_cancel()
            
      
