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
    show_approve=fields.Boolean('Show Approve', compute='compute_show_approve',copy=False)
    total_thirty=fields.Float('30 Days total', compute='compute_thirty_days_expense',copy=False,help="This amount shows total including current amount and previous 30 days paid expenses of expense type")
    mothly_exp_limit=fields.Float('Your Monthly Limit', compute='compute_monthly_expense_limit',copy=False)

    cancel_reason = fields.Char(string='Cancel Reason',track_visibility='always' ,copy=False)
    approve_conf_exist = fields.Boolean(string='Approval Config Exists?',copy=False)
    special_approval = fields.Boolean(string='Special Approval',copy=False)

    uploaded_document_cancel = fields.Many2many('ir.attachment','cancel_attachment_exp_rel','cancel_att','exp_id','Upload Cancel Proof',copy=False,track_visibility='always')
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
    bank_journal_id_expense = fields.Many2one('account.journal', string='Bank Journal', states={'done': [('readonly', True)]},default=lambda self: self.env['account.journal'].search([('type', 'in', ['cash', 'bank']),('company_id','=',self.env.user.company_id.id)], limit=1), help="The payment method used when the expense is paid by the company.")

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

#    expense_details = fields.One2many('payment.expense.line','expense_id',copy=False)
    approved_by = fields.Many2one('res.users', 'Approved By',copy=False)
    requested_by = fields.Many2one('hr.employee', 'Requested By',copy=False)
    user_id = fields.Many2one('res.users', 'User')
    department = fields.Many2one('hr.department', 'Department',related='requested_by.department_id',store=True)
    cheque_status=fields.Selection([('not_clear','Not Cleared'),('cleared','Cleared')], string='Cheque Status',copy=False)
    
    pay_p_up = fields.Selection([('post', 'Done'),
				    ('not_posted', 'Pending')],copy=False,string='Transfer Status',track_visibility='always')
    chq_s_us = fields.Selection([('signed', 'Signed'),
				    ('not_signed', 'Not Signed')],copy=False,string='Cheque Signed/Unsigned',track_visibility='always')
    uploaded_document_tt = fields.Many2many('ir.attachment','bill_attachment_pay_rel','bill','pay_id','Upload TT Docs',copy=False,track_visibility='always')
    bank_id = fields.Many2one('res.partner.bank', 'Bank Name',copy=False,track_visibility='always')
    internal_request_tt=fields.Text('Note',track_visibility='always',copy=False)
#    tot_amount_if_other_expense=fields.Float('Total Amount', compute='amount_other_expense_if_any')

    @api.multi
    def compute_thirty_days_expense(self):
        for record in self:
            thirty_days_from_now=date.today()+timedelta(days=30)
            print "thirty_days_from_nowthirty_days_from_now",thirty_days_from_now
            expense_ids=self.search([('state','not in',['draft','submit','cancel']),('id','!=',record.id),('type_product','=',record.type_product.id),('date','<=',thirty_days_from_now)])
            amount_total_exp=0.0

            if expense_ids:
                for each in expense_ids:
                    amount_total_exp+=each.total_amount
            record.total_thirty=amount_total_exp+record.total_amount
    @api.multi
    def compute_monthly_expense_limit(self):
        for record in self:
            non_approval=self.env['approval.config'].search([('product_type','=',record.type_product.id)])
            if non_approval:
                line_id=self.env['approval.config.line'].search([('approve_id','=',non_approval.id),('approval_by','=',record._uid)])
                if line_id:
                    record.mothly_exp_limit=line_id.monthly_amt
                else:
                    record.mothly_exp_limit=0.0

            
    @api.multi
    def compute_show_approve(self):
        for record in self:
            non_approval=self.env['approval.config'].search([('product_type','=',record.type_product.id)])
            if record.special_approval==True:
                print "sdfsdfsdffsdf",self._uid,self.approval_by
                if record._uid==record.approval_by.id:
                    record.show_approve=True
                    break;
            if non_approval:
                user_ids=[]
                for each_line in non_approval.approval_line:
                    if non_approval.currency_id.id!=each_line.approve_id.currency_id.id:
                        from_currency = non_approval.currency_id
                        to_currency = each_line.approve_id.currency_id
                        limit_amt = from_currency.compute(each_line.approve_amount_upto, to_currency, round=False)
                    else:
                        limit_amt=each_line.approve_amount_upto
                    if limit_amt>record.total_amount:
                        user_ids.append(each_line.approval_by.id)
                if self.env.user.id in user_ids:
                    record.show_approve=True
                    break;
                else:
                    group_id = self.env['ir.model.data'].get_object_reference('aalmir_custom_expense','restricted_hr_expense_grant_for_no_ac')[1]
                    users=self.env['res.groups'].search([('id', '=',group_id)]).users
                    if self.env.user.id in users.ids:
                        record.show_approve=True
                        break;
                    else:
                        record.show_approve=False
                        break;
