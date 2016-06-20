import sublime, sublime_plugin
import os, os.path
import pypyodbc as db
import json
from xml.dom import minidom as dom
from xml.etree import ElementTree as ET


######################################################
#########
#########	By. Russell Little, Cherub Kumar
#########	Sept 2014
#########	This command will create a form
#########		The information it needs is. what to name itself
#########		And which datasets to include. Everything else will be generated from 
#########		the dataset, which is assumed to be correct. No error checking
#########		It will check to make sure that all the keys are correct
#########
#########			Organization
#########			1. run - gets the filenames of datastes and calls the ds input panel
#########			2. post_list - decodes the files into dicts. checks they all have the same keys. if not prompts you to correct them and goes back to post_list. otherwise: goes on to prompt for name
#########			3. post_name_prompt - calls make_form
#########			4. make_form - main creating repo. declares root "form" and populates it with all the stuff.
#########			5. set_output - creates the file
#########			6. category - calls category_prompt, which prompts you to decide where the form should go
#########			7. finalize - adds datasets to datsets.xml if they aren't already there. and categories to categories.xml at the correct location  
#########
#########		Uses the make and create helper functions to create the tags and attributes
######################################################

class FormMakerCommand(sublime_plugin.WindowCommand):
	 
			#this will. 
			#1. ask you for any files you want to include as datasets
			#2. ask you for a name to call the file and show on the form
			#2. extract the fields from the datasets
			#3. make a new file
			#4. draw the form
	def run(self):
	
	#container for preset information
		self.presets={"keys":{"Family Id":{"name":"Family Id","class":"com.wtp.jforms.ui.control.selection.FamilyId","options":"MySQL:mysql.waisman.wisc.edu/wtp_data,GEN_FAMILY,familyid"},"Data Mode":{"name":"Data Mode","class":"com.wtp.jforms.ui.control.selection.RadioSelector","options":"Data Mode,Entry:Entry,Check:Check"},"Twin":{"name":"Twin","class":"com.wtp.jforms.ui.control.selection.RadioSelector","options":"Twin,A:1,B:2"}}}

		self.datasets_dir = 'T:/Source Code/jforms/jforms-workspace/build/dataset'

		self.selected_dataset_files = [] 	# container for .xml filenames of datasets you want to use
		self.filenames = []					# container for .xml filenames available in datasets_dir
		self.filenames.append('quit!') #adds a quit option
		self.filenames.append('remove!') # adds a remove option, in case of mistakes

		
		#DEFAULT FOR TESTING. Comment from here  VVVVVVVVVV

			# Gets filenames from computer and asks which you would like
		walk_result = os.walk(self.datasets_dir)
		print('running')
		self.filenames.extend( [files for root, dirs, files in walk_result][0])
		self.show_list('add') # prompts you for datasets you want to include
		
		#DEFAULT FOR TESTING. comment to HERE    ^^^^^^^^^^ uncomment following two lines
		
		# print(str(self.filenames))		#debuging print
		
		# self.selected_dataset_files.append('bb.xml') #these twi have different keys. 
		# # self.selected_dataset_files.append('mrTwQuestPanas_Gen.xml')
		# self.post_list()





	def post_list(self):
		#Enters here after datasets to include are selected. 
	#	print('entering post_list')
		keys = []
		self.datasets = []
		self.tablenames = []
		#extracting datasets to xml. storing them in self.selected_dataset_files
		for ds in self.selected_dataset_files:
			#print(ds)
			i = self.selected_dataset_files.index(ds)
			ds = ET.parse("%s/%s" % (self.datasets_dir, str(ds)))
			ds = ds.getroot()
			self.datasets.append(ds) # add the etree root to datasets
			self.tablenames.append(ds.get('abrv'))
			#print('%s extracted to etree' % ds.get('name'))
			
			cur_keys = [i.get('name') for i in ds.findall('key')]
			#print(cur_keys)
			
			if len(keys) == 0: #
				#print('Checking keys')
				keys = cur_keys	
			
			for k in keys:
				if k not in cur_keys or len(cur_keys) != len(keys) :
					print('keys do not all match. dataset %s does not match previous ones' % ds.get('filename'))
					self.show_list('add')
					return 						# END EVERYTHING. Go back to the list so they can correct their mistake. 


				#Print each dataset selected fro debugging purposes
			# print(self.to_pretty_print(ds)) #TODO: @debug printing all datasets selected

		if(len(self.selected_dataset_files) > 1):
			self.window.show_input_panel('Form Name','', self.post_name_prompt,None,None)
		else:
			ds = self.selected_dataset_files[0]
			ds = ET.parse("%s/%s" % (self.datasets_dir, str(ds)))
			ds = ds.getroot()
			self.build_form({'name':ds.get('name'), 'filename':ds.get('filename')})

	def post_name_prompt(self, name):
		self.build_form({'name':name.strip()}) #remove any extra whitespace put in

	def build_form(self, name):
		if('filename' not in name.keys()):
			name_safe = '_'.join(name['name'].split(' '))
			self.form = self.make_form({'name':name['name'], 'abrv':name['name'], 'filename':name_safe})
		else:
			self.form = self.make_form({'name':name['name'], 'abrv':name['name'], 'filename':name['filename']})

		# adding datasets
		for ds in self.datasets:
			ds_dict = {}
			ds_dict['file'] = ds.get('filename')
			print(str(ds.attrib))
			ds_dict['connection'] = 'MySQL:mysql.waisman.wisc.edu/wtp_data'
			ds_dict['tablename'] = self.tablenames[self.datasets.index(ds)]

			self.make_dataset(ds_dict)



			#all datasets should have the same keys, so, get a list from the first ds of all keys

		# building the key dict. needs name class options entryset filename 
		#--------------#--------------#--------------#--------------
		tmp_ds = self.datasets[0] # using arbitrary dataset to fill in extraneous fields reuired by jforms
		for k in tmp_ds.findall('key'):
			key_dict = self.presets['keys'][k.get('name')] #includes name class 
			key_dict['entryset'] = tmp_ds.get('name') #TODO: @assumptions setting the entryset of key to the first dataset
			key_dict['filename'] = 'build\dataset\%s.xml' % tmp_ds.get('filename') 

			self.make_key(key_dict) #make the keys

		classid = 1234567890123

		# building the component sets
		#needs name abrv, header and list of datafields
		#---------------------------------------
		for ds in self.datasets: #TODO: @assumptions component set name.header,abrv come from the name of the dataset
			componentset_dict = {}
			componentset_dict['name'] = ds.get('name')
			componentset_dict['abrv'] = ds.get('name')
			componentset_dict['header'] = ds.get('name')

			componentset = self.make_componentset(componentset_dict)

			#building the datafields
			# needs name entryset filename class classid options
			for dt in ds.findall('data'): #TODO: @assumptions datafield name come from data name
				datafield_dict = {}
				datafield_dict['name'] = dt.get('name')
				datafield_dict['entryset'] =ds.get('name') #taking the entryset from the dataset file 
				datafield_dict['filename'] = 'build\dataset\%s.xml' % ds.get('filename')
				datafield_dict['class'] = dt.get('ui')
				
				classid = classid + 1
				
				datafield_dict['classid'] = str(classid)


				if 'blankformat' in dt.get('validator'):
					datafield_dict['options'] = '0,MM/dd/yyyy' #TODO: @assumptions only blankformat datafields get options. else options = ''
				else:
					datafield_dict['options'] = ''

				self.make_datafield(componentset, datafield_dict)

