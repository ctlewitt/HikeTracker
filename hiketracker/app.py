from flask import Flask
from sqlalchemy.orm import sessionmaker
import os
import flask_login
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from flask_mail import Mail


app = Flask(__name__)


app.config.update(
    # email settings
    MAIL_SERVER=os.environ.get('MAIL_SERVER'),
    MAIL_PORT=465,
    MAIL_USE_SSL=True,
    MAIL_PASSWORD=os.environ.get('ADMIN_EMAIL_PASSWORD'),
    MAIL_USERNAME=os.environ.get('ADMIN_EMAIL_USERNAME'),
    DATABASE_URL=os.environ.get('DATABASE_URL'),
    MAPBOX_ID=os.environ.get('MAPBOX_ID'),
    MAPBOX_TOKEN=os.environ.get('MAPBOX_TOKEN'),
)

app.secret_key = os.environ.get('FLASK_LOGIN_SECRET_KEY')
app.login_manager = flask_login.LoginManager()
app.login_manager.init_app(app)
app.login_manager.login_view = "login"

db = SQLAlchemy(app)
engine = create_engine(os.environ.get('DATABASE_URL'))#, echo=True)

app.mail = Mail(app)


Session = sessionmaker(bind=engine)
