/**
 * This is the model class which provides access to the server REST API
 * @type {{}}
 */
class Model {
    async readOne(resource_global) {
        let ajax_options = {
            method: "GET",
            cache: "no-cache",
            headers: {
                "Content-type": "application/json",
                "accepts": "application/json"
            },
        };
        // Call the REST endpoint and wait for data
        let response = await fetch(`/api/intersite-vertical/${resource_global}`, ajax_options);
        let data = await response.json();
        return data;
    }

    async update(resource_global, resource) {
        let ajax_options = {
            method: "PUT",
            cache: "no-cache",
            headers: {
                "Content-type": "application/json",
                "accepts": "application/json"
            },
            body: JSON.stringify(resource)
        };
        // Call the REST endpoint and wait for data
        let response = await fetch(`/api/intersite-vertical/${resource_global}`, ajax_options);
        let data = await response.json();
        return data;
    }
}

/**
 * This is the view class which provides access to the DOM
 */
class View {
    constructor() {
        this.table = document.querySelector(".subresources_container table");
        this.resource_name = document.getElementById("resource_name");
        this.resource_type = document.getElementById("resource_type");
        this.resource_global = document.getElementById("resource_global");
        this.resource_params_master = document.getElementById("resource_params_master");
        this.resource_params_local_cidr = document.getElementById("resource_params_local_cidr");
        this.resource_params_allocation_pool = document.getElementById("resource_params_allocation_pool");
        this.updateButton = document.getElementById("update");
        this.cancelButton = document.getElementById("cancel");
        this.addSubResourceButton = document.getElementById("add_subresource");
    }

    buildTable(resource) {
        let tbody,
            html = "";

        //Update the resource data
        this.resource_global.value = resource.resource_global;
        this.resource_name.value = resource.resource_name;
        this.resource_name.type = resource.resource_type;

        let resource_params = resource.resource_params[0];
        this.resource_params_master.value = resource_params.parameter_master;
        this.resource_params_local_cidr.value = resource_params.parameter_local_cidr;
        this.resource_params_allocation_pool.value = resource_params.parameter_allocation_pool;

        // Iterate over the subresources and build the table
        resource.resource_subresources.forEach((subresource) => {
            html +=
                `<tr data-subresource_id="${subresource.subresource_region}" data-content="${subresource.subresource_uuid}">
                <td>
                    <input id='resource_subresources1' type='text' class='resource_subresources form-control' value="${subresource.subresource_region}" disabled/>
                </td>
                <td>
                    <input id='resource_subresources2' type='text' class='resource_subresources form-control' value="${subresource.subresource_uuid}" disabled/>
                </td>
                <td>
                    <span><button id='subresource_delete' type='button' class='subresource_delete btn btn-danger btn-xs' title='Delete'><i class='fa fa-trash-o fa-button-no-resource'></i></button></span>
                </td>
            </tr>`
        });
        if (this.table.tBodies.length !== 0) {
            this.table.removeChild(this.table.getElementsByTagName("tbody")[0]);
        }
        // Update tbody with our new content
        tbody = this.table.createTBody();
        tbody.innerHTML = html;
        tbody.id = "tbody_subresources";
    }

    errorMessage(msg) {
        $.notify({ message: msg }, { type: 'danger' }, { delay: 8000 });
    }

    validate(name, type, subresources) {
        var validate_name = name;
        var validate_type = type;
        var validate_subresources = subresources;
        var i;
        if (validate_name.length > 32) {
            return false;
        }
        //console.log(validate_type);
        if (validate_type != 'L2') {
            if (validate_type != 'L3') {
                return false;
            }
        }
        console.log(validate_subresources);
        for (i = 0; i < validate_subresources.length; i++) {
            console.log(validate_subresources[i]);
            if (validate_subresources[i] == ',') {
                return false
            }
        }
        if (validate_subresources == '') {
            return false;
        }
        return true;
    }

    error_handler(xhr, textStatus, errorThrown) {
        let error_msg = `${errorThrown}: ${textStatus} - ${xhr}`;
        console.log(error_msg);
        view.error(error_msg);
    }

    notification_handler(notificationThrown) {
        let msg = `${notificationThrown}`;
        view.notification(msg);
        console.log(msg);
    }

