from openerp import fields, models ,api, _
from openerp.exceptions import UserError, ValidationError
import logging
import datetime
from dateutil.relativedelta import *
from datetime import date,datetime,timedelta
import calendar
import openerp.addons.decimal_precision as dp
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.misc import formatLang
from urllib import urlencode
from urlparse import urljoin
_logger = logging.getLogger(__name__)

class account_journal(models.Model):
    _inherit = "account.journal"
#CH_N105 >>inherite field and add request type
    type = fields.Selection(selection_add=[('request', 'Request')])
    
    @api.multi
    def calculate_outstanding_balance(self):
    	account_move = self.env['account.move.line']
    	for rec in self:
    		account_ids = tuple(filter(None, [self.default_debit_account_id.id, self.default_credit_account_id.id]))
		opeing_records=account_move.search([('account_id','in',account_ids),
							('date','<=',datetime.today()),
							('move_id.state','=','posted')],order='date asc')
		opening_bal = unreconcile = pro_balance = 0.0
		# code to find transaction records >>>
		cheque_ids = []
		last_day = date.today().replace(day=calendar.monthrange(date.today().year, date.today().month)[1])
		last_transaction = opeing_records[-1].date if opeing_records else str(date.today())
		for records in opeing_records:
			flag=True
			for chq in records.payment_id.cheque_details:
				flag=False
				if chq.id in cheque_ids:
					continue
				cheque_ids.append(chq.id)
				if chq.reconcile_date and chq.reconcile_date <= str(datetime.today()):
					opening_bal += -chq.amount if records.credit else chq.amount
					if last_transaction < chq.reconcile_date:
						last_transaction = chq.reconcile_date
				if chq.cheque_date < str(last_day):
					# projected balance
					if records.payment_id.payment_type  == 'inbound':
						pro_balance += chq.amount
					elif records.payment_id.payment_type  == 'transfer':
						pro_balance += -chq.amount if records.credit else chq.amount
					else:
						pro_balance -= chq.amount
			if rec.currency_id and flag:
				pro_balance += records.amount_currency
				opening_bal += records.amount_currency
			
			elif flag:
				pro_balance += -records.credit or records.debit
				opening_bal += -records.credit or records.debit
			print ",,,,,",records.date,records.credit , records.debit ,opening_bal , records.amount_currency 
		print ",,,,,",opening_bal,pro_balance,last_transaction
		return opening_bal,pro_balance,last_transaction
    #            to retrive on account click to move lines on bank and cash type
    @api.multi
    def open_action(self):
        print "selfkjdshkjshkjdshnkjsj",self._context
        """return action based on type for related journals"""
        action_name = self._context.get('action_name', False)
        if not action_name:
            if self._context.get('acc_wise_journal_data') and self.type == 'bank':
                action_name = 'action_account_moves_acc'

            elif self.type == 'bank':
#                action_name = 'action_bank_statement_tree'
                action_name = 'action_move_journal_line'
            elif self.type == 'cash':
                action_name = 'action_move_journal_line'
