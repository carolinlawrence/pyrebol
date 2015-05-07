 #!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import util
init="count(area(keyval(name,'Heidelberg')),node(keyval(name,'McDonald's')))"
init="least(area(keyval(name,'Heidelberg')),node(keyval(name,'Burger King')),topx(1))"
init="findkey(area(keyval(name,Berlin@s)),node(keyval(name,'Hot 's Spicy Food')),key(addr:street))"
print init
mrl = util.overpass_to_mrl(init)
print mrl
