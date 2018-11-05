# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api, fields, models, _
from datetime import datetime, date, timedelta
from openerp.exceptions import UserError, ValidationError
from openerp import tools
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
import openerp.addons.decimal_precision as dp
from dateutil.relativedelta import relativedelta


class HrExpense(models.Model):
    _inherit = "hr.expense"
    
    name = fields.Char(string='Expense Description', readonly=True)
    account_pay_id = fields.Many2one('account.move', string='Payment Journal Entry', copy=False, track_visibility="onchange")
    payment_id = fields.Many2one('account.payment', string='Payment', copy=False, track_visibility="onchange")
    type_product = fields.Many2one('type.product', 'Product Type',related='product_id.type_product',store=True)
    product_expense_account = fields.Many2one('account.account', 'Product Expense Account',related='product_id.property_account_expense_id',store=True)
    journal_id = fields.Many2one('account.journal', string='Expense Journal', states={'done': [('readonly', True)], 'post': [('readonly', True)]}, default=lambda self: self.env['account.journal'].search([('type', '=', 'purchase'),('company_id','=',self.env.user.company_id.id)], limit=1), help="The journal used when the expense is done.")

    employee_id = fields.Many2one('hr.employee', string="Employee")
#    check_bank = fields.Boolean(string="Bank Journal")
    product_uom_id = fields.Many2one('product.uom', string='Unit of Measure', required=True)

    refuse_reason = fields.Char(string='Refuse Reason',track_visibility='always' )

    partner_id_preferred = fields.Many2one('res.partner', 'Partner')
    expense_type = fields.Selection([("emp_expense", "Employee Expense"), ("other_expense", "Other Expense")], string="Expense Type")
    approval_status = fields.Selection([("app_required", "Approval Required"), ("app_not_required", "No Approval")],default='app_not_required', string="Approval Status")
#    bank_cash = fields.Selection([("bank", "Bank"), ("cash", "Cash")],default='cash', string="Journal Type?",copy=False)
    bank_journal_id_expense = fields.Many2one('account.journal', string='Bank Journal', states={'done': [('readonly', True)]}, default=lambda self: self.env['account.journal'].search([('type', 'in', ['cash', 'bank']),('company_id','=',self.env.user.company_id.id)], limit=1), help="The payment method used when the expense is paid by the company.")

    internal_note=fields.Text('Remarks on Receipt')
    communication = fields.Char(string='Internal Note')
    is_bank_journal = fields.Boolean(string='Bank Type?')
    pay_date = fields.Date(readonly=True, string="Paid Date")


    uploaded_document = fields.Binary(string='Uploaded Document', default=False , attachment=True)
    uploaded_document_bill = fields.Many2many('ir.attachment','bill_attachment_expense_rel','bill','exp_id','Upload Bills')


    doc_name=fields.Char()
    payment_method = fields.Selection([('neft', 'Fund Transfer'),
				    ('cheque', 'Cheque')],string='Type',copy=False)
				    
    cheque_details = fields.One2many('bank.cheque.details.expense','expense_id','Cheque Details')
    approval_by = fields.Many2one('res.users', 'Approval Req. By',copy=False)
    approved_by = fields.Many2one('res.users', 'Approved By',copy=False)
    requested_by = fields.Many2one('hr.employee', 'Requested By',copy=False)
    user_id = fields.Many2one('res.users', 'User')
    department = fields.Many2one('hr.department', 'Department',related='requested_by.department_id',store=True)
    cheque_status=fields.Selection([('not_clear','Not Cleared'),('cleared','Cleared')], string='Cheque Status')
    
    @api.model
    def default_get(self, fields):
        res = super(HrExpense,self).default_get(fields)
        print "fieldsfieldsfields",fields
        res.update({'bank_journal_id_expense':False,'is_bank_journal':False})
        return res
    
    
    @api.multi
    def print_payment_receipt(self):
        return self.env['report'].get_action(self, 'aalmir_custom_expense.report_payment_account')
        return False
    
    @api.onchange('bank_journal_id_expense')
    def journal_onchange(self):
        print "bank_journal_id_expensebank_journal_id_expense",self.bank_journal_id_expense
    	if self.bank_journal_id_expense.type == 'bank' and self.state!='draft':
            self.is_bank_journal=True

        if self.bank_journal_id_expense.type =='cash' and self.state!='draft':
            self.is_bank_journal=False
            print "is it bank journal-----------------",self.is_bank_journal

