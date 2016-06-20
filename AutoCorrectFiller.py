import sublime, sublime_plugin
import json

def view_contents(view):
    region = sublime.Region(0, view.size())
    return view.substr(region)

class TemplateEventListener(sublime_plugin.EventListener):
	
#############################################################################
#     			Snap to data
#############################################################################
	def on_selection_modified_async(self, view):
		#return ASAP if this is called within the wrong file. 
		#print(len(view.sel()))
		try:
		
			print('within Dataset_Template, this is on_modified starting scope: %s'%view.scope_name(view.sel()[0].begin()))
		#assuming we are modifying the correct file with the correct scope
		#and we are selecting the attribute anywhere other than value
			#then snap to the value section. 
		
			# New Plan. 
			# We can grab all the regions using one command. 
			# so. grab all regions of attribute, find the ones that intersect
			# with the cur selection.
			# then. snap to the value section of that. 

			# So, we'll need to remember the regions of attributes
			# as well as the regions of values 
			#datalist ispresent in all the datalists and nowhere else
			if 'datalist' in view.scope_name(view.sel()[0].begin()):
				cur_selection = view.sel()[0]
				cur_attribute_value_region = self.intersecting_attribute_but_not_value(view, cur_selection)
				if cur_attribute_value_region != -1:
					# #print('reseting selection -----------------------------------------------')
					view.sel().clear()
					view.sel().add(cur_attribute_value_region.begin())
			elif 'dependencies' in view.scope_name(view.sel()[0].begin()):
					self.fill_dependencies_section(view)
			else:
				return

		except IndexError:
			#print('IndexError Caught')
			return

	def fill_dependencies_section(self, view):
		# What this has to do is scan the datalist for dependencies and the dependencies section. take the correct action. and populate the section 
		dependent_data = self.scan_datalist(view)
		#print(str(dependent_data))
		self.populate_dependency_section(view, dependent_data)

	def scan_datalist(self, view):
		#searches the datalist to find lines with "yes" in dependencies. 
			#grabs the datalist section
		datalist_regions = view.find_by_selector("section.datalist")[0]
		datalist_regions = view.lines(datalist_regions)
		datalist_lines = [view.substr(r) for r in datalist_regions] #a list of strings. each a line from datlist
		datalist = [r for r in datalist_lines if not (r.strip().startswith('#') or r.strip().startswith('!') ) and r and not r.isspace()] #r returns the string portion
			#parses list of lines into list of json dicts
		dependent_data = [json.loads(r) for r in datalist]
		for r in dependent_data:
			for k in r:
				r[k] = r[k].strip()

		return [x for x in dependent_data if 'yes' in x['dependencies']]
		
	def populate_dependency_section(self, view, dependent_data):
		print('------------------ ENTERING THE POPULATE SECTION ------------------')
		# what this does is gets a list of existing entries in the dependencies section. It compares them with the entries from the datalist that have a yes in dependencies
		# If it finds an extra one. it will comment it. if it finds missing ones. it will prompt you for them. 
		dep_list = view.find_by_selector("section.dependencies")[0]
		dep_list_regions = view.lines(dep_list)
		dep_list_lines = [view.substr(r) for r in dep_list_regions]
		dep_list = zip(dep_list_lines, dep_list_regions)
		dep_list = [r for r in dep_list if not (r[0].strip().startswith('!')) and r[0] and not r[0].isspace()]
		dep_list_regions = [r[1] for r in dep_list]
		dep_list_lines = [r[0].strip() for r in dep_list]

		dep_list = []
		for i in range(len(dep_list_lines)):
			is_commented = dep_list_lines[i].startswith('#') 
			if(is_commented):
				s = dep_list_lines[i]
				dep_list_lines[i] = s[s.find('{'):len(s)]
			dep_list.append(json.loads(dep_list_lines[i]))
			dep_list[i]['is_commented'] = is_commented
			dep_list[i]['range'] = dep_list_regions[i]

		for r in dep_list:
			for k in r:
				if('range' not in k and 'is_commented' not in k):
					r[k] = r[k].strip()
			r['begin'] = r['range'].a
			r['end'] = r['range'].b


		#now dep_list is a dictionary containgin dependencies. as well as the region of the line and weather it's commented or not.

		entries_in_deplist_not_datalist = [r for r in dep_list if r['name'] not in [x['name'] for x in dependent_data] and not r['is_commented'] ]
		for r in entries_in_deplist_not_datalist:
			self.comment_line(view, r)
			print('%s in dependency list, and not in datailist. should be commented' % r['name'])

		entries_should_be_uncommented = [r for r in dep_list if (r['name'] in [x['name'] for x in dependent_data]) and (r['is_commented'])]
		for r in entries_should_be_uncommented:
			print('%s is in both deplist, and datalist, but is commented. should be uncommented' % r['name'])
			self.uncomment_line(view, r)
		
		entries_in_datalist_not_deplist = [r for r in dependent_data if r['name'] not in [x['name'] for x in dep_list]]
		for r in entries_in_datalist_not_deplist:
			print('%s is in datalist, and not dependency list. should be added' % r['name'])
			self.insert_dependency(view, r)

		# print(str(dep_list))
		return

	def uncomment_line(self, view, line):
		view.run_command('toggle_comment', {'begin': line['begin'], 'end': line['end'], 'is_commented' : True})
		return
	def comment_line(self, view, line):
		#what this has to do is insert a "#" character before line. line should be a reion
		view.run_command('toggle_comment', {'begin': line['begin'], 'end': line['end'], 'is_commented' : False})
		return


	def insert_dependency(self, view, line):
		view.run_command('insert_dependency', {'name': line['name']})
		pass


	def intersecting_attribute_but_not_value(self, view, cur_selection):
		# #print('intersecting attrib starting')
		attr_name = view.scope_name(cur_selection.begin())
		attr_name = attr_name.strip().split(' ')
		attr_name = [str(scope.split('.')[-1]) for scope in attr_name if (len(scope.split('.')) == 3)][0]
		# #print(attr_name) 
		# #print("section.data.%s.begin" %attr_name)
		list_of_nonvalue_regions = view.find_by_selector("section.data.%s.begin" %attr_name)
		list_of_nonvalue_regions.extend(view.find_by_selector("section.data.%s.equote" %attr_name))
		if attr_name != 'field':
			list_of_nonvalue_regions.extend(view.find_by_selector("section.data.%s.end" %attr_name))
		
		# #print(str(list_of_nonvalue_regions))
		for region in list_of_nonvalue_regions:
			intersection = cur_selection.intersection(region) 
			# #print(str(intersection))
			
			if intersection != sublime.Region(0,0):
				extent = view.extract_scope(intersection.begin())
				# #print(str(extent) + " " + view.scope_name(extent.begin()))
				extent.a = extent.a + len(attr_name) + 3
				# #print(str(extent) + " " + view.scope_name(extent.begin()))
				extent = view.extract_scope(extent.begin())
				return extent

		return -1






