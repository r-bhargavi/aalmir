odoo.define('gt_aalmir_coldcalling.FormView', function (require) {
"use strict";
var FormView = require('web.FormView');
var ListView = require('web.ListView');
var core = require('web.core');

FormView.include({
    
     load_form: function(data) {
        var self = this;
        self.options.initial_mode = 'edit';
        if (!data) {
            throw new Error(_t("No data provided."));
        }
        if (this.arch) {
            throw "Form view does not support multiple calls to load_form";
        }
        this.fields_order = [];
        this.fields_view = data;

        this.rendering_engine.set_fields_registry(this.fields_registry);
        this.rendering_engine.set_tags_registry(this.tags_registry);
        this.rendering_engine.set_widgets_registry(this.widgets_registry);
        this.rendering_engine.set_fields_view(data);
        var $dest = this.$el.hasClass("oe_form_container") ? this.$el : this.$el.find('.oe_form_container');
        this.rendering_engine.render_to($dest);

        this.$el.on('mousedown.formBlur', function () {
            self.__clicked_inside = true;
        });

        this.has_been_loaded.resolve();

        // Add bounce effect on button 'Edit' when click on readonly page view.
        this.$el.find(".oe_form_group_row,.oe_form_field,label,h1,.oe_title,.oe_notebook_page, .oe_list_content").on('click', function (e) {
            if(self.get("actual_mode") == "view" && self.$buttons && !$(e.target).is('[data-toggle]')) {
                var $button = self.$buttons.find(".oe_form_button_edit");
                $button.openerpBounce();
                e.stopPropagation();
                core.bus.trigger('click', e);
            }
        });
        //bounce effect on red button when click on statusbar.
        this.$el.find(".oe_form_field_status:not(.oe_form_status_clickable)").on('click', function (e) {
            if((self.get("actual_mode") == "view")) {
                var $button = self.$el.find(".oe_highlight:not(.o_form_invisible)").css({'float':'left','clear':'none'});
                $button.openerpBounce();
                e.stopPropagation();
            }
         });
        this.trigger('form_view_loaded', data);
        return $.when();
    },
    
});

//ListView.include({
//    select_record:function (index, view) {
//        view = view || index === null || index === undefined ? 'form' : 'form';
//        this.dataset.index = index;
//        _.delay(_.bind(function () {
//            this.do_switch_view(view);
//        }, this));
//        this.sidebar.do_hide();
//    },
//});
});
//    render_sidebar: function($node) {
//        if (!this.sidebar && this.options.sidebar) {
//            this.sidebar = new Sidebar(this, {editable: this.is_action_enabled('edit')});
////            if (this.fields_view.toolbar) {
////                this.sidebar.add_toolbar(this.fields_view.toolbar);
////            }
//            this.sidebar.add_items('other', _.compact([
////                { label: _t("Export"), callback: this.on_sidebar_export },
////                this.fields_view.fields.active && {label: _t("Archive"), callback: this.do_archive_selected},
////                this.fields_view.fields.active && {label: _t("Unarchive"), callback: this.do_unarchive_selected},
//                this.is_action_enabled('delete') && { label: _t('Delete'), callback: this.do_delete_selected }
//            ]));
//
//            $node = $node || this.options.$sidebar || this.$('.oe_list_sidebar');
//            this.sidebar.appendTo($node);
//
//            // Hide the sidebar by default (it will be shown as soon as a record is selected)
//            this.sidebar.do_hide();
//        }
//    },
//});




