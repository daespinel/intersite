/*
 * JavaScript file for the application to demonstrate
 * using the API
 */

$('.add_resource').on('click', add);
//$('.remove').on('click', remove);

$('#total_index_1').val(5);
$('#total_index_2').val(6); 

function add() {
    var new_chq_no = parseInt($('#total_chq').val()) + 1;
    var show_index = new_chq_no - 2;
    var id_1 = parseInt($('#total_index_1').val());
    var id_2 = parseInt($('#total_index_2').val());
    var new_input = "<input type='text' maxlength='200' id='service_resources" + id_1 + "' class='service_resources" + new_chq_no + " service_input' placeholder='Resource Region name #"+ show_index +"'> <input type='text' maxlength='200' id='service_resources" + id_2 + "' class='service_resources" + new_chq_no + " service_input' placeholder='Resource uuid #"+ show_index +"'> <br/>";
    var new_id_1 = id_1+2;
    var new_id_2 = id_2+2;

    $('#resource_container').append(new_input);

    $('#total_chq').val(new_chq_no);
    $('#total_index_1').val(new_id_1);
    $('#total_index_2').val(new_id_2); 
}

/*function remove() {
  var last_chq_no = $('#total_chq').val();

  if (last_chq_no > 1) {
    $('#new_' + last_chq_no).remove();
    $('#total_chq').val(last_chq_no - 1);
  }
}*/

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
        $service_resources2 = $('#service_resources2'),
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
            $service_resources.val('');
            $service_resources2.val('');
            $service_interconnections.val('');
            $service_type.val('').focus();
        },
        update_editor: function (service) {
            $service_global.text(service.service_global);
            $service_name.val(service.service_name);
            $service_params.val(service.service_params);
            var array_service = service.service_resources;
            console.log(array_service);
            $service_resources.val(array_service);
            //$service_resources2.val(service.service_resources2);
            $service_interconnections.val(service.service_interconnections);
            $service_type.val(service.service_type).focus();
        },
        set_button_state: function (state) {
            if (state === NEW_RESOURCE) {
                $create.prop('disabled', false);
                $update.prop('disabled', true);
                $delete.prop('disabled', true);
                $service_type.prop('disabled', false);
                $service_params.prop('disabled', false);
                $service_interconnections.prop('disabled', false);
            } else if (state === EXISTING_RESOURCE) {
                $create.prop('disabled', true);
                $update.prop('disabled', false);
                $delete.prop('disabled', false);
                $service_type.prop('disabled', true);
                $service_params.prop('disabled', true);
                $service_interconnections.prop('disabled', true);
            }
        },
        build_table: function (data) {

            let source = $('#services-table-template').html(),
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
        $service_resources2 = $('#service_resources2'),
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
                    console.log(data);
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
        let name = $service_name.val(),
            type = $service_type.val();
        //console.log(name);
        var id_total_resources = parseInt($('#total_index_2').val())-2;
        var i;
        var resources_array= [];
        for (i = 1; i < id_total_resources;i=i+2){
            var resource_region_str = "#service_resources" + String(i);
            var resource_uuid_str = "#service_resources" + String(i+1);
            var resource_region_temp = $(resource_region_str).val();
            var resource_uuid_temp = $(resource_uuid_str).val();
            resources_array.push(resource_region_temp+"-"+resource_uuid_temp);

        }
        console.log(resources_array);

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

    $('table').on('click', 'tbody tr', function (e) {
        let $target = $(e.target).parent(),
            service_global = $target.data('service_global')
        service_name = $target.data('service_name'),
            service_type = $target.data('service_type'),
            service_params = $target.data('service_params'),
            service_resources = $target.data('service_resources'),
            service_interconnections = $target.data('service_interconnections');
        //console.log(service_interconnections);

        var array = service_resources.split("*");
        array.pop();

        view.update_editor({
            service_global: service_global,
            service_name: service_name,
            service_type: service_type,
            service_params: service_params,
            service_resources: array,
            service_interconnections: service_interconnections,
        });
        view.set_button_state(view.EXISTING_RESOURCE);
    });

}(ns.model, ns.view));