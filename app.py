from flask import Flask
from datetime import datetime
from flask import render_template
import connexion
import re

# Create the application instance
app = connexion.App(__name__, specification_dir='./config/')

def main():
    # Read the swagger.yml file to configure the endpoints
    app.add_api('swagger.yml')
    app.run(host='0.0.0.0', port=7575, debug=True)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/about/")
def about():
    return render_template("about.html")

@app.route("/contact/")
def contact():
    return render_template("contact.html")

# If we're running in stand alone mode, run the application
if __name__ == '__main__':
    main()
    