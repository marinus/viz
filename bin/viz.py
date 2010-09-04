"""
VIZ for Splunk by Marinus van Aswegen (mvanaswegen AT gmail.com) v0.1 

Creates a graph based on the relationship between two fields i.e. sourch, destination, protocol.
It builds a graphviz dot file, which is then passed to graphviz for rendering.
  
BE WARNED no precations have been taken to prevent bad things from happening i.e. overwriting of sensitive files, etc
  
Usage

*  | viz field1=x field2=y [lable=z] file=name [engine=dot|neato|twopi|circo|...] [seq=true|false] [flatten=true|false] [graphviz options]
  
  field1, field2 indicate the primary graphing nodes
  label indicates the relationship, can be blank
  file specifies where to write the graph to
  engine allows you to select the graphviz rendering engine, defaults to dot if left blank
  flatten will perform a unique on relationships between nodes, default false
  seq will add a nr to each label as the data is parsed by splunk, useful to follow a seqence of events
  you can add graphviz command directly on the search line i.e. rankdir=RL
  
 Examples
 
 * | viz fiel1=from fiels2=to label=subject file=/tmp/maillog.png engine=circo seq=true ranksep=1.0
 
 * | viz fiel1=ip1 fiels2=ip2 label=protocol file=/tmp/network.png flatten=true 
 
 feedbak appreciated
  

Copyright 2010 Marinus van Aswegen. All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are
permitted provided that the following conditions are met:

   1. Redistributions of source code must retain the above copyright notice, this list of
      conditions and the following disclaimer.

   2. Redistributions in binary form must reproduce the above copyright notice, this list
      of conditions and the following disclaimer in the documentation and/or other materials
      provided with the distribution.

THIS SOFTWARE IS PROVIDED BY MARINUS VAN ASWEGEN ``AS IS'' AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL MARINUS VAN ASWEGEN OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The views and conclusions contained in the software and documentation are those of the
authors and should not be interpreted as representing official policies, either expressed
or implied, of Marinus van Aswegen.

"""

import splunk.Intersplunk
import sys
import math
import os
import tempfile

DEBUG = False # write debug info out

def create_gv_header(fh, options):
	
	if DEBUG:
		open('/tmp/debug.txt','a').write('options=%s\n' % options)		
	
	if engine in ['dot','twopi','circo']:
		fh.write('digraph splunk {\n')
	else:
		fh.write('graph splunk {\n')
	
	for option in options:
		fh.write('\t%s="%s";\n' % (option, options[option]))

def create_gv_footer(fh):
	name = fh.name
	fh.write('}\n')
	fh.close()
	if DEBUG:
		open('/tmp/debug.txt','a').write('file=%s\n' % name)
		
	return name

def fix_name(name):
	return 'X' + name.replace(' ','_').replace('.','_').replace('<','_').replace('>','_').replace('-','_')
	
def add_node(fh, node):
	fh.write('\t%s[label="%s"];\n' % (fix_name(node), node))
	
def link_node(fh, node1, node2, label):
	
	if engine in ['dot','twopi','circo']:
		link = '->'
	else:
		link = '--'
		
	if label:
		l = '[ label = "%s" ]' % label
	else:
		l = ''

	fh.write('\t%s %s %s %s;\n' % (fix_name(node1),link,fix_name(node2), l))
		
def render(fname, output):
	rc = os.system('%s -Tpng %s -o %s' % (gv, fname, output))
	if rc != 0:
		splunk.Intersplunk.generateErrorResults("error generating image, rc=%s" % rc)
		exit(0)


try:   
	keywords,options = splunk.Intersplunk.getKeywordsAndOptions()
		
	if DEBUG:
		open('/tmp/debug.txt','a').write('keywords=%s,options=%s\n' % (keywords,options))

	# patse the params
	if not options.has_key('field1'):
		splunk.Intersplunk.generateErrorResults("field1 not specified")
		exit(0)

	if not options.has_key('field2'):
		splunk.Intersplunk.generateErrorResults("field2 not specified")
		exit(0)

	if not options.has_key('file'):
		splunk.Intersplunk.generateErrorResults("file not specified")
		exit(0)

	field1 = options.get('field1', None)
	field2 = options.get('field2', None)
	label = options.get('label', None)
	fname = options.get('file', None)
	flatten = options.get('flatten', '')
	if 'true' in flatten.lower():
		flatten = True
	else:
		flatten = False
		
	seq = options.get('seq','')
	if 'true' in seq.lower():
		seq = True
	else:
		seq = False
		
	engine = options.get('engine', 'dot')
	if engine.lower() not in ['dot','neato','fdp','twopi','sfdp','circo']:
		splunk.Intersplunk.generateErrorResults("engine not specified, must be dot, neato, fdp, twopi, sfdp or circo")
		exit(0)
	else:
		gv = '/usr/bin/' + engine

	# get gv options
	g_options = {}
	for key in options.keys():
		if key.lower() not in ['field1','field2','label','file','flatten','seq', 'engine']:
			g_options[key] = options[key]

	# create a temp file
	f = tempfile.NamedTemporaryFile(delete=False)
	create_gv_header(f, g_options)
	
	# get the previous search results
	results,unused1,unused2 = splunk.Intersplunk.getOrganizedResults()

	nodes = {}
	links = []

	count = 0
	lines = 0
	# parse the results
	for result in results:
		nodes[result[field1]] = True
		nodes[result[field2]] = True
		
		if not flatten:
		
			if seq:
				links.append((result[field1],result[field2],"(%d) %s " %(count,result.get(label,''))))
				count += 1
			else:
				links.append((result[field1],result[field2],result.get(label,'')))
		else:
			if (result[field1],result[field2],result.get(label,'')) not in links:
				links.append((result[field1],result[field2],result.get(label,'')))
		lines += 1
			
	
	for key in nodes:
		add_node(f, key)
		        
	for (f1,f2,l) in links:
		link_node(f, f1,f2,l)

	# zero results
	results = []

	# output results
	splunk.Intersplunk.outputResults(results)
	
	tfname = create_gv_footer(f)
	render(tfname, fname)

except Exception, e:
	results = splunk.Intersplunk.generateErrorResults(str(e))


