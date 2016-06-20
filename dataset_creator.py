import sublime, sublime_plugin, time

from xml.dom import minidom as dom

from xml.etree import ElementTree as ET

#We need to implement command piece. 
class DatasetCreatorCommand(sublime_plugin.WindowCommand):

##############################

# 	Main

##############################
	def run(self):
		#hardcode defines the valid keys and validators
		self.presets = {"keys":[{"name":"Family Id","field":"familyid","validator":"VARCHAR","ui":"com.wtp.jforms.ui.control.selection.FamilyId"},{"name":"Twin","field":"twin","validator":"INTEGER","ui":"com.wtp.jforms.ui.control.selection.RadioSelector"},{"name":"Data Mode","field":"datamode","validator":"VARCHAR","ui":"com.wtp.jforms.ui.control.selection.RadioSelector"}],"validators":[{"name":"val_0-1_9998_9999","type":"INTEGER","allowblanks":"false","lowerbound":"0","upperbound":"1","valid_values":["9999","9998"]},{"name":"blankformat","type":"VARCHAR","allowblanks":"true","lowerbound":"2147483647","upperbound":"2147483647","valid_values":["9999","9998"]},{"name":"val13_9998_9999","type":"INTEGER","allowblanks":"false","lowerbound":"1","upperbound":"3","valid_values":["9998","9999"]}]}

		#When creating validators and keys we need to map different functions to the current list_type
		self.type_mapping = {"keys": {'maker':self.make_key, 'post':self.post_keys}, "validators": {'maker':self.make_validator, 'post':self.post_validators }, 'dataset':{'parameters':['name','filename'], 'post': self.post_dataset_input}, 'data':{'parameters':['name', 'field', 'validator', 'editable', 'ui'], 'post': self.prompt_custom_data, 'done': self.post_data}}

		self.values_for = {"data":{}, "dataset":{}}
		self.data_list = []


		self.curr_list_type = 'validators'
		

		#Prompt the user for information
		print('Prompt the user for information')
		self.prompt_input_panel('dataset')
		
		
	def post_dataset_input(self):
		#make root dataset
		# TODO: automate filename. make new file?
		# TODO: automate abrv
		print('make root dataset')
		self.dataset = self.create_dataset(self.values_for['dataset'])
		
		print('creates selected validators')
		self.prompt_list('validators')

	def post_validators(self):
		print("Creates keys")
		self.prompt_list('keys')
		
		
	def post_keys(self):
		print('creates data fields')
		self.get_num_data()

	def post_data(self):
		self.make_data()
		print('pretty print dataset')
		pretty_dataset= self.to_pretty_print(self.dataset)
		print(pretty_dataset)

				
		# #creates dependencies
		# print('creates dependencies')
		# self.dataset.append(self.create_dependency('field', [{'field': 'poo1','lowerbound': 'poo2','upperbound': 'poo3','values': ['3','4','5']}]))# 	# self.window.active_view().insert(cursor_pos, pretty_validator)


##############################

# 	Prompting user for info

##############################
	#show input panel for name and filename
	def prompt_input_panel(self, list_type):
		self.type_map_counter = 0
		self.curr_list_type = list_type
		self.open_input_panel()

	#shows input panel. goes to on_done after input is done	
	def open_input_panel(self):
		self.window.show_input_panel(self.type_mapping[self.curr_list_type]['parameters'][self.type_map_counter],'', self.on_done, None, self.on_cancel)

	#increments the counter and sets self.contents (declared in prompt_dataset). 
	def on_done(self, content):
		# Handles Successful input for dataset and data types

		curr_param = self.type_mapping[self.curr_list_type]['parameters'][self.type_map_counter]
		print(self.values_for)
		print("content:" + content)
		self.values_for[self.curr_list_type][curr_param] = content
		print(self.values_for)
		self.type_map_counter += 1
		if self.type_map_counter < len(self.type_mapping[self.curr_list_type]['parameters']):
			#if not done get more input
			self.open_input_panel()
		else:
			#done
			self.input_done()

	def input_done(self):
		self.type_mapping[self.curr_list_type]['post']()

	def on_cancel(self):
		pass #self.type_mapping[curr_list_type][]

##############################

# 	prompting user for validator & key info

