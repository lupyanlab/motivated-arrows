#!/usr/bin/env python
from UserDict import UserDict
from UserList import UserList

import unipath
# import pandas
# from numpy.random import random
import yaml

from psychopy import visual, core, event, sound

from labtools.psychopy_helper import get_subj_info


class Participant(UserDict):
    @classmethod
    def from_gui(cls, gui_yaml):
        """ Pull up a dialogue to get subject info. """
        participant_data = get_subj_info(gui_yaml)
        return cls(**participant_data)

    def write_trial_data(self, trial_data):
        """ Write the dictionary of data to a file in the correct order. """
        pass


class Trials(UserList):
    COLUMNS = [
        'block',
        'block_type',
        'trial',

        # Stimuli
        'cue_type',
        'cue_validity',
        'cue_dir',
        'cue_pos_y',
        'target_dir',
        'target_pos_x',
        'target_pos_y',
        'correct_response',

        # Response columns
        'response',
        'rt',
        'is_correct',
    ]

    @classmethod
    def make(cls, **kwargs):
        pass

    def iter_blocks(self, key='block'):
        """ Yield blocks of trials. """
        block = self[0][key]
        trials_in_block = []
        for trial in self:
            if trial[key] == block:
                trials_in_block.append(trial)
            else:
                yield trials_in_block
                block = trial[key]
                trials_in_block = []


class Experiment(object):
    STIM_DIR = 'stimuli'

    def __init__(self, settings_yaml, texts_yaml):
        with open(settings_yaml, 'r') as f:
            settings = yaml.load(f)

        self.waits = settings.pop('waits')
        self.response_keys = settings.pop('response_keys')
        layout = settings.pop('layout')

        with open(texts_yaml, 'r') as f:
            self.texts = yaml.load(f)

        self.win = visual.Window(fullscr=True, units='pix')

        text_kwargs = dict(win=self.win, font='Consolas', color='black',
                           height=30)
        self.fix = visual.TextStim(text='+', **text_kwargs)
        self.prompt = visual.TextStim(text='?', **text_kwargs)

        self.target = visual.Circle(self.win, radius=10, fillColor='black')

        self.arrows = {}
        for direction in ['left', 'right']:
            arrow_png = unipath.Path(self.STIM_DIR, 'arrows',
                                     'arrow-{}.png'.format(direction))
            self.arrows[direction] = visual.ImageStim(self.win, str(arrow_png))

        self.word = visual.TextStim(self.win, font='Consolas', color='black')

        gutter = layout['left_right_gutter']/2
        frame_positions = dict(left=(-gutter, 0), right=(gutter, 0))
        frame_kwargs = dict(
            win=self.win,
            width=layout['frame_size'],
            height=layout['frame_size'],
            lineColor='black'
        )
        self.frames = []
        for direction in ['left', 'right']:
            self.frames.append(visual.Rect(pos=frame_positions[direction],
                               **frame_kwargs))

        feedback_dir = unipath.Path(self.STIM_DIR, 'feedback')
        self.feedback = {}
        self.feedback[0] = sound.Sound(unipath.Path(feedback_dir, 'buzz.wav'))
        self.feedback[1] = sound.Sound(unipath.Path(feedback_dir, 'bleep.wav'))

        self.timer = core.Clock()

    def run_trial(self, trial):
        if trial['cue_type'] == 'arrow':
            cue = self.arrows[trial['cue_dir']]
        elif trial['cue_type'] == 'word':
            cue = self.word
            cue.setText(trial['cue_dir'])
        else:
            raise NotImplementedError

        cue_pos = (0, 0)
        cue.setPos(cue_pos)

        target_pos = (0, 0)
        self.target.setPos(target_pos)

        cue_offset_to_target_onset = self.waits['cue_onset_to_target_onset'] -\
            self.waits['cue_duration']

        # Begin trial presentation
        # ------------------------
        self.fix.draw()
        for frame in self.frames:
            frame.draw()
        self.win.flip()
        core.wait(self.waits['fixation_duration'])

        # Present cue
        cue.draw()
        for frame in self.frames:
            frame.draw()
        self.win.flip()
        core.wait(self.waits['cue_duration'])

        # Delay between cue and target
        self.fix.draw()
        for frame in self.frames:
            frame.draw()
        self.win.flip()
        core.wait(cue_offset_to_target_onset)

        # Show target
        self.target.draw()
        self.fix.draw()
        for frame in self.frames:
            frame.draw()
        self.win.flip()
        core.wait(self.waits['target_duration'])

        # Get response
        self.timer.reset()
        self.prompt.draw()
        self.win.flip()
        response = event.waitKeys(maxWait=self.waits['response_window'],
                                  keyList=self.response_keys.keys(),
                                  timeStamped=self.timer)
        self.win.flip()
        # ----------------------
        # End trial presentation

        try:
            key, rt = response[0]
        except TypeError:
            rt = self.waits['response_window']
            response = 'timeout'
        else:
            response = self.response_keys[key]

        is_correct = int(response == trial['correct_response'])

        trial['response'] = response
        trial['rt'] = rt * 1000
        trial['is_correct'] = is_correct

        self.feedback[is_correct].play()

        core.wait(self.waits['iti'])

        return trial


def main():
    participant_data = get_subj_info(
        'gui.yaml',
        # check_exists is a simple function to determine if the data file
        # exists, provided subj_info data. It's used to validate the data
        # entered in the gui.
        check_exists=lambda subj_info:
            Participant(**subj_info).data_file.exists()
    )

    participant = Participant(**participant_data)
    trials = Trials.make(**participant)

    # Start of experiment
    experiment = Experiment('settings.yaml', 'texts.yaml')
    experiment.show_instructions()

    participant.write_header(trials.COLUMNS)

    for block in trials.iter_blocks():
        block_type = block[0]['block_type']

        for trial in block:
            trial_data = experiment.run_trial(trial)
            participant.write_trial(trial_data)

        if block_type == 'practice':
            experiment.show_end_of_practice_screen()
        else:
            experiment.show_break_screen()

    experiment.show_end_of_experiment_screen()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['run', 'trials', 'test'],
                        nargs='?', default='run')

    args = parser.parse_args()
    if args.command == 'trials':
        pass
    elif args.command == 'test':
        trial = dict(
            cue_type='arrow',
            cue_validity='valid',
            cue_dir='left',
            target_dir='left',
            correct_response='left',
        )
        experiment = Experiment('settings.yaml', 'texts.yaml')
        trial_data = experiment.run_trial(trial)

        import pprint
        pprint.pprint(trial_data)
    else:
        main()
