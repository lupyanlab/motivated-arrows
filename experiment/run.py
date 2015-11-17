#!/usr/bin/env python
from UserDict import UserDict
from UserList import UserList

import unipath
import pandas
from numpy import random
import yaml

from psychopy import visual, core, event, sound

from labtools.psychopy_helper import get_subj_info
from labtools.trials_functions import expand, extend, add_block


class Participant(UserDict):
    """ Store participant data and provide helper functions. """
    DATA_DIR = 'data'
    DATA_DELIMITER = ','

    def __init__(self, **kwargs):
        """ Standard dict constructor.

        Saves _order if provided. Raises an AssertionError if _order
        isn't exhaustive of kwargs.
        """
        self._data_file = None
        self._order = kwargs.pop('_order', kwargs.keys())

        correct_len = len(self._order) == len(kwargs)
        kwargs_in_order = all([kwg in self._order for kwg in kwargs])
        assert correct_len & kwargs_in_order, "_order doesn't match kwargs"

        self.data = dict(**kwargs)

    @property
    def data_file(self):
        if not unipath.Path(self.DATA_DIR).exists():
            unipath.Path(self.DATA_DIR).mkdir()

        if not self._data_file:
            data_file_name = '{subj_id}.csv'.format(**self)
            self._data_file = unipath.Path(self.DATA_DIR, data_file_name)
        return self._data_file

    def write_header(self, trial_col_names):
        """ Writes the names of the columns and saves the order. """
        self._col_names = self._order + trial_col_names
        self._write_line(self.DATA_DELIMITER.join(self._col_names))

    def write_trial(self, trial):
        assert self._col_names, 'write header first to save column order'
        trial_data = dict(self)
        trial_data.update(trial)
        row_data = [str(trial_data[key]) for key in self._col_names]
        self._write_line(self.DATA_DELIMITER.join(row_data))

    def _write_line(self, row):
        with open(self.data_file, 'a') as f:
            f.write(row + '\n')


