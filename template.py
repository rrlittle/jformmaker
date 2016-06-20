import sublime, sublime_plugin
import os, os.path
import pypyodbc as db
import json
import collections
# connect, execute, commit

from xml.dom import minidom as dom
from xml.etree import ElementTree as ET


# from template.py import view_contents

def view_contents(view):
    region = sublime.Region(0, view.size())
    return view.substr(region)

class DatasetTemplateCommand(sublime_plugin.WindowCommand):
	
	
	
	def run(self):
		
		print('entering template')
		# Get an array of DB fields from the given table
		# print('showing input panel')
			#TODO:@testing for testing this is the point to turn off the name prompt
		self.window.show_input_panel('Table Name','data_', self.on_done,None,None)
		#self.on_done('data_c3_dc_m')	#test table

	def on_done(self, table_name):
		field_names = self.fetchDBFields(table_name)
		


	def fetchDBFields(self, table_name):
		field_names = [] #declaring fieldnames in outer scope
		# open db connection
		conn = db.connect('DSN=wtp_data')
		cur = conn.cursor()
		
		if table_name in [row['table_name'] for row in cur.tables()]: #if table exists
			# print('table %s exists' % table_name)
			cur.execute('select * from %s' % table_name) #select the fields
			field_names = [field[0] for field in cur.description if field[6] and (not (field[0] == 'checked')) ] #save them
		else:	#else prompt the user for the correct table name. assming it was a misspelling or table not initiated
			# print('table %s does not exist' % table_name)
			sublime.status_message('Table Does Not Exist')
			sublime.set_timeout(lambda: self.window.show_input_panel('Table Name','', self.on_done,None,None), 10)
			return	
		cur.close()
		conn.close()
		# print('field names: ' + str(field_names))
		# Create a new tab
		ds_templ = self.window.new_file()

		# Sends the prompt message to the new window
		ds_templ.run_command('scratch_output', {'fieldnames':field_names, 'table_name': table_name })

class ScratchOutputCommand(sublime_plugin.TextCommand):
	def run(self, edit, fieldnames = '', clear = False, table_name = ''):
		# Create a new window for the dataset template
		# Sets the name of the new window
		self.view.set_name('Dataset-Template')
		self.view.set_scratch(True)
		self.view.set_syntax_file("Packages/jformmaker/maker_syntax.tmLanguage")

		if clear:
			region = sublime.Region(0, self.view.size())
			self.view.erase(edit, region)

		output = self.set_output(fieldnames, table_name)
	        

		self.view.insert(edit, 0, output)


	def set_output(self, data_fields, table_name):
		lines = []

		data_field_template = self.buildDataTemplate(data_fields)

		# TODO:@futureproof this is where the template is constructed
		lines.extend([
		#	'! -Study-',
		#	'# name convention for the file is study~tblname~dsName',
		#	'# Imaging = mr',
		#	'# Conte3 = c3',
		#	'# phase 5 = p5',
		#	'# just type a string that is the study name',
		#	'','',
		#	'! !Study~',
		#	'!-Admin-',
		#	'','',
		#	'~Admin~',
			'! -Dataset Name-',
			'# What will the dataset be called? ',
			'# The filename will be a phase_packet_name_study concatenated',
			'~ phase: ',
			'~ packet name: ', #should be vernacular. this will be how it shows up on the form
			'~ study: ', #used to uniquely identify each form, will be represented in filename
			'~ table name:%s' % table_name,
			'! ~Dataset Name~',
			'# ------------------',
			'! -Validators-', #TODO:@assumptions add list of builtin validators
			'# blankformat is a special case',
			'# syntax -> name : range validValue1 validValue2 ... do not include 9999 or 9998',
			'# Assumptions -> allowblanks = false, default value = 9998, accepted values = 9998 + 9999, type = INTEGER',
			'# NOTE: It is ONLY okay to use the character \':\' right here to separate names'
			'',
			' blankformat',
			'# yesno : 0-1',
			'# 1 3',
			'','',
			'! ~Validators~',
			'# ------------------',
			'! -Keys-',
			'',
			' Family',
			'# Check',
			'# Twin',
			'','',
			'! ~Keys~',
			'# ------------------',
			'! -Data List-',
			'',
			'\n'.join(data_field_template),
			# "{'name':" ",'validator':" ",'dependencies':" ",'ui':" ",'field':" "}",
			'','',
			'! ~Data List~',
			'# ------------------',
			'! -Dependencies-'
			'','',
			'! ~Dependencies~'
			]) 
		return '\n'.join(lines)



	def buildDataTemplate(self,field_names):
		# todo: Format the field names to our template
		# data_template = [name+'\t:' for name in field_names]
		data_template = []
		for fn in field_names:
			data_row = '{"dependencies":" ","ui":" ","validator":" ","name":" ","field":"%s"}' % fn
			data_template.append(data_row)
		# print(data_template)
		return data_template