#                action_name = 'action_view_bank_statement_tree'
            elif self.type == 'sale':
                action_name = 'action_invoice_tree1'
            elif self.type == 'purchase':
                action_name = 'action_invoice_tree2'
            else:
                action_name = 'action_move_journal_line'

        _journal_invoice_type_map = {
            ('sale', None): 'out_invoice',
            ('purchase', None): 'in_invoice',
            ('sale', 'refund'): 'out_refund',
            ('purchase', 'refund'): 'in_refund',
            ('bank', None): 'bank',
            ('cash', None): 'cash',
            ('general', None): 'general',
        }
        invoice_type = _journal_invoice_type_map[(self.type, self._context.get('invoice_type'))]
        print "invoice_type--------",invoice_type
        ctx = self._context.copy()
        ctx.pop('group_by', None)
        ctx.update({
            'journal_type': self.type,
            'default_journal_id': self.id,
            'search_default_journal_id': self.id,
            'default_type': invoice_type,
            'type': invoice_type
        })
        print "ctx final=====================",ctx
        ir_model_obj = self.pool['ir.model.data']
        if self._context.get('acc_wise_journal_data') and self.type == 'bank':
            model, action_id = ir_model_obj.get_object_reference(self._cr, self._uid, 'api_dashboard', action_name)
        else:
            model, action_id = ir_model_obj.get_object_reference(self._cr, self._uid, 'account', action_name)
        print "model and action idi----1234------------",model,action_id
        action = self.pool[model].read(self._cr, self._uid, [action_id], context=self._context)[0]
        if self._context.get('acc_wise_journal_data') and self.type == 'bank':
            action['domain']=[('account_id','=',self.default_debit_account_id.id)]
            ctx.update({'group_by': 'account_id'})

        elif ctx.get('search_default_rejected'):
            action['domain'] = [('state','=','rejected')]
        elif ctx.get('search_default_waiting_approval'):
            action['domain'] = [('state','=','waiting_approval')]

        else:
            action['domain'] = self._context.get('use_domain', [])
        print "domain=======================",action
        action['context'] = ctx

        return action

	
    @api.multi
    def get_journal_dashboard_datas(self):
        currency = self.currency_id or self.company_id.currency_id
        number_to_reconcile = last_balance = account_sum = unreconcile= 0 
        ac_bnk_stmt = []
        title = ''
        invoice_wait=0
        number_draft = number_waiting =number_rejected=no_waiting_approval= number_late = sum_draft = sum_waiting=sum_rejected=sum_waiting_approval = sum_late = 0
        unclear_cheque = todays_cheque = tomorrows_cheque = future_cheque = pro_balance = 0
        p_cnt = t_cnt = tm_cnt = f_cnt = chq_cnt= 0
        pre_chq = t_chq = tm_chq = f_chq = 0
        last_transaction =False
        if self.type in ['bank', 'cash']:
            last_bank_stmt = self.env['account.bank.statement'].search([('journal_id', 'in', self.ids)], order="date desc, id desc", limit=1)
            last_balance = last_bank_stmt and last_bank_stmt[0].balance_end or 0
            #Get the number of items to reconcile for that bank journal
            self.env.cr.execute("""SELECT COUNT(DISTINCT(statement_line_id)) 
                        FROM account_move where statement_line_id 
                        IN (SELECT line.id 
                            FROM account_bank_statement_line AS line 
                            LEFT JOIN account_bank_statement AS st 
                            ON line.statement_id = st.id 
                            WHERE st.journal_id IN %s and st.state = 'open')""", (tuple(self.ids),))
            already_reconciled = self.env.cr.fetchone()[0]
            self.env.cr.execute("""SELECT COUNT(line.id) 
                            FROM account_bank_statement_line AS line 
                            LEFT JOIN account_bank_statement AS st 
                            ON line.statement_id = st.id 
                            WHERE st.journal_id IN %s and st.state = 'open'""", (tuple(self.ids),))
            all_lines = self.env.cr.fetchone()[0]
            number_to_reconcile = all_lines - already_reconciled
            # optimization to read sum of balance from account_move_line
            account_ids = tuple(filter(None, [self.default_debit_account_id.id, self.default_credit_account_id.id]))
            if account_ids:
                #amount_field = 'balance' if not self.currency_id else 'amount_currency'
                #query = """SELECT sum(%s) FROM account_move_line WHERE account_id in %%s;""" % (amount_field,)
                #self.env.cr.execute(query, (account_ids,))
                #query_results = self.env.cr.dictfetchall()
                #if query_results and query_results[0].get('sum') != None:
                #    account_sum = query_results[0].get('sum')
                account_sum,pro_balance,last_transaction = self.calculate_outstanding_balance()
                #self.env.cr.execute("select getjournalbalance(%s)"%self.id)
                #query_results = self.env.cr.fetchone()
		#if query_results and query_results['getjournalbalance']:
                #	account_sum,unreconcile = tuple(query_results['getjournalbalance'])
            cheque_ids = self.env['bank.cheque.details'].search(['|',('payment_id.journal_id','=',self.id),
            							('payment_id.destination_journal_id','=',self.id),
            							('reconcile_date','=',False),
            							('payment_id.state','=','posted')])
            for line in cheque_ids :
            	if line.payment_id.payment_type in ('outbound','transfer') and line.payment_id.journal_id.id==self.id:
			if line.cheque_date <= str(date.today()):
				p_cnt += 1
				unclear_cheque += line.amount
			elif line.cheque_date == str(date.today()):
				t_cnt += 1
				todays_cheque += line.amount
			elif line.cheque_date == str(date.today()+timedelta(days=1)):
				tm_cnt += 1
				tomorrows_cheque += line.amount
			else:
				f_cnt += 1
				future_cheque += line.amount
		else:
			chq_cnt += 1
			unreconcile += line.amount
	
            if unclear_cheque and account_sum < (unclear_cheque+todays_cheque) :
	    	pre_chq = 1
            #if todays_cheque and account_sum < (unclear_cheque+todays_cheque):
	    #	t_chq = 1
    	    if tomorrows_cheque and account_sum < (unclear_cheque + todays_cheque + tomorrows_cheque):
    	    	tm_chq = 1
    	    if future_cheque and account_sum < (unclear_cheque + todays_cheque + tomorrows_cheque + future_cheque):
    	    	f_chq = 1
    	    
        #TODO need to check if all invoices are in the same currency than the journal!!!!
        elif self.type in ['sale', 'purchase']:
            title = _('Bills to pay') if self.type == 'purchase' else _('Invoices owed to you')
            # optimization to find total and sum of invoice that are in draft, open state
            query = """SELECT state, amount_total,currency_id AS currency,residual_company_signed FROM account_invoice WHERE journal_id = %s AND state NOT IN ('paid', 'cancel');"""
            self.env.cr.execute(query, (self.id,))
            query_results = self.env.cr.dictfetchall()
            today = datetime.today()
            query = """SELECT amount_total, currency_id AS currency FROM account_invoice WHERE journal_id = %s AND date < %s AND state = 'open';"""
            self.env.cr.execute(query, (self.id, today))
            late_query_results = self.env.cr.dictfetchall()
            sum_draft = 0.0
            sum_rejected = 0.0
            sum_waiting_approval = 0.0
            number_draft = 0
            number_waiting = 0
            number_rejected = 0
            no_waiting_approval=0
            for result in query_results:
                cur = self.env['res.currency'].browse(result.get('currency'))
                if result.get('state') in ['open','draft']:
                   if  fields.Date.context_today(self) < result.get('payment_date_inv'):
                       invoice_wait +=1
                if result.get('state') in ['draft', 'proforma', 'proforma2']:
                    number_draft += 1
                    sum_draft += cur.compute(result.get('amount_total'), currency)
                   
                elif result.get('state') == 'open':
                    number_waiting += 1
                    sum_waiting += result.get('residual_company_signed') #cur.compute(result.get('amount_total'), currency)
                elif result.get('state') == 'rejected':
                    number_rejected += 1
                    sum_rejected += cur.compute(result.get('amount_total'), currency) #cur.compute(result.get('amount_total'), currency)
                    print "number_rejectedv",number_rejected,sum_rejected
                elif result.get('state') == 'waiting_approval':
                    no_waiting_approval += 1
                    sum_waiting_approval += cur.compute(result.get('amount_total'), currency) #cur.compute(result.get('amount_total'), currency)
                    print "no_waiting_approval",no_waiting_approval,sum_waiting_approval
            sum_late = 0.0
            number_late = 0
            for result in late_query_results:
                cur = self.env['res.currency'].browse(result.get('currency'))
                number_late += 1
                sum_late += cur.compute(result.get('amount_total'), currency)
	requests=[]
        #credit=self.env['res.partner.credit'].search([('state','=','request')])
       # if credit:
        #   credit=len(credit)
        if self.user_has_groups('base.group_system'): 
            requests = self.env['account.payment.term.request'].search([('state','=','requested'),('customer_id.customer','=',True)])
        elif self.user_has_groups('account.group_account_user'):
            requests = self.env['account.payment.term.request'].search([('state','=','requested'), ('accountant_id', 'in', [False, self.env.uid]),('customer_id.customer','=',True)])
	num_req = '0'
        if requests:
            num_req = len(requests)

        sup_request=[]
        if self.user_has_groups('base.group_system'): 
            sup_request = self.env['account.payment.term.request'].search([('state','=','requested'),('customer_id.supplier','=',True)])
        elif self.user_has_groups('account.group_account_user'):
            sup_request = self.env['account.payment.term.request'].search([('state','=','requested'), ('accountant_id', 'in', [False, self.env.uid]),('customer_id.supplier','=',True)])
	num_req_sup = '0'
        if sup_request:
            num_req_sup = len(sup_request)
	credt_req=0
	credt = self.env['res.partner.credit'].search([('state','=','request')])
	if credt:
                credt_req = len(credt)
        pending_rqst=self.env['purchase.order'].search([('state','=','awaiting')])
        lst_rqst=[]
        for pend in pending_rqst:
            if pend.management_user.id == self.env.user.id and not pend.approve_mgnt: 
               lst_rqst.append(pend.id)
            if pend.procurement_user.id == self.env.user.id and not pend.approve_prq: 
               lst_rqst.append(pend.id)
            
            if pend.inventory_user.id == self.env.user.id and not pend.approve_inv: 
               lst_rqst.append(pend.id)
        advance_payment=self.env['account.payment'].search([('partner_type', '=', 'customer'),('sale_id','!=',False),('state','=','draft')])
        lines=[]
        not_match="select order_id  from sale_order_line where qty_delivered != qty_invoiced and state ='sale'"
        self._cr.execute(not_match)
        lines=[i[0] for i in self._cr.fetchall()]

        return {
            'number_to_reconcile': number_to_reconcile,
            'account_balance': formatLang(self.env, account_sum, currency_obj=self.currency_id or self.company_id.currency_id),
            'last_balance': formatLang(self.env, last_balance, currency_obj=self.currency_id or self.company_id.currency_id),
            'number_draft': number_draft,
            'number_waiting': number_waiting,
            'number_rejected': number_rejected,
            'no_waiting_approval': no_waiting_approval,
            'number_late': number_late,
            'sum_draft': formatLang(self.env, sum_draft or 0.0, currency_obj=self.currency_id or self.company_id.currency_id),
            'sum_rejected': formatLang(self.env, sum_rejected or 0.0, currency_obj=self.currency_id or self.company_id.currency_id),
            'sum_waiting_approval': formatLang(self.env, sum_waiting_approval or 0.0, currency_obj=self.currency_id or self.company_id.currency_id),
            'sum_waiting': formatLang(self.env, sum_waiting or 0.0, currency_obj=self.currency_id or self.company_id.currency_id),
            'sum_late': formatLang(self.env, sum_late or 0.0, currency_obj=self.currency_id or self.company_id.currency_id),
            'currency_id': self.currency_id and self.currency_id.id or self.company_id.currency_id.id,
            'bank_statements_source': self.bank_statements_source,
            'title': title, 
            'num_req' : num_req,
            'invoice_wait':invoice_wait,
            'num_req_sup':num_req_sup,
	    'credit_request':credt_req,
            'pending_rqst':len(lst_rqst),
            'advance_payment':len(advance_payment),
            'not_match':len(set(lines)),
            'unclear_cheque': formatLang(self.env, (unclear_cheque+todays_cheque), currency_obj=self.currency_id or self.company_id.currency_id),
           # 'todays_cheque': formatLang(self.env, todays_cheque, currency_obj=self.currency_id or self.company_id.currency_id) ,
            'tomorrows_cheque': formatLang(self.env, tomorrows_cheque, currency_obj=self.currency_id or self.company_id.currency_id) ,
            'future_cheque':formatLang(self.env, future_cheque, currency_obj=self.currency_id or self.company_id.currency_id) ,
            'unreconcile_data':formatLang(self.env, unreconcile, currency_obj=self.currency_id or self.company_id.currency_id),
            #'unreconcile':unreconcile,
            'chq_cnt':chq_cnt,
            'erp_balance':formatLang(self.env, account_sum-(unclear_cheque+todays_cheque), currency_obj=self.currency_id or self.company_id.currency_id),
            'color':0,
            'total_cheque':formatLang(self.env, (unclear_cheque+todays_cheque+tomorrows_cheque+future_cheque), currency_obj=self.currency_id or self.company_id.currency_id),
            'total_chq_cnt':(p_cnt+ t_cnt+ tm_cnt + f_cnt),
            'pro_balance':formatLang(self.env,pro_balance, currency_obj=self.currency_id or self.company_id.currency_id),
            'pre_chq':pre_chq,
            #'t_chq':t_chq,
            'tm_chq':tm_chq,
            'f_chq':f_chq,
            'last_transaction':last_transaction,
        }
    
    @api.multi
    def open_cheque_payments(self):
	cheque_ids=[]
	cheque_obj = self.env['bank.cheque.details']
	name = ''
	domain = [('reconcile_date','=',False),
		  ('payment_id.state','=','posted')]
        if self._context.get('type') == 'unclear':
		domain.extend([('payment_id.journal_id','=',self.id),
				('cheque_date','<=',datetime.today()),
				('payment_id.payment_type','!=','inbound')])
		name = 'Current UnReconcile Cheques'
	#elif self._context.get('type') == 'todays':
	#	domain.extend([('cheque_date','=',datetime.today()),
	#			('payment_id.journal_id','=',self.id),
	#			('payment_id.payment_type','!=','inbound')])
	#	name = "Today's Cheque to be clear"
	elif self._context.get('type') == 'tomorrow':
		domain.extend([('cheque_date','=',datetime.today()+timedelta(days=1)),
				('payment_id.journal_id','=',self.id),
				('payment_id.payment_type','!=','inbound')])
		name = "Tomorrow's Cheque Details"
	elif self._context.get('type') == 'future':
		domain.extend([('cheque_date','>',datetime.today()+timedelta(days=1)),
				('payment_id.journal_id','=',self.id),
				('payment_id.payment_type','!=','inbound')])
		name = "Future Cheque Details"
	elif self._context.get('type') == 'un_reconcile':
		domain.extend(['|','&',('payment_id.journal_id','=',self.id),('payment_id.payment_type','=','inbound'),
				('payment_id.destination_journal_id','=',self.id),
	      			])
		name = "Unreconcile Customer Cheque Details"
	elif self._context.get('type') == 'total_chq':
		domain.extend([('payment_id.payment_type','!=','inbound'),('payment_id.journal_id','=',self.id)])
		name = "Total Cheques"
	cheque_ids = cheque_obj.search(domain)
	tree_id=self.env.ref('api_account.account_cheque_tree_view').id
        return {
            'name': name,
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'bank.cheque.details',
	    'views': [(tree_id, 'tree')],
            'type': 'ir.actions.act_window',
            'domain' : [('id', 'in',cheque_ids._ids)],
        }
        
    @api.multi
    def open_action_payment_term(self):
        domain=[]
	requests=[]
        if self._context.get('type') == 'customer':
		if self.user_has_groups(' base.group_system'): 
		    requests = self.env['account.payment.term.request'].search([('customer_id.customer','=',True)])
		elif self.user_has_groups('account.group_account_user'):
		    requests = self.env['account.payment.term.request'].search([('accountant_id', 'in', [False, self.env.uid]),('customer_id.customer','=',True)])
        if self._context.get('type') == 'supplier':
		if self.user_has_groups(' base.group_system'): 
		    requests = self.env['account.payment.term.request'].search([('customer_id.supplier','=',True)])
		elif self.user_has_groups('account.group_account_user'):
		    requests = self.env['account.payment.term.request'].search([('accountant_id', 'in', [False, self.env.uid]),('customer_id.supplier','=',True)])
	tree_id=self.env.ref('gt_order_mgnt.account_payment_term_requested_tree_view').id
	form_id=self.env.ref('gt_order_mgnt.account_payment_term_requested_form_view').id,
        return {
            'name': 'Requested Payment Term',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'account.payment.term.request',
	    'views': [(tree_id, 'tree'), (form_id, 'form')],
            'type': 'ir.actions.act_window',
            'domain' : [('id', 'in', requests._ids)],
            'context' : {'search_default_requested' : 1}
        }
   
    @api.multi
    def open_action_invoice_wait(self):
        today_date=fields.Date.context_today(self)
        requests = self.env['account.invoice'].search([('journal_id.type','=','sale'),('state','in',['open','draft'])])
        for req in requests:
            if today_date < req.payment_date_inv: 
               pass
             
        domain=[('journal_id.type','=','sale'),('payment_date_inv','>',today_date)]
        if self.user_has_groups(' base.group_system'): 
            requests = self.env['account.invoice'].search([])
        elif self.user_has_groups('account.group_account_user'):
            requests = self.env['account.invoice'].search([('accountant_id', 'in', [False, self.env.uid])])
        return {
            'name': 'Requested Awaiting Invoice ',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'account.invoice',
            'view_id': self.env.ref('account.invoice_tree').id,
            'type': 'ir.actions.act_window',
            'domain' :[('journal_id.type','=','sale'),('payment_date_inv','>',today_date)],
            'context' : {'search_default_requested' : 1}
        }

    @api.multi
    def open_action_credit_request(self):
        tree_id=form_id=model=name=''
        domain=[]
        context=''
        if self._context.get('customer'):
           list_ids=[]
	   for rec in self.env['res.partner.credit'].search([('state', '=','request')]):
		list_ids.append(rec.partner_id.id)
           domain=[('id','in',list_ids)]
	   tree_id=self.env.ref('gt_order_mgnt.customer_credit_tree_ac').id #customer_credit_tree').id
	   form_id=self.env.ref('gt_order_mgnt.customer_credit_form_ac').id #customer_credit_form').id
           model='res.partner'
           name='Requested Customer Credit'
        if self._context.get('payment'):
	   tree_id=self.env.ref('account.view_account_payment_tree').id #customer_credit_tree').id
	   form_id=self.env.ref('account.view_account_payment_form').id #customer_credit_form').id
           domain=[('partner_type', '=', 'customer'),('sale_id','!=',False),('state','=','draft')]
           model='account.payment'
           name='Sale Order Advance Payment list'

	if self._context.get('not_match'):
           lines=[]
	   not_match="select order_id  from sale_order_line where qty_delivered != qty_invoiced and state ='sale'"
           self._cr.execute(not_match)
           lines=[i[0] for i in self._cr.fetchall()]
           domain=[('id', 'in', lines)]	
           tree_id = self.env.ref('sale.view_order_tree').id
           form_id = self.env.ref('sale.view_order_form').id
           model='sale.order'
           name='Sale Order in which DO qty is not equal to invocie qty'
           context={'show_sale':True}
        return {
            'name':name ,
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': model,
	    'views': [(tree_id, 'tree'), (form_id, 'form')],
            'type': 'ir.actions.act_window',
            'domain' : domain,
            'context':context
        }

    @api.multi
    def open_po_request(self):
	if self._context.get('request_pending'):
                pending_rqst=self.env['purchase.order'].search([('state','=','awaiting')])
		lst_rqst=[]
		for pend in pending_rqst:
		    if pend.management_user.id == self.env.user.id and not pend.approve_mgnt: 
		       lst_rqst.append(pend.id)
		    if pend.procurement_user.id == self.env.user.id and not pend.approve_prq: 
		       lst_rqst.append(pend.id)
		    
		    if pend.inventory_user.id == self.env.user.id and not pend.approve_inv: 
		       lst_rqst.append(pend.id)
		domain=[('id','in',lst_rqst)]

		_name='Pending Purchase Approval'
		model='purchase.order'
		rq_tree = self.env.ref('purchase.purchase_order_tree', False)
                rq_form =self.env.ref('purchase.purchase_order_form',False)
        if rq_tree:
            views=[]
            if rq_tree and rq_form:
               views=[(rq_tree.id, 'tree'),(rq_form.id, 'form')]
            else:
               views=[(rq_tree.id, 'tree')]
            return {
		'name':_name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': model,
		'views': views,
                'view_id': rq_tree.id,
                'target': 'current',
		'domain':domain,
            }

