
import math
from openerp import fields, models ,api, _
from openerp.tools import amount_to_text_en, float_round
from openerp.exceptions import UserError
import openerp.addons.decimal_precision as dp
INV_TO_PARTN = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
}
# Since invoice amounts are unsigned, this is how we know if money comes in or
# goes out
INV_TO_PAYM_SIGN = {
    'out_invoice': 1,
    'in_refund': 1,
    'in_invoice': -1,
    'out_refund': -1,
}


class InvoiceCustomerPaymentLine(models.Model):
    _name = "invoice.customer.payment.line"
    _rec_name = 'invoice_id'

    invoice_id = fields.Many2one('account.invoice', string="Customer Invoice",
                                 required=True)
    partner_id = fields.Many2one('res.partner', string="Customer Name",
                                 required=True)
    balance_amt = fields.Float("Due Amount", required=True,digits=dp.get_precision('Stock Weight'))
    wizard_id = fields.Many2one('account.register.payments', string="Wizard")
    receiving_amt = fields.Float("Receive Amount", required=True, digits=dp.get_precision('Stock Weight'))
    check_amount_in_words = fields.Char(string="Amount in Words")
    payment_method_id = fields.Many2one('account.payment.method',
                                        string='Payment Type')
    payment_difference = fields.Float(string='Difference Amount',
                                      readonly=True)
    handling = fields.Selection([('open', 'Keep open'),
                                 ('reconcile', 'Mark invoice as fully paid')],
                                default='open',
                                string="Action",
                                copy=False)
    writeoff_account_id = fields.Many2one('account.account', string="Account",
                                          domain=[('deprecated', '=', False)],
                                          copy=False)

    @api.onchange('receiving_amt')
    def _onchange_amount(self):
        self.check_amount_in_words = AmountToTextFractional(self.receiving_amt)
        self.payment_difference = self.balance_amt - self.receiving_amt
        if self.receiving_amt > self.balance_amt:
           raise UserError('Receive Amount not should be greater than Due Amount')

class InvoicePaymentLine(models.Model):
    _name = "invoice.payment.line"
    _rec_name = 'invoice_id'

    invoice_id = fields.Many2one('account.invoice', string="Supplier Invoice",
                                 required=True)
    partner_id = fields.Many2one('res.partner', string="Supplier Name",
                                 required=True)
    balance_amt = fields.Float("Due Amount", required=True, digits=dp.get_precision('Stock Weight'))
    wizard_id = fields.Many2one('account.register.payments', string="Wizard")
    paying_amt = fields.Float("Pay Amount", required=True, digits=dp.get_precision('Stock Weight'))
    check_amount_in_words = fields.Char(string="Amount in Words")

    @api.onchange('paying_amt')
    def _onchange_amount(self):
        self.check_amount_in_words = AmountToTextFractional(self.paying_amt)
        if self.paying_amt > self.balance_amt:
           raise UserError('Pay Amount not should be greater than Due Amount')

