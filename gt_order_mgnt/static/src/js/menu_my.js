$(document).ready(function () {
    $( ".toggle_leftmenu").click(function() {
    	$(".oe_leftbar").slideToggle();
    });
   $( ".toggle_upperheader").click(function() {
    	$(".oe-control-panel").slideToggle();
    });
    
    $(".confirmation").click(function() {
    	return confirm('Are you sure?');
    });
    
               
});
