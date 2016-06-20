'''
	this file contains all the sublime commands to create and modify (not yet)
	jform xmls. 

	this includes (for you to care about) 
	dataset_maker and form_maker
'''

import sublime, sublime_plugin
from xml.dom import minidom as dom
from xml.etree import ElementTree as ET
import sys
# required that pypyodbc is in sublime packages path
# we use it to grab from the database
sys.path.append(sublime.packages_path())
import pypyodbc as db

class NewDatasetCreatorCommand(sublime_plugin.WindowCommand):
	''' this class is to allow the user to run 
		the dataset creator. which will prompt you
		to select a table and populate a dataset template for you.
		you can then set up the template as you wish and close it. 
		which will trigger the creation of a dataset XML document
	'''
	# preset key definitions
	presetkeys = [
		{	"name":"Family Id",
			"field":"familyid",
			"validator":"VARCHAR",
			"ui":"com.wtp.jforms.ui.control.selection.FamilyId"
			},
		{	"name":"Twin",
			"field":"twin",
			"validator":"INTEGER",
			"ui":"com.wtp.jforms.ui.control.selection.RadioSelector"
			},
		{	"name":"Data Mode",
			"field":"datamode",
			"validator":"VARCHAR",
			"ui":"com.wtp.jforms.ui.control.selection.RadioSelector"
		}
	]
	# preset validator definitions
	presetvalidators = [
		{	"name":"val01_9998_9999",
			"type":"INTEGER",
			"allowblanks":"false",
			"lowerbound":"0",
			"upperbound":"1",
			"valid_values":["9999","9998"]
		},
		{	"name":"blankformat",
			"type":"VARCHAR",
			"allowblanks":"true",
			"lowerbound":"2147483647",
			"upperbound":"2147483647",
			"valid_values":["9999","9998"]
			},
		{	"name":"val13_9998_9999",
			"type":"INTEGER",
			"allowblanks":"false",
			"lowerbound":"1",
			"upperbound":"3",
			"valid_values":["9998","9999"]
			}
	]

	def run(self):
		''' the main entry point for this command'''
		# get the table name from the user
		self.con = db.connect(db_con_string)
		cur = self.con.cursor()
		cur.tables()
		self.tables = [t[2] for t in cur]
		cur.close()
		self.prompt_input_panel(self.afterpromptingtablname,
			'table name?')

	def afterpromptingtablename(self, tablename):
		if tablename not in self.tables: # if tablename isn't recognised 
			self.run()
			return
		self.build_template(tablname) # builds the template string 
		# and writes it to a new file 


	def prompt_input_panel(self, on_done, title,
		initial_text='' ):
		''' opens input panel 
			i.e. the text box along the bottom of the screen
			it has a title, and some initial text. 
			this is not a blocking function. so when it closes
			it will jump to on_done 
			'''
		def on_change(string): pass
		def on_cancel(): print('Plugin Canceled')
		self.window.show_input_panel(title, initial_text, 
			on_done, on_change, on_cancel)

	def build_template(self, tablename):
		''' builds a template based on the table selected
			then writes the template to a new file. allowing the user 
			to set it up. upon closing a different sublime commmand will
			create the actual xml dataset'''
		cur = self.con.cursor()
		cur.primaryKeys(tablname)
		keys = [k[3].lower() for k in cur] # get the primary keys for this table
		
		cur.execute('SELECT * FROM %s'%tablename) # get the table
		col_descs = cur.description
		col_names = [c[0] for c in col_descs]
		
		# define the template text
		division = '''\n# ------------------\n'''
		admin_header = [
			'''# What will the dataset be called?''', 
			'''# The filename will be a form_name_phase concatenated''',
			'''~ form name:''',
			'''~ phase:''',
			'''~ tablename:%s'''%tablname
			'''#''',
		]
		validator_header = [
			'''# Here define custom validators you would like to use''',
			'''# syntax -> name : range validValue1 validValue2 ... ''',
			'''# Assumptions are thus:''',
			'''#	allowblanks = false''',
			'''#	default value = 9998''',
			'''#	accepted values + 9998 + 9999''',
			'''#	type = INTEGER''',
			'''# you may also use VARCHAR, MEMO, INTEGER, or date''',
		]
		key_header = [
			'''# here is where keys are defined, they should''' ,
			'''# be populated correctly already, but in case they are''', 
			'''# not you can modify them here''',
		]
		data_header = [
			'''# this section will be autopopulated with one''', 
			'''# dictionary per row. use the autofill to fill it out''',
			'''# I suggest doing it right to left to keep justification''',
		]
		dependency_header = [
			'''# this area is kept up to date automatically as you''',
			'''# modify the data section''',
		]
		
		# add custom template text for this particular tablename
		# admin doesn't need anythin
		# add a custom validator as an example
		validator_header.append('# yesno: 0 1')
		# fill in keys
		for k in self.keypresets:
			keystr = k
			if k not in keys: 
				keystr = '# ' + keystr 
				# comment ones we don't think will be used  
			key_header.append(keystr)

		# fill in data
		for c in col_names:
			datastr = '{'
			data_keys = ['dependencies', 'ui', 'validator', 'name']
			for data_key in data_keys:
				datastr += '"%s":" "'%data_key
			datastr += '}'
			data_header.append(datastr)

		template_str = '!-ADMIN-%s\n!~ADMIN~'%'\n'.join(admin_header)
		template_str += division
		template_str += '!-VALIDATORS-%s\n!~VALIDATORS~'