class AccountRegisterPayments(models.Model):
    _inherit = "account.register.payments"

    @api.depends('invoice_customer_payments.receiving_amt')
    def _compute_customer_pay_total(self):
        self.total_customer_pay_amount = sum(line.receiving_amt for line in
                                             self.invoice_customer_payments)

    @api.depends('invoice_payments.paying_amt')
    def _compute_pay_total(self):
        self.total_pay_amount = sum(line.paying_amt for line in
                                    self.invoice_payments)
                                    
    uploaded_document_tt = fields.Many2many('ir.attachment','bill_attachment_pay_rel','bill','pay_id','Upload TT Docs',copy=False,track_visibility='always')
    bank_id = fields.Many2one('res.partner.bank', 'Bank Name',track_visibility='always',copy=False)

    pay_p_up = fields.Selection([('post', 'Done'),
				    ('not_posted', 'Pending')],copy=False,string='Transfer Status',track_visibility='always')
    chq_s_us = fields.Selection([('signed', 'Signed'),
				    ('not_signed', 'Not Signed')],copy=False,string='Cheque Signed/Unsigned',track_visibility='always')
				    

    is_auto_fill = fields.Char(string="Auto-Fill Pay Amount")
    invoice_payments = fields.One2many('invoice.payment.line', 'wizard_id',
                                       string='Payments')
    is_customer = fields.Boolean(string="Is Customer?")
    invoice_customer_payments =fields.One2many('invoice.customer.payment.line',
                        'wizard_id', string='Receipts')
    cheque_amount = fields.Float("Received Amount", digits=dp.get_precision('Stock Weight'))
    total_pay_amount = fields.Monetary("Total Invoices",
                                    compute='_compute_pay_total')
    total_customer_pay_amount =fields.Monetary("Total Invoices", compute='_compute_customer_pay_total')

    uploaded_document = fields.Binary(string='Uploaded Document', default=False , attachment=True)
    doc_name=fields.Char()
    payment_method = fields.Selection([('neft', 'Fund Transfer'),
				    ('cheque', 'Cheque')],string='Type',copy=False)

    cheque_status=fields.Selection([('not_clear','Not Cleared'),('cleared','Cleared')], string='Cheque Status')				    
    cheque_details = fields.One2many('bank.cheque.details','register_payment_id','Cheque Details')
    pay_type = fields.Selection([('sale', 'Sale'),
				    ('purchase', 'Purchase'),
				    ('cash', 'Cash'),
				    ('bank', 'Bank'),
				    ('general', 'Miscellaneous')],related='journal_id.type')
    
    @api.model
    def default_get(self, fields):
        context = dict(self._context or {})
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')
        # Checks on context parameters
        if not active_model or not active_ids:
            raise UserError(_("Program error: wizard action executed without"
                              " active_model or active_ids in context."))
        if active_model != 'account.invoice':
            raise UserError(_("Program error: the expected model for this"
                              " action is 'account.invoice'. The provided one"
                              " is '%d'.") % active_model)

        # Checks on received invoice records
        invoices = self.env[active_model].browse(active_ids)
        if any(invoice.state != 'open' for invoice in invoices):
            raise UserError(_("You can only register payments for open"
                              " invoices"))
        if any(inv.commercial_partner_id != invoices[0].commercial_partner_id for inv in invoices):
            raise UserError(_("In order to pay multiple invoices at once, they must belong to the same Customer."))
        
        if any(inv.currency_id != invoices[0].currency_id for inv in invoices):
            raise UserError(_("In order to pay multiple invoices at once, they"
                              " must use the same currency."))

        rec = {}
        if 'batch' in context and context.get('batch'):
            lines = []
            if INV_TO_PARTN[invoices[0].type] == 'customer':
                for inv in invoices:
                    lines.append((0, 0, {'partner_id': inv.partner_id.id,
                                         'invoice_id': inv.id,
                                         'balance_amt': inv.residual or 0.0,
                                         'receiving_amt':inv.residual or 0.0,
                                         'payment_difference': inv.residual or 0.0,  # noqa
                                         'handling': 'open'
                                         }))
                rec.update({'invoice_customer_payments': lines,
                            'is_customer': True})
            else:
                for inv in invoices:
                    lines.append((0, 0, {'partner_id': inv.partner_id.id,
                                         'invoice_id': inv.id,
                                         'balance_amt': inv.residual or 0.0,
                                         'paying_amt':  inv.residual or 0.0}))
                rec.update({'invoice_payments': lines, 'is_customer': False})
        else:
            # Checks on received invoice records
            if any(INV_TO_PARTN[inv.type] != INV_TO_PARTN[invoices[0].type]
                   for inv in invoices):
                raise UserError(_("You cannot mix customer invoices and vendor"
                                  " bills in a single payment."))

        total_amount = sum(inv.residual *
                           INV_TO_PAYM_SIGN[inv.type]
                           for inv in invoices)
        rec.update({
            'amount': abs(total_amount),
            'currency_id': invoices[0].currency_id.id,
            'payment_type': total_amount > 0 and 'inbound' or 'outbound',
            'partner_id': invoices[0].commercial_partner_id.id,
            'partner_type': INV_TO_PARTN[invoices[0].type],
        })
        return rec

    @api.multi
    @api.onchange('cheque_details')
    def total_receive(self):
        self.cheque_amount=sum(line.amount for line in self.cheque_details)

    @api.multi
    @api.onchange('payment_method')
    def cheque_details_empty(self):
        if self.payment_method !='cheque':
            self.cheque_details=[]

    def get_payment_batch_vals(self, inv_payment=False, group_data=None):
        if group_data:
            res = {
                'journal_id': self.journal_id.id,
                'payment_method_id': group_data.has_key('payment_method_id') and group_data['payment_method_id'] or self.payment_method_id.id,  # noqa
                'payment_date': self.payment_date,
                'communication': group_data['memo'],
                'invoice_ids': [(4, int(inv), None)
                                for inv in list(group_data['inv_val'])],
                'payment_type': self.payment_type,
                'amount': group_data['total'],
                'currency_id': self.currency_id.id,
                'partner_id': int(group_data['partner_id']),
                'partner_type': group_data['partner_type'],
            }
           # if self.payment_method_id ==\
                #    self.env.ref('account_check_printing.'
                  #               'account_payment_method_check'):
               # res.update({
                  #  'check_amount_in_words': group_data['total_check_amount_in_words'] or '',  # noqa
               # })
            return res

    @api.multi
    def make_payments(self):
        # Make group data either for Customers or Vendors
        context = dict(self._context or {})
        data = {}
        if self.is_customer:
            context.update({'is_customer': True})
            print"(((9999999999999",self.total_customer_pay_amount,self.cheque_amount
            if int(self.total_customer_pay_amount) != int(self.cheque_amount):
                raise UserError(_('Total Invoices'
                                        ' Amount and Check amount does not'
                                        ' match!.'))
            '''if self.cheque_details:
               if self.total_customer_pay_amount != sum(line.amount for line in self.cheque_details):
                  raise UserError(_('Total Cheque'
                                        ' Amount and Total Customer Receive Amount does not'
                                        ' match!.'))
            if self.total_customer_pay_amount > sum(line.balance_amt for line in self.invoice_customer_payments):
                raise UserError(_('Total Invoices Due'
                                        ' Amount and Total Receive Amount does not'
                                        ' match!.'))'''
            for paym in self.invoice_customer_payments:
                if paym.receiving_amt > 0:
                    paym.payment_difference = paym.balance_amt - paym.receiving_amt  # noqa
                    partner_id = str(paym.invoice_id.partner_id.id)
                    if partner_id in data:
                        old_total = data[partner_id]['total']
                        if self.communication:
                            memo = data[partner_id]['memo'] + ' : ' +\
                                self.communication + '-' +\
                                str(paym.invoice_id.number)+"-Amount-"+str(paym.receiving_amt) +'\n'
                        else:
                            memo = data[partner_id]['memo'] + ' : ' +\
                                str(paym.invoice_id.number)+"-Amount-"+str(paym.receiving_amt)  +'\n'
                        amount_total = old_total + paym.receiving_amt
                        amount_word = AmountToTextFractional(amount_total)
                        data[partner_id].update({
                            'partner_id': partner_id,
                            'partner_type': INV_TO_PARTN[paym.invoice_id.type],
                            'total': amount_total,
                            'memo': memo,
                            'payment_method_id': paym.payment_method_id and
                            paym.payment_method_id.id or False,
                            'total_check_amount_in_words': amount_word
                        })
                        data[partner_id]['inv_val'].update({
                            str(paym.invoice_id.id): {
                                'receiving_amt': paym.receiving_amt,
                                'handling': paym.handling,
                                'payment_difference': paym.payment_difference,
                                'writeoff_account_id':
                                    paym.writeoff_account_id and
                                    paym.writeoff_account_id.id or False
                                }
                        })
                    else:
                        if self.communication:
                            memo = self.communication + '-' +\
                                str(paym.invoice_id.number)+"-Amount-"+str(paym.receiving_amt)  +'\n'
                        else:
                            memo = str(paym.invoice_id.number)+"-Amount-"+str(paym.receiving_amt) +'\n'
                        amount_word = AmountToTextFractional(
                            paym.receiving_amt)
                        data.update({
                            partner_id: {
                                'partner_id': partner_id,
                                'partner_type': INV_TO_PARTN[
                                    paym.invoice_id.type],
                                'total': paym.receiving_amt,
                                'payment_method_id':
                                    paym.payment_method_id and
                                    paym.payment_method_id.id or False,
                                'total_check_amount_in_words': amount_word,
                                'memo': memo,
                                'inv_val': {str(paym.invoice_id.id): {
                                    'receiving_amt': paym.receiving_amt,
                                    'handling': paym.handling,
                                    'payment_difference':
                                        paym.payment_difference,
                                    'writeoff_account_id':
                                        paym.writeoff_account_id and
                                        paym.writeoff_account_id.id or False
                                    }
                                }
                            }
                        })
                        print"&&hhhhh&&&777777",memo
        else:
            context.update({'is_customer': False})
            if int(self.total_pay_amount) != int(self.cheque_amount):
                raise UserError(_('Total Invoices'
                                        ' Amount and Check amount does not'
                                        ' match!.'))
            '''if self.cheque_details:
               if self.total_pay_amount != sum(line.amount for line in self.cheque_details):
                  raise UserError(_('Total Cheque'
                                        ' Amount and Total  Pay does not'
                                        ' match!.'))
            if self.total_pay_amount > sum(line.balance_amt for line in self.invoice_payments):
                raise UserError(_('Total Invoices Due'
                                        ' Amount and Total Pay Amount does not'
                                        ' match!.'))'''
            for paym in self.invoice_payments:
                if paym.paying_amt > 0:
                    partner_id = str(paym.invoice_id.partner_id.id)
                    if partner_id in data:
                        old_total = data[partner_id]['total']
                        if self.communication:
                            memo = data[partner_id]['memo'] + ' : ' +\
                                self.communication + '-' +\
                                str(paym.invoice_id.number)+"-Amount-"+str(paym.paying_amt) +'\n'
                        else:
                            memo = data[partner_id]['memo'] + ' : ' +\
                                str(paym.invoice_id.number)+"-Amount-"+str(paym.paying_amt) +'\n'
                        amount_total = old_total + paym.paying_amt
                        amount_word = AmountToTextFractional(amount_total)
                        data[partner_id].update({'partner_id': partner_id,
                                                 'partner_type': INV_TO_PARTN[paym.invoice_id.type],  
                                                 'total': amount_total,
                                                 'memo': memo,
                                                 'total_check_amount_in_words':
                                                     amount_word
                                                 })
                        data[partner_id]['inv_val'].update({str(
                            paym.invoice_id.id): paym.paying_amt})
                    else:
                        if self.communication:
                            memo = self.communication + '-' +\
                                str(paym.invoice_id.number)+"-Amount-"+str(paym.paying_amt) +'\n'
                        else:
                            memo = str(paym.invoice_id.number)+"-Amount-"+str(paym.paying_amt) +'\n'
                        amount_word = AmountToTextFractional(paym.paying_amt)
                        data.update({
                            partner_id:
                                {'partner_id': partner_id,
                                 'partner_type': INV_TO_PARTN[paym.invoice_id.type], 
                                 'total': paym.paying_amt,
                                 'total_check_amount_in_words': amount_word,
                                 'memo': memo,
                                 'inv_val': {str(paym.invoice_id.id):
                                             paym.paying_amt}
                                 }
                        })
        context.update({'group_data': data})
        # Making partner wise payment
        payment_ids = []
        for p in list(data):
            payment = self.env['account.payment'].with_context(context).\
                create(self.get_payment_batch_vals(group_data=data[p]))
            payment.payment_method=self.payment_method
            payment.uploaded_document=self.uploaded_document
            payment.doc_name=self.doc_name
            payment.cheque_status=self.cheque_status
            payment.payment_from='multi'
            for bank_line in self.cheque_details:
                bank_line.payment_id =payment.id
            payment_ids.append(payment.id)
            payment.post()

        view_id = self.env['ir.model.data'].get_object_reference(
            'api_account',
            'view_account_supplier_payment_tree_nocreate')[1]
        return {
            'name': _('Payments Done'),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'account.payment',
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': "[('id','in',%s)]" % (payment_ids),
            'context': {'group_by': 'partner_id'}
        }

    '''@api.multi
    def auto_fill_payments(self):
        ctx = self._context.copy()
        for wiz in self:
            if wiz.is_customer:
                if wiz.invoice_customer_payments:
                    for payline in wiz.invoice_customer_payments:
                        payline.write({'receiving_amt': payline.balance_amt,
                                       'payment_difference': 0.0})
                ctx.update({'reference': wiz.communication or '',
                            'journal_id': wiz.journal_id.id})
            else:
                if wiz.invoice_payments:
                    for payline in wiz.invoice_payments:
                        payline.write({'paying_amt': payline.balance_amt})
                ctx.update({'reference': wiz.communication or '',
                            'journal_id': wiz.journal_id.id})

        return {
            'name': _("Batch Payments"),
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_id': self.id,
            'res_model': 'account.register.payments',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'context': ctx
        }'''