class TemplateEventListener(sublime_plugin.EventListener):
	def on_close(self, view):
		
			#only run if the right things close
		if view.name() != 'Dataset-Template':
			return


			#set global values
		self.classid = 1234567890123
		self.presets ={"keys":[{"name":"Family Id","field":"familyid","validator":"VARCHAR","ui":"com.wtp.jforms.ui.control.selection.FamilyId"},{"name":"Twin","field":"twin","validator":"INTEGER","ui":"com.wtp.jforms.ui.control.selection.RadioSelector"},{"name":"Data Mode","field":"datamode","validator":"VARCHAR","ui":"com.wtp.jforms.ui.control.selection.RadioSelector"}],"validators":[{"name":"blankformat","type":"VARCHAR","allowblanks":"true","lowerbound":"2147483647","upperbound":"2147483647","valid_values":["9999","9998"]}]}



		
		########
		#
		#	PARSING THE TEMPLATE / Creating the dataset xml tree
		#
		##########
		self.extract_and_set(view)  
		

		########
		#
		#	ERROR CHECKING
		#
		##########

		#not currently working.
		#self.name_duplicates() this is not fully implemeted and will break the program



		########
		#
		#	DRAWING the new file.
		#
		##########

		print('about to prettyprint')
		prettyxml = self.to_pretty_print(self.dataset)
		
		#add encoding information
		prettyxml = [
		'<?xml version="1.0" encoding="UTF-8"?>',
		'<!DOCTYPE dataset SYSTEM "../../dtd/dataset.dtd">',
		prettyxml
		]
		prettyxml = '\n'.join(prettyxml)
		#print(prettyxml)
		view.run_command('dataset_output',{'body':prettyxml, 'filename': self.dataset.attrib['filename']})

################################################################################
##########
##########  ERROR CHECKING - Implementation
##########
################################################################################

	def name_duplicates(self):
		dupls = self.check_for_duplicate_names()
		for d in dupls:
			print(d.get('field'))
		if(0 != len(dupls)):
			self.fix_duplicate_names(dupls)
		else:
			return

	def check_for_duplicate_names(self):
		ds = self.dataset
		data = [data for data in ds.findall('data')]
		duplicates = list([x for x in data if [d.get('name') for d in data].count(x.get('name')) > 1 and not x.get('name').strip().isspace()])
		
		return duplicates

	def fix_duplicate_names(self, dupls):
		self.cur_dupl = dupls.pop()

		sublime.active_window().show_input_panel('Duplicate data name %s. enter new name for field %s' % (cur_dupl, ds[i].get('field')),'', self.loop_dupls, None,None)

	def loop_dupls(self, replacement_name):
		ds =self.dataset.findall('data')
		i = ds.index(self.cur_dupl)
		ds[i].set('name', replacement_name)
		self.name_duplicates()




