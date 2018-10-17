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
    
    name = fields.Char(string='Expense Description', readonly=True,states={'draft': [('readonly', False)]})


    employee_id = fields.Many2one('hr.employee', string="Employee")
    product_uom_id = fields.Many2one('product.uom', string='Unit of Measure', required=True)

    refuse_reason = fields.Char(string='Refuse Reason',track_visibility='always' )

    partner_id_preferred = fields.Many2one('res.partner', 'Partner')
    expense_type = fields.Selection([("emp_expense", "Employee Expense"), ("other_expense", "Other Expense")], string="Expense Type")
    approval_status = fields.Selection([("app_required", "Approval Required"), ("app_not_required", "No Approval")],default='app_not_required', string="Approval Status")

    internal_note=fields.Text('Remarks on Receipt')
    communication = fields.Char(string='Internal Note')

    uploaded_document = fields.Binary(string='Uploaded Document', default=False , attachment=True)
    uploaded_document_bill = fields.Binary(string='Uploaded Bills', default=False , attachment=True)
    doc_name=fields.Char()
    payment_method = fields.Selection([('neft', 'Fund Transfer'),
				    ('cheque', 'Cheque')],string='Type')
				    
    cheque_details = fields.One2many('bank.cheque.details','payment_id','Cheque Details')
    approval_by = fields.Many2one('res.users', 'Approval By')
    approved_by = fields.Many2one('res.users', 'Approved By')
    user_id = fields.Many2one('res.users', 'User')
    cheque_status=fields.Selection([('not_clear','Not Cleared'),('cleared','Cleared')], string='Cheque Status')
    
    
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
        if self.partner_id_preferred and self.expense_type=='other_expense':
            self.write({'employee_id':False})
            non_approval=self.env['approval.config.line'].search([('partner_id','=',self.partner_id_preferred.id)])
            if non_approval:
                limit_amt=non_approval.approve_amount
                if self.total_amount>limit_amt:
                    self.write({'approval_status':'app_required','approval_by':non_approval.approval_by.id,'user_id':self._uid,'state': 'submit'})
                else:
                    self.write({'state': 'approve'})
            else:
                self.write({'state': 'submit','approval_status':'app_not_required'})
        else:
            self.write({'state': 'submit','approval_status':'app_not_required'})
        return True

    @api.multi
    def refuse_expenses(self, reason):
        result = super(HrExpense, self).refuse_expenses(reason)

        self.write({'refuse_reason': reason})
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
            jrn = expense.bank_journal_id if expense.payment_mode == 'company_account' else expense.journal_id
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
                    if not expense.bank_journal_id.default_credit_account_id:
                        raise UserError(_("No credit account found for the %s journal, please configure one.") % (expense.bank_journal_id.name))
                    emp_account = expense.bank_journal_id.default_credit_account_id.id
                else:
                    move_line_data={}
                    if not expense.employee_id.address_home_id and expense.expense_type=='employee_expense':
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
                            emp_account = expense.product_id.property_account_payable_id.id
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
        return True
    
    @api.multi
    def approve_expenses(self):
        self.write({'state': 'approve','approved_by':self._uid})

    
    @api.onchange('pay_type')
    def pay_type_onchange(self):
    	if self.pay_type != 'bank':
    		self.payment_method=False
                
    @api.onchange('product_id')
    def _onchange_product_id(self):
        result = super(HrExpense, self)._onchange_product_id()

        if self.product_id:
            if self.product_id.product_tmpl_id.partner_id_preferred:
                self.partner_id_preferred = self.product_id.product_tmpl_id.partner_id_preferred.id
            print "uom-----------------",self.product_id.product_tmpl_id.uom_id.id
            self.product_uom_id= self.product_id.uom_id.id
        return result