from flask import Flask, flash, jsonify, render_template, redirect, request, session, url_for
from flask_socketio import SocketIO, emit
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# List of authorized users with their email, corresponding name, and password
user_data = {
    'jaya.k.ihub@snsgroups.com': ('Jayasima', 'Jayasima07'),
    'prince.v.dt@snsgroups.com': ('Prince', 'Prince01'),
    'mani.g.ihub@snsgroups.com': ('Manigandan', 'Mani1010'),
    'naveen.k.ihub@snsgroups.com': ('Naveen', 'Naveen202'),
    'gokul.s.ihub@snsgroups.com': ('Gokul', 'Gokul118')
}

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Check if the user exists and password is correct
        if email in user_data and user_data[email][1] == password:
            session['user'] = user_data[email][0]  # Store name as the username
            return redirect(url_for('chat'))
        else:
            flash('Incorrect email or password.', 'error')  # Show error message on the page
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/chat')
def chat():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    username = session['user']
    return render_template('chat.html', username=username)

# Store active user sessions
clients = {}  # {sid: username}
rooms = {}  # {username: sid}

@socketio.on('connect')
def connect():
    if 'user' in session:
        emit('prompt_username')
    else:
        return False  # Disconnect unauthorized connections

@socketio.on('set_username')
def set_username():
    username = session['user']
    if username in rooms:
        emit('username_taken')
    else:
        clients[request.sid] = username
        rooms[username] = request.sid
        emit('welcome', username)
        update_user_list()

@socketio.on('send_message')
def send_message(data):
    username = clients.get(request.sid)
    message = data.get('message')
    message_id = str(uuid.uuid4())
    reply_to_id = data.get('reply_to_id')  # Get the ID of the message being replied to (if any)

    # personal message logic
    if message.startswith('@'):
        parts = message.split(" ", 1)
        recipients = parts[0][1:].split(",")
        personal_message = parts[1] if len(parts) > 1 else ""
        
        for recipient in recipients:
            recipient = recipient.strip()
            if recipient in rooms:
                emit('personal_message', {
                    'sender': username,
                    'message': personal_message,
                    'id': message_id,
                    'reply_to': reply_to_id
                }, room=rooms[recipient])
        
        emit('personal_message', {
            'sender': username,
            'message': personal_message,
            'id': message_id,
            'reply_to': reply_to_id
        }, room=request.sid)
    
    else:
        emit('broadcast_message', {
            'sender': username,
            'message': message,
            'id': message_id,
            'reply_to': reply_to_id
        }, broadcast=True)

@socketio.on('react_to_message')
def react_to_message(data):
    message_id = data.get('messageId')
    emoji = data.get('emoji')
    emit('add_reaction', {'messageId': message_id, 'emoji': emoji}, broadcast=True)

@socketio.on('disconnect')
def disconnect():
    username = clients.pop(request.sid, None)
    if username:
        rooms.pop(username, None)
        emit('user_disconnected', username, broadcast=True)
        update_user_list()

@socketio.on('request_usernames')
def handle_usernames_request():
    emit('receive_usernames', list(rooms.keys()))

def update_user_list():
    user_list = list(rooms.keys())
    emit('user_list', user_list, broadcast=True)

if __name__ == "__main__":
    socketio.run(app, host='192.168.56.1', port=5000, debug=True)