################################################################################
##########
##########  EXTRACTIONS - Implementation
##########
################################################################################

	def extract_and_set(self, view):

		sections = [line for line in view_contents(view).split('\n# ------------------') ]
		for section in sections:
			cur_index = sections.index(section)
			section = [line.strip() for line in section.split('\n') if not (line.strip().startswith('#') or line.strip().startswith('!')) and line and not line.isspace()]
			sections[cur_index] = section
		
		sections_vals = sections
		#sections_vals is just a list of lines, each line is a string. 
		#need to parse the string into xml attributes


		# Creating a useful dict from sections
		sections_keys = ['name','validators', 'keys', 'data','dependencies']
		sections = dict(zip(sections_keys, sections_vals))
		# print(str(sections) + '\n:sections before parsing')


			#need the name fields to create the root of xml tree. 'dataset'
		sections['name'] = self.extract_dataset(sections['name'])
		self.dataset = self.create_dataset(sections['name'])
		
			#these each add the extracted info to self.dataset, so dataset had to be initialized before them
		self.extract_validators(sections['validators'])
		self.extract_keys(sections['keys'])
		self.extract_data(sections['data'])
		self.extract_dependencies(sections['dependencies'])


	def extract_dataset(self, name):
	#TODO: @assumption we're using abrv to save the table name
		dataset_dict = {}
#		if '~' not in name[0]:     RIGHT NOW. We're not error checking. If you don't put anything in. it'll fail. cause you suck. 
			# print('got past name check')
		phase_name = name[0].split(':')[1].strip() # e.g. cp3
		form_name = name[1].split(':')[1].strip()  #e.g. twin interview questionnaire
		study = name[2].split(':')[1].strip() # BDI
		table_name = name[3].split(':')[1].strip() # data_c3_bd_t

		dataset_dict['name'] = study
		dataset_dict['abrv'] = table_name

		filename = study.split(" ")
		filename.extend(form_name.split(" "))
		filename.extend(phase_name.split(" "))
		filename = [f for f in filename if not f.isspace()]
		dataset_dict['filename'] = "_".join(filename)
