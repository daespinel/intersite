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
    constructor() {}
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