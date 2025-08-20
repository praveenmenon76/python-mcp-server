class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register_tool(self, name, tool=None):
        if name in self.tools:
            raise ValueError(f"Tool '{name}' is already registered.")
        # Store optional tool metadata/object if provided
        self.tools[name] = tool

    def unregister_tool(self, name):
        self.tools.pop(name, None)

    def get_registered_tools(self):
        return list(self.tools.keys())

    def get_tool(self, name):
        return self.tools.get(name, None)