#		else:    AGAIN. error checking currenlty disabled. 
#			# print('did not get past name check')
#			#TODO: @ defaulting if no name is specified. give it a nonsense name.
#			dataset_dict['name'] = 'DEFAULT_NAME'
#			dataset_dict['abrv'] = name[0].split(':')[1].strip()
#			dataset_dict['filename'] = '_'.join(dataset_dict['name'].split(" "))
#
		return dataset_dict

	def extract_validators(self, validators):
		#validator is each part of the whole string passed in
		for validator in validators:
			#TODO:@WIP if you add more preset validators be sure to add them here
			if 'blankformat' in validator:
				self.make_validator(self.presets['validators'][0])
				
			else:	
				#create a custom validator
				validator_dict = {}
				
				#custom validators should be in the form name:range validVal validVal ...
				#first split on : to separate name 
				#second split on spaces to separate the ranges and valid values

				#getting the name
				validator = [i.strip() for i in validator.split(':')]
				if len(validator) == 2: # there is a name
					validator_dict['name'] = validator[0]
					validator = validator[1]
				elif len(validator) == 1: # did not split, and there is no name
					validator_dict['name'] = ('_').join(validator[0].split(" "))
					validator = validator[0]

				validator = validator.split(" ") 
				#getting range if any
				if '-' in validator[0]: 
					validator_dict['lowerbound'] = validator[0].split('-')[0]
					validator_dict['upperbound'] = validator[0].split('-')[1]
					validator.pop(0)
				else: #if there is no range, specify arbitrary values
					validator_dict['lowerbound'] = '214783647'
					validator_dict['upperbound'] = '214783647'

				validator_dict['valid_values'] = validator # the rest of the array is valid values, which are passed in an array
				validator_dict['valid_values'].extend(['9999', '9998']) #TODO:@assumptions n validator we assume 9999 & 9998 are valid values
				validator_dict['type'] = 'INTEGER' #TODO:@assumptions in validator we assume type is an integer, change here if you would like
				validator_dict['allowblanks'] = 'false' #TODO:@assumptions in validator, we assume allowblannks is false. change here if you would like to change

				self.make_validator(validator_dict)




	def extract_keys(self, keys):
		#keys is a list of strings with any or all of Family. Check, Twin
		if 'Family' in keys:
			self.make_key(self.presets['keys'][0])				 
		if 'Check' in keys:
			self.make_key(self.presets['keys'][1])			
		if 'Twin' in keys:
			self.make_key(self.presets['keys'][2])				 

		

	def extract_data(self, data_list):
		#data list is a list of strings like this  {'name':" ",'validator':" ",'dependency':" ",'ui':" ",'field':'dcco001m'}

		for data in data_list:
			i = data_list.index(data)
			data_list[i] = json.loads(data) #turns string into a dict with above structure

			#print(str(data_list[i]))
			#strip any extraneous whitespace remaining after loads operation
			for k in data_list[i].keys():
				#print(data_list[i][k] + "-: before strip op")
				data_list[i][k] = data_list[i][k].strip()
				#print(data_list[i][k] + "-: after strip op")


			#assign name : DONE ALREADY by User
			if not data_list[i]['name']:
				data_list[i]['name'] = 'DEFAULT_DATA_NAME'
				#TODO:@defaulting if data name is not specified give nonsense name

			#assign field : DONE ALREADY by db
			#assign dependiencies : DONE ALREADY by User
			if 'yes' not in data_list[i]['dependencies'] and 'no' not in data_list[i]['dependencies']:
				data_list[i]['dependencies'] = 'no'
				#TODO:@defaulting if dependencies are not specified they default to no

			#assign validator
			def get_validator_name(self, validator):
				validator = validator.strip()

				validator_list = self.dataset.findall('validator')
				validator_list = [i.get('name') for i in validator_list] + ['MEMO', 'INTEGER', 'VARCHAR'] #TODO: @modify. Here, we add default validators. MEMO, INTEGER, and VARCHAR

				#print(validator)
				#print(str(validator_list))

				if validator in validator_list:
					i = validator_list.index(validator) 
					return validator_list[i]
				else:
					#TODO:@defaulting if validators left unspecified. assigned nonsense name
					return 'DEFAULT_VALIDATOR'

			data_list[i]['validator'] = get_validator_name(self, data_list[i]['validator'])


			#assign editable
			data_list[i]['editable'] = 'true' #TODO: @assumptions we assume all data are editable. please change that here. 


			#assign ui
			def get_ui(self, ui):
				if 'Format' in ui:
					return 'com.wtp.jforms.ui.control.smart.FormatTextFieldBox'
				elif 'Memo' in ui:
					return 'com.wtp.jforms.ui.control.smart.MemoFieldBox'
				elif 'Text' in ui:
					return 'com.wtp.jforms.ui.control.smart.TextFieldBox'
				else:
					return 'com.wtp.jforms.ui.control.smart.TextFieldBox'
					#TODO:@defaulting if no ui is specified. defaulting to textfield box

			data_list[i]['ui'] = get_ui(self, data_list[i]['ui'])

			#assign classid
			self.classid = 1+ self.classid
			data_list[i]['classid'] = str(self.classid)

			#assign template
			data_list[i]['template'] = 'na' #TODO: @assumptions we are not using templates

		self.make_data(data_list)

	def extract_dependencies(self, dep_list):
		dep_list = [json.loads(i) for i in dep_list]
		
		for d in dep_list:
			#print("This is a dep. "+str(d)) # for debugging print out the current dependency	

			for k in d: #strip the whitespace from the dep fields. 
				d[k] = d[k].strip()

			dep_dict = {}
			dep_dict['name'] = d['name']
			dep_dict['parent'] = self.extract_dep_parent(d)
			self.make_dependency(dep_dict)

	def extract_dep_parent(self, dep):
		parent_dict = {}
		parent_dict['field'] = dep['parent']
		enables = self.extract_enable_values(dep['enable_values'])
		parent_dict['lowerbound'] = enables['lowerbound']
		parent_dict['upperbound'] = enables['upperbound']
		parent_dict['enable_values'] = enables['valid_values']

		return parent_dict

	def extract_enable_values(self, enable_string_raw):
	#custom validators should be in the form name:range validVal validVal ...
		#first split on : to separate name 
	#second split on spaces to separate the ranges and valid values

		enable_dict = {}

		#getting the name
		enable = [i.strip() for i in enable_string_raw.split(':')]
		if len(enable) == 2: # there is a name
			enable_dict['name'] = enable[0]
			enable = enable[1]
		elif len(enable) == 1: # did not split, and there is no name
			enable_dict['name'] = ('_').join(enable[0].split(" "))
			enable = enable[0]

		enable = enable.split(" ") 
		#getting range if any
		if '-' in enable[0]: 
			enable_dict['lowerbound'] = enable[0].split('-')[0]
			enable_dict['upperbound'] = enable[0].split('-')[1]
			enable.pop(0)
		else: #if there is no range, specify arbitrary values
			enable_dict['lowerbound'] = '214783647'
			enable_dict['upperbound'] = '214783647'

		enable_dict['valid_values'] = enable # the rest of the array is valid values, which are passed in an array
		return enable_dict

