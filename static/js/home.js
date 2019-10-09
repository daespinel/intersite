/*
 * JavaScript file for the Home page
 */

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
        'delete': function (service_global) {
            let ajax_options = {
                type: 'DELETE',
                url: `/api/intersite-vertical/${service_global}`,
                accepts: 'application/json',
                contentType: 'plain/text'
            };
            return $.ajax(ajax_options)
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
            html = template({ services: data });

            // Append the rows to the table tbody
            $table.append(html);
        },
        error: function (error_msg) {
            $('.error')
                .text(error_msg)
                .css('visibility', 'visible');
            setTimeout(function () {
                $('.error').fadeOut();
            }, 2000)
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
                //console.log(data);
            })
            .fail(function (xhr, textStatus, errorThrown) {
                error_handler(xhr, textStatus, errorThrown);
            });
    }, 100);

    $(document).on('click', '#tableservices tbody tr td button.service_delete',function (e) {
        let $target = $(e.target).parent().parent(),
            service_global = $target.data('service_global');
        console.log(service_global)
        

        if(confirm("Are you sure to delete the service?")){
            model.delete(service_global)
        .done(function(data){
            window.location = '/';
        });    
        };
       
        
    });

    

// handle application events
    //$('table').on('dblclick', 'tbody td.global', function (e) {
    //    let $target = $(e.target).parent(),
    //        service_global = $target.data('service_global');
    //    window.location = `/services/${service_global}`;

    //});


    // generic error handler
    function error_handler(xhr, textStatus, errorThrown) {
        let error_msg = `${textStatus}: ${errorThrown} - ${xhr.responseJSON.detail}`;

        view.error(error_msg);
        console.log(error_msg);
    }

    // handle application events
    //$('table').on('dblclick', 'tbody td.global', function (e) {
    //    let $target = $(e.target).parent(),
    //        service_global = $target.data('service_global');
    //    window.location = `/services/${service_global}`;

    //});

}(ns.model, ns.view));