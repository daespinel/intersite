from flask import Flask
from flask import render_template
import common.utils as service_utils
import connexion
import logging
import re

# Create the application instance
app = connexion.App(__name__, specification_dir='./config/')
logging.basicConfig(format='%(asctime)s.%(msecs)03d %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d,%H:%M:%S', level=logging.INFO)


def main():
    # Read the swagger.yml file to configure the endpoints
    app.add_api('swagger.yml')
    host = service_utils.get_local_host()
    app.run(host=host, port=7575, debug=True)


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/resources")
@app.route("/resources/<string:resource_global>")
def resources(resource_global=""):
    """
    This function just responds to the browser URL
    localhost:7575/resources
    :return:        the rendered template "services.html"
    """
    return render_template("services.html", resource_global=resource_global)


@app.route("/resource/<string:resource_global>")
def resource(resource_global):
    """
    This function responds to the browser URL
    localhost:7575/resource/<person_id>

    :param resource_global:   Id of the resource to show notes for
    :return:            the rendered template "resource.html"
    """
    return render_template("service.html", resource_global=resource_global)


# If we're running in stand alone mode, run the application
if __name__ == '__main__':
    main()