#                else:
#                    record.show_approve=False
#                    break;
            else:
                group_id = self.env['ir.model.data'].get_object_reference('aalmir_custom_expense','restricted_hr_expense_grant_for_no_ac')[1]
                users=self.env['res.groups'].search([('id', '=',group_id)]).users
                if self.env.user.id in users.ids:
                    record.show_approve=True
                    break;
                else:
                    record.show_approve=False
                    break;
                    
#    @api.multi
#    @api.depends('expense_details')
#    def amount_other_expense_if_any(self):
#        for record in self:
#            if record.expense_details:
#                for each_exp in record.expense_details:
#                    record.tot_amount_if_other_expense+=each_exp.amount
    
    @api.onchange('payment_method')
    def pay_method_onchange(self):
    	if self.payment_method and self.payment_method=='neft':
            self.pay_p_up='not_posted'
        else:
            self.pay_p_up=''

    @api.onchange('partner_id_preferred','employee_id')
    def _onchange_partner_emp(self):
        if self.expense_type and self.expense_type=='other_expense':
            bank_id=self.env['res.partner.bank'].search([('partner_id','=',self.partner_id_preferred.id),('active_account','=',True)])
            if len(bank_id)==1:
                self.bank_id=bank_id.id
            return {'domain': {'bank_id': [('partner_id', '=', self.partner_id_preferred.id)]}}

        elif self.expense_type and self.expense_type=='emp_expense':
            self.partner_id_preferred=self.employee_id.address_home_id.id
            print "self.partner_id_preferredself.partner_id_preferred",self.partner_id_preferred
            bank_id=self.env['res.partner.bank'].search([('partner_id','=',self.employee_id.address_home_id.id),('active_account','=',True)])
            print "bank_idbank_idbank_id",bank_id
            if bank_id and len(bank_id)==1:
                self.bank_id=bank_id.id
            return {'domain': {'bank_id': [('partner_id', '=', self.employee_id.address_home_id.id)]}}


    @api.model
    def default_get(self, fields):
        res = super(HrExpense,self).default_get(fields)
        print "fieldsfieldsfields",fields
        res.update({'bank_journal_id_expense':False,'is_bank_journal':False})
        return res
    
    @api.one
    def copy(self, default=None):
        default = dict(default or {})
        default.update({'bank_journal_id_expense':False,'is_bank_journal':False})
        return super(HrExpense, self).copy(default)
    
    
    @api.multi
    def cancel_expense(self):
        cofirm_form = self.env.ref('api_account.pay_cancel_wizard_view_form', False)
        if cofirm_form:
            return {
                        'name':'Cancel Wizard',
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'cancel.pay.reason.wizard',
                        'views': [(cofirm_form.id, 'form')],
                        'view_id': cofirm_form.id,
                        'target': 'new'
                    }
        
    @api.multi
    def print_payment_receipt(self):
        return self.env['report'].get_action(self, 'aalmir_custom_expense.report_payment_account_new1')
        return False
    
    @api.onchange('bank_journal_id_expense')
    def journal_onchange(self):
        self.payment_method=False
        print "bank_journal_id_expensebank_journal_id_expense",self.bank_journal_id_expense
    	if self.bank_journal_id_expense.type == 'bank' and self.state!='draft':
            self.is_bank_journal=True

        if self.bank_journal_id_expense.type =='cash' and self.state!='draft':
            self.is_bank_journal=False
            self.cheque_status=''
            print "is it bank journal-----------------",self.is_bank_journal


        
    
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
#        if self.expense_type=='emp_expense':
#            self.write({'partner_id_preferred':False})
        self.write({'bank_journal_id_expense':False})
        non_approval=self.env['approval.config'].search([('product_type','=',self.type_product.id)])
        print "non_approvalnon_approvalnon_approval",non_approval
        if non_approval:
            if self.total_amount>non_approval.approve_not_req_upto:
                if not non_approval.approval_line:
                    raise UserError(_('There is no Approval Line defined in Approval Configuration.'))

                amt_upto_list=[]
                for each_line in non_approval.approval_line:
                    if non_approval.currency_id.id!=self.currency_id.id:
                        from_currency = non_approval.currency_id
                        to_currency = self.currency_id
                        limit_amt = from_currency.compute(each_line.approve_amount_upto, to_currency, round=False)
                    else:
                        limit_amt=each_line.approve_amount_upto
                    amt_upto_list.append(limit_amt)
                amt_upto_list.sort()
                print "amt_upto_listamt_upto_list",amt_upto_list
                for each_amt in amt_upto_list:
                    if self.total_amount<each_amt:
                        print "each_amteach_amteach_amt",each_amt
                        line_id=self.env['approval.config.line'].search([('approve_amount_upto','=',each_amt),('approve_id','=',non_approval.id)])
                        self.write({'approval_status':'app_required','approval_by':line_id.approval_by.id,'user_id':self._uid,'state': 'submit'})
                        return True
                    else:
                        group_id = self.env['ir.model.data'].get_object_reference('aalmir_custom_expense','restricted_hr_expense_grant_for_no_ac')[1]
                        print "group_idgroup_id",group_id
                        users=self.env['res.groups'].search([('id', '=',group_id)]).users
                        if users:
                            self.write({'approval_status':'app_required','approval_by':users[0].id,'user_id':self._uid,'state': 'submit'})

