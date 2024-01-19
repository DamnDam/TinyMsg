import threading
import uuid
import time
import json
from datetime import datetime, timezone, timedelta
from flask import Flask, request, session, render_template, Response
from flask_sqlalchemy import SQLAlchemy

# Clean database configuration
CLEANING_FREQUENCY = 60
MAX_MESSAGES = 100
MAX_LISTENER_AGE = 300

# create the database model
db = SQLAlchemy()

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(128))
    timestamp = db.Column(db.DateTime)

class Listener(db.Model):
    id = db.Column(db.String(36), primary_key=True, unique=True)
    last_seen = db.Column(db.DateTime)
    last_message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=True)

# initialize the flask application
app = Flask(__name__)

# configure the database (sqlite in RAM)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'    
db.init_app(app)

# create the database tables
with app.app_context():
    db.create_all()

def create_listener(last_message_id=None):
    listener = Listener(id=str(uuid.uuid4()), last_seen=datetime.utcnow(), last_message_id=last_message_id)
    db.session.add(listener)
    db.session.commit()
    return listener

# Database cleaning
last_cleaning_time = time.time()

def clean_db():
    global last_cleaning_time
    with app.app_context():
        # get the ids of the last X messages
        ids_to_keep = db.session.query(Message.id).order_by(Message.timestamp.desc()).limit(MAX_MESSAGES).all()
        ids_to_keep = [id[0] for id in ids_to_keep]
        # delete all messages that are not in the last
        db.session.query(Message).filter(~Message.id.in_(ids_to_keep)).delete(synchronize_session=False)

        # delete all listeners that have not been seen for X seconds
        Listener.query.filter(Listener.last_seen < datetime.utcnow() - timedelta(seconds=MAX_LISTENER_AGE)).delete()
        db.session.commit()
        last_cleaning_time = time.time()

# POST / - post a new message
@app.route('/', methods=['POST'])
def post_message():
    content = request.data.decode('utf-8')
    message = Message(content=content, timestamp=datetime.utcnow())
    db.session.add(message)
    db.session.commit()
    if time.time() - last_cleaning_time > CLEANING_FREQUENCY:
        threading.Thread(target=clean_db).start()
    return 'Message posted successfully', 201

# GET / - view the messages
@app.route('/', methods=['GET'])
def view_messages():
    messages = Message.query.order_by(Message.id.asc()).all()
    if not messages:
        listener = create_listener()
    else:
        listener = create_listener(last_message_id=messages[-1].id)
    # convert the messages to a list of dictionaries
    messages = [
        {
            'timestamp': int(message.timestamp.replace(tzinfo=timezone.utc).timestamp()), 
            'content': message.content
        } 
        for message in messages
    ]
    return render_template('messages.html', listener_id=listener.id, messages=messages)

# GET /stream - stream the messages
@app.route('/stream')
def stream():
    # get the listener id from the query string
    listener_id = request.args.get('listener_id', None)
    if not listener_id:
        return Response(status=400)
    def generate(listener_id):
        with app.app_context():
            listener = db.session.get(Listener, listener_id)
            if not listener:
                listener = create_listener()
        
            while True:
                if listener.last_message_id is None:
                    messages = Message.query.order_by(Message.id.asc()).all()
                else:
                    messages = Message.query.filter(Message.id > listener.last_message_id).order_by(Message.id.asc()).all()
                
                for message in messages:
                    data = {
                        "timestamp": int(message.timestamp.replace(tzinfo=timezone.utc).timestamp()),
                        "content": message.content
                    }
                    yield f"data: {json.dumps(data)}\n\n"

                if messages:
                    listener.last_seen = datetime.utcnow()
                    listener.last_message_id = messages[0].id
                    db.session.commit()
                time.sleep(1)

    return Response(generate(listener_id), mimetype="text/event-stream")