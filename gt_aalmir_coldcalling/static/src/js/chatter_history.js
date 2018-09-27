odoo.define('gt_aalmir_coldcalling.gt_aalmir_coldcalling', function (require) {
"use strict";
var Chatter = require('mail.Chatter');
var WebClient = require('web.WebClient');
//var ChatterComposer=require('mail.chatter.ChatComposer');
//var chat_manager = require('mail.chat_manager');
var composer = require('mail.composer');
var core = require('web.core');
var common = require('web.form_common');
var Model = require('web.Model');
var time = require('web.time');
var utils = require('web.utils');
console.log('kkkkkkkkk');
// check counter 

var TimeCounter = common.AbstractField.extend(common.ReinitializeFieldMixin, {
    start: function() {
        console.log('jjjjjjjjj');
        this._super();
        var self = this;
        console.log('OOOOOOOOOOOOOOOOOOO',this.field_manager.datarecord);
        this.field_manager.on("view_content_has_changed", this, function () {
            self.render_value();
        });
    },
    start_time_counter: function(){
        var self = this;
        clearTimeout(this.timer);
        if (this.field_manager.datarecord.state == 'startworking') {
            this.duration += 1000;
            this.timer = setTimeout(function() {
                self.start_time_counter();
            }, 1000);
        } else {
            clearTimeout(this.timer);
        }
        this.$el.html($('<span>' + moment.utc(this.duration).format("HH:mm:ss") + '</span>'));
    },
    render_value: function() {
        this._super.apply(this, arguments);
        var self = this;
        this.duration;
        console.log(this.field_manager.datarecord.id, this.duration);
        var productivity_domain = [['id', '=', this.field_manager.datarecord.id]];
        console.log(productivity_domain);
        new Model('mrp.production.workcenter.line').call('search_read', [productivity_domain, []]).then(function(result) {
            if (self.get("effective_readonly")) {
                self.$el.removeClass('o_form_field_empty');
                var current_date = new Date();
                self.duration = 0;
                
                _.each(result, function(data) {
                          //var diff=self.get_date_difference(time.auto_str_to_date(data.date_start), current_date);
                          //console.log('dddddddddddd',diff);
                          if (data.date_start) {
                              self.duration += self.get_date_difference(time.auto_str_to_date(data.date_start), current_date);
                              //self.duration =self.duration - diff
                           }
                   
                    console.log('RRRRRRRr',data.date_start,data.date_end);
                });
                self.start_time_counter();
            }
        });
    },
    get_date_difference: function(date_start, date_finished) {
       var current_date = new Date();
        console.log('ppppppppp',date_start)
        var difference = moment(current_date).diff(moment(date_start));
        console.log('hhhhhhhhh',difference)
        return moment.duration(difference);
    },
});

//  check counter
Chatter.include({
    events: {
        "click .o_chatter_history_show": "show_history",
        "click .o_chatter_history_hide": "hide_history",
        "click .o_chatter_button_new_message": "on_open_composer_new_message",
        "click .o_chatter_button_log_note": "on_open_composer_log_note",
        "click .o_chatter_button_mail_history":"open_test",
    },
    show_history:function(){
      $(".o_mail_thread").show();
      $(".o_chatter_history_show").hide();
       $(".o_chatter_history_hide").show();
     },
    hide_history:function(){
      $(".o_mail_thread").hide();
      $(".o_chatter_history_show").show();
       $(".o_chatter_history_hide").hide();
      
     },
  
    open_test:function(options){
     var old_composer = this.composer;
     this.open_composer();
     //var con=[]
     //con=_.copyObj(this.composer.context);
     //console.log(con);
     //this.composer.context = _.extend(this.composer.context,{
                //default_parent_id: this.composer.id,
                //default_body: 'hello',
                 //default_attachment_ids: _.pluck(this.composer.get('attachment_ids'), 'id'),
                 //default_partner_ids: this.composer.partner_ids,
                //default_is_log:  this.composer.options.is_log,
                //mail_post_autofollow: true,
       // });
     //console.log(this.context, this.composer.context , this.composer.context.default_body);
     var tst=this.composer.on_open_full_composer();
     
     
     },
   
});
core.form_widget_registry.add('mrp_time_counter', TimeCounter);
});


