from flask import Flask
from flask import render_template
import common.utils as service_utils
import connexion
import re

# Create the application instance
app = connexion.App(__name__, specification_dir='./config/')

def main():
    # Read the swagger.yml file to configure the endpoints
    app.add_api('swagger.yml')
    host = service_utils.get_local_host()
    app.run(host=host, port=7575, debug=True)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/services")
@app.route("/services/<string:global_id>")
def services(global_id=""):
    """
    This function just responds to the browser URL
    localhost:5000/people
    :return:        the rendered template "people.html"
    """
    return render_template("services.html", global_id=global_id)

# If we're running in stand alone mode, run the application
if __name__ == '__main__':
    main()
    