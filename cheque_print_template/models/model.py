from openerp import api, fields, models, _
from openerp.tools import amount_to_text_en, float_round
import math


class BankChequeDetials(models.Model):
    _inherit = 'bank.cheque.details'
    
    check_amount_in_words = fields.Char(string="Amount in Words")

    @api.onchange('amount')
    def _onchange_amount(self):
        print "changei in amount called------------------------",self.amount
        # TODO: merge, refactor and complete the amount_to_text and amount_to_text_en classes
        check_amount_in_words = amount_to_text_en.amount_to_text(math.floor(self.amount), lang='en', currency='')
        check_amount_in_words = check_amount_in_words.replace(' and Zero Cent', '') # Ugh
        decimals = self.amount % 1
        if decimals >= 10**-2:
            check_amount_in_words += _(' and %s/100 Fils') % str(int(round(float_round(decimals*100, precision_rounding=1))))
        self.check_amount_in_words = check_amount_in_words+' '+'Only'
        print "check_amount_in_words--------------",self.check_amount_in_words


    def split_date(self):
        date_list=[]
        if self.payment_date:
#            dates=self.payment_date.replace('-')
#            for date in dates:
            pay_date = self.change_date_format(self.payment_date)
            date_list.append(pay_date)
        return date_list
    
    @api.multi
    def action_cheque_print(self):
        self.ensure_one()
        self._onchange_amount()
        return self.env['report'].get_action(self, 'cheque_print_template.report_cheque_print_template')


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    account_pay_cheque=fields.Boolean('A/c Pay Cheque')