# 				inster this:
# 				
#	 			
		prettyxml = self.to_pretty_print(self.form)
		
		#ad encoding information
		prettyxml = [
		'<?xml version="1.0" encoding="UTF-8"?>',
		'<!DOCTYPE form SYSTEM "../../dtd/form.dtd">',
		prettyxml
		]
		prettyxml = '\n'.join(prettyxml)

		print(prettyxml)
		self.window.run_command('dataset_output',{'body':prettyxml, 'filename': self.form.attrib['filename']})


		

##########################################################
#
#		Quick List displaying datasets
#			Organization
#			enter this block with show_list('add' or 'remove')
# 				that will show the list of either the filenames to add
# 				or, the already selected files, to be removed
# 			when the an item is selected. on_close or remove_file_on_close is called is called
# 			if a file is removed it will just bring you back to add another
# 			select quit! to quit
# 			select remove! to remove a ds
# 				if you didn't want to remove a ds select oops! 
#			
#			returns to post_lsit
#########################################################
		
		#ENTRY POINT
	def show_list(self, type_of_list):
		#TODO: display number of selected datasets in status bar
		print('in show_list')
		if 'add' in type_of_list:
		#	print('about to show list of files to add')
			print('about to be showing adding list.')
			self.show_quick_panel(self.filenames, self.on_list_close)
		else:
			#print('about to be showing remove list')
			print('about to show list of files to remove')
			self.show_quick_panel(self.selected_dataset_files, self.remove_ds_on_close)
	
		#this function starts up the quick panel in a threadsafe way
	def show_quick_panel(self, options, on_close):
		#print('showing quick panel')
		#print(str(options))
		#print(str(on_close))
		print('showing quick panel')
		sublime.set_timeout(lambda: self.window.show_quick_panel(options, on_close), 10)


	def remove_ds_on_close(self, index_of_choice):
		if index_of_choice != self.selected_dataset_files.index('oops!'): 
			#allows you to go back without removing anything
			self.selected_dataset_files.pop(self.selected_dataset_files.index('oops!')) # be sure to reove oops!
			ds = self.selected_dataset_files.pop(index_of_choice)
			self.filenames.append(ds)
			print('removed %s' %str(ds))
		else:
			ds = self.selected_dataset_files.pop(index_of_choice) 
		self.show_list('add')


		#EXIT
	def on_list_close(self, index_of_choice):
		if index_of_choice == self.filenames.index('quit!'):
			#if index of choice index of 'quit!' then quit.
			self.post_list() # EXIT 
		elif index_of_choice == self.filenames.index('remove!'):
			self.selected_dataset_files.append('oops!')
			self.show_list('remove')
			#if you would like to remove a file from selected dataset
		elif index_of_choice == -1:
			return
		else:
			#remove index from list and 
			ds = self.filenames.pop(index_of_choice)
			print("selected %s" %str(ds))
			self.selected_dataset_files.append(ds)
			self.show_list('add')


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



