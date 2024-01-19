import threading
import time
import json
from datetime import datetime, timezone
from flask import Flask, request, render_template, Response
from flask_sqlalchemy import SQLAlchemy

MESSAGE_MAX_LENGTH = 128
CLEANING_FREQUENCY = 60
MAX_MESSAGES = 1024

# create the database model
db = SQLAlchemy()

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(MESSAGE_MAX_LENGTH))
    timestamp = db.Column(db.DateTime)

# initialize the flask application
app = Flask(__name__)

# configure the database (sqlite in RAM)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'    
db.init_app(app)

# create the database tables
with app.app_context():
    db.create_all()

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
    # convert the messages to a list of dictionaries
    last_message_id = messages[-1].id if messages else -1
    messages = [
        {
            'timestamp': int(message.timestamp.replace(tzinfo=timezone.utc).timestamp()), 
            'content': message.content
        } 
        for message in messages
    ]
    return render_template('messages.html', last_message_id=last_message_id, messages=messages)

# GET /stream - stream the messages
@app.route('/stream')
def stream():
    # get the last message id
    start_id = request.args.get('start_id')
    def generate(start_id):
        with app.app_context():       
            while True:
                messages = Message.query.filter(Message.id > start_id).order_by(Message.id.asc()).all()
                
                for message in messages:
                    data = {
                        "timestamp": int(message.timestamp.replace(tzinfo=timezone.utc).timestamp()),
                        "content": message.content
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                    start_id = message.id
                time.sleep(1)

    return Response(generate(start_id), mimetype="text/event-stream")