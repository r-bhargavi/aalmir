# -*- encoding: utf-8 -*-


from openerp.osv import osv, fields
from openerp.tools.translate import _

class stock_picking_merge_wizard(osv.osv_memory):
    _name = "stock.picking.merge.wizard"
    _description = "Merge Stock Pickings"
    
    _columns = {
        
        "target_picking_id": fields.many2one("stock.picking","Target Picking"),
        "picking_ids": fields.many2many("stock.picking","wizard_stock_move_picking_merge_chosen","merge_id","picking_id"),

        "target_picking_id_state": fields.related("target_picking_id", "state", type="char", string="Target Picking State"),
       
        "target_picking_id_location_id": fields.related("target_picking_id", "location_id", type="many2one", relation='stock.location', string="Target Picking Location"),
        "target_picking_id_location_dest_id": fields.related("target_picking_id", "location_dest_id", type="many2one", relation='stock.location', string="Target Picking Destination Location"),
        "target_picking_id_company_id": fields.related("target_picking_id", "company_id", type="many2one", relation='res.company', string="Target Picking Company"),
        "target_picking_id_partner_id":fields.related("target_picking_id", "partner_id", type="many2one", relation='res.partner', string="Target Partner "),
        "target_picking_id_sale_id":fields.related("target_picking_id", "sale_id", type="many2one", relation='sale.order', string="sale"),
        "commit_merge": fields.boolean("Commit merge"),
    }        
  
    def get_specialhandlers(self):
        return {}
  
  
    def return_view(self, cr, uid, name, res_id):
        data_pool = self.pool.get('ir.model.data')
        result = data_pool.get_object_reference(cr, uid, 'stock_merge_picking', name)
        view_id = result and result[1] or False
        r = {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.picking.merge.wizard',
            'views': [(view_id, 'form')],
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': res_id,
        }
        return r
    
    def is_compatible_many2one(self, cr, uid, target, merge, context=None):
        fields_pool = self.pool.get("ir.model.fields")
        fields_search = fields_pool.search(cr, uid, [('ttype','=','many2one'),('model','=','stock.picking'),('relation','<>',self._name)])
        failedfields = []
        for field in fields_pool.browse(cr, uid, fields_search, context):
            print"8888888888888888888888888",field
            # don't handle specialhandlers fields as incompatible            
            if field.name in self.get_specialhandlers().keys():
                continue
            print"&&&&&&&&&&&&&&&",getattr(target, field.name)
            # compare fields
            related_target_id = getattr(target, field.name)
            related_merge_id = getattr(merge, field.name)
            if (related_target_id.id != related_merge_id.id):
                failedfields.append(field)
        return {'result': (len(failedfields)==0), 'fields': failedfields}
    
    def do_target(self, cr, uid, ids, context=None):
        # look if we got compatible views
        picking_pool = self.pool.get('stock.picking')
               
        found = False
        found_incompatible = False
        incompatible_notes = _('Near misses:')

        for session in self.browse(cr, uid, ids):
            # search if there are any compatible merges at all
            similiar_ids = picking_pool.search(cr, uid, [('id','<>',session.target_picking_id.id),
                                                ('state','=',session.target_picking_id.state),
                                                
                                               ])
            print"similiar_idssimiliar_idssimiliar_ids",similiar_ids
            # ensure that many2one relations are compatible 
            for merge in picking_pool.browse(cr, uid, similiar_ids):
                print"%%%%%%%%%%%%%%%%%%%%%", merge
                is_compatible = self.is_compatible_many2one(cr, uid, session.target_picking_id, merge, context)
                if (is_compatible['result']):
                    found = True
                else:
                    found_incompatible = True
                    for f in is_compatible['fields']:
                        desc = self.get_fieldname_translation(cr, uid, f, context)
                        incompatible_notes += "\n" + _('%s: %s (%s) differs.') % (str(merge.name), desc, f.name) 
            return self.return_view(cr, uid, 'merge_picking_form_target', ids[0])
        
    def get_fieldname_translation(self, cr, uid, field, context=None):
        if ((context) and (context['lang'])):
            name = str(field.model) + "," + str(field.name)
            trans_pool = self.pool.get('ir.translation')
            trans_search = trans_pool.search(cr, uid, [('lang','=',context['lang']),('name','=',name),('type','=','field')])
            for trans in trans_pool.browse(cr, uid, trans_search):
                return trans.value        
        return field.field_description
    
    def is_view(self, browse):
       
        if (browse):
            if (hasattr(browse, "_auto")):
                if (not getattr(browse, "_auto")):
                    return True
        return False
          
    def is_translateable(self, browse):
        if (browse):
            cols = getattr(browse, "_columns") or False
            remotefield = cols[self.remote_note] or False
            return (remotefield.translate) 
        return False
    
    def do_check(self, cr, uid, ids, context=None):
        for session in self.browse(cr, uid, ids):
            target = session.target_picking_id
            for merge in session.picking_ids:
                is_compatible = self.is_compatible_many2one(cr, uid, target, merge, context)
        return self.return_view(cr, uid, 'merge_picking_form_checked', ids[0])        
    
    def do_merge(self, cr, uid, ids, context=None):
        for session in self.browse(cr, uid, ids):
            if not session.commit_merge: 
                raise osv.except_osv(_('Unchecked'),_('You did not check the Commit Merge checkbox.'))
                return self.return_view(cr, uid, 'merge_picking_form_checked', ids[0])

        # merge
        picking_pool = self.pool.get("stock.picking")
        fields_pool = self.pool.get("ir.model.fields")
    
        for session in self.browse(cr, uid, ids):
            print"{(((((((((((((999hhhhhhhhh",session
            target = session.target_picking_id
            
            target_changes = {"date_done": target.date_done }

            # prepare notes, esp. if not existing           
            if (target.note):
                target_changes['note'] = target.note + "\n"
            else:
                target_changes['note'] = ""

            if (target.merge_notes):
                target_changes['merge_notes'] = target.merge_notes + ";\n"
            else:
                target_changes['merge_notes'] = ""
            target_changes['merge_notes'] += "This is a merge target."


            for merge in session.picking_ids:
                # fetch notes

                linenote = " Merged " + str(merge.name)
                if (merge.origin != target.origin):
                    linenote += ", had Origin " + str(merge.origin)
                
                if (merge.date != target.date):
                    linenote += ", from " + str(merge.date)

                if (merge.note):
                    linenote += ", Notes: " + str(merge.note)

                target_changes['merge_notes'] += linenote + ";\n"

                if (merge.note):
                    target_changes['note'] += str(merge.note) + "\n"
                if (merge.move_type == 'direct'):
                    target_changes['move_type'] = 'direct'
                
                # date_done = MAX(date_done)
                if (target_changes['date_done'] < merge.date_done):
                    target_changes['date_done'] = merge.date_done
                fields_search = fields_pool.search(cr, uid, [('model','=','stock.picking'),('ttype','=','many2one')])
                for field in fields_pool.browse(cr, uid, fields_search):
                    if field.name in self.get_specialhandlers().keys():
                        specialhandler_name = self.get_specialhandlers().get(field.name)
                        specialhandler = getattr(self, specialhandler_name)
                        target_changes = specialhandler(cr, uid, field.name, merge, target, target_changes)
                fields_search = fields_pool.search(cr, uid, [('relation','=','stock.picking'),('model','<>',self._name),
                                                             '|',('ttype','=','many2one'),('ttype','=','many2many')])
                for field in fields_pool.browse(cr, uid, fields_search):
                    
                    if field.name in self.get_specialhandlers().keys():
                        specialhandler_name = self.get_specialhandlers().get(field.name)
                        specialhandler = getattr(self, specialhandler_name)
                        target_changes = specialhandler(cr, uid, field.name, merge, target, target_changes)
                for field in fields_pool.browse(cr, uid, fields_search):


                    if not (field.name in self.get_specialhandlers().keys()):
                        model_pool = self.pool.get(field.model)
                        if (not model_pool):
                            continue
                        if self.is_view(model_pool):
                            continue
                        if (field.ttype == 'many2one'):
                            model_search = model_pool.search(cr, uid, [(field.name,'=',merge.id)])
                            model_pool.write(cr, uid, model_search, {field.name: target.id})
                        if (field.ttype == 'many2many'):
                            model_search = model_pool.search(cr, uid, []) 
                            model_pool.write(cr, uid, model_search, {field.name: [(3,merge.id),(4,target.id)]})
                picking_pool.write(cr, uid, [merge.id], {'sale_id':target.sale_id.id})
                print"((99999999999999999mmm",picking_pool, merge.id
            picking_pool.write(cr, uid, [target.id], target_changes)
                
        return self.return_view(cr, uid, 'merge_picking_form_done', ids[0])        

stock_picking_merge_wizard()

