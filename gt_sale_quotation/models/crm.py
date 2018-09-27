from openerp import fields, models, api,_
class CrmLead(models.Model):
	_inherit='crm.lead'

	def _compute_can_edit_name(self):
		self.n_edit_inquiry_note = self.env.user.has_group('base.group_sale_manager')

	n_website=fields.Char('Website')
	n_inquiry_note=fields.Text('Inquiry Description')
	n_upload_att=fields.Char('Attachment')
	n_country=fields.Char('Country')
        n_lead_id=fields.Char('Lead ID', readonly=True)

	n_edit_inquiry_note=fields.Boolean(compute='_compute_can_edit_name') #CH_N046

        @api.model
        def create(self, vals):
            number= self.env['ir.sequence'].next_by_code('crm.lead') or 'New'
            vals['n_lead_id']= int(number) + int(1910)
            result = super(CrmLead, self).create(vals)
            return result


	@api.multi
	@api.onchange('n_country')
	def country_change(self):
		if self.n_country:
			country_id =self.env['res.country'].search([('name','like',str(self.n_country))],limit=1)
			if country_id:
				self.country_id=country_id.id
 

