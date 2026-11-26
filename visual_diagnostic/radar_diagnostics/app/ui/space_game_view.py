from nicegui import ui

class SpaceGameView:
    def __init__(self):
        self.container = None

    def build(self):
        with ui.column().classes("w-full h-full p-0 m-0 no-wrap").style("flex: 1 1 100%; min-height: 85vh; overflow: hidden;") as self.container:
            ui.element('iframe').props('src="/game/index.html"').classes('w-full h-full').style('border: none; min-height: 85vh; flex: 1;')

    def refresh(self):
        pass
