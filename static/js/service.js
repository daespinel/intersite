/**
 * This is the model class which provides access to the server REST API
 * @type {{}}
 */
class Model {
    async readOne(service_global) {
        let ajax_options = {
            method: "GET",
            cache: "no-cache",
            headers: {
                "Content-type": "application/json",
                "accepts": "application/json"
            },
        };
        // Call the REST endpoint and wait for data
        let response = await fetch(`/api/intersite-vertical/${service_global}`, ajax_options);
        let data = await response.json();
        return data;
    }

    async update(service_global, service) {
        let ajax_options = {
            method: "PUT",
            cache: "no-cache",
            headers: {
                "Content-type": "application/json",
                "accepts": "application/json"
            },
            body: JSON.stringify(service)
        };
        // Call the REST endpoint and wait for data
        let response = await fetch(`/api/intersite-vertical/${service_global}`, ajax_options);
        let data = await response.json();
        return data;
    }
}

/**
 * This is the view class which provides access to the DOM
 */
class View {
    constructor() {
        this.table = document.querySelector(".resources_container table");
        this.service_global = document.getElementById("service_global");
        this.service_name = document.getElementById("service_name");
        this.service_type = document.getElementById("service_type");
        this.service_params_master = document.getElementById("service_params_master");
        this.service_params_local_cidr = document.getElementById("service_params_local_cidr");
        this.service_params_allocation_pool = document.getElementById("service_params_allocation_pool");
        this.updateButton = document.getElementById("update");
        this.cancelButton = document.getElementById("cancel");
        this.addResourceButton = document.getElementById("add_resource");
    }

    buildTable(service) {
        let tbody,
            html = "";

        //Update the service data
        this.service_global.value = service.service_global;
        this.service_name.value = service.service_name;
        this.service_name.type = service.service_type;

        let service_params = service.service_params[0];
        this.service_params_master.value = service_params.parameter_master;
        this.service_params_local_cidr.value = service_params.parameter_local_cidr;
        this.service_params_allocation_pool.value = service_params.parameter_allocation_pool;

        // Iterate over the resources and build the table
        service.service_resources.forEach((resource) => {
            html +=
                `<tr data-resource_id="${resource.resource_region}" data-content="${resource.resource_uuid}">
                <td>
                    <input id='service_resources1' type='text' class='service_resources form-control' value="${resource.resource_region}" disabled/>
                </td>
                <td>
                    <input id='service_resources2' type='text' class='service_resources form-control' value="${resource.resource_uuid}" disabled/>
                </td>
                <td>
                    <span><button id='resource_delete' type='button' class='resource_delete btn btn-danger btn-xs' title='Delete'><i class='fa fa-trash-o fa-button-no-service'></i></button></span>
                </td>
            </tr>`
        });
        if (this.table.tBodies.length !== 0) {
            this.table.removeChild(this.table.getElementsByTagName("tbody")[0]);
        }
        // Update tbody with our new content
        tbody = this.table.createTBody();
        tbody.innerHTML = html;
    }

    errorMessage(msg) {
        $.notify({ message: msg }, { type: 'danger' }, { delay: 8000 });
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
        this.initializeAddResourceEvent();
        this.initializeDeleteResource();
    }

    async initializeTable() {
        try {
            let urlServiceGlobal = document.getElementById("url_service_global").value,
                service = await this.model.readOne(urlServiceGlobal);
            this.view.buildTable(service);
        } catch (err) {
            this.view.errorMessage(err);
        }
    }

    initializeCancelEvent() {
        document.getElementById("cancel").addEventListener("click", async (evt) => {
            evt.preventDefault();
            if (confirm("Are you sure to cancel the service update?")) {
                window.location.href = "/";
            };
        });
    }

    initializeAddResourceEvent() {
        document.getElementById("add_resource").addEventListener("click", async (evt) => {
            evt.preventDefault();
            var show_index = parseInt($('#total_chq').val());
            var new_chq_no = show_index + 1;
            var new_res_input = `
            <tr>
                <td>
                    <input id='service_resources1' type='text' class='service_resources form-control' placeholder='Resource Region name'/>
                </td>
                <td>
                    <input id='service_resources2' type='text' class='service_resources form-control' placeholder='Resource uuid'/>
                </td>
                <td>
                    <span><button id='resource_delete' type='button' class='resource_delete btn btn-danger btn-xs' title='Delete'><i class='fa fa-trash-o fa-button-no-service'></i></button></span>
                </td>
            </tr>`;
            $('#resources_container').append(new_res_input);
            $('#total_chq').val(new_chq_no);
        });
    }

    initializeDeleteResource() {
        $(document).on('click', '#resources_container tbody tr td button.resource_delete', function (e) {
            var target = $(e.target).parent().parent().parent();
            var last_chq_no = $('#total_chq').val();
            if (last_chq_no > 3) {
                target.remove()
                $('#total_chq').val(last_chq_no - 1);
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