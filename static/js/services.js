/*
 * JavaScript file for the application to demonstrate
 * using the API
 */

// Create the namespace instance
let ns = {};

// Create the model instance
ns.model = (function () {
    'use strict';

    // Return the API
    return {
        read_one: function (service_global) {
            let ajax_options = {
                type: 'GET',
                url: `/api/intersite-vertical/${service_global}`,
                accepts: 'application/json',
                dataType: 'json'
            };
            return $.ajax(ajax_options);
        },
        read: function () {
            let ajax_options = {
                type: 'GET',
                url: '/api/intersite-vertical',
                accepts: 'application/json',
                dataType: 'json'
            };
            return $.ajax(ajax_options);
        },
        create: function (service) {
            let ajax_options = {
                type: 'POST',
                url: '/api/intersite-vertical',
                accepts: 'application/json',
                contentType: 'application/json',
                dataType: 'json',
                data: JSON.stringify(service)
            };
            return $.ajax(ajax_options)
        },
        update: function (service) {
            let ajax_options = {
                type: 'PUT',
                url: '/api/intersite-vertical/${service.service_global}',
                accepts: 'application/json',
                contentType: 'application/json',
                dataType: 'json',
                data: JSON.stringify(service)
            };
            return $.ajax(ajax_options)
        },
        'delete': function (service_global) {
            let ajax_options = {
                type: 'DELETE',
                url: '/api/intersite-vertical/${service_global}',
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

    var $table = $(".services table");

    const NEW_RESOURCE = 0,
        EXISTING_RESOURCE = 1;

    let $service_global = $('#service_global'),
        $service_name = $('#service_name'),
        $service_type = $('#service_type'),
        $service_params = $('#service_params'),
        $service_resources = $('#service_resources'),
        $service_interconnections = $('#service_interconnections'),
        $create = $('#create'),
        $update = $('#update'),
        $delete = $('#delete'),
        $reset = $('#reset');
        
    // return the API
    return {
        NEW_RESOURCE: NEW_RESOURCE,
        EXISTING_RESOURCE: EXISTING_RESOURCE,
        reset: function () {
            $service_global.text('');
            $service_name.val('');
            $service_params.val('');
            $service_type.val('').focus();
        },
        update_editor: function (service) {
            $service_global.text(service.service_global);
            $service_name.val(service.service_name);
            $service_params.val(service.service_params);
            $service_type.val(service.service_type).focus();
        },
        set_button_state: function (state) {
            if (state === NEW_RESOURCE) {
                $create.prop('disabled', false);
                $update.prop('disabled', true);
                $delete.prop('disabled', true);
            } else if (state === EXISTING_RESOURCE) {
                $create.prop('disabled', true);
                $update.prop('disabled', false);
                $delete.prop('disabled', false);
            }
        },
        build_table: function (data) {
            
            let source = $('#services-table-template').html(),
                template = Handlebars.compile(source),
                html;

            // Create the HTML from the template and notes
            html = template({services: data});

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

// Create the controller
ns.controller = (function (m, v) {
    'use strict';

    let model = m,
        view = v,
        $url_service_global = $('#url_service_global'),
        $service_global = $('#service_global'),
        $service_name = $('#service_name'),
        $service_type = $('#service_type'),
        $service_params = $('#service_params'),
        $service_resources = $('#service_resources'),
        $service_interconnections = $('#service_interconnections');

    // Get the data from the model after the controller is done initializing
    setTimeout(function () {
        view.reset();
        model.read()
            .done(function (data) {
                view.build_table(data);
            })
            .fail(function (xhr, textStatus, errorThrown) {
                error_handler(xhr, textStatus, errorThrown);
            })

        if ($url_service_global.val() !== "") {
            model.read_one($url_service_global.val())
                .done(function (data) {
                    view.update_editor(data);
                    view.set_button_state(view.EXISTING_RESOURCE);
                })
                .fail(function (xhr, textStatus, errorThrown) {
                    error_handler(xhr, textStatus, errorThrown);
                });
        }
    }, 100)

    // generic error handler
    function error_handler(xhr, textStatus, errorThrown) {
        let error_msg = `${textStatus}: ${errorThrown} - ${xhr.responseJSON.detail}`;

        view.error(error_msg);
        console.log(error_msg);
    }
    // initialize the button states
    view.set_button_state(view.NEW_RESOURCE);

    // Validate input
    function validate(type, resources) {
        return type !== "" && resources !== "";
    }

    // Create our event handlers
    $('#create').click(function (e) {
        let name = $name.val(),
            type = $type.val(),
            resources = $resources.val();

        e.preventDefault();

        if (validate(type, resources)) {
            model.create(name, type, resources)
        } else {
            alert('Problem with type or resources');
        }
    });

    $('#update').click(function (e) {
        let id = $id.val();

        e.preventDefault();

        if (validate(type, resources)) {
            model.update(type, resources)
        } else {
            alert('Problem with type or resources input');
        }
        e.preventDefault();
    });

    $('#delete').click(function (e) {
        let id = $id.val();

        e.preventDefault();

        if (validate('placeholder', lname)) {
            model.delete(id)
        } else {
            alert('Problem with ID');
        }
        e.preventDefault();
    });

    $('#reset').click(function () {
        view.reset();
        view.set_button_state(view.NEW_RESOURCE);
    })

    $('table').on('dblclick', 'tbody tr', function (e) {
        let $target = $(e.target).parent(),
            service_global = $target.data('global')
            service_name = $target.data('name'),
            service_type = $target.data('type'),
            service_params = $target.data('params'),
            service_resources = $target.data('resources'),
            service_interconnections = $target.data('interconnections');

        view.update_editor({  service_global: service_global, service_name: service_name, service_type: service_type, service_params: service_params, service_resources: service_resources, service_interconnections: service_interconnections });
    });

}(ns.model, ns.view));