# amountInt: int value
# returns: string of amountInt converted to english text,
#           with decimals converted to cent fractional
def AmountToTextFractional(amountInt):
    amount_word = amount_to_text_en.amount_to_text(
        math.floor(amountInt), lang='en', currency='')
    amount_word = amount_word.replace(' and Zero Cent', '')
    decimals = amountInt % 1
    if decimals >= 10**-2:
        amount_word += _(' and %s/100') % str(int(round(
            float_round(decimals*100, precision_rounding=1))))
    return amount_word

class AccountPayment(models.Model):
    _inherit = "account.payment"

  
    @api.multi
    def _create_payment_entry(self, amount):
        """ Create a journal entry corresponding to a payment, if the payment
            references invoice(s) they are reconciled.
            Return the journal entry.
        """
        # If group data
        if 'group_data' in self._context:
            aml_obj = self.env['account.move.line'].\
                with_context(check_move_validity=False)
            invoice_currency = False
            if self.invoice_ids and\
                    all([x.currency_id == self.invoice_ids[0].currency_id
                         for x in self.invoice_ids]):
                invoice_currency = self.invoice_ids[0].currency_id
            move = self.env['account.move'].create(self._get_move_vals())
            p_id = str(self.partner_id.id)
            for inv in self._context.get('group_data')[p_id]['inv_val']:
                amt = 0
                if 'is_customer' in self._context and\
                        self._context.get('is_customer'):
                    amt = -(self._context.get('group_data')[p_id]['inv_val']
                            [inv]['receiving_amt'])
                else:
                    amt = self._context.get('group_data')[p_id]['inv_val'][inv]

                debit, credit, amount_currency, currency_id =\
                    aml_obj.with_context(date=self.payment_date).\
                    compute_amount_fields(amt, self.currency_id,
                                          self.company_id.currency_id,
                                          invoice_currency)
                counterpart_aml_dict =\
                    self._get_shared_move_line_vals(debit,
                                                    credit, amount_currency,
                                                    move.id, False)
                current_invoice = self.env['account.invoice'].browse(int(inv))
                counterpart_aml_dict.update(
                    self._get_counterpart_move_line_vals(current_invoice))
                counterpart_aml_dict.update({'currency_id': currency_id})
                counterpart_aml = aml_obj.create(counterpart_aml_dict)
                if 'is_customer' in self._context and\
                        self._context.get('is_customer'):
                    handling = self._context.get('group_data')[p_id]['inv_val'][inv]['handling']  # noqa
                    payment_difference = self._context.get('group_data')[p_id]['inv_val'][inv]['payment_difference'] 
                    writeoff_account_id = self._context.get('group_data')[p_id]['inv_val'][inv]['writeoff_account_id']  
                    if handling == 'reconcile' and\
                            payment_difference:
                        writeoff_line =\
                            self._get_shared_move_line_vals(0, 0, 0, move.id,
                                                            False)
                        debit_wo, credit_wo, amount_currency_wo, currency_id =\
                            aml_obj.with_context(date=self.payment_date).\
                            compute_amount_fields(
                                payment_difference,
                                self.currency_id,
                                self.company_id.currency_id,
                                invoice_currency)
                        writeoff_line['name'] = _('Counterpart')
                        writeoff_line['account_id'] = writeoff_account_id
                        writeoff_line['debit'] = debit_wo
                        writeoff_line['credit'] = credit_wo
                        writeoff_line['amount_currency'] = amount_currency_wo
                        writeoff_line['currency_id'] = currency_id
                        writeoff_line = aml_obj.create(writeoff_line)
                        if counterpart_aml['debit']:
                            counterpart_aml['debit'] += credit_wo - debit_wo
                        if counterpart_aml['credit']:
                            counterpart_aml['credit'] += debit_wo - credit_wo
                        counterpart_aml['amount_currency'] -=\
                            amount_currency_wo
                current_invoice.register_payment(counterpart_aml)
                # Write counterpart lines
                if not self.currency_id != self.company_id.currency_id:
                    amount_currency = 0
                liquidity_aml_dict =\
                    self._get_shared_move_line_vals(credit, debit,
                                                    -amount_currency, move.id,
                                                    False)
                liquidity_aml_dict.update(
                    self._get_liquidity_move_line_vals(-amount))
                aml_obj.create(liquidity_aml_dict)
            move.post()
            return move

        return super(AccountPayment, self)._create_payment_entry(amount)
