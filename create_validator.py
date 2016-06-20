import sublime, sublime_plugin

from xml.dom import minidom as dom

from xml.etree import ElementTree as ET

class createValidatorCommand(sublime_plugin.TextCommand):
	def run(self, edit, args):
		
		cursor_pos = self.view.sel()[0].begin()
		
		new_validator = self.create_validator(args["name"], args["validation_type"], args["allowblanks"], args["lowerbound"], args["upperbound"], args["valid_values"])
		pretty_validator= self.to_pretty_print(new_validator)

		self.view.insert(edit, cursor_pos, pretty_validator)


	def create_validator(self, name, validation_type, allowblanks, lowerbound, upperbound, valid_values):
		validator = ET.Element("validator", {'name': name, 'type': validation_type,'defaultvalue':'9998', 'allowblanks': allowblanks, 'lowerbound':lowerbound, 'upperbound':upperbound})
		for value in valid_values:
			self.add_valid_values(value, validator)
		return validator

	def add_valid_values(self, value, root):
		ET.SubElement(root, "valid", {'value':value})


	def to_pretty_print(self,root):

		rough_string = ET.tostring(root)
		reparsed = dom.parseString(rough_string)
		
		pretty = reparsed.toprettyxml(indent="    ")
		prettyarray = pretty.split('\n')
		prettyXML = "\n".join(prettyarray[1:])
		return prettyXML