#    @api.onchange('bank_cash')
#    def bank_cash_onchange(self):
#        print "bank_cash=======",self.bank_cash
#    	if self.bank_cash and self.bank_cash == 'bank':
#            self.is_bank_journal=True
#            self.bank_journal_id=False
#            return {'domain': {'bank_journal_id_expense': [('type', '=', 'bank'),('company_id', '=', self.company_id.id)]}}
#        elif self.bank_cash and self.bank_cash == 'cash':
#            self.is_bank_journal=False
#            return {'domain': {'bank_journal_id_expense': [('type', '=', 'cash'),('company_id', '=', self.company_id.id)]}}
        
    
    @api.onchange('requested_by')
    def requested_by_onchange(self):
        print "requeste by---------------------d",self.requested_by
    	if self.requested_by:
            self.bank_journal=True
            
    @api.onchange('company_id')
    def company_onchange(self):
        print "copmany id now",self.company_id
    	if self.company_id:
            journal_search=self.env['account.journal'].search([('type', '=', 'purchase'),('company_id','=',self.company_id.id)], limit=1)
            print "journal_searchjournal_search",journal_search
            if journal_search:
                self.journal_id=journal_search.id
            return {'domain': {'bank_journal_id_expense': [('company_id', '=', self.company_id.id),('type', 'in', ['bank','cash'])]}}


    @api.model
    def create(self, vals):
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.expense')
            expense = super(HrExpense, self).create(vals)
            #voucher.assert_balanced()
            return expense

    
    @api.multi
    def submit_expenses(self):
        if any(expense.state != 'draft' for expense in self):
            raise UserError(_("You can only submit draft expenses!"))
        if self.total_amount==0.0:
            raise UserError(_("Expense Amount Cannot be zero!"))
        self.write({'user_id':self._uid})
        if self.expense_type=='other_expense':
            self.write({'employee_id':False})
        if self.expense_type=='employee_expene':
            self.write({'partner_id_preferred':False})
        self.write({'bank_journal_id_expense':False})
        non_approval=self.env['approval.config.line'].search([('type_product','=',self.type_product.id)])
        print "non_approvalnon_approvalnon_approval",non_approval
        if non_approval:
            if non_approval.currency_id.id!=self.currency_id.id:
                from_currency = non_approval.currency_id
                to_currency = self.currency_id
                limit_amt = from_currency.compute(non_approval.approve_amount, to_currency, round=False)
            else:
                limit_amt=non_approval.approve_amount
            if self.total_amount>limit_amt:
                self.write({'approval_status':'app_required','approval_by':non_approval.approval_by.id,'user_id':self._uid,'state': 'submit'})
            else:
                self.write({'state': 'approve'})
        else:
            self.write({'state': 'submit','approval_status':'app_not_required'})
        return True

    @api.multi
    def refuse_expenses(self, reason):
        result = super(HrExpense, self).refuse_expenses(reason)

        self.write({'refuse_reason': reason,'approved_by':False,'approval_by':False})
        return result
    
    def _prepare_move_line(self, line):
        '''
        This function prepares move line of account.move related to an expense
        '''
        if self.employee_id:
            partner_id = self.employee_id.address_home_id.commercial_partner_id.id
        if self.expense_type=='other_expense' and self.partner_id_preferred:
            partner_id=self.partner_id_preferred.id
        else:
            partner_id=False
        return {
            'date_maturity': line.get('date_maturity'),
            'partner_id': partner_id,
            'name': line['name'][:64],
            'debit': line['price'] > 0 and line['price'],
            'credit': line['price'] < 0 and -line['price'],
            'account_id': line['account_id'],
            'analytic_line_ids': line.get('analytic_line_ids'),
            'amount_currency': line['price'] > 0 and abs(line.get('amount_currency')) or -abs(line.get('amount_currency')),
            'currency_id': line.get('currency_id'),
            'tax_line_id': line.get('tax_line_id'),
            'tax_ids': line.get('tax_ids'),
            'ref': line.get('ref'),
            'quantity': line.get('quantity',1.00),
            'product_id': line.get('product_id'),
            'product_uom_id': line.get('uom_id'),
            'analytic_account_id': line.get('analytic_account_id'),
        }

    @api.multi
    def action_move_create(self):
        '''
        main function that is called when trying to create the accounting entries related to an expense
        '''
        if not self.bank_journal_id_expense:
            raise UserError(_("Please select Bank Journal for Processiong Payment"))

        if any(expense.state != 'approve' for expense in self):
            raise UserError(_("You can only generate accounting entry for approved expense(s)."))

        if any(expense.employee_id != self[0].employee_id for expense in self):
            raise UserError(_("Expenses must belong to the same Employee."))

        if any(not expense.journal_id for expense in self):
            raise UserError(_("Expenses must have an expense journal specified to generate accounting entries."))

        journal_dict = {}
        maxdate = False
        for expense in self:
            if expense.date > maxdate:
                maxdate = expense.date
            jrn = expense.bank_journal_id_expense if expense.payment_mode == 'company_account' else expense.journal_id
            journal_dict.setdefault(jrn, [])
            journal_dict[jrn].append(expense)

        for journal, expense_list in journal_dict.items():
            #create the move that will contain the accounting entries
            move = self.env['account.move'].create({
                'journal_id': journal.id,
                'company_id': self.env.user.company_id.id,
                'date': maxdate,
            })
            for expense in expense_list:
                company_currency = expense.company_id.currency_id
                diff_currency_p = expense.currency_id != company_currency
                #one account.move.line per expense (+taxes..)
                move_lines = expense._move_line_get()

                #create one more move line, a counterline for the total on payable account
                total, total_currency, move_lines = expense._compute_expense_totals(company_currency, move_lines, maxdate)
                    
                if expense.payment_mode == 'company_account':
                    if not expense.bank_journal_id_expense.default_credit_account_id:
                        raise UserError(_("No credit account found for the %s journal, please configure one.") % (expense.bank_journal_id_expense.name))
                    emp_account = expense.bank_journal_id_expense.default_credit_account_id.id

                else:
                    move_line_data={}
                    if expense.expense_type=='employee_expense' and not expense.employee_id.address_home_id:
                        raise UserError(_("No Home Address found for the employee %s, please configure one.") % (expense.employee_id.name))
                    if expense.employee_id:
                        print expense.employee_id.address_home_id
                        emp_account = expense.employee_id.address_home_id.property_account_payable_id.id
                        name=expense.employee_id.name
                    else:
                        if expense.expense_type=='other_expense' and expense.partner_id_preferred:
                            emp_account = expense.partner_id_preferred.property_account_payable_id.id
                            name=expense.partner_id_preferred.name
                        else:
                            emp_account = expense.product_id.property_account_expense_id.id
                            name=expense.product_id.name
                   
                print "namenamename----------------",name,emp_account
                move_line_data={
                        'type': 'dest',
                        'name':name ,
                        'price': total,
                        'account_id': emp_account,
                        'date_maturity': expense.date,
                        'amount_currency': diff_currency_p and total_currency or False,
                        'currency_id': diff_currency_p and expense.currency_id.id or False,
                        'ref': expense.employee_id.address_home_id.ref if expense.employee_id else expense.partner_id_preferred.name if expense.partner_id_preferred else False,
                        }
                move_lines.append(move_line_data)

                #convert eml into an osv-valid format
                lines = map(lambda x:(0, 0, expense._prepare_move_line(x)), move_lines)
                print "lines===================",lines
                move.with_context(dont_create_taxes=True).write({'line_ids': lines})
                expense.write({'account_move_id': move.id, 'state': 'post'})
                if expense.payment_mode == 'company_account':
                    expense.paid_expenses()
            move.post()
        print "expenkdskjdsnhkjfhdskjfjkednf",expense.uploaded_document
        pay_dict={'payment_type': 'outbound',
        'payment_method_id': self.env.ref('account.account_payment_method_manual_out').id,
        'payment_method': self.payment_method,
        'partner_type': 'supplier',
        'amount': expense.total_amount,
        'expense_pay':True,
        'expense_id':expense.id,
        'currency_id': expense.currency_id.id,
        'payment_date': date.today(),
        'journal_id': expense.bank_journal_id_expense.id,
        'communication': expense.communication,
        'internal_note': expense.internal_note,
        }
        
        if self.expense_type=='other_expense':
            if self.partner_id_preferred:
                pay_dict.update({ 'partner_id': self.partner_id_preferred.id})
            else:
                pay_dict.update({ 'partner_id': self.env.user.partner_id.id})
            
        else:
            pay_dict.update({ 'partner_id': self.employee_id.address_home_id.id})

                   

        payment = self.env['account.payment'].create(pay_dict)
        print "paymentpaymentpayment",payment,emp_account
        print "jhdgijedhjewd",payment.journal_id
        payment.post()
        if self.cheque_details:
            vals=[]
            for each in self.cheque_details:
                vals.append((0,0,{
					'partner_id':each.partner_id, 
					'journal_id':each.journal_id,
					'bank_name':each.bank_name.id,
					'communication': each.communication,
					'cheque_no': each.cheque_no,
					'branch_name': each.branch_name,
					'amount': each.amount,
					'reconcile_date': each.reconcile_date,
#					'register_payment_id': each.register_payment_id,
#					'payment_id':payment.id,
					'reconcile_date': each.reconcile_date,
					'cheque_status':each.expense_id.cheque_status
                                        }))
            print "valspppppppppppppppppppppppppppppppp",vals
            payment.write({'cheque_details':vals})
        if self.uploaded_document:
            payment.write({'uploaded_document': self.uploaded_document})

        move_line_id=self.env['account.move.line'].search([('payment_id','=',payment.id)])
        move_pay=move_line_id[0].move_id
        expense.write({'account_pay_id': move_pay.id,'payment_id':payment.id,'pay_date':date.today()})
        expense.paid_expenses()

        return True
    
    @api.multi
    def approve_expenses(self):
        self.write({'state': 'approve','approved_by':self._uid})

    
                
    @api.onchange('product_id')
    def _onchange_product_id(self):
        result = super(HrExpense, self)._onchange_product_id()

        if self.product_id:
            if self.product_id.product_tmpl_id.partner_id_preferred:
                self.partner_id_preferred = self.product_id.product_tmpl_id.partner_id_preferred.id
            print "uom-----------------",self.product_id.product_tmpl_id.uom_id.id
            self.product_uom_id= self.product_id.uom_id.id
            self.type_product= self.product_id.type_product
        return result
    
    
class BankChequeDetailsExpense(models.Model):
    '''to store cheque details against bank'''
    _name = "bank.cheque.details.expense"
    
    expense_id = fields.Many2one('hr.expense','Payment Name')
    journal_id = fields.Many2one('account.journal',related="expense_id.bank_journal_id_expense",string='Journal')
    partner_id = fields.Many2one('res.partner',related="expense_id.partner_id_preferred",string='Supplier/Customer')
    bank_name = fields.Many2one('cheque.bank.name','Bank Name')
    communication = fields.Char(related="expense_id.communication",string='Internal Note')
    #bank_id = fields.Many2one('res.partner.bank', 'Bank Name')
    cheque_no = fields.Char('Cheque No.')
    cheque_date = fields.Date('Cheque Date')
    branch_name = fields.Char('Bank Branch Name')
    amount = fields.Float('Amount')
    reconcile_date = fields.Date('Reconcile Date')
    register_payment_id=fields.Many2one('account.register.payments')
    cheque_status=fields.Selection([('not_clear','Not Cleared'),('cleared','Cleared')],related="expense_id.cheque_status", string='Cheque Status')
    
    		   			   			