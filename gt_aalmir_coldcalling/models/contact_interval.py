from openerp.osv import fields,osv
from openerp.tools.translate import _
from datetime import datetime,timedelta, date
class CrmLead(osv.osv):
    _inherit = 'crm.lead'
    def send_interval_email(self, cr, uid, ids=None, context=None):
        lead_obj = self.pool.get('crm.lead')
        mail_mail = self.pool.get('mail.mail')
        sale_users = self.pool.get('res.users')
        sale_order=self.pool.get('sale.order')        
        call_history=self.pool.get('crm.coldcalling.history') 
        users=sale_users.search(cr, uid, [('salesperson_bool', '=', True)])
        d1=datetime.now().strftime('%Y-%m-%d %H:%M:%S') ;
        date_now_d = datetime.strptime(d1, "%Y-%m-%d %H:%M:%S").strftime('%d') 
        date_now_m = datetime.strptime(d1, "%Y-%m-%d %H:%M:%S").strftime('%m')  
        date_now_y = datetime.strptime(d1, "%Y-%m-%d %H:%M:%S").strftime('%y') 
        mail_ids = [] 
        for sale in sale_users.browse(cr, uid, users):
            
            lead_state=lead_obj.search(cr, uid, [('stage_2','in',['not_contacted','contacted']),('user_id', '=',sale.id)])            
            lead_inquiries=lead_obj.search(cr,uid, ['|', ('type','=','lead'), ('type','=',False), ('stage_id','!=', False), ('stage_2','in',[False,'qualified']),('user_id', '=',sale.id)])
            opportunity=lead_obj.search(cr, uid, [('type','=','opportunity'),('user_id', '=',sale.id)])
            sale_search=sale_order.search(cr, uid, [('state', 'in',('sale','done')),('user_id', '=',sale.id)])
            interval_lead=lead_obj.search(cr, uid, [('cont_bool','=',True),('stage_2','in',['not_contacted','contacted']), ('user_id', '=',sale.id)])
            create_lead= lead_obj.search(cr, uid, [('stage_2','in',['not_contacted','contacted']),('user_id', '=',sale.id)])
            big_time_id = lead_obj.search(cr, uid, [('stage_2','in',['not_contacted','contacted']),('user_id', '=',sale.id)])
            today_contact_lead = lead_obj.search(cr, uid, [('stage_2','in',['contacted']),('user_id', '=',sale.id)])
            lead_qualified=lead_obj.search(cr, uid, [('stage_2','in',['qualified']),('user_id', '=',sale.id)])
            lead_disqualified=lead_obj.search(cr, uid, [('stage_2','in',['disqualified']),('user_id', '=',sale.id)]) 
            big_len=0
            today_contact_lead_len=0
            subject = str(sale.name)+" Daily Report"
            email_from =sale.login
            email_cc=sale.sale_team_id.user_id.login if sale.sale_team_id else ''
            footer = _("Kind regards.\n") 
            footer +=sale.company_id.name

            salesperson_target=sale.salesperson_target
            monthly_target = sale.monthly_target
            currency_name = sale.company_id.currency_id.name
            today_target_body ='<table style="width: 100%; height: 15%;font-family:arial;""><col width="150"><col width="270"><col width="250"><tr><td colspan=4 align="center"><b><u>Target Report Summary</u></b></td></tr>'

            #### Todays qualified lead from coldcalling qualified_date
            today_progress_body='<table style="width: 100%; height: 15%;font-family:arial;""><col width="270"><col width="200"><col width="150"><tr><td colspan=4 align="center"><b><u>Progress Report Sumnmary</u></b></td></tr>'
            qualified_len=0
            for qualify in lead_obj.browse(cr, uid, lead_qualified):
                if qualify.qualified_date:
                   qualify_create_d = datetime.strptime(qualify.qualified_date,'%Y-%m-%d %H:%M:%S').strftime('%d')
                   qualify_create_m= datetime.strptime(qualify.qualified_date,'%Y-%m-%d %H:%M:%S').strftime('%m')
                   qualify_create_y = datetime.strptime(qualify.qualified_date,'%Y-%m-%d %H:%M:%S').strftime('%y')
                   if qualify_create_d == date_now_d and qualify_create_m == date_now_m and qualify_create_y ==date_now_y:
                      qualified_len = qualified_len +1
            
            ##### Todays Inquiries 
            #for inquiries in lead_obj.browse(cr, uid, lead_inquiries):
            #    date_create_d = datetime.strptime(inquiries.create_date,'%Y-%m-%d %H:%M:%S').strftime('%d')
            #    date_create_m= datetime.strptime(inquiries.create_date,'%Y-%m-%d %H:%M:%S').strftime('%m')
            #    date_create_y = datetime.strptime(inquiries.create_date,'%Y-%m-%d %H:%M:%S').strftime('%y')                             
            #    if date_create_d == date_now_d and date_create_m == date_now_m and date_create_y ==date_now_y:
			
            ## Todays create new opportunity 
            total=sale_total=quto_amount=0
            for oppor in lead_obj.browse(cr, uid, opportunity):
                date_create_d = datetime.strptime(oppor.create_date,'%Y-%m-%d %H:%M:%S').strftime('%d')
                date_create_m= datetime.strptime(oppor.create_date,'%Y-%m-%d %H:%M:%S').strftime('%m')
                date_create_y = datetime.strptime(oppor.create_date,'%Y-%m-%d %H:%M:%S').strftime('%y')                             
                if date_create_d == date_now_d and date_create_m == date_now_m and date_create_y ==date_now_y:
                   total += 1
                   sale_total += oppor.sale_number ## todays total quotation 
		
            today_progress_body += _('<tr><td><b>Total New Leads Created:</b></td><td align="left">'+str(total)+'</td><td></td><td></td></tr>')
            today_progress_body += _('<tr><td><b>Leads Qualified From Cold Calling:</b></td><td align="left">'+str(qualified_len)+'</td><td></td><td></td></tr>')
	
	### todays Disqualified lead from cold calling 
            disqualified_len=0
            for disqualify in lead_obj.browse(cr, uid, lead_disqualified):
                if disqualify.disqualified_date:
                   disqualify_create_d = datetime.strptime(disqualify.disqualified_date,'%Y-%m-%d %H:%M:%S').strftime('%d')
                   disqualify_create_m= datetime.strptime(disqualify.disqualified_date,'%Y-%m-%d %H:%M:%S').strftime('%m')
                   disqualify_create_y = datetime.strptime(disqualify.disqualified_date,'%Y-%m-%d %H:%M:%S').strftime('%y')
                   if disqualify_create_d == date_now_d and disqualify_create_m == date_now_m and disqualify_create_y ==date_now_y:
                      disqualified_len =  disqualified_len +1

            today_progress_body += _('<tr><td><b>Leads Disqualified From Cold Calling:</b></td><td align="left">'+str(disqualified_len)+'</td><td></td><td></td></tr>')

	    ## Quotation_amount
            quotation_search=sale_order.search(cr, uid, [('state', 'in',('draft','sent')),('user_id', '=',sale.id)]) 
            total_quot =total_quot_amount=0
            for order in sale_order.browse(cr, uid, quotation_search):
                order_create_d = datetime.strptime(order.create_date,'%Y-%m-%d %H:%M:%S').strftime('%d')
                order_create_m= datetime.strptime(order.create_date,'%Y-%m-%d %H:%M:%S').strftime('%m')
                order_create_y = datetime.strptime(order.create_date,'%Y-%m-%d %H:%M:%S').strftime('%y')
                if order_create_d == date_now_d and order_create_m == date_now_m and order_create_y ==date_now_y:
                   total_quot +=1 #### total sales order
                   total_quot_amount += order.n_base_currency_amount
            today_progress_body += _('<tr><td><b>Quotation Created:</b></td><td align="left">'+str(total_quot)+'</td><td align="left"><b>Total Amount:</b></td><td>'+str(total_quot_amount)+' '+str(currency_name)+'</td></tr>')

            ### Todays total sales order 
            total_order =total_amount=0
            for order in sale_order.browse(cr, uid, sale_search):
                order_create_d = datetime.strptime(order.date_order,'%Y-%m-%d %H:%M:%S').strftime('%d')
                order_create_m= datetime.strptime(order.date_order,'%Y-%m-%d %H:%M:%S').strftime('%m')
                order_create_y = datetime.strptime(order.date_order,'%Y-%m-%d %H:%M:%S').strftime('%y')
                if order_create_d == date_now_d and order_create_m == date_now_m and order_create_y ==date_now_y:
                   total_order +=1 #### total sales order
                   total_amount += order.n_base_currency_amount
            today_progress_body += _('<tr><td><b>Sales Order Created:</b></td><td align="left">'+str(total_order)+'</td><td align="left"><b>Total Amount:</b></td><td>'+str(total_amount)+' '+str(currency_name)+'</td></tr>')
            today_progress_body += '</table>'

            ## Toydays Contact Leads
            today_con_body='<table style="width: 100%; height: 15%;font-family:arial;""><tr><td colspan=3 align="center"><b><u>Today Clients Contacted In Cold Calling</u></b></td></tr> <tr> <td ><b>Customer Name</b> </td> <td><b>Contact Type</b></td><td></td></tr>'

            for contact_lead in lead_obj.browse(cr, uid, today_contact_lead): 
                date_dt = datetime.strptime(contact_lead.last_contacted ,'%Y-%m-%d %H:%M:%S').strftime('%d') if contact_lead.last_contacted else ''
                date_mt = datetime.strptime(contact_lead.last_contacted ,'%Y-%m-%d %H:%M:%S').strftime('%m') if contact_lead.last_contacted else ''
                date_yt = datetime.strptime(contact_lead.last_contacted ,'%Y-%m-%d %H:%M:%S').strftime('%y') if contact_lead.last_contacted else '' 

                if date_dt == date_now_d and date_mt == date_now_m and date_yt ==date_now_y:
                  today_contact_lead_len = today_contact_lead_len + 1 
                  call_len=len(contact_lead.coldcalling_ids)
                  mail=note=call=mass=0
                  history_val=call_history.search(cr, uid, [('is_mass_mail', '=',True), ('res_id', '=',contact_lead.id)])
                  if history_val:
                     mass = len(history_val)
                  for history in contact_lead.coldcalling_ids:
                      if history.send_mail == True:
                         mail=mail +1
                      if history.set_reminder == True:
                         note=note + 1
                      if history.send_mail != True and history.set_reminder != True:
                         call =call + 1
                  #mass= call_len - (call + mail +note)
                  n_body ='<tr>'
                  n_body +='<td>'+str(contact_lead.name)+'</td>'
                  n_body +='<td><b>Call:</b> \t'+str(call_len)+' \
                  		<b>Mail:</b> \t'+str(mail)+' \
                  		<b>Notification:</b> \t'+str(note)+' \
                  		<b>Mass Mail:</b> \t'+str(mass)+'</td></tr>'
                  today_con_body +=n_body
            today_con_body +=_('<tr><td colspan=3><b>Total:   '+str(today_contact_lead_len)+'<b></td></tr></table>')

		
    	    today_target_body +=_('<tr><td><b>Daily Calls Target:</b> </td><td>'+str(salesperson_target)+'</td>')
            today_target_body +=_('<td><b>Monthly Sales Target:</b></td><td>'+str(monthly_target)+' '+str(currency_name)+'</td></tr>')
            today_target_body +=_('<tr><td><b>Calls Done Today:</b></td><td>'+str(today_contact_lead_len)+'</td>') 
	    
	    #Target Achieved Till
            today_amount=0.0
            first_date=datetime.strftime(datetime.today().replace(day=1),'%Y-%m-%d')+' 00:00:00'
            sale_ids=sale_order.search(cr, uid, [('state', 'in',('sale','done')),('user_id', '=',sale.id),('date_order','>',first_date)])
            for line in sale_order.browse(cr,uid,sale_ids):
                        today_amount += line.n_base_currency_amount
            today_target_body+=_('<td><b>Target Achieved Till Today:</b></td><td>'+str(today_amount)+' '+str(currency_name)+'</td></tr></table>') 

            ## Time Exceed 
            time_exceed_body='<table style="width: 100%; height: 15%;font-family:arial;""><col width="35%"><col width="25%"><col width="20%"><col width="20%"><tr><td colspan=4 align="center"><b><u>Contacting Time of Client Exceed</u></b></td></tr> <tr> <td ><b>Customer Name</b> </td> <td align="center"><b>Last Contact Date</b></td> <td align="center"><b>Last Contact Days</b></td><td align="center"><b>Cont Interval Days</b></td></tr>'
            for time_lead in lead_obj.browse(cr, uid, big_time_id):
                n_body='' 
                if int(time_lead.number_of_days) >= int(time_lead.contact_interval):
                   big_len = big_len +1
                   n_body ='<tr>'
                   n_body +='<td>'+str(time_lead.name if time_lead.name else " " )+'</td>'
                   n_body +='<td align="center">'+str(time_lead.last_contacted if time_lead.last_contacted else " " )+'</td>'
                   n_body +='<td align="center">'+str(time_lead.number_of_days if time_lead.number_of_days else " " )+'</td>'
                   n_body +='<td align="center">'+str(time_lead.contact_interval if time_lead.contact_interval else " " )+'</td></tr>'
                time_exceed_body +=n_body
            time_exceed_body +=_('<tr><td colspan=4><b>Total:   '+str(big_len)+'<b></td></tr></table>')

            ## Create lead
            create_body='<table style="width: 100%; height: 15%;font-family:arial;""><col width="40%"><col width="10%"><col width="35%"><col width="15%"><tr><td colspan=4 align="center"><b><u>New Coldcalling Records created </u></b></td></tr> <tr> <td ><b>Customer Name</b> </td><td></td><td><b>Mobile No</b></td><td></td></tr>'
            create_len=0
            for create_ld in lead_obj.browse(cr, uid, create_lead):
                date_create_d = datetime.strptime(create_ld.create_date,'%Y-%m-%d %H:%M:%S').strftime('%d')
                date_create_m = datetime.strptime(create_ld.create_date,'%Y-%m-%d %H:%M:%S').strftime('%m')
                date_create_y = datetime.strptime(create_ld.create_date,'%Y-%m-%d %H:%M:%S').strftime('%y')
            	n_body=''               
                if date_create_d == date_now_d and date_create_m == date_now_m and date_create_y ==date_now_y:
                   create_len = create_len +1
            	   n_body ='<tr>'
                   n_body +='<td>'+str(create_ld.name)+'</td><td></td>'
                   n_body +='<td>'+str(create_ld.mobile)+'</td><td></td></tr>'
                create_body +=n_body
            create_body +=_('<tr><td colspan=4 ><b>Total:   '+str(create_len)+'<b></td></tr></table>')

            ## Today Change interval time 
            body='<table style="width: 100%; height: 15%;font-family:arial;""><tr><td colspan=3 align="center"><b><u>Cold Calling Contact Interval Changed</u></b></td></tr> <tr> <td><b>Customer Name</b> </td> <td><b>Old Interval Duration Days</b></td> <td><b>New Interval Duration Days</b><td></tr>'

            interval_lenth=0
            for interval_lead in lead_obj.browse(cr, uid, interval_lead):
                interval_create_d = datetime.strptime(interval_lead.interval_date,'%Y-%m-%d %H:%M:%S').strftime('%d')
                interval_create_m = datetime.strptime(interval_lead.interval_date,'%Y-%m-%d %H:%M:%S').strftime('%m')
                interval_create_y = datetime.strptime(interval_lead.interval_date,'%Y-%m-%d %H:%M:%S').strftime('%y')
            	n_body=''               
                if interval_create_d == date_now_d and interval_create_m == date_now_m and interval_create_y ==date_now_y:
                   interval_lenth=interval_lenth +1
                   n_body ='<tr>'
                   n_body +='<td>'+str(interval_lead.name)+'</td>'
                   n_body +='<td>'+str(interval_lead.cont_pre_val)+'</td>'
                   n_body +='<td>'+str(interval_lead.cont_last_val)+'</td></tr>'  
                body +=n_body 
            body +=_('<tr><td colspan=4><b>Total:   '+str(interval_lenth)+'<b></td></tr></table>')  
            mail_ids.append(mail_mail.create(cr, uid,{
                        'email_to': email_from,
                       # 'email_from':email_from,
			'auto_delete':False,
                        'subject': subject,
			#'email_cc':email_cc,
                        'body_html': '<pre><span class="inner-pre" style="font-size: 15px">%s<br>%s<br>%s<br>%s</br>%s<br>%s<br>%s</span></pre>' %( create_body,body,time_exceed_body,today_con_body, today_progress_body,today_target_body,footer)
                  }, context=context))
        mail_mail.send(cr, uid, mail_ids, context=context)            
        
          
