from typing import Iterator, List
from midiutil.MidiFile import MIDIFile
import librosa
import subprocess
import os

class AnalysisPoint:
    """A class representing one data point in AnalyzedSong.

    Attributes
    ----------
    time_stamp : float
        description
    frequency : float
        description
    note_name : str
        description
    duration: float
        duration of the note in secs
    """
    def __init__(self, time_stamp: float, frequency: float,
        note_name: str, duration: float):
        """
        Parameters
        ----------
        time_stamp : float
            the starting time of each time segments.
        frequency : float
            the dominant frequency at each time segments.
        note_name : str
            the note name that corresponds to the dominant frequency.
        duration: float
            duration of the note in secs
        """
        self.time_stamp = time_stamp
        self.frequency = frequency
        self.note_name = note_name
        self.duration = duration

    def _duration_to_lilypond(self, chunk_duration):
        """A helper function for note_to_lilypond

        Parameters
        ----------
        chunk_duration: float
            duration of one beat secs
        """
        # Assuming 0.25 seconds per quarter note
        quarter_note_duration = 0.25  # seconds
        duration_in_quarters = self.duration / quarter_note_duration
        
        # Define common musical note lengths in terms of quarter note durations
        note_lengths = {
            4.0: "1",  # Whole note
            2.0: "2",  # Half note
            1.0: "4",  # Quarter note
            0.5: "8",  # Eighth note
            0.25: "16",  # Sixteenth note
            # Add more if needed
        }
        
        # Find the closest note length to the duration_in_quarters
        closest_note_length = min(note_lengths.keys(), key=lambda length: abs(length - duration_in_quarters))
        return note_lengths[closest_note_length]

    def note_to_lilypond(self, chunk_duration):
        """Returns a string representatiion of the note in lilypond format

        Parameters
        ----------
        chunk_duration: float
            duration of one beat secs

        Returns
        -------
        str
            a string representatiion of the note in lilypond format
        """
        lilypond_notation = ""
        name = self.note_name[:-1].lower()  # Extract the note letter(s) and make them lowercase
        octave = int(self.note_name[-1])  # Extract the octave as an integer
        octave_difference = octave - 4  # Determine octave difference from C4
        if octave_difference > 0:
            octave_adjustment = "'" + str(octave_difference)
        else:
            #octave_adjustment = "," + str(-1*octave_difference)
            octave_adjustment = "'"

        lily_duration = self._duration_to_lilypond(chunk_duration)
        lilypond_notation += f"{name}{octave_adjustment}{lily_duration} "
        #lilypond_notation += "\n}"
        return lilypond_notation

    def __repr__(self):
        """
        Represents the point as a string containing the note data and duration.
        """
        return f"{self.note_name}{self.duration}"


class AnalyzedSong:
    """A class representing the song after analysis. 

    Attributes
    ----------
    data : list[AnalysisPoint]
        description

    Methods
    -------
    add_point(time_stamp, frequency, note_name)
        add a time point and corresponding frequency and note name to the AnalyzedSong.
    get_analysis()
        Returns the list of analyzed data points.
    save_to_file(filename)
        Saves the analysis results to a file.
    notes_to_lilypond(self, chunk_duration)
        Returns a represtnation of the song notes in lilypond format.
    generate_sheet_music(self, image_name, chunk_duration=0.25)
        Generates a represtnation of the song notes in lilypond format
        and saves it to a PDF file. 
    """
    def __init__(self):
        """
        Parameters
        ----------
        data : list[AnalysisPoint]
            description
        """
        self.data = []

    def add_point(self, time_stamp: float, frequency: float,
        note_name: str, duration: float):
        """ Adds one analyzed point to the analyzed song. 

        detailed description

        Parameters
        ----------
        time_stamp : float
            the starting time of each time segments.
        frequency : float
            the dominant frequency at each time segments.
        note_name : str
            the note name that corresponds to the dominant frequency.
        duration: float
            duration of the note in secs
        """
        self.data.append(AnalysisPoint(time_stamp, frequency, note_name, duration))

    def get_analysis(self) -> List[AnalysisPoint]:
        """ Returns the list of analyzed data points.

        Returns
        -------
        list[AnalysisPoint]
            A populated list of AnalysisPoints 
        """
        return self.data

    def _combine_notes(self, chunk_duration):
        """Updates self.data array to combine consecutive identical notes together

        Parameters
        ----------
        chunk_duration: float
            duration of one beat in secs
        """
        combined_notes = []
        current_note = None
        current_freq = None
        current_start_time = 0.0
        duration = 0.0

        for point in self.data:
            if current_note == point.note_name:
                duration += chunk_duration  # assuming each segment represents 0.25s as per your example
            else:
                if current_note is not None:
                    combined_notes.append(AnalysisPoint(current_start_time, current_freq, current_note, duration))
                current_note = point.note_name
                current_start_time = point.time_stamp
                current_freq = point.frequency
                duration = chunk_duration

        # Add the last note
        if current_note is not None:
            combined_notes.append(AnalysisPoint(current_start_time, current_freq, current_note, duration))

        self.data = combined_notes
        return

    def save_to_file(self, filename: str):
        """ Saves the analysis results to a file.

        Parameters
        -------
        filename : str
            name of the file to save the analysis to.
        """
        with open(filename, 'w') as file:
            file.write(str(self))

    def __repr__(self):
        """
        Represents the song as a comma-delimited sequence of notes and their durations.
        """
        string = ''

        for i, point in enumerate(self.data):
            string += str(point)

            if i + 1 < len(self.data):
                string += ','

        return string


    def notes_to_lilypond(self, chunk_duration):
        """Returns a represtnation of the song notes in lilypond format

        Parameters
        ----------
        chunk_duration: float
            duration of one beat secs

        Returns
        -------
        str
            A represtnation of the song notes in lilypond format
        """
        #combine consecutive identical notes
        self._combine_notes(chunk_duration)
        lilypond_notation = "\\relative c' {\n    \\key c \\major\n    \\time 4/4\n"

        for point in self.data:
            lilypond_notation += point.note_to_lilypond(chunk_duration)
        lilypond_notation += "\n}"
        return lilypond_notation

