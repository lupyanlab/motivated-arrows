from UserDict import UserDict
from UserList import UserList


class Participant(UserDict):
	@classmethod
	def from_gui(gui_yaml):
		""" Pull up a dialogue to get subject info. """
		pass

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
	pass

if __name__ == '__main__':
	participant = Participant.from_gui('gui.yaml')
	trials = TrialList.from_kwargs(**participant)
	experiment = Experiment()

	experiment.show_instructions()
	
	for block in trials.iterblocks():
		for trial in block:
			trial_data = experiment.run_trial(trial)
			participant.write_trial_data(trial_data)
