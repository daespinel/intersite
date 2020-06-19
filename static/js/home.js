// Create the namespace instance
let ns = {};

// Create the model instance
ns.model = (function () {
    'use strict';

    // Return the API
    return {
        'read': function () {
            let ajax_options = {
                type: 'GET',
                url: '/api/intersite-vertical',
                accepts: 'application/json',
                dataType: 'json'
            };
            return $.ajax(ajax_options);
        },
        'delete': function (resource_global) {
            let ajax_options = {
                type: 'DELETE',
                url: `/api/intersite-vertical/${resource_global}`,
                accepts: 'application/json',
                contentType: 'plain/text'
            };
            return $.ajax(ajax_options)
        },
        'readOne': function(resource_global){
            let ajax_options = {

            };
            return
        },
        'read_name': function() {
            let ajax_options = {
                type: 'GET',
                url: '/api/region',
                accepts: 'application/json',
                dataType: 'json'
            };
            return $.ajax(ajax_options);
        }
    };
}());


// Create the view instance
ns.view = (function () {
    'use strict';

    var $table = $(".blog table");

    // Return the API
    return {
        build_table: function (data) {
            let source = $('#blog-table-template').html(),
                template = Handlebars.compile(source),
                html;

            // Create the HTML from the template and notes
            html = template({ resources: data });

            // Append the rows to the table tbody
            $table.append(html);
        },
        error: function (msg) {
            $.notify({message: msg},{type: 'danger'}, {delay:8000},{onClosed: this.redirecting()});
        },
        notifaction: function (msg) {
            $.notify({message: msg},{type: 'success'},{delay:8000},{onClosed: this.redirecting()});
        },
        redirecting: function () {
            setTimeout(() => {
                window.location = '/';
            }, 9000);
        }

    };
}());

// Create the controller instance
ns.controller = (function (m, v) {
    'use strict';
    let model = m,
        view = v;

    // Get the note data from the model after the controller is done initializing
    setTimeout(function () {

        // Attach event handlers to the promise returned by model.read()
        model.read()
            .done(function (data) {
                view.build_table(data);
            })
            .fail(function (xhr, textStatus, errorThrown) {
                error_handler(xhr, textStatus, errorThrown);
            });
    }, 100);

    $(document).on('click', '#tableresources tbody tr td button.resource_delete',function (e) {
        let $target = $(e.target).parent().parent(),
            resource_global = $target.data('resource_global');
        console.log(resource_global)
        

        if(confirm("Are you sure to delete the resource?")){
            model.delete(resource_global)
        .done(function(data){
            notification_handler(data);
        })
        .fail(function (xhr, textStatus, errorThrown) {
            error_handler(xhr, textStatus, errorThrown);
        });    
        };    
    });

    $(document).on('click', '#tableresources tbody tr td button.resource_update',function (e) {
        let $target = $(e.target).parent().parent(),
            resource_global = $target.data('resource_global'),
            resource_master = $target[0].childNodes[7].childNodes[7].value;
        read_name()
        .done(function (data) {
            console.log(data)
            if(resource_master == data){
                window.location = `/resource/${resource_global}`;
            }else{
                $.notify({message: "This is not the master for the resource: It can not be updated here."},{type: 'danger'}, {delay:8000});
            };
        })
        
            
    });

    // generic error handler
    function error_handler(xhr, textStatus, errorThrown) {
        let error_msg = `${textStatus}: ${errorThrown} - ${xhr.responseJSON.detail}`;
        view.error(error_msg);
        console.log(error_msg);
    }

    function notification_handler(notificationThrown) {
        let msg = `${notificationThrown}`;
        view.notifaction(msg);
    }

}(ns.model, ns.view));