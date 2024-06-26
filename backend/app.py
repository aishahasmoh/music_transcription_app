"""
Echo Flask API

Flask-based REST API that serves as the backend for the Echo mobile application.

Includes various routes that all involve interacting with the MySQL database,
for creating, updating, and retrieving user data, as well as processing audio recordings
to generate note sequences viewable on the frontend.
"""

import ast
import os
import re
from flask import Flask, request, jsonify, send_file
from flask_mysqldb import MySQL
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from audio_processing import Song, convert_m4a_to_wav, AudioAnalyzer

NOTE_DATA_PATH = './note_data'
AUDIO_DATA_PATH = './audio_data'
METERING_DATA_PATH = './metering_data'

app = Flask(__name__)
db = MySQL()

app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_ROOT_PASSWORD')
app.config['MYSQL_DB'] = 'echo_db'
app.config['MYSQL_PORT'] = 53346

db.init_app(app)
CORS(app)


@app.route('/get-user-data/<email>', methods=['GET'])
def get_user_data(email):
    """
    Fetches data for a particular user.

    Parameters
    ----------
    email : str
        The email address of the user to fetch data for.

    Returns
    -------
    JSON response
        A JSON response containing the user's data, including display name, sequences, and folders.
    """

    cursor = db.connection.cursor()
    query = "SELECT * FROM Users WHERE email = %s"
    cursor.execute(query, (email,))
    user = cursor.fetchone()

    if user is None:
        response = jsonify({"error": "User does not exist"}), 404
        response[0].headers.add('Access-Control-Allow-Origin', '*')
        return response

    username = user[1]
    folders = []
    sequences = []

    query = "SELECT folder_id, display_name, created FROM Folders WHERE owner = %s"
    cursor.execute(query, (email,))
    raw_folders = cursor.fetchall()

    for raw_folder in raw_folders:
        folder_id = raw_folder[0]
        display_name = raw_folder[1]
        created = raw_folder[2]

        folder = {
            "id": folder_id,
            "display_name": display_name,
            "created": created,
            "sequences": [],
        }

        query = "SELECT sequence FROM Contains WHERE folder = %s"
        cursor.execute(query, (folder_id,))
        folder_sequences = cursor.fetchall()

        for sequence in folder_sequences:
            sequence_id = sequence[0]
            folder["sequences"].append(sequence_id)

        folders.append(folder)

    query = "SELECT sequence_id, bpm, display_name, filename, created FROM Sequences WHERE creator = %s"
    cursor.execute(query, (email,))
    raw_sequences = cursor.fetchall()

    for raw_sequence in raw_sequences:
        sequence_id = raw_sequence[0]
        bpm = raw_sequence[1]
        display_name = raw_sequence[2]
        filename = raw_sequence[3]
        created = raw_sequence[4]
        notes = ''
        metering_data = []
        notes_path = f'{NOTE_DATA_PATH}/{filename}.txt'
        metering_data_path = f'{METERING_DATA_PATH}/{filename}.txt'

        if os.path.exists(notes_path):
            with open(notes_path, 'r') as f:
                notes = f.read()

        if os.path.exists(metering_data_path):
            with open(metering_data_path, 'r') as f:
                metering_data_raw = f.read()

            metering_data = ast.literal_eval(metering_data_raw)  # formatted as a string

        sequence = {
            "id": sequence_id,
            "display_name": display_name,
            "created": created,
            "notes": notes,
            "metering_data": metering_data,
        }

        sequences.append(sequence)

    user_data = {
        "username": username,
        "folders": folders,
        "sequences": sequences,
    }

    response = jsonify(user_data)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/get-recording-file/<int:sequence_id>', methods=['GET'])
def get_recording_file(sequence_id):
    """
    Fetches the M4A file corresponding to a recorded sequence.

    Parameters
    ----------
    sequence_id : int
        The sequence to be retrieved

    Returns
    -------
    M4A response
        The recorded sequence as a M4A file
    """

    cursor = db.connection.cursor()
    query = "SELECT filename FROM Sequences WHERE sequence_id = %s"
    cursor.execute(query, (sequence_id,))
    sequence = cursor.fetchone()
    cursor.close()

    if sequence is None:
        response = jsonify({"error": "Sequence does not exist"}), 404
        response[0].headers.add('Access-Control-Allow-Origin', '*')
        return response

    filename = sequence[0]
    path = f'{AUDIO_DATA_PATH}/{filename}.m4a'
    response = send_file(path, as_attachment=True)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/process-recording', methods=['POST'])
