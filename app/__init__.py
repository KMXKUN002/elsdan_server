from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager 


app = Flask(__name__)
app.config.from_envvar('ENV_DIRECTORY')
jwt = JWTManager(app)

db = SQLAlchemy(app)
db.Model.metadata.reflect(bind=db.engine)

from app import routes