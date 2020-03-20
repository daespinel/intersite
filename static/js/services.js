// Create the namespace instance
read_name()
    .done(function (data) {
        // Here we put the data into the name of the PoC
        document.getElementById('service_resources1').placeholder = data;
    })

// Return the API
let ns = {};

// Create the model instance
ns.model = (function () {
    'use strict';

    // Return the API
    return {
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
            //console.log(service);
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
        read_name: function () {
            let ajax_options = {
                type: 'GET',
                url: '/api/region',
                accepts: 'application/json',
                dataType: 'json'
            };
            return $.ajax(ajax_options);
        },
    };
}());

// Create the view instance
ns.view = (function () {
    'use strict';

    const NEW_RESOURCE = 0,
        EXISTING_RESOURCE = 1;

    let $service_global = $('#service_global'),
        $service_name = $('#service_name'),
        $service_type = $('#service_type'),
        $service_params = $('#service_params'),
        $service_resources1 = $('#service_resources1'),
        $service_resources2 = $('#service_resources2'),
        $service_interconnections = $('#service_interconnections'),
        $create = $('#create'),
        $reset = $('#reset');

    // return the API
    return {
        NEW_RESOURCE: NEW_RESOURCE,
        EXISTING_RESOURCE: EXISTING_RESOURCE,
        reset: function () {
            $service_global.text('');
            $service_name.val('');
            $service_params.val('');
            $('#total_chq').val('3');
            $service_interconnections.val('');
            $service_type.val('L3').focus();
            $('#myForm :input').val('');
            read_name();
        },
        set_button_state: function (state) {
            if (state === NEW_RESOURCE) {
                $create.prop('disabled', false);
                $service_type.prop('disabled', false);
                $service_params.prop('disabled', false);
                $service_interconnections.prop('disabled', false);
                $('#service_name').removeAttr('disabled');
                $('#myForm :input').removeAttr('disabled');
            } else if (state === EXISTING_RESOURCE) {
                $create.prop('disabled', true);
                $service_type.prop('disabled', true);
                $service_params.prop('disabled', true);
                $service_interconnections.prop('disabled', true);
            }
        },
        error: function (msg) {
            $.notify({ message: msg }, { type: 'danger' });
        },
        notification: function (msg) {
            $.notify({ message: msg }, { type: 'success' }, { delay: 8000 }, { onClosed: this.redirecting() });
        },
        redirecting: function () {
            setTimeout(() => {
                window.location = '/';
            }, 9000);
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
        $service_resources1 = $('#service_resources1'),
        $service_resources2 = $('#service_resources2'),
        $service_interconnections = $('#service_interconnections');

    // Get the data from the model after the controller is done initializing
    setTimeout(function () {
        view.reset();
    }, 100)

    // generic error handler
    function error_handler(xhr, textStatus, errorThrown) {
        let error_msg = `${textStatus}: ${errorThrown} - ${xhr.responseJSON.detail}`;
        console.log(error_msg);
        view.error(error_msg);
    }
    function notification_handler(notificationThrown) {
        let msg = `${notificationThrown}`;
        view.notification(msg);
        console.log(msg);
    }
    // initialize the button states
    view.set_button_state(view.NEW_RESOURCE);

    // Validate input
    function validate(name, type, resources) {
        var validate_name = name;
        var validate_type = type;
        var validate_resources = resources;

        if (validate_name.length > 32) {
            return false;
        }
        //console.log(validate_type);
        if (validate_type != 'L2') {
            if (validate_type != 'L3') {
                return false;
            }
        }
        if (validate_resources == '') {
            return false;
        }
        return true;
    }

    $('#add_resource').click(function (e) {
        var show_index = parseInt($('#total_chq').val());
        var new_chq_no = show_index + 1;
        var new_res_input = "<tr><td><input id='service_resources1' type='text' class='service_resources form-control' placeholder='Resource Region name'/></td><td><input id='service_resources2' type='text' class='service_resources form-control' placeholder='Resource uuid'/></td><td><span><button id='resource_delete' type='button' class='resource_delete btn btn-danger btn-xs' title='Delete'><i class='fa fa-trash-o fa-button-no-service'></i></button></span></td></tr>";
        $('#resources_container').append(new_res_input);
        $('#total_chq').val(new_chq_no);
    });

    $(document).on('click', '#resources_container tbody tr td button.resource_delete', function (e) {
        var target = $(e.target).parent().parent().parent();
        var last_chq_no = $('#total_chq').val();
        if (last_chq_no > 3) {
            target.remove()
            $('#total_chq').val(last_chq_no - 1);
        }
    });

    // Create our event handlers
    $('#create').click(function (e) {
        var last_chq_no = $('#total_chq').val();
        $('#service_name').prop('disabled', true);
        $('#service_type').prop('disabled', true);
        $('#create').prop('disabled', true);
        $('#add_resource').prop('disabled', true);
        var table = document.getElementById('resources_container');
        var i;
        $('#myForm :input').prop('disabled', true);
        var resources_array = [];
        var resource_region_str = '';
        var resource_uuid_str = '';
        for (i = 0; i < table.rows.length; i++) {
            var row = table.rows[i];
            var cells = row.cells;
            var c;
            for (c = 0; c < cells.length; c++) {
                var cell = cells[c];
                var inputElem = cell.children[0];
                var isInput = inputElem instanceof HTMLInputElement;
                if (isInput) {
                    if (inputElem.id == 'service_resources1')
                        resource_region_str = inputElem.value
                    if (inputElem.id == 'service_resources2')
                        resource_uuid_str = inputElem.value
                }
            }
            resources_array.push(resource_region_str + "," + resource_uuid_str);
        }

        let name = $service_name.val(),
            type = $service_type.val();

        e.preventDefault();
        if (validate(name, type, resources_array)) {
            model.create({ 'name': name, 'type': type, 'resources': resources_array })
                .done(function (data) {
                    var answer_global = data['service_global'];
                    var answer_name = data['service_name'];
                    var answer_type = data['service_type'];
                    var answer_params = data['service_params'][0]['parameter_allocation_pool'];
                    var $output = "Service Created: \n Service global ID: " + answer_global + "\n Service name: " + answer_name + "\n Service type: " + answer_type + "\n Service params: " + answer_params;
                    notification_handler($output);
                })
                .fail(function (xhr, textStatus, errorThrown) {
                    error_handler(xhr, textStatus, errorThrown);
                    view.set_button_state(view.NEW_RESOURCE);

                });


        } else {
            alert('Problem with the validation');
            $('#service_name').removeAttr('disabled');
            $('#service_type').removeAttr('disabled');
            $('#create').prop('disabled', false);
            $('#create').removeAttr('disabled');
            $('#add_resource').prop('disabled', false);
            $('#add_resource').removeAttr('disabled');
            $('#myForm :input').prop('disabled', false);
            $('#myForm :input').removeAttr('disabled');
        }

    });
    $('#reset').click(function (e) {
        view.reset();
        view.set_button_state(view.NEW_RESOURCE);
    });

}(ns.model, ns.view));