    error (msg) {
        $.notify({ message: msg }, { type: 'danger' }, { delay: 8000 }, { onClosed: this.redirecting_update() });
    }

    notification (msg) {
        $.notify({ message: msg }, { type: 'success' }, { delay: 8000 }, { onClosed: this.redirecting_home() });
    }

    redirecting_home (){
        setTimeout(() => {
            window.location = '/';
        }, 9000);
    }

    redirecting_update (){
        setTimeout(() => {
            let global_url = document.getElementById("resource_global").value;
            window.location = '/resource/' + global_url;
        }, 9000);
    }
}

/**
 * This is the controller class for the user interaction
 */
class Controller {
    constructor(model, view) {
        this.model = model;
        this.view = view;

        this.initialize();
    }

    async initialize() {
        await this.initializeTable();
        this.initializeCancelEvent();
        this.initializeAddSubResourceEvent();
        this.initializeDeleteSubResource();
        this.initializeUpdateResource();
    }

    async initializeTable() {
        try {
            let urlResourceGlobal = document.getElementById("url_resource_global").value,
                resource = await this.model.readOne(urlResourceGlobal);
            this.view.buildTable(resource);
        } catch (err) {
            this.view.errorMessage(err);
        }
    }


    initializeCancelEvent() {
        document.getElementById("cancel").addEventListener("click", async (evt) => {
            evt.preventDefault();
            if (confirm("Are you sure to cancel the resource update?")) {
                window.location.href = "/";
            };
        });
    }

    initializeAddSubResourceEvent() {
        document.getElementById("add_subresource").addEventListener("click", async (evt) => {
            evt.preventDefault();
            var show_index = parseInt($('#total_chq').val());
            var new_chq_no = show_index + 1;
            var new_res_input = `
            <tr>
                <td>
                    <input id='resource_subresources1' type='text' class='resource_subresources form-control' placeholder='SubResource Region name'/>
                </td>
                <td>
                    <input id='resource_subresources2' type='text' class='resource_subresources form-control' placeholder='SubResource uuid'/>
                </td>
                <td>
                    <span><button id='subresource_delete' type='button' class='subresource_delete btn btn-danger btn-xs' title='Delete'><i class='fa fa-trash-o fa-button-no-resource'></i></button></span>
                </td>
            </tr>`;
            $('#tbody_subresources').append(new_res_input);
            $('#total_chq').val(new_chq_no);
        });
    }

    initializeDeleteSubResource() {
        $(document).on('click', '#subresources_container tbody tr td button.subresource_delete', function (e) {
            var target = $(e.target).parent().parent().parent();
            var last_chq_no = $('#total_chq').val();
            if (last_chq_no > 3) {
                target.remove()
                console.log(target)
                $('#total_chq').val(last_chq_no - 1);
            }
        });
    }

    initializeUpdateResource() {
        var self = this;
        document.getElementById("update").addEventListener("click", async (evt) => {
            var last_chq_no = $('#total_chq').val();
            $('#update').prop('disabled', true);
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
                subresources_array.push(subresource_region_str + "," + subresource_uuid_str)
            }

            let global = document.getElementById("resource_global").value,
                type = document.getElementById("resource_type").value,
                name = document.getElementById("resource_name").value;


            evt.preventDefault();
            if (self.view.validate(name, type, subresources_array)) {
                try {
                    let response = await this.model.update(global, { 'subresources': subresources_array });
                    if (response['status'] == 404) {
                        console.log(response);
                        self.view.error_handler(response['title'], response['status'], response['detail']);
                    }
                    console.log(response);
                    var answer_global = response['resource_global'];
                    var $output = "Resource Updated: \n Resource global ID: " + answer_global;
                    //self.view.notification_handler($output);
                    //})
                    //.fail(function (xhr, textStatus, errorThrown) {
                     //   self.view.error_handler(xhr, textStatus, errorThrown);
                     //   });
                    
                } catch (err) {
                    self.view.error_handler(err)
                }

            } else {
                alert('Problem with the validation: check the list of resources');
            }
        });
    }
}
// Create the MVC components
const model = new Model();
const view = new View();
const controller = new Controller(model, view);

// export the MVC components as the default
export default {
    model,
    view,
    controller
};