##############################

	
	#gets the number of keys or validators and sets the current list type
	def prompt_list(self, list_type):
		self.presets_counter = 0 #resets the counter
		print('changing curr_list_type from -> ' + self.curr_list_type + ' <- to -> ' + list_type + ' <-' )
		self.curr_list_type = list_type #declares and sets class variable to the current list type (keys or validator)
		self.window.show_input_panel('Number of ' + self.curr_list_type , '', self.get_list_input,None,None)

	#
	def get_list_input(self, num_list_items):
		print('number of list items: '+str(num_list_items) + '. counter is at: ' + str(self.presets_counter))	
		self.num_list_items = int(num_list_items)
		if self.presets_counter < self.num_list_items:
			self.options = self.get_options_from_presets()
			print('about to be showing quick panel. Counter is: ' + str(self.presets_counter) + '. type: ' + self.curr_list_type)
			self.show_quick_panel(self.options, self.on_list_close)
		else:
			print('returning to main properly')
			self.type_mapping[self.curr_list_type]['post']()

	def show_quick_panel(self, options, on_close):
		print('showing quick panel')
		sublime.set_timeout(lambda: self.window.show_quick_panel(options, on_close), 10)

	# TODO: @refactor hardcoded items
	def on_list_close(self, index_of_option):
		print('prompt returned ' + str(index_of_option))
		if index_of_option != -1:
			#makes a tag of the correct type once one has been selected
			self.type_mapping[self.curr_list_type]['maker'](self.presets[self.curr_list_type][index_of_option])
			
			print(self.presets[self.curr_list_type][index_of_option]['name']) #TODO: @TESTING
			self.presets_counter += 1

			self.get_list_input(self.num_list_items)
		else: # the quick panel has been canceled. End early
			sublime.status_message('Quick panel was exited. Dataset Maker canceled.')

	def get_options_from_presets(self):
		tmp_list = []
		for x in self.presets[self.curr_list_type]:
			tmp_list.append(x['name'])
		return tmp_list


##############################

#	Prompt for custom data

##############################
	def get_num_data(self):
		self.data_counter = 0 #resets the counter
		self.window.show_input_panel('Number of Data Fields', '', self.set_num_data,None,None)

	def set_num_data(self, num_data):
		self.num_data = int(num_data)
		self.prompt_custom_data()

	def prompt_custom_data(self):
		print('--------------------------------------------------------------------------')
		#TODO @refactor remove hardcoded counter
		
		
		if (self.values_for['data']) :
			#if data is filled

			print("should be full dict: " + str(self.values_for['data']))
			#add to datalist
			self.data_list.append(self.values_for['data'])
			print(str(self.values_for['data']) + '      ' + str(self.data_list))
			#reset data
			self.values_for['data'] = {}
		
		if self.data_counter < self.num_data:
			self.prompt_input_panel('data')
			self.data_counter += 1

		else:
			self.post_data()





##############################

#	CREATORS

##############################
	def make_validator(self, args):
		self.dataset.append(self.create_validator(args))

	def make_key(self, args):
		self.dataset.append(self.create_key(args))

	def make_data(self):
		print(self.data_list)
		for i in self.data_list:
			i['classid'] = 'a'
			i['dependencies'] = 'False'
			print(i)
			self.dataset.append(self.create_data(i))

	def create_validator(self, args):
		validator = ET.Element("validator", {'name': args[ 'name' ], 'type': args[ 'type' ],'defaultvalue':'9998', 'allowblanks': args[ 'allowblanks' ], 'lowerbound':args[ 'lowerbound' ], 'upperbound': args[ 'upperbound' ]})
		for value in args['valid_values']:
			self.add_valid_values(value, validator)
		return validator

	def add_valid_values(self, value, root):
		ET.SubElement(root, "valid", {'value':value})
##############################
	#TODO: @futurproof change abrv so that its actually an abrv not just 'name'
	def create_dataset(self, args):
		dataset = ET.Element("dataset", {'name':args['name'],'abrv':args['name'],'filename':args['filename']})
		return dataset

	def create_key(self, args):
		key = ET.Element("key", {'name': args[ 'name' ], 'field': args[ 'field' ],'template':'na', 'validator': args[ 'validator' ], 'ui':args[ 'ui' ], 'value':""})
		return key

	def create_data(self, args): #TODO: @futureproof 2 ways of making classids. start at 111... and randomization w/error checking. check if classids have to match forms.  
		data = ET.Element("data", {'name': args[ 'name' ], 'field': args[ 'field' ],'template':'na', 'validator': args[ 'validator' ], 'dependencies':args[ 'dependencies' ], 'editable':args[ 'editable' ], 'ui':args[ 'ui' ], 'classid':args[ 'classid' ]})
		return data

	def create_dependency(self, args):
		dependency = ET.Element("dependency", {'field':args[ 'field' ]})
		for p in args[ 'parents' ]:
			self.add_parent_tag(dependency, p)
		return dependency

	#parent_attr should be a dictionary with all arttributes + values key that holds an array of enable values
	def add_parent_tag(self, dependency, parent_attr):
		parent = ET.SubElement(dependency, "parent", {'field':parent_attr['field'],'lowerbound':parent_attr['lowerbound'],'upperbound': parent_attr['upperbound']})
		for x in parent_attr['values']:
			ET.SubElement(parent, "enable", {'value':x})	


##############################

#	Prettifier

##############################

	def to_pretty_print(self,root):

		rough_string = ET.tostring(root)
		reparsed = dom.parseString(rough_string)
		
		pretty = reparsed.toprettyxml(indent="    ")
		prettyarray = pretty.split('\n')
		prettyXML = "\n".join(prettyarray[1:])
		return prettyXML



