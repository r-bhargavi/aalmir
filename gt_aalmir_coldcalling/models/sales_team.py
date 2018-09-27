from openerp import models

class crm_team(models.Model):

    _inherit = 'crm.team'

    def action_your_pipeline(self, cr, uid, context=None):

        result = super(crm_team, self).action_your_pipeline(cr, uid, context=context)
        IrModelData = self.pool['ir.model.data']
        print "REsult ::",result
        tree_view_id = IrModelData.xmlid_to_res_id(cr, uid, 'crm.crm_case_tree_view_oppor')
        form_view_id = IrModelData.xmlid_to_res_id(cr, uid, 'crm.crm_case_form_view_oppor')
        kanb_view_id = IrModelData.xmlid_to_res_id(cr, uid, 'crm.crm_case_kanban_view_leads')
        if result:
            result.update({
                'views': [

                    [tree_view_id, 'tree'],
                    [form_view_id, 'form'],
                    [kanb_view_id, 'kanban'],
                    [False, 'graph'],
                    [False, 'calendar'],
                    [False, 'pivot']
                ]
            })

        return result
