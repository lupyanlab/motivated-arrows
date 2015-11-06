from UserDict import UserDict
from UserList import UserList

from psychopy import visual, core, event

from labtools import get_subj_info


class Participant(UserDict):
	@classmethod
	def from_gui(cls, gui_yaml):
		""" Pull up a dialogue to get subject info. """
		participant_data = get_subj_info(gui_yaml)
		return cls(**participant_data)

	def write_trial_data(self, trial_data):
		""" Write the dictionary of data to a file in the correct order. """
		pass


class TrialList(UserList):
	@classmethod
	def from_kwargs(**kwargs):
		""" Create a trial list from settings. """
		pass

	def iter_blocks(self, key='block'):
		""" Return trials in blocks. """
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
	def __init__(self, settings_yaml):
		with open(settings_yaml, 'r') as f:
			self.settings = yaml.load(f)

		self.win = visual.Window(fullscr=True, units='pix')

	@property
	def fields(self):
		return sorted(self.settings.keys())

	def show_instructions(self):
		pass

	def run_trial(self, trial):
		trial.update(self.settings)
		return trial


def main():
	participant = Participant.from_gui('gui.yaml')
	trials = TrialList.from_kwargs(**participant)
	experiment = Experiment('settings.yaml')

	header = participant.fields + experiment.fields + trials.fields
	participant.write_header(header)

	experiment.show_instructions()

	for block in trials.iterblocks():
		for trial in block:
			trial_data = experiment.run_trial(trial)
			participant.write_trial_data(trial_data)


if __name__ == '__main__':
	main()
