odoo.define('gt_order_mgnt', function (require) {
'use strict';

    var Dialog = require('web.Dialog');
Dialog.include({
    open: function() {
        var self = this;
        var ret = self._super.apply(self, arguments);
        self.$modal.draggable({handle: ".modal-header"});
        return ret;
    },
    close: function() {
        var self = this;
        if(self.$modal.draggable("instance")) {
            self.$modal.draggable("destroy");
        }
        self._super.apply(self, arguments);
    }
});
});