class Trials(UserList):
    COLUMNS = [
        'block',
        'block_type',
        'trial',
        # Stimuli
        'cue_type',
        'cue_validity',
        'cue_dir',
        'cue_pos_dy',
        'target_loc',
        'target_pos_dy',
        'correct_response',
        # Determined at runtime
        'cue_pos_y',
        'target_pos_x',
        'target_pos_y',
        # Response columns
        'response',
        'rt',
        'is_correct',
    ]

    @classmethod
    def make(cls, **kwargs):
        seed = kwargs.get('seed')
        prng = random.RandomState(seed)
        ratio_cue_valid = kwargs.get('ratio_cue_valid', 0.67)

        trials = pandas.DataFrame({'cue_type': ['arrow', 'word']})
        trials = expand(trials, 'cue_validity', values=['valid', 'invalid'],
                        ratio=ratio_cue_valid, seed=seed)

        trials = extend(trials, max_length=320)
        trials['target_loc'] = prng.choice(['left', 'right'], len(trials))
        trials['correct_response'] = trials['target_loc']

        reverser = dict(left='right', right='left')
        def pick_cue_dir(trial):
            cue_validity = trial['cue_validity']
            target_loc = trial['target_loc']
            if cue_validity == 'valid':
                return target_loc
            elif cue_validity == 'invalid':
                return reverser[target_loc]
            else:
                raise NotImplementedError('cue_validity: %s' % cue_validity)
        trials['cue_dir'] = trials.apply(pick_cue_dir, axis=1)

        # Determine cue pos and target pos
        trials['cue_pos_dy'] = 0.
        trials['target_pos_dy'] = 0.
        trials[['cue_pos_dy', 'target_pos_dy']] = prng.multivariate_normal(
            mean=[0, 0], cov=[[1, 0], [0, 1]], size=len(trials)
        )
        # Actual units (pixels) are determined at runtime.
        for x in ['target_pos_x', 'target_pos_y', 'cue_pos_y']:
            trials[x] = ''

        trials = add_block(trials, size=60, start=1, seed=seed)
        trials['block_type'] = 'test'

        # Add practice trials
        num_practice = 8
        practice_ix = prng.choice(trials.index, num_practice)
        practice_trials = trials.ix[practice_ix, ]
        trials.drop(practice_ix, inplace=True)
        practice_trials['block'] = 0
        practice_trials['block_type'] = 'practice'
        trials = pandas.concat([practice_trials, trials])

        trials['trial'] = range(len(trials))

        # Add blank columns for response variables
        for x in ['response', 'rt', 'is_correct']:
            trials[x] = ''

        return cls(trials.to_dict('record'))

    def write(self, trials_csv='sample_trials.csv'):
        trials = pandas.DataFrame.from_records(self)
        trials = trials[self.COLUMNS]
        trials.to_csv(trials_csv, index=False)

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

    def __init__(self, settings_yaml='settings.yaml', texts_yaml='texts.yaml'):
        with open(settings_yaml, 'r') as f:
            settings = yaml.load(f)

        self.waits = settings.pop('waits')
        self.response_keys = settings.pop('response_keys')
        self.survey_url = settings.pop('survey_url')
        layout = settings.pop('layout')
        self.positions = layout.pop('positions')

        with open(texts_yaml, 'r') as f:
            self.texts = yaml.load(f)

        self.win = visual.Window(fullscr=True, allowGUI=False, units='pix')

        text_kwargs = dict(win=self.win, font='Consolas', color='black',
                           height=30)
        self.fix = visual.TextStim(text='+', **text_kwargs)
        self.prompt = visual.TextStim(text='?', **text_kwargs)

        word_kwargs = dict(text_kwargs)
        word_kwargs['height'] = 30
        self.word = visual.TextStim(**word_kwargs)

        self.target = visual.Circle(self.win, radius=10, fillColor='black',
                                    lineColor=None, opacity=0.1)

        self.arrows = {}
        for direction in ['left', 'right']:
            arrow_png = unipath.Path(self.STIM_DIR, 'arrows',
                                     'arrow-{}.png'.format(direction))
            self.arrows[direction] = visual.ImageStim(self.win, str(arrow_png))



        frame_kwargs = dict(
            win=self.win,
            width=layout['frame_size'],
            height=layout['frame_size'],
            lineColor='black'
        )
        self.frames = []
        for direction in ['left', 'right']:
            self.frames.append(visual.Rect(pos=self.positions[direction],
                               **frame_kwargs))

        # 3 seems to be about max of the sampling distribution
        half_frame = layout['frame_size']/2
        multiplier = half_frame / 3
        def project(y):
            return y * multiplier
        self.project = project

        x_edge = half_frame/6.0
        def uniform_x(loc):
            x_center = self.positions[loc][0]
            return random.uniform(x_center-x_edge, x_center+x_edge)
        self.uniform_x = uniform_x

        feedback_dir = unipath.Path(self.STIM_DIR, 'feedback')
        self.feedback = {}
        self.feedback[0] = sound.Sound(unipath.Path(feedback_dir, 'buzz.wav'))
        self.feedback[1] = sound.Sound(unipath.Path(feedback_dir, 'bleep.wav'))

        self.timer = core.Clock()

    def run_trial(self, trial):
        cue_type = trial['cue_type']
        cue_dir = trial['cue_dir']
        if cue_type == 'arrow':
            cue = self.arrows[cue_dir]
        elif cue_type == 'word':
            cue = self.word
            cue.setText(cue_dir)
        else:
            raise NotImplementedError('cue_type: %s' % cue_type)

        # Determine vertical cue location
        trial['cue_pos_y'] = self.project(trial['cue_pos_dy'])
        trial['target_pos_y'] = self.project(trial['target_pos_dy'])
        trial['target_pos_x'] = self.uniform_x(trial['target_loc'])

        cue_pos = (0, trial['cue_pos_y'])
        cue.setPos(cue_pos)

        target_pos = (trial['target_pos_x'], trial['target_pos_y'])
        self.target.setPos(target_pos)

        cue_offset_to_target_onset = self.waits['cue_onset_to_target_onset'] -\
            self.waits['cue_duration']

        for frame in self.frames:
            frame.autoDraw = True

        # Begin trial presentation
        # ------------------------
        self.fix.draw()
        self.win.flip()
        core.wait(self.waits['fixation_duration'])

        # Present cue
        cue.draw()
        self.win.flip()
        core.wait(self.waits['cue_duration'])

        # Delay between cue and target
        self.win.flip()
        core.wait(cue_offset_to_target_onset)

        # Show target
        self.timer.reset()
        self.target.draw()
        self.win.flip()
        core.wait(self.waits['target_duration'])

        # Get response
        self.prompt.draw()
        self.win.flip()
        response = event.waitKeys(maxWait=self.waits['response_window'],
                                  keyList=self.response_keys.keys(),
                                  timeStamped=self.timer)
        for frame in self.frames:
            frame.autoDraw = False
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

        if trial['block_type'] == 'practice' or response == 'timeout':
            self.feedback[is_correct].play()

        if response == 'timeout':
            self.show_screen('timeout')

        core.wait(self.waits['iti'])

        return trial

    def show_screen(self, name):
        if name == 'instructions':
            self._show_instructions()
        elif name in self.texts:
            self._show_screen(text=self.texts[name])
        else:
            raise NotImplementedError('%s is not a valid screen' % name)

    def _show_screen(self, text):
        visual.TextStim(text=text, **self.screen_text_kwargs).draw()
        self.win.flip()
        response = event.waitKeys(keyList=['space', 'q'])[0]

        if response == 'q':
            core.quit()

    def _show_instructions(self):
        instructions = sorted(self.texts['instructions'].items())

        main_kwargs = dict(self.screen_text_kwargs)
        main_kwargs['height'] = 25
        main_kwargs['pos'] = (0, 350)

        main = visual.TextStim(**main_kwargs)
        for num, text in instructions:
            main.setText(text)
            main.draw()

            advance_keys = ['space', 'q']

            if num == 1:
                for frame in self.frames:
                    frame.draw()
                self.target.setPos(self.positions['left'])
                self.target.draw()
                advance_keys = ['left', 'q']
            elif num == 2:
                for frame in self.frames:
                    frame.draw()
                self.arrows['left'].draw()
                self.word.setText('right')
                self.word.setPos((0, 100))
                self.word.draw()

            self.win.flip()
            response = event.waitKeys(keyList=advance_keys)[0]

            if response in ['left', 'right']:
                self.feedback[1].play()

            if response == 'q':
                core.quit()


    @property
    def screen_text_kwargs(self):
        if not hasattr(self, 'screen_text_kwargs'):
            self._screen_text_kwargs = dict(
                win=self.win,
                font='Consolas',
                color='black',
                height=30,
                wrapWidth=800,
            )
        return self._screen_text_kwargs


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
    last_block_num = trials[-1]['block']

    # Start of experiment
    experiment = Experiment('settings.yaml', 'texts.yaml')
    experiment.show_screen('instructions')

    participant.write_header(trials.COLUMNS)

    for block in trials.iter_blocks():
        block_num = block[0]['block']
        block_type = block[0]['block_type']

        for trial in block:
            trial_data = experiment.run_trial(trial)
            participant.write_trial(trial_data)

        if block_type == 'practice':
            experiment.show_screen('end_of_practice')
        elif block_num != last_block_num:
            experiment.show_screen('break')

    experiment.show_screen('end_of_experiment')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    command_choices = ['main', 'maketrials', 'singletrial', 'instructions',
                       'survey']
    parser.add_argument('command', choices=command_choices,
                        nargs='?', default=command_choices[0])

    default_trial_options = dict(
        cue_type='arrow',
        cue_validity='valid',
        cue_dir='left',
        target_loc='left',
    )

    args = parser.parse_args()
    if args.command == 'maketrials':
        trials = Trials.make()
        trials.write()
    elif args.command == 'singletrial':
        trial = dict(
            cue_type='arrow',
            cue_validity='valid',
            cue_dir='left',
            target_loc='left',
            correct_response='left',
        )
        experiment = Experiment('settings.yaml', 'texts.yaml')
        trial_data = experiment.run_trial(trial)

        import pprint
        pprint.pprint(trial_data)
    elif args.command == 'instructions':
        experiment = Experiment()
        screens = ['instructions', 'end_of_practice', 'break', 'timeout',
                   'end_of_experiment']
        for name in screens:
            experiment.show_screen(name)
    elif args.command == 'survey':
        experiment = Experiment()
        import webbrowser
        webbrowser.open(experiment.survey_url.format(subj_id='TESTSUBJ', computer='TESTCOMPUTER'))
        core.quit()
    else:
        main()
