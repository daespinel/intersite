from flask import Flask
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

# If we're running in stand alone mode, run the application
if __name__ == '__main__':
    main()
    