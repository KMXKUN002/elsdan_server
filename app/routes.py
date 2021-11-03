import json
import os
import xml.etree.ElementTree as ET

import requests
from authlib.integrations.flask_client import OAuth
from flask import abort, jsonify, url_for, request
from flask_httpauth import HTTPBasicAuth
# Flask JSON Web Token manager
from flask_jwt_extended import (create_access_token, create_refresh_token,
                                get_jwt_identity, jwt_required)
from flask_restful import Api
from requests.auth import HTTPBasicAuth as RequestsAuth

from app import app
from app.resources import (DatatypeResource, DeviceResource,
                           FileDetailResource, FileManageResource,
                           SensorResource, TagResource, fetch_token,
                           update_token)

auth = HTTPBasicAuth()
api = Api(app)
app.secret_key = os.urandom(24)

api.add_resource(DatatypeResource, '/api/datatype')
api.add_resource(DeviceResource, '/api/device')
api.add_resource(SensorResource, '/api/sensor')
api.add_resource(FileDetailResource, '/api/filedetail')
api.add_resource(TagResource, '/api/tag')
api.add_resource(FileManageResource, '/api/file')


@app.route('/', methods=['GET'])
@jwt_required()
def index():
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user)


@app.route('/login', methods=['POST'])
@auth.login_required
def login():
    username = auth.current_user()
    access_token = create_access_token(identity=username)
    refresh_token = create_refresh_token(identity=username)
    return {
        'username': username,
        'access_token': access_token,
        'refresh_token': refresh_token
    }


@app.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    username = get_jwt_identity()
    access_token = create_access_token(identity=username)
    return {
        'username': username,
        'access_token': access_token
    }


@auth.verify_password
def verify_password(username, password):
    if not (username and password):
        abort(401)

    # Authenticate against Nextcloud and fetch user data
    endpoint = app.config['NEXTCLOUD_USER_ENDPOINT'] + username
    response = requests.get(
        endpoint,
        headers={'OCS-APIRequest': 'true'},
        auth=RequestsAuth(username, password)
    )
    if response.status_code != 200:
        abort(401)

    # Read XML response from Nextcloud.
    # tree_root[0][0] finds the tag <status>
    # tree_root[1][0] finds <enabled>, whether the client is enabled
    # tree_root[1][2] finds <id>, the user ID recorded on the Nextcloud system
    # See more at https://docs.nextcloud.com/server/14/developer_manual/client_apis/OCS/index.html
    tree_root = ET.fromstring(response.content)
    if (tree_root[0][0].text == 'ok'
        and tree_root[1][0].text == '1'
        and tree_root[1][2].text == username):
        return username
    else:
        abort(401)


@app.errorhandler(422)
def handle_error(err):
    headers = err.data.get("headers", None)
    messages = err.data.get("messages", ["Invalid request."])
    if headers:
        return {"errors": messages}, err.code, headers
    else:
        return {"errors": messages}, err.code


@app.errorhandler(413)
def too_large(err):
    return {"errors": "Your file is too large (>{}MB)"\
            .format(app.config['MAX_CONTENT_LENGTH'] / 1024 ** 2)}, err.code


if __name__ == '__main__':
    app.run(debug=True)
