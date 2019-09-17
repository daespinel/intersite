/*
 * JavaScript file for the application to demonstrate
 * using the API
 */
$('#total_index_1').val(5);
$('#total_index_2').val(6); 
 /*
$('#add_resource').on('click', add_res);
$('.remove').on('click', remove_res);




function add_res() {
    var show_index = parseInt($('#total_chq').val());
    var new_chq_no = show_index + 1;
    var id_1 = parseInt($('#total_index_1').val());
    var id_2 = parseInt($('#total_index_2').val());
    var new_input = "<input type='text' maxlength='200' id='service_resources" + id_1 + "' class='service_resources" + new_chq_no + " service_input' placeholder='Resource Region name #"+ show_index +"'> <input type='text' maxlength='200' id='service_resources" + id_2 + "' class='service_resources" + new_chq_no + " service_input' placeholder='Resource uuid #"+ show_index +"'> <br/>";
    var new_res_input = "<tr><td><label>"+show_index+"</label></td><td><input id='service_resources"  + id_1 +"' type='text' class='service_resources"  + new_chq_no + " form-control' placeholder='Resource Region name'/></td><td><input id='service_resources" +id_2+ "' type='text' class='service_resources" + new_chq_no + " form-control' placeholder='Resource uuid'/></td><td><span><i class='fa fa-trash-o'></i></span></td></tr>";
    var new_id_1 = id_1+2;
    var new_id_2 = id_2+2;
    //console.log(new_res_input);
    
    //var table_resources = document.getElementById('resources_container');
    //var new_row = table_resources.rows[0].cloneNode(true);
    //var len = table_resources.rows.length;
    //table_resources.appendChild(new_row);
    //new_row.cells[0].innerHTML = new_res_input;
    $('#resources_container').append(new_res_input);
    

    $('#total_chq').val(new_chq_no);
    $('#total_index_1').val(new_id_1);
    $('#total_index_2').val(new_id_2); 
}

function remove_res() {
  var last_chq_no = $('#total_chq').val();
  var last_index_1 = $('#total_index_1').val()-2;
  var last_index_2 = $('#total_index_2').val()-2;

  if (last_chq_no > 3) {
    var identi = '#service_resources' + String(last_index_1); 
    var valor = $('#service_resources' + last_index_1).val();
    console.log(valor);
    console.log(identi)
    $('#service_resources' + last_index_1).remove();
    $('#service_resources' + last_index_2).remove();
    $('#total_chq').val(last_chq_no - 1);
    $('#total_index_1').val(last_index_1 - 2);
    $('#total_index_2').val(last_index_2 - 2);
  }
}
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
        }
        
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
        $service_resources = $('#service_resources'),
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
            $('#total_index_1').val('5');
            $('#total_index_2').val('6'); 
            $service_interconnections.val('');
            $service_type.val('').focus();
        },
        set_button_state: function (state) {
            if (state === NEW_RESOURCE) {
                $create.prop('disabled', false);
                $service_type.prop('disabled', false);
                $service_params.prop('disabled', false);
                $service_interconnections.prop('disabled', false);
            } else if (state === EXISTING_RESOURCE) {
                $create.prop('disabled', true);
                $service_type.prop('disabled', true);
                $service_params.prop('disabled', true);
                $service_interconnections.prop('disabled', true);
            }
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
    }, 100)

    // generic error handler
    function error_handler(xhr, textStatus, errorThrown) {
        let error_msg = `${textStatus}: ${errorThrown} - ${xhr.responseJSON.detail}`;
        view.error(error_msg);
        alert(error_msg);
        $('#service_name').prop('disabled', false);
        $('#service_type').prop('disabled', false);
        $('#create').prop('disabled', false);
        $('#add_resource').prop('disabled', false);
        $('#remove').prop('disabled', false);
        var id_total_resources = parseInt($('#total_index_2').val())-2;
        var i;
        for (i = 1; i < id_total_resources;i=i+2){
            $('#service_resources' + + String(i)).prop('disabled', false);
            $('#service_resources' + + String(i+1)).prop('disabled', false);
        }
        console.log(error_msg);

    }
    // initialize the button states
    view.set_button_state(view.NEW_RESOURCE);

    // Validate input
    function validate(name, type, resources) {
        var validate_name=name;
        var validate_type = type;
        var validate_resources = resources;
        
        if(validate_name.length > 32){
            console.log('Problem with the name');
            return false;
        }
        //console.log(validate_type);
        if(validate_type != 'L2'){
            if(validate_type != 'L3'){
                console.log('problem with type');
            return false;
            }
        }

        if(validate_resources == ''){
            console.log('problem with resources');
            return false;
        }

        return true;
    }

    $('#add_resource').click(function(e){
        var show_index = parseInt($('#total_chq').val());
        var new_chq_no = show_index + 1;
        var id_1 = parseInt($('#total_index_1').val());
        var id_2 = parseInt($('#total_index_2').val());
        //var new_input = "<input type='text' maxlength='200' id='service_resources" + id_1 + "' class='service_resources" + new_chq_no + " service_input' placeholder='Resource Region name #"+ show_index +"'> <input type='text' maxlength='200' id='service_resources" + id_2 + "' class='service_resources" + new_chq_no + " service_input' placeholder='Resource uuid #"+ show_index +"'> <br/>";
        var new_res_input = "<tr><td><label>"+show_index+"</label></td><td><input id='service_resources"  + id_1 +"' type='text' class='service_resources"  + new_chq_no + " form-control' placeholder='Resource Region name'/></td><td><input id='service_resources" +id_2+ "' type='text' class='service_resources" + new_chq_no + " form-control' placeholder='Resource uuid'/></td><td><span><i class='fa fa-trash-o'></i></span></td></tr>";
        var new_id_1 = id_1+2;
        var new_id_2 = id_2+2;
        console.log(new_res_input);
        
        //var table_resources = document.getElementById('resources_container');
        //var new_row = table_resources.rows[0].cloneNode(true);
        //var len = table_resources.rows.length;
        //table_resources.appendChild(new_row);
        //new_row.cells[0].innerHTML = new_res_input;
        $('#resources_container').append(new_res_input);
        

        $('#total_chq').val(new_chq_no);
        $('#total_index_1').val(new_id_1);
        $('#total_index_2').val(new_id_2);
        //return false;
    });

    $('#remove_resource').click(function(e){
        var last_chq_no = $('#total_chq').val();
        var last_index_1 = $('#total_index_1').val()-2;
        var last_index_2 = $('#total_index_2').val()-2;

        if (last_chq_no > 3) {
            var identi = '#service_resources' + String(last_index_1); 
            var valor = $('#service_resources' + last_index_1).val();
            console.log(valor);
            console.log(identi)
            $('#service_resources' + last_index_1).remove();
            $('#service_resources' + last_index_2).remove();
            $('#total_chq').val(last_chq_no - 1);
            $('#total_index_1').val(last_index_1 - 2);
            $('#total_index_2').val(last_index_2 - 2);
        }
    });

    // Create our event handlers
    $('#create').click(function (e) {
        $('#service_name').prop('disabled', true);
        $('#service_type').prop('disabled', true);
        $('#create').prop('disabled', true);
        $('#add_resource').prop('disabled', true);
        $('#remove').prop('disabled', true);
        var id_total_resources = parseInt($('#total_index_2').val())-2;
        for (i = 1; i < id_total_resources;i=i+2){
            $('#service_resources' + + String(i)).prop('disabled', true);
            $('#service_resources' + + String(i+1)).prop('disabled', true);
        }
        let name = $service_name.val(),
            type = $service_type.val();
        console.log(name);
        
        var i;
        var resources_array= [];
        for (i = 1; i < id_total_resources;i=i+2){
            var resource_region_str = "#service_resources" + String(i);
            var resource_uuid_str = "#service_resources" + String(i+1);
            var resource_region_temp = $(resource_region_str).val();
            var resource_uuid_temp = $(resource_uuid_str).val();
            resources_array.push(resource_region_temp+","+resource_uuid_temp);

        }
        console.log(resources_array);

        e.preventDefault();
        if (validate(name, type, resources_array)) {
            model.create({'name':name, 'type':type, 'resources':resources_array})
            .done(function(data) {
                var answer_global = data['service_global'];
                var answer_name = data['service_name'];
                var answer_type = data['service_type'];
                var answer_params = data['service_params'];
                var $output = "Service Created: \n Service global ID: "+ answer_global + "\n Service name: "+answer_name +"\n Service type: "+answer_type + "\n Service params: "+answer_params;
                console.log($output);
                alert($output);
                window.location = '/';
            })
            .fail(function(xhr, textStatus, errorThrown) {
                error_handler(xhr, textStatus, errorThrown);
            });

        view.reset();
        } else {
            alert('Problem with the validation');
        }
    });

    $('#reset').click(function (e) {
        view.reset();
        view.set_button_state(view.NEW_RESOURCE);
    });


}(ns.model, ns.view));