import sublime, sublime_plugin, json

class CustomValidatorCommand(sublime_plugin.WindowCommand):

	def run(self):
		self.parameters = ['name', 'validation_type', 'allowblanks', 'lowerbound', 'upperbound', 'valid_values']	
		self.contents =['','','','','','']
		self.counter = 0

		self.show_prompt()

	def show_prompt(self):
		self.window.show_input_panel(self.parameters[self.counter],'',self.on_done,None,None)

	def on_done(self, content):
		
		if self.counter == self.parameters.index('valid_values'):
			# Expecting comma delimited values
			content = content.split(',')

		self.contents[self.counter] = content
		self.counter += 1
		if self.counter < len(self.parameters):
			self.show_prompt()
		else:
			self.input_done()

	def input_done(self):
		parameters_dict = dict(zip(self.parameters,self.contents))
		curr_view = self.window.active_view()
		print(parameters_dict)
		curr_view.run_command('create_validator', { "args": parameters_dict })
		
	
	