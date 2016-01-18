(function() {
    var original = {};
    var policy;
    var handlers = null; // list of handlers attached to deviceready
    var expecting_deviceready = true;

    
    // initialize policy ---------------------
    policy = {}
    //----------------------------------------

//    var policy_creation = true;
    //Default values
    if (typeof policy.blockAll === "undefined") policy.blockAll =      false;    // if true no accesses are granted no matter what the tickets say.
    if (typeof policy.allowAll === "undefined") policy.allowAll =      false;   // if true all accesses are granted no matter what the tickets say (unless blockAll)
    if (typeof policy.generate === "undefined") policy.generate =      true;    // used internally: if false does not generate any new tickets
    if (!policy.mperms)                         policy.mperms =        0;
    if (!policy.buttons)                        policy.buttons =       [];
    if (!policy.deny)                           policy.deny =          function(){};
    if (!policy.guard)                          policy.guard =         [];
    if (!policy.guard_exec)                     policy.guard_exec =    [];
    if (!policy.guard_require)                  policy.guard_require = [];

    policy.mperms_local = 0;
    policy.mperms_global = policy.mperms;
    delete policy.mperms;

    var deviceReadyFired = false; //log if device ready was fired and don't fire it again.
    

    original.addEventListener = document.addEventListener;
    original.dispatchEvent    = document.dispatchEvent;

    //ToBE stored
    // hasOwnProperty, typeof?, alert, apply?, call?, length, split, indexof, hasAttribute, getAttribute, match, toString?, toNummeric

    var exec_guarded = function(f,f_this,f_arguments) {
	var allowed_global = (policy.mperms_global > 0);
	var allowed_local  = (policy.mperms_local  > 0);
	var perms_pre;
	if (!policy.blockAll) {
	    if (policy.allowAll) {
		var back = f.apply(f_this,f_arguments);
		//alert("original function executed");
		return back;
	    }
	    if (allowed_local) {
		perms_pre = policy.mperms_local;
		var back = f.apply(f_this,f_arguments);
		policy.mperms_local = perms_pre -1; //only ever decrease by 1, even if wrapped by this policy multiple times
		return back;
	    }
	    if (allowed_global) {
		perms_pre = policy.mperms_global;
		var back = f.apply(f_this,f_arguments);
		policy.mperms_global = perms_pre -1; //only ever decrease by 1, even if wrapped by this policy multiple times
		return back;
	    }
	}
	return policy.deny(f_this,f_arguments);
    }
    
    var guard_API=function(orig) {
	return function() {
	    return exec_guarded(orig,this,arguments);
	}
    }
    var guard_exec = function(clas,meth) {
	var ce;
	if ((typeof Cordova !== 'undefined') && ('exec' in Cordova) ) {
	    ce = Cordova.exec;
	}
	if ((typeof cordova !== 'undefined') && ('exec' in cordova) ) {
	    ce = cordova.exec;
	}
	if ((typeof PhoneGap !== 'undefined') && ('exec' in PhoneGap) ) {
	    ce = PhoneGap.exec;
	}
	if (typeof ce === 'undefined') {
	    //alert('exec not found');
	    return;
	}
	//alert ("wrapping "  + clas + ", " + meth);

	wrapped_exec = function() {
	    if ( ( arguments[2] == clas) && (arguments[3] == meth) ) {
		return exec_guarded(ce,this,arguments);
	    } else {
		return ce.apply(this,arguments);
	    }
	};
	if (typeof Cordova !== 'undefined') Cordova.exec = wrapped_exec;					   
	if (typeof cordova !== 'undefined') cordova.exec = wrapped_exec;
	if (typeof PhoneGap !== 'undefined') PhoneGap.exec = wrapped_exec;
    };

    var guard_require = function(plugin,meth) {
	if (typeof cordova === 'undefined') return;
	if (typeof cordova.require === 'undefined') return;
	
	var orig_req = cordova.require;

	cordova.require = function() {
	    var api_obj = orig_req.apply(this,arguments);
	    if (arguments[0] === plugin) {
		if (typeof api_obj[meth] === 'undefined') {
		    alert(meth + " not found in plugin " + plugin);
		} else {
		    //find exact location:
		    var iter = api_obj;
		    while (!iter.hasOwnProperty(meth)) iter = iter.__proto__
		    iter[meth] = guard_API(iter[meth]);
		}
	    }
	    return api_obj;
	}
    }

    var wrap_APIs = function() {
	for (var i=0;i<policy.guard.length;i++) {
	    var iter = window;
	    var last = window;
	    var path = policy.guard[i].split(".");
	    var found = true
	    for (var j=0;j<path.length;j++) {
		if (path[j] in iter) {
		    last = iter;
		    iter = iter[path[j]];
		} else {
		    found = false;
		    break;
		}
	    }
	    if (found) {
		//alert("wrapping " + path);
		last[path[j-1]] = guard_API(iter);
	    } else {
		//alert('not found ' + path);
	    }
	}
	if (typeof navigator !== 'undefined') {
	    if (typeof navigator.notification !== 'undefined') {
		if (typeof navigator.notification.confirm !== 'undefined') {
//		    alert("wrapping dialog")
		    navigator.notification.confirm = guard_dialog(navigator.notification.confirm);
		} //else alert("confirm not found");
	    } //else alert("notification not found");
	} //else alert("navigator not found")
    }
    var wrap_exec = function() {
	for (var i=0;i<policy.guard_exec.length;i++) {
	    var cm = policy.guard_exec[i].split(".");
	    guard_exec(cm[0],cm[1]);
	}
    }

    var wrap_require = function() {
//	alert("Wrapping require apis");
	for (var i=0;i<policy.guard_require.length;i++) {
	    var cm = policy.guard_require[i].split(".");
	    guard_require(cm[0],cm[1]);
	}
    }

    wrap_exec();
    wrap_APIs();
    wrap_require();
    
    original.addEventListener.call(document,
				   'deviceready',
				   function() {
//				       alert("deviceready received");
				       deviceReadyFired = true;
				       //Do the wrapping: ----------------------------------------
				       wrap_APIs();
				       wrap_exec();
				       wrap_require();
				       // -------------------------------------------------------

				       expecting_deviceready = false;
				       // call hold back handlers
				       var h = handlers;
				       while (h!== null) {
					   h.args[1].apply(h.this,arguments);
					   h=h.next;
				       }
				       //call hold back handlers by the cordova 'addEventListener'
				       h = document.addEventListener.getHandlers();
				       while (h !== null) {
					   try {
					       h.args[1].apply(h.this,arguments);
					   }
					   finally {
					       h=h.next;
					   }
				       }
				   }, true
				  );

    var policy_mark;
    // listen whether additional libraries are inserted
    var observer=new MutationObserver(function (mutations) {
	for (var i=0;i<mutations.length;i++) {
	    if (!mutations.hasOwnProperty(i)) continue;
	    var mutation = mutations[i];
	    if (mutation.type === "childList") {
		if (!mutation.addedNodes) continue;
		for (var j=0;j<mutation.addedNodes.length;j++) {
		    if (!mutation.addedNodes.hasOwnProperty(j)) continue;
		    var node = mutation.addedNodes[j];
		    if (typeof node.tagName === "undefined") continue;
		    if (node.tagName.toLowerCase() == "script") {
			//alert("script added: " + node.getAttribute("src"));
			wrap_APIs();
			wrap_exec();
			wrap_require();
			//duplicate deviceready event to make sure it arives even in old versions of Phonegap
			document.addEventListener("deviceready",function() {if (!deviceReadyFired){deviceReadyFired = true; document.dispatchEvent(new Event('deviceready'));}});
		    } else if (policy_mark) {
			var pol = eval_policy(node);
			if ( policy_active(pol) ){
			    node.style.borderStyle = "solid";
			    node.style.borderColor = "red";
			    node.style.borderWidth = "5px";
			}
		    }
		}
	    } else if (mutation.type === "attributes") {
		var node = mutation.target;
		
		var pol = eval_policy(node);
		if (policy_active(pol)) {
		    node.style.borderStyle = "solid";
		    node.style.borderColor = "red";
		    node.style.borderWidth = "5px";
		}
	    }
	}
    });
    var config = {subtree: true, childList: true};
    if (policy_mark) config.attributes=true;
    observer.observe(document,config);
    
    //Wrap confirmation dialogs
    var guard_dialog=function(orig) {
	return function() {
	    //save button lables
	    var buttonlables = [ "OK","Cancel"];
	    if (arguments.hasOwnProperty(3)) {
		buttonlables = arguments[3];
		if (typeof buttonlables == 'string') {
		    buttonlables = buttonlables.split(','); //old version took buttons as comma sep list
		}
	    }

	    var orig_callback = arguments[1];
	    var new_callback = function(buttonIndex) {
		//Go through all the possible confirmable tickets
		var buttonText = buttonlables[buttonIndex-1];
//		alert(buttonText);
		for (var i=0; i<policy.confirmable.length; i++) {
		    if (!policy.confirmable.hasOwnProperty(i)) continue;
		    var cable = policy.confirmable[i];
		    if (cable.buttons.indexOf(buttonText) > -1) {
			if (cable.local) {
			    policy.mperms_local += cable.mperms;
			    alert("Policy granted locally: " + policy.mperms_local);
			} else {
			    policy.mperms_global += cable.mperms;
			    alert("Policy granted globally: " + policy.mperms_global);
			}
		    }
		}
		//Delete all confirmables (They had their chance)
		policy.confirmable = [];
		//Execute original Callback
		orig_callback.apply(this,arguments);
	    }

	    //Execute original dialog
	    arguments[1] = new_callback;
	    return orig.apply(this,arguments);
	}
    }


    
    //Wrap inputs --------------------------------------------------
    var iter = document;
    while (iter.__proto__.addEventListener) {iter = iter.__proto__;}

    //wrap dispatchEvent
    iter.dispatchEvent = function() {
	var ret;
	var is_click = (arguments[0].type === "click");
	if (is_click) {
	    var old = policy.generate;
	    policy.generate = false;
	}
	ret = original.dispatchEvent.apply(this,arguments)
	if (is_click) {
	    policy.generate = old;
	}
    };

    /* expected return: Object containing
       - mperms_local : the number of local  tickets to be granted
       - mperms_global: the number of global tickets to be granted
       - confirm: list of confirmable tickets. Each element in the list is an object with the following properties:
           - buttons: list of captions of buttons, that confirm this ticket
	   - mperms:  number of tickets that can be confirmed
	   - local:   BOOLEAN specifying whether these tickets will be local or global
       - (optional) allowAll: new value for the allowAll parameter of the policy
       - (optional) blockAll: new value for the blockAll parameter of the policy
	   */
    var eval_policy = function(target) {
	var pol = {mperms_local:0,mperms_global:0,confirm:[]};
	for (var i=0;i<policy.buttons.length;i++) {
	    var applies = true;
	    var button = policy.buttons[i];
	    if (typeof button.cond === "undefined") button.cond = [];
	    for (var crit in button.cond) {
		if (!target.hasAttribute(crit)) {
		    applies = false;
		    break;
		}
		var tcrit = target.getAttribute(crit);
		var pcrit = button.cond[crit];
		if (typeof button.match !== "string")
		    button.match = "exact";
		switch (button.match) {
		case "exact":
    		    if (tcrit !== pcrit)
			applies = false;
		    break;
		case "different":
		    if (tcrit === pcrit)
			applies = false
		    break;
		case "contains":
		    if (tcrit.indexOf(pcrit) === -1 )
			applies = false;
		    break;
		case "regex":
		    if (! tcrit.match(pcrit) )
			applies = false;
		    break;
		case "begins":
		    if (tcrit.indexOf(pcrit) !== 0 )
			applies = false;
		    break;
		case "ends":
		    if (tcrit.indexOf(pcrit, tcrit.length - pcrit.length) === -1)
			applies = false;
		    break;
		default:
		    applies = false;
		}
	    }

	    if (applies) {
		var b_mperms = button.mperms;
		// update allowAll and blockAll if neccessary:
		if (typeof button.allowAll !== 'undefined') {
		    if (typeof pol.allowAll === 'undefined') {
			pol.allowAll = button.allowAll;
		    } else {
			pol.allowAll = pol.allowAll && button.allowAll;
		    }
		}
		if (typeof button.blockAll !== 'undefined') {
		    if (typeof pol.blockAll === 'undefined') {
			pol.blockAll = button.blockAll;
		    } else {
			pol.blockAll = pol.blockAll || button.blockAll;
		    }
		}
		// correct b_mperms depending on type of target
		if (button.checkbox) { //defined and trueish
		    if (typeof target.checked === 'undefined') b_mperms = 0; // target is not what the policy asked for
		    else if (!target.checked) b_mperms = -b_mperms;                // target has been unchecked -> retract tickets
		}
		// add tickets to the correct pile in pol
		if (button.hasOwnProperty("confirm")) {
		    //If the mperms need to be confirmed, save the condition and number
		    var cable = {buttons:button.confirm,mperms:b_mperms}; // new confirmable
		    if (typeof button.local !== "undefined") cable.local = button.local;
		    pol.confirm.push(cable); 
		} else {
		    if (!policy.generate) continue;
		    if (button.local) //defined and trueish
			pol.mperms_local += b_mperms;
		    else
			pol.mperms_global += b_mperms;
		}
	    }
	}
	return pol;
    };

    var policy_active= function(pol) {
	if (pol.mperms_local !== 0) return true;
	if (pol.mperms_global !== 0) return true;
	if (typeof pol.allowAll !== "undefined") return true;
	if (typeof pol.blockAll !== "undefined") return true;
	if (typeof pol.confirm !== "undefined") 
	    if (pol.confirm.length > 0) return true;
	return false;
    }
    
    var policy_creation;
    var exec_policy= function(target) {
	if (policy_creation) alert("pressed \n" + htmlElement2string(target));
	    
	var pol = eval_policy(target);
	var granted = false;

	policy.mperms_global += pol.mperms_global;
	policy.mperms_local  += pol.mperms_local;
	if ( (pol.mperms_local !== 0) || (pol.mperms_global !== 0) ) alert("Policy granted: total (" + policy.mperms_global + "," + policy.mperms_local + ")");
	window.setTimeout(function() {policy.mperms_local = 0},0);

	if (typeof pol.allowAll !== "undefined") {
	    policy.allowAll = pol.allowAll;
	    alert("Policy activated: allowAll =" + policy.allowAll);
	}
	
	//store confirmable tickets
	if (pol.confirm.length > 0) {
	    alert("Policy awaits confirmation");
	    policy.confirmable = pol.confirm;
	}
    }

    //listen for all click events at the root of DOM
    original.addEventListener.call(document,'click',function(event){exec_policy(event.target)},true);

    //Auxiliary functions for policy creation
    function htmlElement2string(h) {
	var attrs = h.attributes;
	if (attrs.length == 0) return "";
	var str = attrs[0].nodeName + ":" + attrs[0].nodeValue;
	for (var i = 1;i<attrs.length;i++) {
	    if (!attrs.hasOwnProperty(i)) continue;
	    str = str + "\n" + attrs[i].nodeName + ":" + attrs[i].nodeValue;
	}
	return str;
    }   
})();
//alert("wrapper executed");


//Policy Wrapper
// Version 20151126
// Pro: can wrap all onclick events and addEventHandler
//      can handle fractional permissions
//      allows different kinds of matching for the constraints in button policies
//      can wrap cordova libraries which are injected dynamically.
//      can delay the ticket generation until specified button was pushed in confirmation dialog
//      can reduct tickets if checkbox is unchecked
//      can draw a red frame around buttons which fulfil the policy
//      allows local permissions
//      allows policies specifying allowAll and blockAll
// Con: check does not work
// Ideas: Have a maximal amount of permissions, an application can hold at any point
//        Allow button policies, which set the total amount of tickets to 0. (e.g. back button)
// TODO: wrap confirm via require and exec
// TODO: local allowAll, denyAll
// TODO: wrap exec via require