def process_recording():
    """
    Processes an uploaded vocal recording by converting it into
    a note sequence, saving it, and returning it to the frontend.

    Parameters
    ----------
    File file: An M4A file of the vocal recording of the audio sequence.
    str user: The email of the creator of the song.
    str display_name: The display name associated with the recording.
    int instrument: The ID of the default playback instrument.
    str metering_data: The metering data associated with the recording, formatted as a string.

    Returns
    -------
    JSON response
        A JSON response containing the processed sequence data for the frontend.
    """

    if 'file' not in request.files:
        response = jsonify({"error": "No recording provided"}), 400
        response[0].headers.add('Access-Control-Allow-Origin', '*')
        return response

    recording = request.files['file']

    if not recording or not recording.filename.endswith('.m4a'):
        response = jsonify({"error": "Invalid recording format"}), 415
        response[0].headers.add('Access-Control-Allow-Origin', '*')
        return response
    
    metering_data = request.form.get('metering_data')
    
    # validate that metering data represents a list
    if not (metering_data.startswith('[') and metering_data.endswith(']')):
        response = jsonify({"error": "Metering data not formatted correctly"}), 400
        response[0].headers.add('Access-Control-Allow-Origin', '*')
        return response
    
    try:
        format_test = ast.literal_eval(metering_data)

        if not isinstance(format_test, list):
            raise ValueError
        
        for item in format_test:
            float(item)  # verify each item is a number

            if not type(item) == str:
                raise ValueError
    except (SyntaxError, ValueError):
        response = jsonify({"error": "Metering data not formatted correctly"}), 400
        response[0].headers.add('Access-Control-Allow-Origin', '*')
        return response

    display_name = request.form.get('display_name')

    if display_name is None:
        response = jsonify({"error": "Display name does not exist"}), 400
        response[0].headers.add('Access-Control-Allow-Origin', '*')
        return response

    if '/' in display_name or '\\' in display_name or '.' in display_name:
        response = jsonify({"error": "Display name cannot include slashes or periods"}), 400
        response[0].headers.add('Access-Control-Allow-Origin', '*')
        return response

    user = request.form.get('user')

    if user is None:
        response = jsonify({"error": "User does not exist"}), 400
        response[0].headers.add('Access-Control-Allow-Origin', '*')
        return response

    cursor = db.connection.cursor()
    query = "SELECT * FROM Sequences WHERE creator = %s AND display_name = %s"
    cursor.execute(query, (user, display_name))
    num_sequences_with_same_name = len(cursor.fetchall())
    filename = f'{user}-{display_name}{num_sequences_with_same_name}'
    metering_path = f'{METERING_DATA_PATH}/{filename}.txt'

    with open(metering_path, 'w') as f:
        f.write(metering_data)

    recording_path = f'{AUDIO_DATA_PATH}/{filename}'
    recording_m4a_path = f'{recording_path}.m4a'
    recording_wav_path = f'{recording_path}.wav'
    recording.save(recording_m4a_path)
    convert_m4a_to_wav(recording_path)
    instrument = 1  # default playback instrument is unused, so default to 1 instead of `request.form.get('instrument', type=int)`
    sequence = Song(recording_wav_path, 0.25)
    processed_sequence = sequence.audio_to_notes()
    note_path = f'{NOTE_DATA_PATH}/{filename}.txt'
    processed_sequence.save_to_file(note_path)
    query = "INSERT INTO Sequences (instrument, bpm, creator, display_name, filename) VALUES (%s, %s, %s, %s, %s)"
    cursor.execute(query, (instrument, 0, user, display_name, filename))  # use default value of 0 for BPM (currently uncalculated)
    query = "SELECT LAST_INSERT_ID()"
    cursor.execute(query)
    record = cursor.fetchone()
    record_id = record[0]
    query = "SELECT * FROM Sequences WHERE sequence_id = %s"
    cursor.execute(query, (record_id,))
    raw_sequence_data = cursor.fetchone()
    db.connection.commit()
    cursor.close()
    sequence_id = raw_sequence_data[0]
    created = raw_sequence_data[6]

    sequence_data = {
        "id": sequence_id,
        "display_name": display_name,
        "created": created,
        "notes": str(processed_sequence),
        "metering_data": ast.literal_eval(metering_data)
    }

    response = jsonify(sequence_data)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/rename-sequence/<int:sequence_id>/<display_name>', methods=['PUT'])