#############################################################################
#     			Auto Complete
#############################################################################
	def on_query_completions(self, view, prefix, locations):
		# cursors should have a range of zero, but there can be many of them, else, break
		#print('on_query_completions has been called')
		if self.should_trigger(view):
			return self.get_autocomplete_list(view)
		
	def get_autocomplete_list(self, view):
		scope_name = view.scope_name(view.sel()[0].begin())
		if 'field' in scope_name:
			#print('returning field list')
			return( [] , sublime.INHIBIT_WORD_COMPLETIONS )
		elif 'validator.value' in scope_name or 'validator.equote' in scope_name:
			section_content= self.get_section_content(view, 1) #1 is the index of validators
			#print('returning validator list')
			return( zip( section_content['validators'] + ['MEMO', 'VARCHAR', 'INTEGER'] , section_content['validators'] + ['MEMO', 'VARCHAR', 'INTEGER']) , sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
		elif 'dependencies' in scope_name:
			#print('returning dependencies list')
			return( zip(['yes', 'no'],['yes', 'no']) , sublime.INHIBIT_WORD_COMPLETIONS )
		elif 'ui' in scope_name:
			#print('returning ui list')
			return( zip(['Format','Memo','Text'],['Format','Memo','Text']) , sublime.INHIBIT_WORD_COMPLETIONS)
		else:
			#print('scope_name: ' + scope_name +'. Unrecognized')
			return []
			pass


	def should_trigger(self,view):
		#print('enter should_trigger')

		tmp = view.scope_name(view.sel()[0].begin())		

		for sel in view.sel(): #checking each selection in sel()
			#print('testing selection ' + str(sel))
			scope = view.scope_name(sel.begin())

			if (tmp != scope):	# Checking that each selection has the same scope_name
				#print('selection scope is not the same new: ' + scope + ', old: ' + tmp)
				return False

			if(sel.begin() - sel.end() != 0): # checking that each selection has a range of 0 
				#print('the selection range is not zero. ' + str(sel))
				return False
			
			if((not self.should_trigger_from_scope(scope))): #cheking that each selection is in a scope that shuld trigger 
				#print('selection selection_is_correct_regions not in correct region. ' + scope)
				return False
				
			tmp = scope #resets tmp

		#print('Tests Passed should_trigger returning true')
		return True

	def should_trigger_from_scope(self, scope):
		# TODO:@WIP add the rest of the scope names we want to fill in
		scope_names = [
		'field',
		'validator',
		'name',
		'ui',
		'dependencies']

		for name in scope_names:
			if name in scope:
				#print('scope: '+ scope +' matches a known scope from syntax file')
				return True
				pass
		return False

	def get_section_content(self, view, index_of_section_to_return):
		#print('entering get_section contents')
		#This method should return a dict with useful autofill information for each section.
			#step 1. break the view into sections
			#step 2. parse out useful information. 
				#NOTE: for now. the only thing that uses this is validator
					# UI uses explicit fills


		#get the contents of each section
		sections = [line for line in view_contents(view).split('\n# ------------------') ]
		#section index 0 = Dataset Name
		#section index 1 = Validators
		#section index 2 = Keys
		#section index 3 = Data List
		#section index 4 = Dependencies

		section = sections[index_of_section_to_return]

		#break into individual lines and remove comments and blank lines
		section = [line.strip() for line in section.split('\n') if not (line.strip().startswith('#') or line.strip().startswith('!') ) and line and not line.isspace()]
					#remove whitespace		#seperate into lines 		#ignore lines starting with #					!			and aren't empty

		#TODO:@WIP Add here any other special autofill code. add another elif clause
		if index_of_section_to_return == 1:
			#return validator info:
			#1. # if there is a colon, take the string before th colon. as the name
				# if no colon, take the whole string
			validator_names = [line.split(':')[0].strip() for line in section]
					# 		#returns a list of lines delimited by ':'
			#2. # if there was no colon, switch ' ' to '_'
			validator_names = [('_').join(name.split(' ')) for name in validator_names] 
				 	#		# overwrites validator_names. switching spaces to underscores
			
			return {'validators': validator_names}


class ToggleCommentCommand (sublime_plugin.TextCommand):
	def run(self, edit, begin, end, is_commented):
		if(is_commented):
			self.view.erase(edit, sublime.Region(begin, begin + 1))
			pass
		else:
			self.view.insert(edit, begin, '#')
		pass

class InsertDependencyCommand (sublime_plugin.TextCommand):
	def run(self, edit, name):
		dep_list = self.view.find_by_selector("section.dependencies")[0]
		dep_list = self.view.lines(dep_list)
		last_region = dep_list[-1]

		dep_template = '{"name": "%s", "parent": " ", "enable_values": " "}\n' % name 

		self.view.insert(edit, last_region.a, dep_template)
		pass