##############################

#	CREATORS
#		builds individual tags for the xml tree

#		MAKES CALL CREATES IN THE CORRECT WAY. 
##############################
	def make_validator(self, args):
		self.dataset.append(self.create_validator(args))

	def make_key(self, args):
		self.dataset.append(self.create_key(args))

	def make_data(self, data_list):
		# print(data_list)
		for i in data_list:
			self.dataset.append(self.create_data(i))

	def make_dependency(self, args):
		self.dataset.append(self.create_dependency(args))
	
##############################
	#args is a dictionary with key, specified in the thing. 
	
	def create_validator(self, args):
		validator = ET.Element("validator", {'name': args[ 'name' ], 'type': args[ 'type' ],'defaultvalue':'9998', 'allowblanks': args[ 'allowblanks' ], 'lowerbound':args[ 'lowerbound' ], 'upperbound': args[ 'upperbound' ]})
		for value in args['valid_values']:
			self.add_valid_values(value, validator)
		return validator

	def add_valid_values(self, value, validator):
		ET.SubElement(validator, "valid", {'value':value})

#args has name, and a filename
	def create_dataset(self, args):
		dataset = ET.Element("dataset", {'name':args['name'],'abrv':args['abrv'],'filename':args['filename']})
		return dataset
#args has name, fiels
	def create_key(self, args):
		key = ET.Element("key", {'name': args[ 'name' ], 'field': args[ 'field' ],'template':'na', 'validator': args[ 'validator' ], 'ui':args[ 'ui' ], 'value':""})
		return key

	def create_data(self, args): #TODO: @futureproof 2 ways of making classids. start at 111... and randomization w/error checking. check if classids have to match forms.  
		data = ET.Element("data", {'name': args[ 'name' ], 'field': args[ 'field' ],'template':'na', 'validator': args[ 'validator' ], 'dependencies':args[ 'dependencies' ], 'editable':args[ 'editable' ], 'ui':args[ 'ui' ], 'classid':args[ 'classid' ]})
		return data

	def create_dependency(self, args):
		dependency = ET.Element("dependency", {'field':args[ 'name' ]})
		print(str(args))
		self.add_parent_tag(dependency, args['parent'])
		return dependency

	#parent_attr should be a dictionary with all arttributes + values key that holds an array of enable values
	def add_parent_tag(self, dependency, parent_attr):
		print(str(parent_attr))
		parent = ET.SubElement(dependency, "parent", {'field':parent_attr['field'],'lowerbound':parent_attr['lowerbound'],'upperbound': parent_attr['upperbound']})
		for x in parent_attr['enable_values']:
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


class DatasetOutputCommand (sublime_plugin.TextCommand):
	def run(self, edit, body, filename):
		print("entering dataset output")
		# dataset = args['dataset']
		
		dataset_file = sublime.active_window().new_file()
		print(str(body))
		dataset_file.set_name(filename + ".xml")
		dataset_file.set_scratch(False)
		dataset_file.set_syntax_file("Packages/XML/XML.tmLanguage")

		dataset_file.insert(edit, 0, str(body))
		print('writing to the file dataset')
		

