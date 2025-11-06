#!/usr/bin/env python3
from oxygen.oxygen import OxygenLibrary

lib = OxygenLibrary()
# call a handler keyword programmatically (args as list/tuple, kwargs as dict)
result = lib.run_keyword('my_handler_keyword', ('path/to/result.xml',), {})