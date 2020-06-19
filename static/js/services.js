// Create the namespace instance
read_name()
    .done(function (data) {
        // Here we put the data into the name of the PoC
        document.getElementById('resource_subresources1').placeholder = data;
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
        create: function (resource) {
            //console.log(resource);
            let ajax_options = {
                type: 'POST',
                url: '/api/intersite-vertical',
                accepts: 'application/json',
                contentType: 'application/json',
                dataType: 'json',
                data: JSON.stringify(resource)
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

    let $resource_global = $('#resource_global'),
        $resource_name = $('#resource_name'),
        $resource_type = $('#resource_type'),
        $resource_params = $('#resource_params'),
        $resource_subresources1 = $('#resource_subresources1'),
        $resource_subresources2 = $('#resource_subresources2'),
        $resource_interconnections = $('#resource_interconnections'),
        $create = $('#create'),
        $reset = $('#reset');

    // return the API
    return {
        NEW_RESOURCE: NEW_RESOURCE,
        EXISTING_RESOURCE: EXISTING_RESOURCE,
        reset: function () {
            $resource_global.text('');
            $resource_name.val('');
            $resource_params.val('');
            $('#total_chq').val('3');
            $resource_interconnections.val('');
            $resource_type.val('L3').focus();
            $('#myForm :input').val('');
            read_name();
        },
        set_button_state: function (state) {
            if (state === NEW_RESOURCE) {
                $create.prop('disabled', false);
                $resource_type.prop('disabled', false);
                $resource_params.prop('disabled', false);
                $resource_interconnections.prop('disabled', false);
                $('#resource_name').removeAttr('disabled');
                $('#myForm :input').removeAttr('disabled');
            } else if (state === EXISTING_RESOURCE) {
                $create.prop('disabled', true);
                $resource_type.prop('disabled', true);
                $resource_params.prop('disabled', true);
                $resource_interconnections.prop('disabled', true);
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
        $url_resource_global = $('#url_resource_global'),
        $resource_global = $('#resource_global'),
        $resource_name = $('#resource_name'),
        $resource_type = $('#resource_type'),
        $resource_params = $('#resource_params'),
        $resource_subresources1 = $('#resource_subresources1'),
        $resource_subresources2 = $('#resource_subresources2'),
        $resource_interconnections = $('#resource_interconnections');

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
    function validate(name, type, subresources) {
        var validate_name = name;
        var validate_type = type;
        var validate_subresources = subresources;

        if (validate_name.length > 32) {
            return false;
        }
        //console.log(validate_type);
        if (validate_type != 'L2') {
            if (validate_type != 'L3') {
                return false;
            }
        }
        if (validate_subresources == '') {
            return false;
        }
        return true;
    }

    $('#add_subresource').click(function (e) {
        var show_index = parseInt($('#total_chq').val());
        var new_chq_no = show_index + 1;
        var new_res_input = "<tr><td><input id='resource_subresources1' type='text' class='resource_subresources form-control' placeholder='subResource Region name'/></td><td><input id='resource_subresources2' type='text' class='resource_subresources form-control' placeholder='subResource uuid'/></td><td><span><button id='subresource_delete' type='button' class='subresource_delete btn btn-danger btn-xs' title='Delete'><i class='fa fa-trash-o fa-button-no-resource'></i></button></span></td></tr>";
        $('#subresources_container').append(new_res_input);
        $('#total_chq').val(new_chq_no);
    });

    $(document).on('click', '#subresources_container tbody tr td button.subresource_delete', function (e) {
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
        $('#resource_name').prop('disabled', true);
        $('#resource_type').prop('disabled', true);
        $('#create').prop('disabled', true);
        $('#add_subresource').prop('disabled', true);
        var table = document.getElementById('subresources_container');
        var i;
        $('#myForm :input').prop('disabled', true);
        var subresources_array = [];
        var subresource_region_str = '';
        var subresource_uuid_str = '';
        for (i = 0; i < table.rows.length; i++) {
            var row = table.rows[i];
            var cells = row.cells;
            var c;
            for (c = 0; c < cells.length; c++) {
                var cell = cells[c];
                var inputElem = cell.children[0];
                var isInput = inputElem instanceof HTMLInputElement;
                if (isInput) {
                    if (inputElem.id == 'resource_subresources1')
                        subresource_region_str = inputElem.value
                    if (inputElem.id == 'resource_subresources2')
                        subresource_uuid_str = inputElem.value
                }
            }
            subresources_array.push(subresource_region_str + "," + subresource_uuid_str);
        }

        let name = $resource_name.val(),
            type = $resource_type.val();

        e.preventDefault();
        if (validate(name, type, subresources_array)) {
            model.create({ 'name': name, 'type': type, 'subresources': subresources_array })
                .done(function (data) {
                    var answer_global = data['resource_global'];
                    var answer_name = data['resource_name'];
                    var answer_type = data['resource_type'];
                    var answer_params = data['resource_params'][0]['parameter_allocation_pool'];
                    var $output = "Resource Created: \n Resource global ID: " + answer_global + "\n Resource name: " + answer_name + "\n Resource type: " + answer_type + "\n Resource params: " + answer_params;
                    notification_handler($output);
                })
                .fail(function (xhr, textStatus, errorThrown) {
                    error_handler(xhr, textStatus, errorThrown);
                    view.set_button_state(view.NEW_RESOURCE);

                });


        } else {
            alert('Problem with the validation: check the infos');
            $('#resource_name').removeAttr('disabled');
            $('#resource_type').removeAttr('disabled');
            $('#create').prop('disabled', false);
            $('#create').removeAttr('disabled');
            $('#add_subresource').prop('disabled', false);
            $('#add_subresource').removeAttr('disabled');
            $('#myForm :input').prop('disabled', false);
            $('#myForm :input').removeAttr('disabled');
        }

    });
    $('#reset').click(function (e) {
        view.reset();
        view.set_button_state(view.NEW_RESOURCE);
    });

}(ns.model, ns.view));