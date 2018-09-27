openerp.aalmir_logo = function(instance) {
    var _t = instance.web._t,
    _lt = instance.web._lt;
    var QWeb = instance.web.qweb;

    instance.web.WebClient.include({
        init: function() {
            console_log('++++++++++++++++++++++++++############++++++++++++++++++++++');
            this.set('title_part', {"zopenerp": "api"});
            return this._super();
        },
    })
}
