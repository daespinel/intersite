/*
 * JavaScript file for the application to demonstrate
 * using the API
 */

// Create the namespace instance
let ns = {};

// Create the model instance
ns.model = (function() {
    'use strict';

    let $event_pump = $('body');

    // Return the API
    return {
        'read': function() {
            let ajax_options = {
                type: 'GET',
                url: 'api/intersite-vertical',
                accepts: 'application/json',
                dataType: 'json'
            };
            $.ajax(ajax_options)
            .done(function(data) {
                $event_pump.trigger('model_read_success', [data]);
            })
            .fail(function(xhr, textStatus, errorThrown) {
                $event_pump.trigger('model_error', [xhr, textStatus, errorThrown]);
            })
        },
        create: function(name, type, resources) {
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
                //data: {'name': name,
                //       'type': type,
                //       'resources': resources}
            };
            console.log("joder");
            $.ajax(ajax_options)
            .done(function(data) {
                $event_pump.trigger('model_create_success', [data]);
            })
            .fail(function(xhr, textStatus, errorThrown) {
                $event_pump.trigger('model_error', [xhr, textStatus, errorThrown]);
            })
        },
        update: function(id) {
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
            $.ajax(ajax_options)
            .done(function(data) {
                $event_pump.trigger('model_update_success', [data]);
            })
            .fail(function(xhr, textStatus, errorThrown) {
                $event_pump.trigger('model_error', [xhr, textStatus, errorThrown]);
            })
        },
        'delete': function(id) {
            let ajax_options = {
                type: 'DELETE',
                url: 'api/intersite-vertical/' + id,
                accepts: 'application/json',
                contentType: 'plain/text'
            };
            $.ajax(ajax_options)
            .done(function(data) {
                $event_pump.trigger('model_delete_success', [data]);
            })
            .fail(function(xhr, textStatus, errorThrown) {
                $event_pump.trigger('model_error', [xhr, textStatus, errorThrown]);
            })
        }
    };
}());

// Create the view instance
ns.view = (function() {
    'use strict';

    let $id = $('#id'),
        $name = $('#name'),
        $type = $('#type'),
        $resources = $('#resources'),
        $interconnections = $('#interconnections');

    // return the API
    return {
        reset: function() {
            $id.val('');
            $name.val('');
            $type.val('');
            $resources.val('');
            $interconnections.val('').focus();
        },
        update_editor: function(id) {
            $id.val(id).focus();
        },
        build_table: function(service) {
            let rows = ''

            // clear the table
            $('.service table > tbody').empty();

            // did we get a service array?
            if (service) {
                for (let i=0, l=service.length; i < l; i++) {
                    rows += `<tr><td class="id">${service[i].id}</td><td class="name">${service[i].name}</td><td class="type">${service[i].type}</td><td class="resources">${service[i].resources}</td><td class="interconnections">${service[i].interconnections}</td></tr>`;
                }
                $('table > tbody').append(rows);
            }
        },
        error: function(error_msg) {
            $('.error')
                .text(error_msg)
                .css('visibility', 'visible');
            setTimeout(function() {
                $('.error').css('visibility', 'hidden');
            }, 3000)
        }
    };
}());

// Create the controller
ns.controller = (function(m, v) {
    'use strict';

    let model = m,
        view = v,
        $event_pump = $('body'),
        $id = $('#id'),
        $name = $('#name'),
        $type = $('#type'),
        $resources = $('#resources'),
        $interconnections = $('#interconnections');

    // Get the data from the model after the controller is done initializing
    setTimeout(function() {
        model.read();
    }, 100)

    // Validate input
    function validate(type,resources) {
        return type !== "" && resources !== "";
    }

    // Create our event handlers
    $('#create').click(function(e) {
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

    $('#update').click(function(e) {
        let id = $id.val();

        e.preventDefault();

        if (validate(type, resources)) {
            model.update(type, resources)
        } else {
            alert('Problem with type or resources input');
        }
        e.preventDefault();
    });

    $('#delete').click(function(e) {
        let id = $id.val();

        e.preventDefault();

        if (validate('placeholder', lname)) {
            model.delete(id)
        } else {
            alert('Problem with ID');
        }
        e.preventDefault();
    });

    $('#reset').click(function() {
        view.reset();
    })

    $('table > tbody').on('dblclick', 'tr', function(e) {
        let $target = $(e.target),
            id,
            name,
            type,
            resources,
            interconnections;

        id = $target
            .parent()
            .find('td.id')
            .text();

        name = $target
            .parent()
            .find('td.name')
            .text();

        type = $target
            .parent()
            .find('td.type')
            .text();

        resources = $target
            .parent()
            .find('td.resources')
            .text();

        interconnections = $target
            .parent()
            .find('td.interconnections')
            .text();

        view.update_editor(id, name, type, resources, interconnections);
    });

    // Handle the model events
    $event_pump.on('model_read_success', function(e, data) {
        view.build_table(data);
        view.reset();
    });

    $event_pump.on('model_create_success', function(e, data) {
        model.read();
    });

    $event_pump.on('model_update_success', function(e, data) {
        model.read();
    });

    $event_pump.on('model_delete_success', function(e, data) {
        model.read();
    });

    $event_pump.on('model_error', function(e, xhr, textStatus, errorThrown) {
        let error_msg = textStatus + ': ' + errorThrown + ' - ' + xhr.responseJSON.detail;
        view.error(error_msg);
        console.log(error_msg);
        console.log("joder");
    })
}(ns.model, ns.view));