#                        self._cr.execute('SELECT ID FROM approval_config_line where approve_amount_upto=(select max(approve_amount_upto) from approval_config_line where approve_id=%s)', (non_approval.id,))
#                        result=self._cr.fetchone()
#                        print "resultresult",result
#                        cl_brw=self.env['approval.config.line'].browse(result[0])
                        else:
                            self.write({'approval_status':'app_required','user_id':self._uid,'state': 'submit'})

            else:
                self.write({'state': 'approve'})
        else:
            self.write({'approve_conf_exist':True})

            group_id = self.env['ir.model.data'].get_object_reference('aalmir_custom_expense','restricted_hr_expense_grant_for_no_ac')[1]
            print "group_idgroup_id",group_id
            users=self.env['res.groups'].search([('id', '=',group_id)]).users
            self.write({'state': 'submit','approval_status':'app_required'})
            if users:
                self.write({'approval_by':users[0].id})

        return True

    @api.multi
    def refuse_expenses(self, reason):
        result = super(HrExpense, self).refuse_expenses(reason)

        self.write({'refuse_reason': reason,'approved_by':False,'approval_by':False,'special_approval':False})
        return result
    
    def _prepare_move_line(self, line):
        '''
        This function prepares move line of account.move related to an expense
        '''
        if self.employee_id:
            partner_id = self.employee_id.address_home_id.commercial_partner_id.id
        elif self.expense_type=='other_expense' and self.partner_id_preferred:
            partner_id=self.partner_id_preferred.id
        else:
            partner_id=False
        print "partner id==================",partner_id
        return {
            'date_maturity': line.get('date_maturity'),
            'partner_id': partner_id,
            'name': str(line['name'][:64])+'-'+str(self.description),
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
    def _move_line_get(self):
        account_move = []
        for expense in self:
            if expense.product_id:
                account = expense.product_id.product_tmpl_id._get_product_accounts()['expense']
                if not account:
                    raise UserError(_("No Expense account found for the product %s (or for it's category), please configure one.") % (expense.product_id.name))
            else:
                account = self.env['ir.property'].with_context(force_company=expense.company_id.id).get('property_account_expense_categ_id', 'product.category')
                if not account:
                    raise UserError(_('Please configure Default Expense account for Product expense: `property_account_expense_categ_id`.'))
            amt=0.0
            unit_amount_each,unit_amount_total=0.0,0.0
#            if expense.expense_details:
#                for each_exp in expense.expense_details:
#                    unit_amount_each+=each_exp.expense_id_other.unit_amount
#                unit_amount_total=unit_amount_each+expense.unit_amount
#            else:
            unit_amount_total=expense.unit_amount
#            if expense.expense_details:
#                amt=expense.tot_amount_if_other_expense+expense.total_amount
#            else:
            amt=expense.total_amount
                
            print "amtamtamtamtamtamt",amt,unit_amount_total
            move_line = {
                    'type': 'src',
                    'name': expense.name.split('\n')[0][:64],
                    'price_unit': unit_amount_total,
                    'quantity': expense.quantity,
                    'price': amt,
                    'account_id': account.id,
                    'product_id': expense.product_id.id,
                    'uom_id': expense.product_uom_id.id,
                    'analytic_account_id': expense.analytic_account_id.id,
                }
            account_move.append(move_line)
            
            # Calculate tax lines and adjust base line
            taxes = expense.tax_ids.compute_all(unit_amount_total, expense.currency_id, expense.quantity, expense.product_id)
            account_move[-1]['price'] = taxes['total_excluded']
            account_move[-1]['tax_ids'] = [(6, 0, expense.tax_ids.ids)]
            for tax in taxes['taxes']:
                account_move.append({
                    'type': 'tax',
                    'name': tax['name'],
                    'price_unit': tax['amount'],
                    'quantity': 1,
                    'price': tax['amount'],
                    'account_id': tax['account_id'] or move_line['account_id'],
                    'tax_line_id': tax['id'],
                })
        return account_move

    @api.multi
    def action_move_create(self):
        '''
        main function that is called when trying to create the accounting entries related to an expense
        '''
        
        if self.bank_journal_id_expense and self.bank_journal_id_expense.type=='bank' and self.bank_journal_id_expense.currency_id:
            print self.bank_journal_id_expense.currency_id.id,self.currency_id.id
            if self.bank_journal_id_expense.currency_id.id!=self.currency_id.id:
                raise UserError(_("Currency of Expense did not match with Bank Currency.Please check!!"))
            
        if self.payment_method and self.payment_method=='cheque':
            cheque_amt=sum(line.amount for line in self.cheque_details)
            print "total------------------",round(self.total_amount,2)-round(cheque_amt,2)
            if round(self.total_amount,2)-round(cheque_amt,2)!=0.0:
                raise UserError(_("Cheque Amount does not match with Expense Amount.Please check!!"))

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
                    if expense.expense_type=='emp_expense' and not expense.employee_id.address_home_id:
                        raise UserError(_("No Home Address found for the employee %s, please configure one.") % (expense.employee_id.name))
                    if expense.expense_type=='emp_expense':
                            print expense.employee_id.address_home_id
                            expense.partner_id_preferred=expense.employee_id.address_home_id.id
                            emp_account = expense.employee_id.address_home_id.property_account_payable_id.id
                            name=expense.employee_id.name
                    else:
                        if expense.expense_type=='other_expense' and expense.partner_id_preferred:
                            emp_account = expense.partner_id_preferred.property_account_payable_id.id
                            name=expense.partner_id_preferred.name

                        else:
                            emp_account = expense.product_id.property_account_expense_id.id
                            name=expense.product_id.name

                if not emp_account:
                    raise UserError(_("Please Define Partner for registering payment"))

                   
                print "namenamename----------------",name,emp_account
                move_line_data={
                        'type': 'dest',
                        'name':str(name)+'-'+str(expense.description) ,
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
        amt=0.0
#        if expense.expense_details:
#            amt=expense.total_amount+expense.tot_amount_if_other_expense
#        else:
        amt=expense.total_amount
            
        print "amtamtamtamtamt",amt
        pay_dict={'payment_type': 'outbound',
        'payment_method_id': self.env.ref('account.account_payment_method_manual_out').id,
        'payment_method': self.payment_method,
        'partner_type': 'supplier',
        'amount': amt,
        'expense_pay':True,
        'expense_id':expense.id,
        'currency_id': expense.currency_id.id,
        'payment_date': date.today(),
        'journal_id': expense.bank_journal_id_expense.id,
        'communication': expense.communication,
        'internal_note': expense.internal_note,
        }
#        if expense.expense_details:
#            pay_dict.update({'expense_payment_rel':[(4, [x.expense_id_other.id for x in expense.expense_details])]})
        if expense.cheque_status:
            if expense.cheque_status=='cleared':
                expense.chq_s_us='signed'
        if expense.chq_s_us:
            pay_dict.update({'chq_s_us':expense.chq_s_us})
        if expense.pay_p_up:
            pay_dict.update({'pay_p_up':expense.pay_p_up,'bank_id':expense.bank_id.id,'internal_request_tt':expense.internal_request_tt})
            if expense.uploaded_document_tt:
                pay_dict.update({'uploaded_document_tt':[(4, self.uploaded_document_tt.ids if self.uploaded_document_tt else False)]})

        if self.expense_type=='other_expense':
            if self.partner_id_preferred:
                p_id=self.partner_id_preferred
                pay_dict.update({ 'partner_id': p_id.id})
            else:
#                p_id=False
                pay_dict.update({ 'partner_id': False})
            
        else:
            p_id=self.employee_id.address_home_id
            pay_dict.update({ 'partner_id':p_id.id})

                   
        print "pay_dictpay_dictpay_dict",pay_dict
        payment = self.env['account.payment'].create(pay_dict)
        print "paymentpaymentpayment",payment,payment.partner_id
        print "jhdgijedhjewd",payment.journal_id
        payment.post()
        print "paymentpaymentpayme4444444444444444nt",payment,payment.partner_id

        if self.cheque_details:
            vals=[]
            for each in self.cheque_details:
                vals.append((0,0,{
					'partner_id':each.partner_id, 
					'journal_id':each.journal_id,
					'bank_name':each.bank_name.id,
					'partner_id':payment.partner_id.id,
					'communication': each.expense_id.communication,
					'cheque_no': each.cheque_no,
					'branch_name': each.branch_name,
					'amount': each.amount,
					'reconcile_date': each.reconcile_date,
#					'register_payment_id': each.register_payment_id,
#					'payment_id':payment.id,
					'reconcile_date': each.reconcile_date,
					'cheque_date': each.cheque_date,
					'cheque_status':each.expense_id.cheque_status
                                        }))
                each.write({'partner_id':payment.partner_id.id})
            print "valspppppppppppppppppppppppppppppppp",vals
            payment.write({'cheque_details':vals})
        if self.uploaded_document:
            payment.write({'uploaded_document': self.uploaded_document})

        move_line_id=self.env['account.move.line'].search([('payment_id','=',payment.id)])
        move_pay=move_line_id[0].move_id
        expense.write({'account_pay_id': move_pay.id,'payment_id':payment.id,'pay_date':date.today()})
#        if expense.expense_details:
#            for each in expense.expense_details:
#                each.expense_id_other.write({'uploaded_document':expense.uploaded_document if expense.uploaded_document else False,'account_pay_id': move_pay.id,'payment_id':payment.id,'pay_date':date.today(),'communication':expense.communication,'internal_note':expense.internal_note,'account_move_id':expense.account_move_id.id,'bank_journal_id_expense':expense.bank_journal_id_expense.id})
#                each.expense_id_other.paid_expenses()
        expense.paid_expenses()

        return True
    
    @api.multi
    def send_for_special_approval(self):
            self.write({'special_approval':False})
            group_id = self.env['ir.model.data'].get_object_reference('aalmir_custom_expense','restricted_hr_expense_grant_for_no_ac')[1]
            users=self.env['res.groups'].search([('id', '=',group_id)]).users  
            self.write({'approval_by':users[0].id})
    @api.multi
    def approve_expense_custom(self):
        group_id = self.env['ir.model.data'].get_object_reference('aalmir_custom_expense','restricted_hr_expense_grant_for_no_ac')[1]
        users=self.env['res.groups'].search([('id', '=',group_id)]).users
        print "usersusersusers",users
        if self._uid in users.ids:
            self.write({'state': 'approve','approved_by':self._uid})
            return True

        if self.approve_conf_exist==False:
            non_approval=self.env['approval.config'].search([('product_type','=',self.type_product.id)])
            if non_approval:
                line_id=self.env['approval.config.line'].search([('approve_id','=',non_approval.id),('approval_by','=',self._uid)])
            thirty_days_from_now=date.today()+timedelta(days=30)
            print "thirty_days_from_nowthirty_days_from_now",thirty_days_from_now
            expense_ids=self.search([('state','not in',['draft','submit','cancel']),('id','!=',self.id),('type_product','=',self.type_product.id),('date','<=',thirty_days_from_now)])
            amount_total_exp=0.0
            if expense_ids:
                for each in expense_ids:
                    amount_total_exp+=each.total_amount
            print "jhjhjkjhkjnkj-------",amount_total_exp
            if amount_total_exp and (amount_total_exp+self.total_amount>line_id.monthly_amt):
                self.write({'special_approval':True})
                self.env.cr.commit()
#            else:
#                self.write({'state': 'approve','approved_by':self._uid})
            
            if amount_total_exp and (amount_total_exp+self.total_amount>line_id.monthly_amt):
                raise UserError(_("Expense Amount including current expenses crosses the limit of montly expense approval which is %s.") % (line_id.monthly_amt))
        else:
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
#    
    
class BankChequeDetailsExpense(models.Model):
    '''to store cheque details against bank'''
    _name = "bank.cheque.details.expense"
    
    expense_id = fields.Many2one('hr.expense','Payment Name')
    journal_id = fields.Many2one('account.journal',related="expense_id.bank_journal_id_expense",string='Journal')
    partner_id = fields.Many2one('res.partner',related="expense_id.partner_id_preferred",string='Supplier/Customer',store=True)
    bank_name = fields.Many2one('cheque.bank.name','Bank Name')
    communication = fields.Char(related="expense_id.communication",string='Internal Note')
    #bank_id = fields.Many2one('res.partner.bank', 'Bank Name')
    cheque_no = fields.Char('Cheque No.')
    cheque_date = fields.Date('Cheque Date')
    branch_name = fields.Char('Bank Branch Name')
    amount = fields.Float('Amount',digits=dp.get_precision('Account'))
    reconcile_date = fields.Date('Reconcile Date')
    register_payment_id=fields.Many2one('account.register.payments')
    cheque_status=fields.Selection([('not_clear','Not Cleared'),('cleared','Cleared')],related="expense_id.cheque_status", string='Cheque Status',copy=False)
    
    		   			   			
class PaymentExpenseDetails(models.Model):
    '''to store cheque details against bank'''
    _name = "payment.expense.line"
    
    expense_id_other = fields.Many2one('hr.expense','Expense')
    expense_id = fields.Many2one('hr.expense','Expense')
    amount = fields.Float('Amount',digits=dp.get_precision('Account'))
    
    		   			   			
    @api.onchange('expense_id_other')
    def expense_id_onchange(self):
    	if self.expense_id_other:
            if self.expense_id_other.partner_id_preferred.id!=self.expense_id.partner_id_preferred.id:
                self.expense_id_other=False
                return {'warning': {'title': "Invalid", 'message': "You cannot merge expenses of two different partners!!"}}
            if self.expense_id_other.id!=self.expense_id.id:
                self.expense_id_other=False
                return {'warning': {'title': "Invalid", 'message': "You cannot select same expense to pay as the main expense is also same!!"}}
            self.amount=self.expense_id_other.total_amount
        return {'domain': {'expense_id_other': [('partner_id_preferred', '=', self.expense_id.partner_id_preferred.id)]}}


    @api.onchange('amount')
    def amount_onchange(self):
    	if self.amount and self.amount!=self.expense_id_other.total_amount:
            self.amount=self.expense_id_other.total_amount
            return {'warning': {'title': "Invalid", 'message': "You cannot change approved the expense amount!!!"}}