##############################

#	MAKERS
#	builds xml tags
	# High level
	#pass them a dict of attributes and they will append it to root
	#with the exception of datafields, which will append to passed component set 

##############################
	#needs name, abrv, filename
	def make_form(self, args):
		form = self.create_form(args)
		return form

	#needs attribs file, tablename
	#automates connection
	# e.g. {'file': 'f', 'tablename':'tbl'}
	def make_dataset(self, args):
		self.form.append(self.create_dataset(args))

	#needs attribs name entryset filename class options
	#e.g. {'name': 'n', 'entryset': 'es', 'filename': 'pathToXMLFile', 'class}
	def make_key(self, args):
		self.form.append(self.create_key(args))

	#needs a list of datafields, name, 
	#e.g. {'name':'n','datafields': [df1, df2, ...]}
	#automates 
	def make_componentset(self, args):
		componentset = self.create_component_set(args)
		self.form.append(componentset)
		return componentset

	#needs name, entryset, 
	def make_datafield(self, component_set, args):
		component_set.append(self.create_datafield(args))



##############################
# 	CREATORS
	#Lower Level	
##############################
	def create_form(self, args):
		form = ET.Element("form", {'name':args['name'], 'abrv':args['abrv'], 'filename':args['filename']})
		return form


	#needs name, tablename 
	#TODO: @assumptions uses mySQL connection for datasets
	def create_dataset(self, args):
		dataset = ET.Element("dataset", {'file':args['file'],'connection':args['connection'],'tablename':args['tablename']})
		return dataset

	#needs name, entryset, filename, class options
	def create_key(self, args):
		key = ET.Element("key", {'name': args[ 'name' ], 'entryset':args['entryset'], 'filename': args[ 'filename' ],'class':args[ 'class' ], 'options':args['options']})
		return key

	#requires name, abrv, header, list of datafields. if there are no datafields. it just leaves them out
	#TODO: @assumptions component setsdisplayheader = true numcols = 2
	def create_component_set(self, args):
		component_set = ET.Element("componentset", {'name':args['name'], 'abrv': args['abrv'], 'numcols': '2', 'displayheader':'true', 'header':args['header']})
		if 'datafields' in args.keys():
			for df in args[ 'datafields' ]:
				component_set.append(self.create_datafield(df))
		return component_set

	#needs name entryset filename class classid options
	#TODO: @assumptions datafields editable = true type = 0   
	def create_datafield(self, args):
		datafield = ET.Element("datafield", {'name':args['name'], 'entryset':args['entryset'], 'filename':args['filename'], 'type':'0', 'class':args['class'], 'editable':'true', 'classid':args['classid'], 'options':args['options']})
		return datafield

	