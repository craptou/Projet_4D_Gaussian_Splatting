"""Force the pinned renderer's undeformed 3D branch for a static-scene control."""


def instrument_static_render(text):
    anchor='from gaussian_renderer import render, network_gui'
    if text.count(anchor)!=1:raise ValueError('Pinned renderer import differs; refusing static instrumentation')
    replacement='''from gaussian_renderer import render as upstream_render, network_gui
def render(*args, **kwargs):
    kwargs['stage'] = 'coarse'
    return upstream_render(*args, **kwargs)
'''
    return text.replace(anchor,replacement)
