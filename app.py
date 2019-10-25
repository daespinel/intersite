from flask import Flask
from flask import render_template
import common.utils as service_utils
import connexion
import logging
import re

# Create the application instance
app = connexion.App(__name__, specification_dir='./config/')
logging.basicConfig(level=logging.DEBUG)

def main():
    # Read the swagger.yml file to configure the endpoints
    app.add_api('swagger.yml')
    host = service_utils.get_local_host()
    app.run(host=host, port=7575, debug=True)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/services")
@app.route("/services/<string:service_global>")
def services(service_global=""):
    """
    This function just responds to the browser URL
    localhost:7575/services
    :return:        the rendered template "services.html"
    """
    return render_template("services.html", service_global=service_global)

# If we're running in stand alone mode, run the application
if __name__ == '__main__':
    main()
    