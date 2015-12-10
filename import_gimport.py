
import imp
import sys
import urllib2

def from_github(url='https://github.com/scottidler/gimport/raw/master/gimport.py'):
    name = 'gimport'
    response = urllib2.urlopen(url)
    module = imp.new_module(name)
    exec response.read() in module.__dict__
    sys.modules[name] = module
    return module
