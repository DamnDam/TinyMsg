import threading
import time
import json
from datetime import datetime, timezone
from flask import Flask, request, render_template, Response, current_app, escape
from flask_sqlalchemy import SQLAlchemy

MESSAGE_MAX_LENGTH = 128 # in characters
CLEANING_FREQUENCY = 60 # in seconds
MAX_MESSAGES = 1024 # maximum number of messages to keep

# create the database model
db = SQLAlchemy()

# Message model
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(MESSAGE_MAX_LENGTH))
    timestamp = db.Column(db.DateTime)

    # convert the message to a JSON string
    def __repr__(self):
        return json.dumps({
            'id': self.id,
            'content': self.content,
            'timestamp': int(self.timestamp.replace(tzinfo=timezone.utc).timestamp())
        })

def create_app():
    # initialize the flask application
    app = Flask(__name__)

    # configure the database (sqlite in RAM)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'    
    db.init_app(app)

    with app.app_context():
        # create the database tables
        db.create_all()
        # app level variable
        current_app.last_cleaning_time = time.time()

    # Database cleaning thread
    def clean_db():
        with app.app_context():
            # get the ids of the last X messages
            ids_to_keep = db.session.query(Message.id).order_by(Message.timestamp.desc()).limit(MAX_MESSAGES).all()
            ids_to_keep = [id[0] for id in ids_to_keep]
            # delete all messages that are not in the selected ids
            # (synchronize_session=False to gain performance)
            db.session.commit()
            current_app.last_cleaning_time = time.time()

    # POST / - post a new message
    @app.route('/', methods=['POST'])
    def post_message():
        content = escape(request.data.decode('utf-8'))
        # check the message length
        if len(content) > MESSAGE_MAX_LENGTH:
            return 'Message too long', 400
        # create the message
        message = Message(content=content, timestamp=datetime.utcnow())
        # add the message to the database
        db.session.add(message)
        db.session.commit()

        if time.time() - current_app.last_cleaning_time > CLEANING_FREQUENCY:
            # start a thread to clean the database
            threading.Thread(target=clean_db).start()
        return 'Message posted successfully', 201

    # GET / - view the messages
    @app.route('/', methods=['GET'])
    def view_messages():
        messages = Message.query.order_by(Message.id.asc()).all()
        # get the id of the last message
        last_message_id = messages[-1].id if messages else -1
        return render_template('messages.html', last_message_id=last_message_id, messages=messages)

    # GET /stream - stream the messages (Server-Sent Events protocol)
    @app.route('/stream')
    def stream():
        # get the last message id from the query string
        start_id = request.args.get('start_id')

        # generator function to stream the messages
        # generators are special functions that loop 
        # and yield values one by one to the caller
        def generate(start_id):
            with app.app_context():       
                while True: # infinite loop to keep the connection alive
                    messages = Message.query.filter(Message.id > start_id).order_by(Message.id.asc()).all()
                    
                    for message in messages:
                        # send the message to the client
                        yield f"data: {message}\n\n" 
                        start_id = message.id
                    # delay the next iteration to avoid busy waiting
                    time.sleep(1)

        return Response(generate(start_id), mimetype="text/event-stream")
    
    return app