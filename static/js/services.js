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
        read: function () {
            let ajax_options = {
                type: 'GET',
                url: 'api/intersite-vertical',
                accepts: 'application/json',
                dataType: 'json'
            };
            return $.ajax(ajax_options)
        },
        create: function (name, type, resources) {
            console.log("joder");
            console.info("joder");
            let ajax_options = {
                type: 'POST',
                url: 'api/intersite-vertical',
                accepts: 'application/json',
                contentType: 'application/json',
                dataType: 'json',
                data: JSON.stringify({
                    'name': name,
                    'type': type,
                    'resources': resources
                })
            };
            return $.ajax(ajax_options)
        },
        update: function (id) {
            let ajax_options = {
                type: 'PUT',
                url: 'api/intersite-vertical/' + id,
                accepts: 'application/json',
                contentType: 'application/json',
                dataType: 'json',
                data: JSON.stringify({
                    'id': id
                })
            };
            return $.ajax(ajax_options)
        },
        'delete': function (id) {
            let ajax_options = {
                type: 'DELETE',
                url: 'api/intersite-vertical/' + id,
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

    const NEW_RESOURCE = 0,
        EXISTING_RESOURCE = 1;

    let $service_id = $('#id'),
        $global = $('#global'),
        $name = $('#name'),
        $type = $('#type'),
        $resources = $('#resources'),
        $interconnections = $('#interconnections'),
        $create = $('#create'),
        $update = $('#update'),
        $delete = $('#delete'),
        $reset = $('#reset');

    // return the API
    return {
        NEW_RESOURCE: NEW_RESOURCE,
        EXISTING_RESOURCE: EXISTING_RESOURCE,
        reset: function () {
            $service_id.val('');
            $global.val('');
            $name.val('');
            $type.val('');
            $resources.val('');
            $interconnections.val('').focus();
        },
        update_editor: function (id) {
            $id.val(id).focus();
        },
        build_table: function (service) {
            let source = $('#blog-table-template').html(),
                template = Handlebars.compile(source),
                html;

            // clear the table
            $('.blog table > tbody').empty();

            // did we get a service array?
            if (service) {
                html = template({ service: service })
                $('table > tbody').append(html);
            }
        },
        error: function (error_msg) {
            $('.error')
                .text(error_msg)
                .css('visibility', 'visible');
            setTimeout(function () {
                $('.error').css('visibility', 'hidden');
            }, 3000)
        }
    };
}());

// Create the controller
ns.controller = (function (m, v) {
    'use strict';

    let model = m,
        view = v,
        $url_service_id = $('#url_service_id')
        $service_id = $('#service_id'),
        $service_global = $('#global'),
        $service_name = $('#name'),
        $service_type = $('#type'),
        $service_params = $('#params'),
        $service_resources = $('#resources'),
        $service_interconnections = $('#interconnections');

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

        if ($url_service_id.val() !== "") {
            model.read_one(parseInt($url_service_id.val()))
                .done(function (data) {
                    view.update_editor(data);
                    view.set_button_state(view.EXISTING_RESOURCE);
                })
                .fail(function (xhr, textStatus, errorThrown) {
                    error_handler(xhr, textStatus, errorThrown);
                });
        }
    }, 100)

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
    })

    $('table').on('dblclick', 'tbody tr', function (e) {
        let $target = $(e.target).parent(),
            service_id = $target.data('service_id'),
            global = $target.data('global')
            name = $target.data('name'),
            type = $target.data('type'),
            params = $target.data('params'),
            resources = $target.data('resources'),
            interconnections = $target.data('interconnections');

        view.update_editor({ service_id: service_id, global: global, name: name, type: type, params: params, resources: resources, interconnections: interconnections });
    });

    // Handle the model events
    $event_pump.on('model_read_success', function (e, data) {
        view.build_table(data);
        view.reset();
    });

    $event_pump.on('model_create_success', function (e, data) {
        model.read();
    });

    $event_pump.on('model_update_success', function (e, data) {
        model.read();
    });

    $event_pump.on('model_delete_success', function (e, data) {
        model.read();
    });

    $event_pump.on('model_error', function (e, xhr, textStatus, errorThrown) {
        let error_msg = textStatus + ': ' + errorThrown + ' - ' + xhr.responseJSON.detail;
        view.error(error_msg);
        console.log(error_msg);
        console.log("joder");
    })
}(ns.model, ns.view));