def rename_sequence(sequence_id, display_name):
    """
    Renames a sequence.

    Parameters
    ----------
    sequence_id : int
        The unique identifier for the sequence.
    display_name : str
        The new name of the sequence.

    Returns
    -------
    JSON response
        A JSON confirmation of the sequence rename.
    """

    cursor = db.connection.cursor()
    query = "SELECT * FROM Sequences WHERE sequence_id = %s"
    cursor.execute(query, (sequence_id,))
    sequence = cursor.fetchone()

    if sequence is None:
        cursor.close()
        response = jsonify({"error": f"Sequence {sequence_id} does not exist"}), 404
        response[0].headers.add('Access-Control-Allow-Origin', '*')
        return response

    query = "UPDATE Sequences SET display_name = %s WHERE sequence_id = %s"
    cursor.execute(query, (display_name, sequence_id))
    db.connection.commit()
    cursor.close()
    response = jsonify({"message": f"Sequence {sequence_id} renamed to {display_name} successfully"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/update-sequence-data/<int:sequence_id>/<updated_sequence>', methods=['PUT'])
def update_sequence_data(sequence_id, updated_sequence):
    """
    Updates the note data associated with an audio sequence.

    Parameters
    ----------
    sequence_id : int
        The unique identifier for the sequence.
    updated_sequence : str
        The new note data of the sequence, formatted sequentially as a string.

    Returns
    -------
    JSON response
        A JSON confirmation of the note data update.
    """

    cursor = db.connection.cursor()
    query = "SELECT filename FROM Sequences WHERE sequence_id = %s"
    cursor.execute(query, (sequence_id,))
    sequence = cursor.fetchone()
    cursor.close()

    if sequence is None:
        response = jsonify({"error": f"Sequence {sequence_id} does not exist"}), 404
        response[0].headers.add('Access-Control-Allow-Origin', '*')
        return response

    # validate sequence format
    notes = updated_sequence.split(',')
    analyzer = AudioAnalyzer()
    pattern = r"^(" + "|".join(analyzer.Note_Names) + r")(\d+(\.\d+)?)$"

    for note in notes:
        if not re.match(pattern, note):
            response = jsonify({"error": "Invalid new sequence data"}), 400
            response[0].headers.add('Access-Control-Allow-Origin', '*')
            return response

    filename = sequence[0]
    path = f'{NOTE_DATA_PATH}/{filename}.txt'

    with open(path, 'w') as f:
        f.write(updated_sequence)

    response = jsonify({"message": f"Sequence {sequence_id} updated successfully"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/create-folder/<display_name>/<owner>', methods=['POST'])
def create_folder(display_name, owner):
    """
    Creates a new folder.

    Parameters
    ----------
    display_name : str
        The display name for the folder.
    owner : str
        The email of the user who owns the folder.

    Returns
    -------
    JSON response
        A JSON response containing the new folder ID.
    """

    cursor = db.connection.cursor()
    query = "INSERT INTO Folders (display_name, owner) VALUES (%s, %s)"
    cursor.execute(query, (display_name, owner))
    query = "SELECT LAST_INSERT_ID()"
    cursor.execute(query)
    folder = cursor.fetchone()
    db.connection.commit()
    cursor.close()
    folder_id = folder[0]
    response = jsonify({"folder_id": folder_id})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/rename-folder/<int:folder_id>/<display_name>', methods=['PUT'])
def rename_folder(folder_id, display_name):
    """
    Renames a folder.

    Parameters
    ----------
    folder_id : int
        The unique identifier for the folder.
    display_name : str
        The new name of the folder.

    Returns
    -------
    JSON response
        A JSON confirmation of the folder rename.
    """

    cursor = db.connection.cursor()
    query = "SELECT display_name FROM Folders WHERE folder_id = %s"
    cursor.execute(query, (folder_id,))
    folder = cursor.fetchone()

    if folder is None:
        cursor.close()
        response = jsonify({"error": "Folder does not exist"}), 404
        response[0].headers.add('Access-Control-Allow-Origin', '*')
        return response

    original_name = folder[0]
    query = "UPDATE Folders SET display_name = %s WHERE folder_id = %s"
    cursor.execute(query, (display_name, folder_id))
    db.connection.commit()
    cursor.close()
    response = jsonify({"message": f"{original_name} renamed to {display_name} successfully"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/update-folder-contents', methods=['PUT'])
def update_folder_contents():
    """
    Update the contents of a folder, including adding or removing sequences.
    TODO replace with add and delete routes

    Parameters
    ----------
    folder_id : int
        The unique identifier for the folder.
    sequences : list of int
        An array of the sequences now contained in the folder.

    Returns
    -------
    JSON response
        A JSON confirmation of the folder contents update.
    """

    if not request.is_json:
        response = jsonify({"error": "Invalid request format"}), 400
        response[0].headers.add('Access-Control-Allow-Origin', '*')
        return response

    data = request.get_json()
    folder_id = data.get('folder_id')
    sequences = data.get('sequences')

    if folder_id is None:
        response = jsonify({"error": "Missing folder ID"}), 400
        response[0].headers.add('Access-Control-Allow-Origin', '*')
        return response

    if sequences is None:
        response = jsonify({"error": "Missing folder sequences"}), 400
        response[0].headers.add('Access-Control-Allow-Origin', '*')
        return response

    if not isinstance(sequences, list) or not all(isinstance(sequence_id, int) for sequence_id in sequences):
        response = jsonify({"error": "Invalid sequence IDs"}), 400
        response[0].headers.add('Access-Control-Allow-Origin', '*')
        return response

    cursor = db.connection.cursor()
    query = "SELECT * FROM Folders WHERE folder_id = %s"
    cursor.execute(query, (folder_id,))
    folder = cursor.fetchone()

    if folder is None:
        cursor.close()
        response = jsonify({"error": f"Folder does not exist"}), 404
        response[0].headers.add('Access-Control-Allow-Origin', '*')
        return response

    folder_owner = folder[2]

    for sequence_id in sequences:
        query = "SELECT creator FROM Sequences WHERE sequence_id = %s"
        cursor.execute(query, (sequence_id,))
        sequence = cursor.fetchone()

        if sequence is None:
            cursor.close()
            response = jsonify({"error": f"Sequence {sequence_id} does not exist"}), 404
            response[0].headers.add('Access-Control-Allow-Origin', '*')
            return response

        sequence_owner = sequence[0]

        if sequence_owner != folder_owner:
            cursor.close()
            response = jsonify({"error": f"Sequence {sequence_id} is not owned by {folder_owner}"}), 403
            response[0].headers.add('Access-Control-Allow-Origin', '*')
            return response

    query = "SELECT sequence FROM Contains WHERE folder = %s"
    cursor.execute(query, (folder_id,))
    current_sequences = cursor.fetchall()
    current_sequence_ids = [sequence[0] for sequence in current_sequences]

    for sequence_id in sequences:  # add newly added sequences
        if sequence_id not in current_sequence_ids:
            query = "INSERT INTO Contains (folder, sequence) VALUES (%s, %s)"
            cursor.execute(query, (folder_id, sequence_id))

    for sequence_id in current_sequence_ids:  # remove newly removed sequences
        if sequence_id not in sequences:
            query = "DELETE FROM Contains WHERE sequence = %s"
            cursor.execute(query, (sequence_id,))

    db.connection.commit()
    cursor.close()
    display_name = folder[1]
    response = jsonify({"message": f"{display_name} updated successfully"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/delete-folder/<int:folder_id>', methods=['DELETE'])
def delete_folder(folder_id):
    """
    Deletes a folder.

    Parameters
    ----------
    folder_id : int
        The unique identifier for the folder to be deleted.

    Returns
    -------
    JSON response
        A JSON confirmation of the folder deletion.
    """

    cursor = db.connection.cursor()
    query = "DELETE FROM Contains WHERE folder = %s"
    cursor.execute(query, (folder_id,))
    query = "DELETE FROM Folders WHERE folder_id = %s"
    cursor.execute(query, (folder_id,))
    db.connection.commit()
    cursor.close()
    response = jsonify({"message": f"Database updated successfully"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/delete-sequence/<int:sequence_id>', methods=['DELETE'])
def delete_sequence(sequence_id):
    """
    Deletes a sequence.

    Parameters
    ----------
    sequence_id : int
        The unique identifier for the sequence to be deleted.

    Returns
    -------
    JSON response
        A JSON confirmation of the sequence deletion.
    """

    cursor = db.connection.cursor()
    query = "DELETE FROM Contains WHERE sequence = %s"
    cursor.execute(query, (sequence_id,))
    query = "DELETE FROM Sequences WHERE sequence_id = %s"
    cursor.execute(query, (sequence_id,))
    db.connection.commit()
    cursor.close()
    response = jsonify({"message": f"Database updated successfully"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/create-user/<email>/<username>', methods=['POST'])
def create_user(email, username):
    """
    Creates a user.

    Parameters
    ----------
    email : str
        The user's email, which will serve as the user's unique DB identifier.
    username : str
        The user's display name.

    Returns
    -------
    JSON response
        A JSON confirmation of user creation.
    """

    cursor = db.connection.cursor()
    query = "INSERT INTO Users (email, display_name) VALUES (%s, %s)"
    cursor.execute(query, (email, username))
    db.connection.commit()
    cursor.close()
    response = jsonify({"message": f"{username}'s account created"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.errorhandler(Exception)
def handle_exception(e):
    """
    A global exception handler that more eloquently addresses non-defined exceptions.

    Returns
    -------
    JSON response
        An error with code 500 and a message regarding what went wrong during the execution of the route's code.
    """
    if isinstance(e, HTTPException):
        response = jsonify({"error": e.description}), e.code
    else:
        response = jsonify({"error": e}), 500

    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


