import time
import json
import pytz

from datetime import datetime

from flask import Flask, request, render_template, Response
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(128))
    timestamp = db.Column(db.DateTime, default=datetime.now(pytz.utc))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'    
db.init_app(app)

@app.route('/', methods=['POST'])
def post_message():
    content = request.data.decode('utf-8')
    message = Message(content=content)
    db.session.add(message)
    db.session.commit()
    return 'Message posted successfully', 200

def event_stream():
    with app.app_context():
        while True:
            new_message = Message.query.order_by(Message.id.desc()).first()
            if new_message is not None:
                unix_timestamp = int(new_message.timestamp.timestamp())
                print(new_message.timestamp)
                print(unix_timestamp)
                data = {
                    "timestamp": unix_timestamp,
                    "content": new_message.content
                }
                yield f"data: {json.dumps(data)}\n\n"
                db.session.delete(new_message)
                db.session.commit()
            else:
                time.sleep(.1)  # wait for 1 second before checking for new messages again

@app.route('/stream')
def stream():
    # returns a stream of messages to the client
    return Response(event_stream(), mimetype="text/event-stream")


@app.route('/', methods=['GET'])
def view_messages():
    return render_template('messages.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)